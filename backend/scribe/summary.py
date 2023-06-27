"""Utility functions for the Scribe backend."""
import smtplib
import ssl
import os
import time
import pytz
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
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


def send_summary(summary_id: str, user_email: str, summary_filename: str, transcript_filename: str):
    """Send summary to user."""
    print("Sending summary...", flush=True)
    text = "Hey there, \n\nPlease find the notes from your recent conversation attached. We also included the transcript in case you want to refresh your memory.\n\nThank you for using Scribe!\n\nSincerely,\nThe Scribe Team\n\nP.S. While a powerful tool, Scribe is an early-stage project, and we live for your feedback. Please take 2 minutes to let us know what worked and what didn't, so we can make Scribe better for you. Or tweet your feedback @tryscribeai."
    subject = "Scribe Summary"
    send_mail(user_email, subject, text, [
              summary_filename, transcript_filename])
    update_time(summary_id)
    os.remove(transcript_filename)
    os.remove(summary_filename)


def generate_summary(transcript_filename: str, summary_id: int, approval_link: str):
    print("Generating summary...", flush=True)
    # Set API key, prompt, and model
    openai.api_key = os.getenv("OPENAI_API_KEY")
    prompt_summary = os.getenv("PROMPT_SUMMARY")
    prompt_chunk_summary = os.getenv("PROMPT_CHUNK_SUMMARY")
    prompt_final_summary = os.getenv("PROMPT_FINAL_SUMMARY")

    model = "gpt-3.5-turbo-16k"
    enc = tiktoken.encoding_for_model(model)
    # full context lendth is 16384 but we need to account for the prompt and completion
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
    overflow = False
    summary = ""

    with open(transcript_filename, "r", encoding="UTF-8") as file:
        transcript = file.read()

    if transcript == "":
        raise Exception("Transcript is empty")

    num_tokens = len(enc.encode(transcript))

    # Check if the transcript can be summarized in one chunk
    if num_tokens <= max_tokens:
        # Send the transcript to the OpenAI API
        completion_length = context_length - summary_prompt_length - num_tokens
        summary = get_summary(model, prompt_summary,
                              transcript, completion_length, overflow)

    if overflow or num_tokens > max_tokens:
        # Split the transcript into chunks recursively
        overflow = False
        transcript_chunks = []
        split_transcript(transcript, context_length, transcript_chunks, enc)
        summary_chunks = []
        # Summarize each chunk
        for chunk in transcript_chunks:
            completion_length = context_length - \
                chunk_prompt_length - len(enc.encode(chunk))
            summary_chunk = get_summary(
                model, prompt_chunk_summary, chunk, completion_length, overflow)
            summary_chunks.append(summary_chunk)
        # Create master summary
        summary_chunks = ' '.join(summary_chunks) + " Master summary: "
        completion_length = context_length - \
            final_prompt_length - len(enc.encode(summary_chunks))
        summary = get_summary(
            model, prompt_final_summary, summary_chunks, completion_length, overflow)

    if summary == "":
        raise Exception("Summary is empty")

    # Save the summary to a file
    user_email = supabase.table('summaries').select("user_email").eq(
        'id', summary_id).execute().data[0]['user_email']
    summary_filename = save_file(
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
    send_approval_email(summary_filename, transcript_filename,
                        summary_id, approval_link)

    os.remove(transcript_filename)
    os.remove(summary_filename)

    return summary_filename


@retry(stop=stop_after_attempt(2), wait=wait_fixed(60))  # handle rate limiting
def get_summary(model: str, prompt: str, text: str, completion_length: int, overflow: bool) -> str:
    response = openai.ChatCompletion.create(
        model=model,
        messages=[{"role": "system", "content": prompt}, {
            "role": "user", "content": text}],
        max_tokens=completion_length,
    )
    if response['choices'][0]['finish_reason'] == 'length':
        overflow = True
    return response['choices'][0]['message']['content']


def split_transcript(transcript: str, context_length: int, transcript_chunks: list, enc):
    """Recursively split the transcript into chunks until they are shorter than context_length."""
    transcript_length = len(enc.encode(transcript))
    if transcript_length >= context_length:
        # find the period closest to the middle of the transcript
        middle = transcript_length // 2
        period_index = transcript.rfind('. ', 0, middle)
        first_half = transcript[:period_index + 1]
        second_half = transcript[period_index + 1:]
        split_transcript(first_half, context_length, transcript_chunks, enc)
        split_transcript(second_half, context_length, transcript_chunks, enc)
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


def save_file(text, directory, user_email) -> str:
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


def send_approval_email(summary_filename: str, transcript_filename: str, summary_id: int, approval_link: str):
    """Send email with summary for QA."""
    print("Sending email with summary for approval...", flush=True)
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
