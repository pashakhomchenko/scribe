"""Celery tasks."""
import os
import time
import requests
from datetime import datetime
import pathlib
from supabase import create_client, Client
from dotenv import load_dotenv
import whisper

load_dotenv()
TRANSCRIPTS_FOLDER = pathlib.Path(
    __file__).resolve().parent/"files"/"transcripts"


def generate_transcript(audio_filename):
    print("Generating transcript...")
    start_time = time.time()

    # load audio
    audio = whisper.load_audio(audio_filename)

    print(f'{audio_filename} loaded')

    # load model
    model = whisper.load_model("medium")

    # transcribe audio
    result = model.transcribe(audio)

    transcript_filename = save_file((result["text"]), TRANSCRIPTS_FOLDER)

    print(f'Transcript generated in {time.time() - start_time} seconds')

    return transcript_filename


def save_file(text, directory) -> str:
    # generate current timestamp
    timestamp = int(time.time())
    date_string = datetime.fromtimestamp(
        timestamp).strftime('%Y-%m-%d_%H-%M-%S')

    filename = f'Transcript_{date_string}.txt'

    # save transcript in the "transcripts" sub-folder
    with open(f'{directory}/{filename}', 'w', encoding="UTF-8") as f:
        # write to the file using the write method
        f.write(text)

    return f'{directory}/{filename}'


def main():
    supabase: Client = create_client(
        os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
    print("Connected to supabase")

    # Fetch all the entries that require transcription from supabase
    res = supabase.table("summaries").select(
        "*").filter('transcript_file', 'is', 'null').execute().data

    for row in res:
        if row['transcript_file'] is not None:
            continue
        audio_file = row['audio_file']
        transcript_filename = generate_transcript(audio_file)
        # add transcript file to supabase
        supabase.table('summaries').update(
            {'transcript_file': transcript_filename}).eq('id', row['id']).execute()
        # send api request to summarize the transcript
        url = os.getenv("SUMMARIZE_URL")
        response = requests.post(
            url, json={'transcript_file': transcript_filename, 'id': row['id']}, timeout=10)
        if response.status_code != 202:
            print(f"Error sending request: {response.text}")


if __name__ == '__main__':
    main()
