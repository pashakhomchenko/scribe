"""API endpoints."""
import os
import time
from datetime import datetime
from flask import g, request, Blueprint, current_app as app
from werkzeug.utils import secure_filename
from celery import result
import mutagen
from . import utils

bp = Blueprint('api', __name__, url_prefix='/api/v1')

@bp.route("/", methods=['GET'])
def get_resources():
    """Return resources."""
    context = {
        "summarize": "/api/v1/summarize/",
        "approve": "/api/v1/approve/<task_uuid>",
        "resources": "/api/v1/"
    }
    return context, 200


@bp.route("/summarize/", methods=['POST'])
@utils.requires_auth
@utils.requires_subscription
def summarize():
    """Accept files for summary from subscribed users."""

    if 'file' not in request.files:
        return {"message": "No file sent"}, 400
    file = request.files['file']

    if file.filename == '':
        return {"message": "No file selected"}, 400

    if allowed_file(file.filename):
        return {"message": "Invalid file type"}, 400
    file_ext = os.path.splitext(file.filename)[1].lower()

    file_type = 'audio' if file_ext in app.config['AUDIO_EXTENSIONS'] else 'text'
    file_folder = app.config['AUDIO_UPLOAD_FOLDER'] if file_type == 'audio' else app.config['TEXT_UPLOAD_FOLDER']

    # TODO: Check if upload file are actually audio or text files

    date_string = datetime.fromtimestamp(int(time.time())).strftime('%Y-%m-%d_%H-%M-%S')
    filename_str = f'{g.user.email}_{date_string}{file_ext}'
    filename = secure_filename(filename_str)
    filename = os.path.join(file_folder, filename)
    file.save(filename)

    # Check the length of the file
    if file_type == 'audio':
        audio = mutagen.File(filename)
        if audio is None:
            return {"message": "Invalid audio file"}, 400
        if audio.info.length > 60 * g.subscription["max_audio_length"]:
            if os.path.isfile(filename):
                os.remove(filename)
            return {"message": f"Audio file is too long, the length must be less than {g.subscription['max_audio_length']} minutes"}, 400

    # Check the size of text file
    if file_type == 'text':
        if os.path.getsize(filename) > 1000 * g.subscription["max_audio_length"]: # 1 minute of conversation is about 1000 bytes
            if os.path.isfile(filename):
                os.remove(filename)
            return {"message": f"Text file is too big, the size must be less than {g.subscription['max_audio_length']} KB (1 minute of conversation is approximately 1KB in plain text file)"}, 400

    approve_url = f'{request.root_url}api/v1/approve/{{task_uuid}}'
    # Send task to celery
    app.extensions['celery'].send_task('scribe.tasks.summarize', [g.user.email, filename, file_type, approve_url])

    # Decrease user credits
    utils.decrease_credits(g.user.id)

    return {"message": "File accepted for processing"}, 202

@bp.route("/approve/<task_uuid>", methods=['GET'])
def approve(task_uuid):
    """Send summary to the user."""
    res = result.AsyncResult(task_uuid)
    if res.state == 'PENDING':
        return {"message": "Task is still pending"}, 202
    if res.state == 'FAILURE':
        return {"message": "Task failed"}, 500
    try:
        res_dict = res.get(timeout=1.0)
    except Exception:
        return {"message": "Task failed"}, 500
    if res_dict is None:
        return {"message": "No result entry found in redis"}, 500
    if res_dict['user_email'] is None or res_dict['user_filename'] is None or res_dict['summary_filename'] is None or res_dict['transcript_filename'] is None:
        return {"message": "Some information is missing in redis entry"}, 500
    app.extensions['celery'].send_task('scribe.tasks.send_summary', [res_dict['user_email'], res_dict['user_filename'], res_dict['summary_filename'], res_dict['transcript_filename']])
    return {"message": "Summary approved"}, 200

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in (app.config['AUDIO_EXTENSIONS'], app.config['TEXT_EXTENSIONS'])
