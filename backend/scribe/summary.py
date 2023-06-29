"""Utility functions for the Scribe backend."""
import smtplib
import ssl
import os
import time
import traceback
from functools import wraps
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
import pytz
import openai
import boto3
import tiktoken
from supabase import Client
from tenacity import retry, stop_after_attempt, wait_fixed
from flask import current_app as app

# The reason we declare this on the top level is that we only have access to the app context during intialization
supabase: Client = app.extensions['supabase']
S3_BUCKET = app.config['S3_BUCKET']
SUMMARIES_FOLDER = app.config['SUMMARIES_FOLDER']


def handle_exceptions(func):
    """Catch any exceptions and put the traceback into the database."""
    @wraps(func)
    def decorated(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception:
            trace = traceback.format_exc()
            print(trace, flush=True)
            summary_id = args[0]
            supabase.table('summaries').update(
                {'status': f'Error: {trace}'}).eq('id', summary_id).execute()
    return decorated


@handle_exceptions
def send_summary(summary_id: str, user_email: str, summary_filename: str, transcript_filename: str):
    """Send summary to user."""
    print(f"Sending summary for summary_id: {summary_id}", flush=True)
    text = "Hey there, \n\nPlease find the notes from your recent conversation attached. We also included the transcript in case you want to refresh your memory.\n\nThank you for using Scribe!\n\nSincerely,\nThe Scribe Team\n\nP.S. While a powerful tool, Scribe is an early-stage project, and we live for your feedback. Please take 2 minutes to let us know what worked and what didn't, so we can make Scribe better for you. Or tweet your feedback @tryscribeai."
    subject = "Scribe Summary"
    send_mail(user_email, subject, text, [
              summary_filename, transcript_filename])
    update_time(summary_id)
    supabase.table('summaries').update(
        {'Status': "Success"}).eq('id', summary_id).execute()
    os.remove(transcript_filename)
    os.remove(summary_filename)


@handle_exceptions
def generate_summary(summary_id: int, transcript_filename: str, approval_link: str):
    """Generate a summary given a transcript."""
    print(f"Generating summary for summary_id: {summary_id}", flush=True)
    start_time = time.time()
    # Set API key, prompt, and model
    openai.api_key = os.getenv("OPENAI_API_KEY")
    prompt_summary = os.getenv("PROMPT_SUMMARY")
    prompt_chunk_summary = os.getenv("PROMPT_CHUNK_SUMMARY")
    prompt_final_summary = os.getenv("PROMPT_FINAL_SUMMARY")
    if prompt_summary is None or prompt_chunk_summary is None or prompt_final_summary is None:
        raise Exception("Prompts not set")

    model = "gpt-3.5-turbo-16k"
    enc = tiktoken.encoding_for_model(model)
    context_length = 16384
    system_messages = 20

    # Prompt length and 20 tokens for the system messages
    summary_prompt_length = len(enc.encode(
        prompt_summary)) + system_messages
    chunk_prompt_length = len(enc.encode(
        prompt_chunk_summary)) + system_messages
    final_prompt_length = len(enc.encode(
        prompt_final_summary)) + system_messages
    prompt_length = max(chunk_prompt_length,
                        final_prompt_length, summary_prompt_length)
    # Give at least 1000 tokens for the summary
    max_tokens = context_length - prompt_length - 1000
    summary = ""

    with open(transcript_filename, "r", encoding="UTF-8") as file:
        transcript = file.read()

    if transcript == "":
        raise Exception("Transcript is empty")

    num_tokens = len(enc.encode(transcript))

    # Check if the transcript can be summarized in one chunk
    if num_tokens <= max_tokens:
        # Send the transcript to the OpenAI API
        summary = get_summary(model, prompt_summary,
                              transcript)

    if num_tokens > max_tokens:
        # Split the transcript into chunks recursively
        transcript_chunks = []
        split_transcript(transcript, max_tokens, transcript_chunks, enc)
        summary_chunks = []
        # Summarize each chunk
        for chunk in transcript_chunks:
            summary_chunk = get_summary(model, prompt_chunk_summary, chunk)
            summary_chunks.append(summary_chunk)
        # Create master summary
        summary_chunks = '\n'.join(summary_chunks) + "\nMaster summary: "
        print(prompt_final_summary, flush=True)
        print(summary_chunks, flush=True)
        summary = get_summary(model, prompt_final_summary, summary_chunks)

    if summary == "":
        raise Exception("Summary is empty")

    # Save the summary to a file
    user_email = supabase.table('summaries').select("user_email").eq(
        'id', summary_id).execute().data[0]['user_email']
    summary_filename = save_summary(
        summary, SUMMARIES_FOLDER, user_email)

    # Upload the summary to S3
    s3 = boto3.client('s3')
    s3_filename = summary_filename.rsplit(
        '/', 2)[1] + '/' + summary_filename.rsplit('/', 2)[2]
    s3.upload_file(summary_filename, S3_BUCKET, s3_filename)

    # Save the summary in the database
    supabase.table('summaries').update(
        {'summary_file': s3_filename}).eq('id', summary_id).execute()

    # Send the approval email
    send_approval_email(summary_filename, transcript_filename, approval_link)

    os.remove(transcript_filename)
    os.remove(summary_filename)

    print(f"Time taken: {time.time() - start_time}", flush=True)


@retry(stop=stop_after_attempt(2), wait=wait_fixed(60))  # handle rate limiting
def get_summary(model: str, prompt: str, text: str) -> str:
    response = openai.ChatCompletion.create(
        model=model,
        messages=[{"role": "system", "content": prompt}, {
            "role": "user", "content": text}],
    )
    if response['choices'][0]['finish_reason'] == 'length':
        response = openai.ChatCompletion.create(
            model=model,
            messages=[{"role": "system", "content": prompt + " Make it short!"}, {
                "role": "user", "content": text}],
        )
    return response['choices'][0]['message']['content']


def split_transcript(transcript: str, max_tokens: int, transcript_chunks: list, enc):
    """Recursively split the transcript into chunks until they are shorter than context_length."""
    transcript_length = len(enc.encode(transcript))
    if transcript_length >= max_tokens:
        # Split the transcript in half
        middle = len(transcript) // 2
        first_half = transcript[:middle]
        second_half = transcript[middle:]
        split_transcript(first_half, max_tokens, transcript_chunks, enc)
        split_transcript(second_half, max_tokens, transcript_chunks, enc)
    else:
        transcript_chunks.append(transcript)


def update_time(summary_id: str):
    """Update sent_at and time_taken fields in the database."""
    # Fetch created_at from supabase
    created_at = supabase.table('summaries').select(
        'created_at').eq('id', summary_id).execute().data[0]['created_at']
    # Create timestampz for sent_at with timezone
    sent_at = pytz.utc.localize(datetime.utcnow())
    created_at = datetime.strptime(created_at, "%Y-%m-%dT%H:%M:%S.%f%z")
    # Calculate time taken and format in x hours, y minutes, z seconds
    time_taken = sent_at - created_at
    time_taken = time.strftime('%H hours, %M minutes, %S seconds',
                               time.gmtime(time_taken.total_seconds()))
    # Update sent_at and time_taken in supabase
    supabase.table('summaries').update(
        {'sent_at': sent_at.isoformat(), 'time_taken': time_taken}).eq('id', summary_id).execute()


def save_summary(text, directory, user_email) -> str:
    # generate current timestamp
    timestamp = int(time.time())
    date_string = datetime.fromtimestamp(
        timestamp).strftime('%Y-%m-%d_%H-%M-%S')

    filename = f'Summary_{user_email}_{date_string}.txt'

    # save transcript in the "transcripts" sub-folder
    with open(f'{directory}/{filename}', 'w', encoding="UTF-8") as f:
        # write to the file using the write method
        f.write(text)

    return f'{directory}/{filename}'


def send_approval_email(summary_filename: str, transcript_filename: str, approval_link: str):
    """Send email with summary for QA."""
    text = f'Please review the summary below and click the link to approve it.\n\n{approval_link}'
    subject = 'Generated summary for approval'
    send_mail(None, subject, text, [summary_filename, transcript_filename])


def send_mail(send_to=None, subject=None, text=None, files=None):
    """Helper send email function."""
    context = ssl.create_default_context()
    scribe_email = "tryscribeai@gmail.com"

    if os.getenv("GMAIL_PASSWORD") is None:
        raise Exception("GMAIL_PASSWORD is not set")

    scribe_password = os.getenv("GMAIL_PASSWORD")

    with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
        server.login(scribe_email, scribe_password)

        msg = MIMEMultipart()
        msg['Subject'] = subject
        msg['To'] = send_to if send_to is not None else scribe_email
        msg['From'] = "tryscribeai@gmail.com"

        for file in files or []:
            with open(file, 'rb') as fp:
                part = MIMEApplication(fp.read().decode('utf-8'))
                part.add_header('Content-Disposition',
                                'attachment', filename=os.path.basename(file))
                msg.attach(part)

        msg.attach(MIMEText(text, 'plain', 'utf-8'))
        server.send_message(msg)
