"""Celery tasks."""
import os
import time
import requests
import argparse
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
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description='Generate summary for a transcript file')
    parser.add_argument('--summary_id', type=int,
                        help='ID of the summary to generate', required=True)
    args = parser.parse_args()
    summary_id = args.summary_id

    supabase: Client = create_client(
        os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

    # Fetch the row from supabase
    res = supabase.table("summaries").select(
        "*").eq('id', summary_id).execute()['data'][0]

    if res.error:
        print(f"Error fetching data: {res.error}")
        return

    if res['transcript_file'] is None:
        audio_file = res['audio_file']
        transcript_filename = generate_transcript(audio_file)
        # add transcript file to supabase
        supabase.table('summaries').update(
            {'transcript_file': transcript_filename}).eq('id', res['id']).execute()
        # send api request to summarize the transcript
        url = os.getenv("SUMMARIZE_URL")
        if url:
            with open(transcript_filename, 'r', encoding='utf-8') as f:
                transcript = f.read()
            response = requests.post(
                url, json={'transcript_file': transcript, 'id': summary_id}, timeout=10)
            if response.status_code != 202:
                print(f"Error sending request: {response.text}")


if __name__ == '__main__':
    main()
