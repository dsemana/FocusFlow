import os
import logging
from pathlib import Path
import click
from flask import Flask, request, redirect, url_for, render_template
from flask_login import current_user
from werkzeug.exceptions import HTTPException
from werkzeug.security import generate_password_hash
from .extensions import db, migrate, login, csrf, limiter
from .models import Student, WebSession, now
from .session import DatabaseSessionInterface


def create_app(config=None, *, instance_path=None):
    app = Flask(__name__, instance_path=instance_path)
    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    if os.getenv("TRUST_PROXY") == "1":
        from werkzeug.middleware.proxy_fix import ProxyFix

        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
    production = os.getenv("APP_ENV") == "production"
    app.config.update(
        SECRET_KEY=os.getenv("SECRET_KEY"),
        SQLALCHEMY_DATABASE_URI=os.getenv("DATABASE_URL") or "sqlite:///focusflow.db",
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SQLALCHEMY_ENGINE_OPTIONS={"pool_pre_ping": True},
        SESSION_COOKIE_NAME="focusflow_session",
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SECURE=production,
        SESSION_COOKIE_SAMESITE="Lax",
        # Device preview and mobile network changes can alter the browser
        # fingerprint. Mark such sessions non-fresh instead of revoking login.
        # Credential changes separately require the current password.
        SESSION_PROTECTION="basic",
        SESSION_IDLE_MINUTES=int(os.getenv("SESSION_IDLE_MINUTES", "30")),
        WTF_CSRF_TIME_LIMIT=14400,
        MAX_CONTENT_LENGTH=256 * 1024,
        RATELIMIT_STORAGE_URI=os.getenv("RATELIMIT_STORAGE_URI", "memory://"),
        PRIORITY_WEIGHTS=(0.55, 0.30, 0.15),
        PRODUCTION=production,
        DUMMY_HASH=generate_password_hash("not-a-real-user-password"),
    )
    if config:
        app.config.update(config)
    if (
        not app.config.get("SECRET_KEY")
        or len(app.config["SECRET_KEY"]) < 32
        or app.config["SECRET_KEY"].startswith("replace-with")
    ):
        raise RuntimeError("Set SECRET_KEY to at least 32 random characters in .env.")
    if not app.config["SQLALCHEMY_DATABASE_URI"].startswith("sqlite:"):
        raise RuntimeError(
            "FocusFlow uses SQLite. Remove DATABASE_URL or set a sqlite:/// URL."
        )
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "pool_pre_ping": True,
        "connect_args": {"timeout": 30, "check_same_thread": False},
    }
    if production and app.config["RATELIMIT_STORAGE_URI"] == "memory://":
        raise RuntimeError(
            "Production requires shared rate limiting: set RATELIMIT_STORAGE_URI to Redis."
        )
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s"
    )
    for extension in (db, login, csrf, limiter):
        extension.init_app(app)
    from .database import configure_sqlite

    configure_sqlite(app)
    migrate.init_app(app, db)
    app.session_interface = DatabaseSessionInterface()

    @login.user_loader
    def load_user(ident):
        try:
            return db.session.get(Student, int(ident))
        except (TypeError, ValueError):
            return None

    @login.unauthorized_handler
    def unauthorized():
        if request.path.startswith("/api/"):
            return {"success": False, "message": "Sign in to continue."}, 401
        return redirect(url_for("page", page_name="login"))

    from .routes.auth import auth
    from .routes.api import api

    app.register_blueprint(auth)
    app.register_blueprint(api)

    @app.get("/health")
    def health():
        db.session.execute(db.text("SELECT 1"))
        return {"status": "ok"}

    @app.get("/")
    def home():
        return redirect("/dashboard" if current_user.is_authenticated else "/login")

    @app.get("/<page_name>")
    def page(page_name):
        public = ("login", "register")
        private = (
            "dashboard",
            "tasks",
            "courses",
            "deadlines",
            "calendar",
            "planner",
            "notifications",
            "profile",
            "settings",
        )
        if page_name not in public + private:
            from werkzeug.exceptions import NotFound

            raise NotFound()
        if page_name in public:
            if current_user.is_authenticated:
                return redirect("/dashboard")
            return render_template("auth.html", page=page_name)
        if not current_user.is_authenticated:
            return redirect("/login")
        return render_template("app.html", page=page_name, user=current_user)

    @app.errorhandler(HTTPException)
    def http_error(error):
        db.session.rollback()
        return {
            "success": False,
            "message": error.description,
            "errors": getattr(error, "errors", {}),
        }, error.code

    @app.errorhandler(Exception)
    def unexpected(error):
        db.session.rollback()
        app.logger.exception("Unhandled application error")
        return {
            "success": False,
            "message": "Something went wrong. Please try again.",
        }, 500

    @app.after_request
    def headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
        )
        if app.config["PRODUCTION"]:
            response.headers["Strict-Transport-Security"] = "max-age=31536000"
        if request.path.startswith("/api/") or current_user.is_authenticated:
            response.headers["Cache-Control"] = "no-store"
        return response

    @app.cli.command("reminders")
    def reminders_command():
        """Generate idempotent reminders independently of any browser."""
        from .services.reminders import generate

        total = 0
        for ident in db.session.execute(db.select(Student.id)).scalars().all():
            total += generate(ident)
        click.echo(f"Generated {total} notifications.")

    @app.cli.command("purge-sessions")
    def purge():
        result = db.session.execute(
            db.delete(WebSession).where(WebSession.expires_at < now())
        )
        db.session.commit()
        click.echo(f"Removed {result.rowcount} expired sessions.")

    return app
