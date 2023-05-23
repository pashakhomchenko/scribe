"""Scribe package initializer."""
import os
from flask import Flask
from flask_cors import CORS
from celery import Celery, Task
from dotenv import load_dotenv
from supabase import create_client, Client

from . import api
from . import config
from . import utils


def create_app(test_config=None):
    """Create and configure the app"""
    load_dotenv()

    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY='dev',
        CELERY={
            "broker_url": os.environ.get('REDIS_URL'),
            "result_backend": os.environ.get('REDIS_URL'),
        },
    )

    celery_init_app(app)
    supabase_init_app(app)

    app.config.from_object(config)

    if test_config is None:
        # load the instance config, if it exists, when not testing
        app.config.from_pyfile('config.py', silent=True)
    else:
        # load the test config if passed in
        app.config.from_mapping(test_config)

    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    app.register_blueprint(api.bp)
    app.register_error_handler(utils.AuthError, utils.handle_auth_error)

    CORS(app)
    return app


def celery_init_app(app: Flask) -> Celery:
    class FlaskTask(Task):
        def __call__(self, *args: object, **kwargs: object) -> object:
            with app.app_context():
                return self.run(*args, **kwargs)

    celery_app = Celery(app.name, task_cls=FlaskTask)
    celery_app.config_from_object(app.config["CELERY"])
    celery_app.set_default()
    app.extensions["celery"] = celery_app
    return celery_app


def supabase_init_app(app: Flask) -> Client:
    supabase: Client = create_client(
        os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
    app.extensions["supabase"] = supabase
    return supabase
