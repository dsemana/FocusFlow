"""SQLite integrity and cross-process transaction serialization."""

from sqlalchemy import event
from .extensions import db


def configure_sqlite(app):
    with app.app_context():
        engine = db.engine

        @event.listens_for(engine, "connect")
        def configure_connection(connection, record):
            # SQLAlchemy owns BEGIN/COMMIT, including transactional schema changes.
            connection.isolation_level = None
            cursor = connection.cursor()
            cursor.execute("PRAGMA busy_timeout=30000")
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.close()

        @event.listens_for(engine, "begin")
        def begin_transaction(connection):
            # Session lookup precedes route validation, and session saving writes
            # even on GET. Acquire the database writer reservation before reads
            # so a competing request cannot validate against a stale snapshot.
            # SQLite coordinates this across processes, not just Python threads.
            connection.exec_driver_sql("BEGIN IMMEDIATE")
