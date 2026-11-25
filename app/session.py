"""Opaque cookie token; all session contents and revocation live in the database."""

import hashlib
import secrets
from datetime import timedelta
from flask.sessions import SessionInterface, SessionMixin
from werkzeug.datastructures import CallbackDict
from .extensions import db
from .models import WebSession, now


class ServerSession(CallbackDict, SessionMixin):
    def __init__(self, initial=None, token=None):
        def changed(obj):
            obj.modified = True

        super().__init__(initial, changed)
        self.token = token or secrets.token_urlsafe(48)
        self.modified = False


class DatabaseSessionInterface(SessionInterface):
    @staticmethod
    def digest(token):
        return hashlib.sha256(token.encode()).hexdigest()

    def open_session(self, app, request):
        token = request.cookies.get(self.get_cookie_name(app))
        if token and len(token) <= 128:
            record = db.session.get(WebSession, self.digest(token))
            if record and record.expires_at > now():
                return ServerSession(record.data, token)
        return ServerSession()

    def save_session(self, app, session, response):
        key = self.digest(session.token)
        record = db.session.get(WebSession, key)
        if not session:
            if record:
                db.session.delete(record)
                db.session.commit()
            response.delete_cookie(self.get_cookie_name(app), path="/")
            return
        expiry = now() + timedelta(minutes=app.config["SESSION_IDLE_MINUTES"])
        if not record:
            record = WebSession(token_hash=key, data=dict(session), expires_at=expiry)
            db.session.add(record)
        else:
            record.data, record.expires_at = dict(session), expiry
        db.session.commit()
        response.set_cookie(
            self.get_cookie_name(app),
            session.token,
            expires=expiry,
            httponly=True,
            secure=app.config["SESSION_COOKIE_SECURE"],
            samesite="Lax",
            path="/",
        )

    def regenerate(self, session):
        record = db.session.get(WebSession, self.digest(session.token))
        if record:
            db.session.delete(record)
        session.token = secrets.token_urlsafe(48)
        session.modified = True
