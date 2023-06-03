"""Celery tasks."""
import os
import time
from datetime import datetime
import pathlib
from supabase import create_client, Client
from dotenv import load_dotenv
import whisper

load_dotenv()
TRANSCRIPTS_FOLDER = pathlib.Path(
    __file__).resolve().parent.parent/"files"/"transcripts"


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

    # Fetch all rows from your_table
    result = supabase.table("summaries").select("*").execute()

    if result.error:
        print(f"Error fetching data: {result.error}")
        return

    for row in result.data:
        if row['transcript_file'] is None:
            audio_file = row['audio_file']
            transcript_filename = generate_transcript(audio_file)
            # add transcript file to supabase
            supabase.table('summaries').update(
                {'transcript_file': transcript_filename}).eq('id', row['id']).execute()
            # send api request to summarize the transcript


if __name__ == '__main__':
    main()
