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
        "*").eq("transcript_file", None).execute()['data']

    if res.error:
        print(f"Error fetching data: {res.error}")
        return

    for row in res:
        if row['audio_file'] is not None:
            continue
        audio_file = row['audio_file']
        transcript_filename = generate_transcript(audio_file)
        # add transcript file to supabase
        supabase.table('summaries').update(
            {'transcript_file': transcript_filename}).eq('id', row['id']).execute()
        # send api request to summarize the transcript
        url = os.getenv("SUMMARIZE_URL")
        with open(transcript_filename, 'r', encoding='utf-8') as f:
            transcript = f.read()
        response = requests.post(
            url, json={'transcript_file': transcript, 'id': row['id']}, timeout=10)
        if response.status_code != 202:
            print(f"Error sending request: {response.text}")


if __name__ == '__main__':
    main()
