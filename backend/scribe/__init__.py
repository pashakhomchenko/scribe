"""Scribe package initializer."""
import os
from flask import Flask
from flask_cors import CORS
from dotenv import load_dotenv
from supabase import create_client, Client


def create_app(test_config=None):
    """Create and configure the app"""
    load_dotenv()

    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY='dev',
    )

    supabase_init_app(app)

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

    with app.app_context():
        from . import config
        app.config.from_object(config)

        from . import api
        from . import auth

        app.register_blueprint(api.bp)
        app.register_error_handler(auth.AuthError, auth.handle_auth_error)

    CORS(app)
    return app


def supabase_init_app(app: Flask) -> Client:
    """Initialize Supabase client."""
    supabase: Client = create_client(
        os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
    app.extensions["supabase"] = supabase
    return supabase
