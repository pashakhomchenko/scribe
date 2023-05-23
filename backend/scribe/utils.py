"""Utility functions for the Scribe backend."""
from functools import wraps
from flask import current_app as app, jsonify, g, request
from supabase import Client

class AuthError(Exception):
    """AuthError Exception class."""
    def __init__(self, error, status_code):
        self.error = error
        self.status_code = status_code

def handle_auth_error(ex):
    """Handle AuthError exceptions."""
    response = jsonify(ex.error)
    response.status_code = ex.status_code
    return response

def requires_auth(func):
    """Check Supabase token and add user to request context."""
    @wraps(func)
    def decorated(*args, **kwargs):
        supabase: Client = app.extensions['supabase']
        auth = request.headers.get("Authorization", None)
        if not auth:
            raise AuthError({"code": "authorization_header_missing",
                            "description":
                                "Authorization header is expected"}, 401)

        parts = auth.split()

        if parts[0].lower() != "bearer":
            raise AuthError({"code": "invalid_header",
                            "description":
                                "Authorization header must start with"
                                " Bearer"}, 401)
        if len(parts) == 1:
            raise AuthError({"code": "invalid_header",
                            "description": "Token not found"}, 401)
        if len(parts) > 2:
            raise AuthError({"code": "invalid_header",
                            "description":
                                "Authorization header must be"
                                " Bearer token"}, 401)

        token = parts[1]
        try:
            user = supabase.auth.get_user(token)
        except Exception as exc:
            raise AuthError({"code": "invalid_token",
                                "description": "token is invalid"}, 401) from exc
        if not user:
            raise AuthError({"code": "invalid_token",
                                "description": "token is invalid"}, 401)
        g.user = user.user
        return func(*args, **kwargs)
    return decorated

def requires_subscription(func):
    """Check subscription info in Supabase and make sure that user has enough credits."""
    @wraps(func)
    def decorated(*args, **kwargs):
        supabase: Client = app.extensions['supabase']
        subscription = supabase.table('subscriptions').select('*').eq('user_id', g.user.id).eq('status', 'active').single().execute()
        if not subscription:
            raise AuthError({"code": "unauthorized",
                                "description": "user is not subscribed"}, 401)
        if subscription.data['credits'] is None or subscription.data['credits'] <= 0:
            raise AuthError({"code": "unauthorized",
                                "description": "user has no credits"}, 401)
        g.subscription = subscription.data
        return func(*args, **kwargs)
    return decorated

def decrease_credits(user_id):
    """Decrease user credits by one."""
    supabase: Client = app.extensions['supabase']
    subscription = g.subscription
    if subscription:
        users_credits = subscription['credits'] - 1
        supabase.table('subscriptions').update({'credits': users_credits}).eq('user_id', user_id).execute()
