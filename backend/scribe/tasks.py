"""Celery tasks."""
import smtplib
import ssl
import os
import time
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
import pathlib
from celery import Celery
from dotenv import load_dotenv
import openai
import whisper

load_dotenv()

app = Celery('scribe', broker=os.environ.get('REDIS_URL'), backend=os.environ.get('REDIS_URL'))

# There should be a way to get these from Flask config, maybe?
TRANSCRIPTS_FOLDER = pathlib.Path(__file__).resolve().parent.parent/"files"/"transcripts"
SUMMARIES_FOLDER = pathlib.Path(__file__).resolve().parent.parent/"files"/"summaries"

@app.task(bind=True, autoretry_for=(Exception,), retry_kwargs={'max_retries': 1, 'countdown': 5})
def summarize(self, user_email: str, user_filename: str, file_type: str, approve_url: str) -> dict:
    """Generate summary given an audio file."""

    transcript_filename = None
    if file_type == "audio":
        print("Transcribing audio...")
        # transcribe the recording with Whisper
        transcript_filename = generate_transcript(user_filename)
        # transcript_filename = '/app/files/transcripts/Transcript_2023-04-10_22-49-21.txt'
    elif file_type == "text":
        transcript_filename = user_filename

    print("Summarizing transcript...")
    # summarise the conversation with GPT
    summary_filename = generate_summary(transcript_filename)
    # summary_filename = '/app/files/summaries/Summary_2023-04-10_22-49-44.txt'

    # send summary for QA
    send_approval_email(self, summary_filename, transcript_filename, approve_url)

    # email output
    # send_email_confirmation(receiver_email)

    context = {
        "user_email": user_email,
        "user_filename": user_filename,
        "summary_filename": summary_filename,
        "transcript_filename": transcript_filename
    }

    return context

@app.task(autoretry_for=(Exception,), retry_kwargs={'max_retries': 5, 'countdown': 5})
def send_summary(user_email: str, user_filename: str, summary_filename: str, transcript_filename: str):
    """Send summary to user."""
    print("Sending summary...")
    text = "Hey there, \n\nPlease find the notes from your recent conversation attached. We also included the transcript in case you want to refresh your memory.\n\nThank you for using Scribe!\n\nSincerely,\nThe Scribe Team\n\nP.S. While a powerful tool, Scribe is an early-stage project, and we live for your feedback. Please take 2 minutes to let us know what worked and what didn't, so we can make Scribe better for you. Or tweet your feedback @tryscribeai."
    subject = "Scribe Summary"
    send_mail(user_email, subject, text, [summary_filename, transcript_filename])
    if os.path.isfile(user_filename):
        os.remove(user_filename)


def generate_transcript(audio_filename):
    print("Generating transcript...")

    # load audio
    audio = whisper.load_audio(audio_filename)

    print(f'{audio_filename} loaded')

    # pad / trim it to fit 30 seconds to test
    # audio = whisper.pad_or_trim(audio)
    # print(f'{file.name} trimmed')

    # load model
    model = whisper.load_model("medium")

    # transcribe audio
    result = model.transcribe(audio)

    transcript_filename = save_file((result["text"]), TRANSCRIPTS_FOLDER)

    return transcript_filename


def generate_summary(transcript_filename: str):
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
    summaries = ''.join(response['choices'][0]['text'] for response in responses)

    # Send the prompt to the OpenAI API
    response = openai.Completion.create(
        model=model_engine,
        prompt=prompt_final_summary + summaries + "Summary: ",
        max_tokens=600
    )

    # Save the generated text
    message = response.choices[0].text
    summary_filename = save_file(message, SUMMARIES_FOLDER)

    return summary_filename

def save_file(text, directory) -> str:
    assert directory in [TRANSCRIPTS_FOLDER, SUMMARIES_FOLDER]

    # generate current timestamp
    timestamp = int(time.time())
    date_string = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d_%H-%M-%S')

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

def send_approval_email(self, summary_filename: str, transcript_filename: str, approve_url: str):
    """Send email with summary for QA."""
    print("Sending email with summary for approval...")
    task_uuid = self.request.id
    approve_link = approve_url.format(task_uuid=task_uuid)
    text = f'Please review the summary below and click the link to approve it.\n\n{approve_link}'
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
                part.add_header('Content-Disposition', 'attachment', filename=os.path.basename(file))
                msg.attach(part)

        msg.attach(MIMEText(text, 'plain', 'utf-8'))
        server.send_message(msg)
