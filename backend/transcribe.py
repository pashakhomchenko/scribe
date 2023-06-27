"""Celery tasks."""
import os
import time
import requests
from datetime import datetime
import argparse
import pathlib
from supabase import create_client, Client
from dotenv import load_dotenv
import whisper
import boto3

load_dotenv()
DOWNLOAD_FOLDER = pathlib.Path(__file__).resolve().parent
S3_BUCKET = "scribe-backend-files"


def generate_transcript(audio_filename, user_email):
    print("Generating transcript...")
    start_time = time.time()

    # load audio
    audio = whisper.load_audio(audio_filename)

    print(f'{audio_filename} loaded')

    # load model
    model = whisper.load_model("medium")

    # transcribe audio
    result = model.transcribe(audio)

    transcript_filename = save_file(
        (result["text"]), DOWNLOAD_FOLDER, user_email)

    print(f'Transcript generated in {time.time() - start_time} seconds')

    return transcript_filename


def save_file(text, directory, user_email) -> str:
    # generate current timestamp
    timestamp = int(time.time())
    date_string = datetime.fromtimestamp(
        timestamp).strftime('%Y-%m-%d_%H-%M-%S')

    filename = f'Transcript_{user_email}_{date_string}.txt'

    # save transcript in the "transcripts" sub-folder
    with open(f'{directory}/{filename}', 'w', encoding="UTF-8") as f:
        # write to the file using the write method
        f.write(text)

    return f'{directory}/{filename}'


def main():
    # Parse arguments
    parser = argparse.ArgumentParser()
    parser.add_argument('summary_id')
    summary_id = parser.parse_args().summary_id

    # Connect to supabase
    supabase: Client = create_client(
        os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
    print("Connected to supabase")

    # Fetch summary_id entry from supabase
    res = supabase.table("summaries").select(
        "*").eq('id', summary_id).execute().data[0]

    # Check if transcript file already exists
    if res['transcript_file'] is not None:
        return
    audio_file = res['audio_file']

    # Download audio file from S3
    s3 = boto3.client('s3')
    download_path = f'{DOWNLOAD_FOLDER}/{audio_file.split("/")[-1]}'
    s3.download_file(Bucket=S3_BUCKET,
                     Key=audio_file, Filename=download_path)

    # Generate transcript
    transcript_filename = generate_transcript(download_path, res['user_email'])

    # Upload transcript to S3
    s3_filename = f'transcripts/{transcript_filename.split("/")[-1]}'
    s3.upload_file(Filename=transcript_filename,
                   Bucket=S3_BUCKET, Key=s3_filename)

    # add transcript file to supabase
    supabase.table('summaries').update(
        {'transcript_file': s3_filename}).eq('id', res['id']).execute()

    # send api request to summarize the transcript
    url = os.getenv("SUMMARIZE_URL")
    response = requests.post(
        url, json={'transcript_file': s3_filename, 'id': res['id']}, timeout=10)
    if response.status_code != 202:
        print(f"Error sending request: {response.text}")

    # delete audio and transcript file
    os.remove(download_path)
    os.remove(transcript_filename)


if __name__ == '__main__':
    main()
