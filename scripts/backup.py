"""Consistent SQLite backup, including committed data still in the WAL."""

import argparse
import sqlite3
from pathlib import Path


def main():
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", type=Path, default=root / "instance/focusflow.db")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    source = args.database.resolve()
    target = args.output.resolve()
    if not source.is_file():
        parser.error("The source database does not exist.")
    if source == target or target.exists():
        parser.error("Choose a new backup path; existing files are never overwritten.")
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("xb"):
        pass
    original = sqlite3.connect(source.as_uri() + "?mode=ro", uri=True, timeout=30)
    backup = sqlite3.connect(target)
    try:
        original.backup(backup)
        if backup.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise RuntimeError("Backup failed SQLite integrity validation.")
    finally:
        backup.close()
        original.close()
    print(f"Verified SQLite backup: {target}")


if __name__ == "__main__":
    main()
