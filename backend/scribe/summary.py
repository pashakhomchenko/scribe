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
from flask import current_app as app
from supabase import Client
import openai

TRANSCRIPTS_FOLDER = pathlib.Path(
    __file__).resolve().parent.parent/'files'/'transcripts'
SUMMARIES_FOLDER = pathlib.Path(
    __file__).resolve().parent.parent/'files'/'summaries'


def send_summary(user_email: str, audio_filename: str, summary_filename: str, transcript_filename: str):
    """Send summary to user."""
    print("Sending summary...")
    text = "Hey there, \n\nPlease find the notes from your recent conversation attached. We also included the transcript in case you want to refresh your memory.\n\nThank you for using Scribe!\n\nSincerely,\nThe Scribe Team\n\nP.S. While a powerful tool, Scribe is an early-stage project, and we live for your feedback. Please take 2 minutes to let us know what worked and what didn't, so we can make Scribe better for you. Or tweet your feedback @tryscribeai."
    subject = "Scribe Summary"
    send_mail(user_email, subject, text, [
              summary_filename, transcript_filename])
    if os.path.isfile(audio_filename):
        os.remove(audio_filename)


def generate_summary(transcript_filename: str, summary_id: int, approval_link: str):
    print("Generating summary...")
    # Set API key, prompt, and model
    openai.api_key = os.getenv("OPENAI_API_KEY")
    prompt_chunk_summary = os.getenv("PROMPT_CHUNK_SUMMARY")
    prompt_final_summary = os.getenv("PROMPT_FINAL_SUMMARY")

    model_engine = "text-davinci-003"

    transcript = ""

    with open(transcript_filename, "r", encoding="UTF-8") as file:
        transcript = file.read()

    if transcript == "":
        raise Exception("Transcript is empty")

    # Split the text into sentences
    sentences = transcript.split('. ')

    # Initialize the list of responses
    responses = []

    # Initialize the chunk
    chunk = ""

    # Initialize the chunk word count
    chunk_word_count = 0

    # Iterate over the sentences
    for sentence in sentences:
        # Split the sentence into words
        words = sentence.split()

        # Iterate over the words
        for word in words:
            # Check if the chunk is full
            if chunk_word_count + 1 > 1000:
                # Send the chunk to the OpenAI API
                response = openai.Completion.create(
                    engine=model_engine,
                    prompt=prompt_chunk_summary + chunk + "Summary: ",
                    max_tokens=200,
                    n=1,
                    stop=None,
                    temperature=0.7,
                )

                # Append the response to the list
                print(response.choices[0].text)
                responses.append(response)

                # Reset the chunk
                chunk = ""

                # Reset the chunk word count
                chunk_word_count = 0

            # Add the word to the chunk
            chunk += word + " "

            # Increment the chunk word count
            chunk_word_count += 1

    # Check if there is any leftover chunk
    if chunk:
        # Send the chunk to the OpenAI API
        response = openai.Completion.create(
            engine=model_engine,
            prompt=prompt_chunk_summary + chunk + "Summary: ",
            max_tokens=600,
            n=1,
            stop=None,
            temperature=0.7,
        )

        # Append the response to the list
        print(response.choices[0].text)
        responses.append(response)

    # Concatenate all the responses into one prompt
    summaries = ''.join(response['choices'][0]['text']
                        for response in responses)

    # Send the prompt to the OpenAI API
    response = openai.Completion.create(
        model=model_engine,
        prompt=prompt_final_summary + summaries + "Summary: ",
        max_tokens=600
    )

    # Save the generated text
    message = response.choices[0].text
    summary_filename = save_file(message, SUMMARIES_FOLDER)

    # Save the summary in the database
    supabase: Client = app.extensions['supabase']
    supabase.table('summaries').update(
        {'summary_file': summary_filename, 'summary': message}).eq('id', summary_id).execute()

    # Send the approval email
    send_approval_email(summary_filename, transcript_filename,
                        summary_id, approval_link)

    return summary_filename


def save_file(text, directory) -> str:
    assert directory in [TRANSCRIPTS_FOLDER, SUMMARIES_FOLDER]

    # generate current timestamp
    timestamp = int(time.time())
    date_string = datetime.fromtimestamp(
        timestamp).strftime('%Y-%m-%d_%H-%M-%S')

    # generate file name
    if directory == TRANSCRIPTS_FOLDER:
        filename = f'Transcript_{date_string}.txt'
    elif directory == SUMMARIES_FOLDER:
        filename = f'Summary_{date_string}.txt'

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
