from flask import Blueprint, request, session, current_app
from flask_login import login_user, logout_user, current_user, login_required
from flask_wtf.csrf import generate_csrf
from sqlalchemy.exc import IntegrityError
from ..extensions import db, limiter
from ..models import Student, UserPreference, WebSession
from ..validation import body, text, email, password, ValidationError

auth = Blueprint("auth", __name__, url_prefix="/api/auth")


def ok(data=None, message="Success", status=200):
    return {"success": True, "message": message, "data": data}, status


@auth.get("/csrf")
def token():
    return ok({"csrf_token": generate_csrf()})


@auth.post("/register")
@limiter.limit("10 per hour")
def register():
    data = body(request)
    name = text(data, "full_name", 120, True)
    address = email(data.get("email"))
    secret = password(data.get("password"))
    if secret != data.get("password_confirmation"):
        raise ValidationError("password_confirmation", "Passwords must match.")
    if db.session.execute(
        db.select(Student).where(Student.email == address)
    ).scalar_one_or_none():
        return {"success": False, "message": "This email is already registered."}, 409
    student = Student(full_name=name, email=address)
    student.set_password(secret)
    student.preference = UserPreference()
    db.session.add(student)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return {"success": False, "message": "This email is already registered."}, 409
    current_app.session_interface.regenerate(session)
    session.clear()
    login_user(student)
    return ok(student.public(), "Account created", 201)


@auth.post("/login")
@limiter.limit("10 per minute")
def login():
    data = body(request)
    address = email(data.get("email"))
    secret = data.get("password")
    if not isinstance(secret, str) or len(secret) > 128:
        raise ValidationError("password", "Enter your password.")
    student = db.session.execute(
        db.select(Student).where(Student.email == address)
    ).scalar_one_or_none()
    # Perform a real password hash check even for unknown accounts.
    from werkzeug.security import check_password_hash

    valid = (
        student.check_password(secret)
        if student
        else check_password_hash(current_app.config["DUMMY_HASH"], secret)
    )
    if not student or not valid:
        return {"success": False, "message": "Email or password is incorrect."}, 401
    current_app.session_interface.regenerate(session)
    session.clear()
    login_user(student)
    return ok(student.public(), "Welcome back")


@auth.post("/logout")
@login_required
def logout():
    logout_user()
    session.clear()
    return ok(message="Signed out")


@auth.get("/me")
@login_required
def me():
    return ok(current_user.public())
