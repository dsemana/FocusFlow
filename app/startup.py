"""Initialize local configuration and schema before the server accepts requests."""

import os
import secrets
import threading
import time
from contextlib import contextmanager
from pathlib import Path

from dotenv import load_dotenv
from flask_migrate import upgrade

from . import create_app

_thread_lock = threading.Lock()


@contextmanager
def startup_lock(path, timeout=30):
    """Serialize first starts across workers on Windows and Unix."""
    with _thread_lock:
        with path.open("a+b") as stream:
            stream.seek(0, os.SEEK_END)
            if stream.tell() == 0:
                stream.write(b"\0")
                stream.flush()
            deadline = time.monotonic() + timeout
            while True:
                try:
                    stream.seek(0)
                    if os.name == "nt":
                        import msvcrt

                        msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
                    else:
                        import fcntl

                        fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                    break
                except OSError:
                    if time.monotonic() >= deadline:
                        raise RuntimeError(
                            "Timed out waiting for another server to initialize."
                        )
                    time.sleep(0.05)
            try:
                yield
            finally:
                stream.seek(0)
                if os.name == "nt":
                    msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    fcntl.flock(stream.fileno(), fcntl.LOCK_UN)


def create_server_app(project_root=None):
    root = Path(project_root or Path(__file__).resolve().parents[1]).resolve()
    load_dotenv(root / ".env")
    instance = root / "instance"
    instance.mkdir(parents=True, exist_ok=True)
    with startup_lock(instance / "startup.lock"):
        secret = os.getenv("SECRET_KEY")
        if not secret:
            key_file = instance / "secret.key"
            if not key_file.exists():
                descriptor = os.open(
                    key_file, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600
                )
                with os.fdopen(descriptor, "w", encoding="ascii") as stream:
                    stream.write(secrets.token_hex(32))
            secret = key_file.read_text(encoding="ascii").strip()
        app = create_app({"SECRET_KEY": secret}, instance_path=str(instance))
        with app.app_context():
            # Apply versioned upgrades only. Existing accounts and records survive.
            upgrade(directory=str(root / "migrations"))
        return app
