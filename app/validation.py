import math
import re
from datetime import datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from werkzeug.exceptions import BadRequest


class ValidationError(BadRequest):
    def __init__(self, field, message):
        super().__init__(message)
        self.errors = {field: [message]}


def body(request):
    value = request.get_json(silent=True)
    if not isinstance(value, dict):
        raise ValidationError("body", "Send a JSON object.")
    return value


def text(data, key, maximum, required=False):
    value = data.get(key, "")
    if (
        not isinstance(value, str)
        or len(value.strip()) > maximum
        or (required and not value.strip())
    ):
        raise ValidationError(
            key, f"Enter {'1' if required else '0'} to {maximum} characters."
        )
    return value.strip()


def number(value, key, minimum, maximum):
    if isinstance(value, bool):
        raise ValidationError(key, "Enter a valid number.")
    try:
        value = float(value)
    except (TypeError, ValueError):
        raise ValidationError(key, "Enter a valid number.")
    if not math.isfinite(value) or not minimum <= value <= maximum:
        raise ValidationError(key, f"Enter a number between {minimum} and {maximum}.")
    return value


def identifier(value, key):
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValidationError(key, "Enter a positive integer ID.")
    return value


def choice(value, key, options):
    if not isinstance(value, str) or value not in options:
        raise ValidationError(key, "Choose one of: " + ", ".join(options))
    return value


def instant(value, key):
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if result.tzinfo is None:
            raise ValueError()
        return result.astimezone(timezone.utc).replace(tzinfo=None)
    except (ValueError, TypeError, AttributeError):
        raise ValidationError(key, "Use an ISO 8601 date/time with timezone.")


def email(value):
    if (
        not isinstance(value, str)
        or len(value) > 254
        or not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", value.strip())
    ):
        raise ValidationError("email", "Enter a valid email address.")
    return value.strip().lower()


def password(value):
    if (
        not isinstance(value, str)
        or not 10 <= len(value) <= 128
        or not re.search(r"[A-Za-z]", value)
        or not re.search(r"[0-9]", value)
    ):
        raise ValidationError(
            "password", "Use 10-128 characters including a letter and a number."
        )
    return value


def timezone_name(value):
    try:
        ZoneInfo(value)
    except (ZoneInfoNotFoundError, TypeError, ValueError):
        raise ValidationError("timezone", "Enter a valid IANA timezone.")
    return value
