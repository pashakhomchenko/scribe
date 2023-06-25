"""Configuration file for the Scribe backend."""
import pathlib
SCRIBE_ROOT = pathlib.Path(__file__).resolve().parent.parent
TEXT_UPLOAD_FOLDER = SCRIBE_ROOT/'files'/'transcripts'
AUDIO_UPLOAD_FOLDER = SCRIBE_ROOT/'files'/'audio_uploads'
SUMMARIES_FOLDER = SCRIBE_ROOT/'files'/'summaries'
TRANSCRIPTS_FOLDER = SCRIBE_ROOT/'files'/'transcripts'
AUDIO_EXTENSIONS = {'.mp3', '.mp4', '.m4a',
                    '.flac', '.wav', '.mov', '.avi', '.ogg'}
TEXT_EXTENSIONS = {'.txt'}
S3_BUCKET = "scribe-backend-files"
MAX_CONTENT_LENGTH = 300 * 1000 * 1000  # 300 MB
