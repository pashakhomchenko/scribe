"""Utility functions for the Scribe backend."""
import smtplib
import ssl
import os
import time
import pathlib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from supabase import Client, create_client
import openai
import boto3
import tiktoken

TRANSCRIPTS_FOLDER = pathlib.Path(
    __file__).resolve().parent.parent/'files'/'transcripts'
SUMMARIES_FOLDER = pathlib.Path(
    __file__).resolve().parent.parent/'files'/'summaries'
S3_BUCKET = "scribe-backend-files"

supabase: Client = create_client(
    os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))


def send_summary(user_email: str, summary_filename: str, transcript_filename: str):
    """Send summary to user."""
    print("Sending summary...")
    text = "Hey there, \n\nPlease find the notes from your recent conversation attached. We also included the transcript in case you want to refresh your memory.\n\nThank you for using Scribe!\n\nSincerely,\nThe Scribe Team\n\nP.S. While a powerful tool, Scribe is an early-stage project, and we live for your feedback. Please take 2 minutes to let us know what worked and what didn't, so we can make Scribe better for you. Or tweet your feedback @tryscribeai."
    subject = "Scribe Summary"
    send_mail(user_email, subject, text, [
              summary_filename, transcript_filename])
    os.remove(transcript_filename)
    os.remove(summary_filename)


def generate_summary(transcript_filename: str, summary_id: int, approval_link: str):
    print("Generating summary...")
    # Set API key, prompt, and model
    openai.api_key = os.getenv("OPENAI_API_KEY")
    prompt_chunk_summary = os.getenv("PROMPT_CHUNK_SUMMARY")
    prompt_final_summary = os.getenv("PROMPT_FINAL_SUMMARY")

    model = "gpt-3.5-turbo-16k"
    enc = tiktoken.encoding_for_model(model)
    # full context lendth is 16384 but we need to account for the prompt and completion
    context_length = 15384
    max_tokens = 800  # account for the prompt
    overflow = False
    summary = ""

    with open(transcript_filename, "r", encoding="UTF-8") as file:
        transcript = file.read()

    if transcript == "":
        raise Exception("Transcript is empty")

    num_tokens = len(enc.encode(transcript))

    # Check if the transcript can be summarized in one chunk
    if num_tokens <= context_length:
        # Send the transcript to the OpenAI API
        response = openai.ChatCompletion.create(
            model=model,
            messages=[{"role": "system", "content": prompt_chunk_summary}, {
                "role": "user", "content": transcript}],
            max_tokens=max_tokens,
        )
        if response['choices'][0]['finish_reason'] == 'length':
            overflow = True
        summary = response['choices'][0]['message']['content']

    if overflow or num_tokens > context_length:
        transcript_chunks = []
        split_transcript(transcript, context_length, transcript_chunks, enc)
        summary_chunks = []
        for chunk in transcript_chunks:
            response = openai.ChatCompletion.create(
                model=model,
                messages=[{"role": "system", "content": prompt_chunk_summary}, {
                    "role": "user", "content": chunk}],
                max_tokens=max_tokens,
            )
            summary_chunks.append(response['choices'][0]['message']['content'])
        # Create master summary
        response = openai.ChatCompletion.create(
            model=model,
            messages=[{"role": "system", "content": prompt_final_summary}, {
                "role": "user", "content": ' '.join(summary_chunks) + "Master summary: "}],
        )
        summary = response['choices'][0]['message']['content']

    # Save the summary to a file
    user_email = supabase.table('summaries').select("user_email").eq(
        'id', summary_id).execute().data[0]['user_email']
    summary_filename = save_file(summary, SUMMARIES_FOLDER, user_email)

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
    print("Sending email with summary for approval...")
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
