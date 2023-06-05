"""API endpoints."""
import os
import time
import threading
from datetime import datetime
from flask import g, request, Blueprint, current_app as app
from werkzeug.utils import secure_filename
from supabase import Client
import mutagen
import boto3
from . import utils

bp = Blueprint('api', __name__, url_prefix='/api/v1')


@bp.route("/", methods=['GET'])
def get_resources():
    """Return resources."""
    context = {
        "submit": "/api/v1/submit/",
        "summarize": "/api/v1/summarize/",
        "approve": "/api/v1/approve/<task_uuid>",
        "resources": "/api/v1/"
    }
    return context, 200


@bp.route("/submit/", methods=['POST'])
@utils.requires_auth
@utils.requires_subscription
def submit():
    """Accept files for summary from subscribed users."""

    if 'file' not in request.files:
        return {"message": "No file sent"}, 400
    file = request.files['file']

    if file.filename == '':
        return {"message": "No file selected"}, 400

    if utils.allowed_file(file.filename):
        return {"message": "Invalid file type"}, 400
    file_ext = os.path.splitext(file.filename)[1].lower()

    file_type = 'audio' if file_ext in app.config['AUDIO_EXTENSIONS'] else 'text'
    file_folder = app.config['AUDIO_UPLOAD_FOLDER'] if file_type == 'audio' else app.config['TEXT_UPLOAD_FOLDER']

    # TODO: Check if upload file are actually audio or text files

    date_string = datetime.fromtimestamp(
        int(time.time())).strftime('%Y-%m-%d_%H-%M-%S')
    filename_str = f'{g.user.email}_{date_string}{file_ext}'
    filename = secure_filename(filename_str)
    filename = os.path.join(file_folder, filename)
    file.save(filename)

    supabase: Client = app.extensions['supabase']

    # Check the length of the file
    if file_type == 'audio':
        audio = mutagen.File(filename)
        if audio is None:
            return {"message": "Invalid audio file"}, 400
        if audio.info.length > 60 * g.subscription["max_audio_length"]:
            if os.path.isfile(filename):
                os.remove(filename)
            return {"message": f"Audio file is too long, the length must be less than {g.subscription['max_audio_length']} minutes"}, 400
        data, count = supabase.table('summaries').insert(
            {'audio_file': filename, 'user_email': g.user.email}).execute()
        summary_id = data[0]['id']

        # Push a job to AWS Batch
        job_name = f"summarize-audio-{datetime.now().strftime('%Y-%m-%d-%H-%M-%S')}"
        job_definition = "scribe-job-definition"
        job_queue = "scribe-job-queue"
        command = ["python", "summarize.py", "--summary_id", summary_id]
        client = boto3.client('batch')
        response = client.submit_job(
            jobName=job_name,
            jobQueue=job_queue,
            jobDefinition=job_definition,
            containerOverrides={
                'command': command
            }
        )

    # Check the size of text file
    if file_type == 'text':
        # 1 minute of conversation is about 1000 bytes
        if os.path.getsize(filename) > 1000 * g.subscription["max_audio_length"]:
            if os.path.isfile(filename):
                os.remove(filename)
            return {"message": f"Text file is too big, the size must be less than {g.subscription['max_audio_length']} KB (1 minute of conversation is approximately 1KB in plain text file)"}, 400
        data, count = supabase.table('summaries').insert(
            {'transcript_file': filename, 'user_email': g.user.email}).execute()
        transcript_file = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        summary_id = data[0]['id']
        thread = threading.Thread(
            target=summarize, args=(transcript_file, summary_id))
        thread.start()

    # Decrease user credits
    utils.decrease_credits(g.user.id)

    return {"message": "File accepted for processing"}, 202


@bp.route("/summarize/", methods=['POST'])
def summarize():
    transcript_file = request.json.get('transcript_file')
    if not transcript_file:
        return {"message": "Transcript file not found in request body"}, 400
    summary_id = request.json.get('id')
    if not summary_id:
        return {"message": "ID not found in request body"}, 400

    # Run generate_summary asynchronously
    thread = threading.Thread(target=utils.generate_summary,
                              args=(transcript_file, summary_id))
    thread.start()

    # Return a success message to the client
    return {"message": "Summary generation started"}, 202


@bp.route("/approve/<summary_id>", methods=['GET'])
def approve(summary_id):
    """Send summary to the user."""
    supabase: Client = app.extensions['supabase']
    res = supabase.table('summaries').select('user_email', 'audio_file',
                                             'summary_file', 'transcript_file').eq('id', summary_id).execute()['data'][0]
    thread = threading.Thread(target=utils.send_summary,
                              args=(res['user_email'], res['audio_file'], res['summary_file'], res['transcript_file']))
    thread.start()
    return {"message": "Summary approved"}, 200
