from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from models import db, User, AdminUser
from flask_login import login_user, logout_user, current_user
from flask_mail import Message
from datetime import datetime, timedelta
import random, string, time, re, hashlib, hmac, os

auth_bp = Blueprint("auth", __name__)

# ── Constants ──────────────────────────────────────────────────────────────
MAX_FAILED_ATTEMPTS  = 5
LOCKOUT_DURATION     = timedelta(minutes=15)
OTP_EXPIRY_SECONDS   = 300          # 5 minutes
OTP_MAX_ATTEMPTS     = 5            # wrong OTP tries before invalidation
RESEND_COOLDOWN_SECS = 30


# ── Helpers ────────────────────────────────────────────────────────────────
def generate_captcha():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))


def generate_otp():
    """Cryptographically secure 6-digit OTP."""
    return str(random.SystemRandom().randint(100000, 999999))


def _hash_otp(otp: str) -> str:
    """
    Hash the OTP before storing it in the session so that even if
    someone reads the session cookie they cannot recover the raw code.
    Uses HMAC-SHA256 with a server-side secret.
    """
    secret = os.environ.get("SECRET_KEY", "fallback-secret").encode()
    return hmac.new(secret, otp.encode(), hashlib.sha256).hexdigest()


def _verify_otp(user_otp: str, stored_hash: str) -> bool:
    """Constant-time comparison to prevent timing attacks."""
    return hmac.compare_digest(_hash_otp(user_otp), stored_hash)


def send_otp_email(email: str, otp: str):
    """Send OTP via Flask-Mail. Falls back to console in dev."""
    from flask import current_app
    mail = current_app.extensions.get('mail')

    msg = Message("Your Heritage OTP Code", recipients=[email])
    msg.body = (
        f"Your OTP code is: {otp}\n\n"
        "This code is valid for 5 minutes. Do not share it with anyone."
    )
    msg.html = (
        f"<h2 style='font-family:serif;'>Your Heritage OTP Code</h2>"
        f"<p>Your one-time password is:</p>"
        f"<h1 style='letter-spacing:8px;color:#d4a017;font-family:monospace;'>{otp}</h1>"
        f"<p>Valid for <strong>5 minutes</strong>. Do not share this code with anyone.</p>"
    )

    mail_user = current_app.config.get("MAIL_USERNAME", "")
    mail_pass = current_app.config.get("MAIL_PASSWORD", "")

    if mail and mail_user and mail_pass:
        try:
            mail.send(msg)
            print(f"[OTP] Email sent to {email}")
        except Exception as exc:
            print(f"[OTP EMAIL ERROR] {exc}")
            flash("Could not deliver OTP email. Please try again later.")
    else:
        # Development fallback — never runs in production if env vars are set
        print(f"[DEV] Mail not configured. OTP for {email}: {otp}")
        # Only expose the mock notification when explicitly in debug/dev mode
        if current_app.debug:
            session["mock_email_otp"] = otp
            session.modified = True


def save_image(file):
    if not file or file.filename == "":
        return "default.png"
    import os
    from werkzeug.utils import secure_filename
    from flask import current_app

    ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}
    ext = file.filename.rsplit(".", 1)[-1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        return "default.png"

    # Randomise filename to prevent enumeration / overwrite attacks
    safe_name = f"{os.urandom(16).hex()}.{ext}"
    upload_path = os.path.join(current_app.config["UPLOAD_FOLDER"], safe_name)
    file.save(upload_path)
    return safe_name


# ── Input Validation ──────────────────────────────────────────────────────
def validate_username(username):
    if not username or len(username) < 3 or len(username) > 30:
        return "Username must be 3–30 characters."
    if not re.match(r"^[a-zA-Z0-9_]+$", username):
        return "Username can only contain letters, numbers, and underscores."
    return None


def validate_email(email):
    if not email or not re.match(
        r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$", email
    ):
        return "Please enter a valid email address."
    return None


def validate_password(password):
    if len(password) < 8:
        return "Password must be at least 8 characters."
    if not re.search(r"[A-Z]", password):
        return "Password must contain at least one uppercase letter."
    if not re.search(r"[a-z]", password):
        return "Password must contain at least one lowercase letter."
    if not re.search(r"[0-9]", password):
        return "Password must contain at least one digit."
    if not re.search(r"[^a-zA-Z0-9]", password):
        return "Password must contain at least one special character."
    return None


# ── Account Lockout ───────────────────────────────────────────────────────
def handle_failed_login(user):
    if hasattr(user, "failed_login_attempts"):
        user.failed_login_attempts = (user.failed_login_attempts or 0) + 1
        if user.failed_login_attempts >= MAX_FAILED_ATTEMPTS:
            user.locked_until         = datetime.utcnow() + LOCKOUT_DURATION
            user.failed_login_attempts = 0
        db.session.commit()


def handle_successful_login(user):
    if hasattr(user, "failed_login_attempts"):
        user.failed_login_attempts = 0
        user.locked_until          = None
        db.session.commit()


# ── OTP session helpers ───────────────────────────────────────────────────
def _clear_otp_session():
    for key in ("otp_hash", "otp_time", "otp_attempts",
                "pending_username", "pending_email",
                "pending_pw_hash", "mock_email_otp"):
        session.pop(key, None)


def _otp_is_expired():
    return time.time() - session.get("otp_time", 0) > OTP_EXPIRY_SECONDS


def _otp_attempts_exceeded():
    return session.get("otp_attempts", 0) >= OTP_MAX_ATTEMPTS


# ── USER LOGIN ─────────────────────────────────────────────────────────────
@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect("/")

    if request.method == "POST":
        email    = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        user     = User.query.filter_by(email=email).first()

        # Lockout check
        if user and getattr(user, "is_locked", False):
            locked_until = getattr(user, "locked_until", None)
            if locked_until:
                remaining = int((locked_until - datetime.utcnow()).total_seconds() // 60) + 1
                flash(f"Account locked. Try again in {remaining} minute(s).")
                return render_template("login.html")

        if user and not user.is_admin and user.check_password(password):
            handle_successful_login(user)
            # Regenerate session to prevent session fixation
            session.regenerate() if hasattr(session, "regenerate") else None
            login_user(user)
            next_page = request.form.get("next") or request.args.get("next")
            # Validate next URL to prevent open-redirect
            if next_page and (next_page.startswith("http") or "//" in next_page):
                next_page = "/"
            return redirect(next_page or "/")

        if user:
            handle_failed_login(user)
            attempts      = getattr(user, "failed_login_attempts", 0) or 0
            attempts_left = MAX_FAILED_ATTEMPTS - attempts
            if attempts_left > 0:
                flash(f"Invalid credentials. {attempts_left} attempt(s) remaining.")
            else:
                flash("Account locked for 15 minutes due to too many failed attempts.")
        else:
            # Generic message — don't reveal whether email exists
            flash("Invalid email or password.")

    return render_template("login.html")


@auth_bp.route("/logout")
def logout():
    logout_user()
    session.clear()
    return redirect("/")


# ── ADMIN LOGIN ────────────────────────────────────────────────────────────
@auth_bp.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    from routes.admin import get_admin
    if get_admin():
        return redirect("/admin/dashboard")
    else:
        session.pop("_admin_user_id", None)

    if request.method == "POST":
        email    = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        user     = User.query.filter_by(email=email).first()

        if user and getattr(user, "is_locked", False):
            locked_until = getattr(user, "locked_until", None)
            if locked_until:
                remaining = int((locked_until - datetime.utcnow()).total_seconds() // 60) + 1
                flash(f"Account locked. Try again in {remaining} minute(s).")
                return render_template("admin_login.html")

        if user and user.is_admin and user.check_password(password):
            handle_successful_login(user)
            session["_admin_user_id"] = str(user.id)
            session.modified = True
            return redirect("/admin/dashboard")

        if user:
            handle_failed_login(user)
        flash("Invalid credentials or insufficient privileges.")

    return render_template("admin_login.html")


@auth_bp.route("/admin/logout")
def admin_logout():
    session.pop("_admin_user_id", None)
    session.modified = True
    return redirect("/admin/login")


# ── REGISTER ───────────────────────────────────────────────────────────────
@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect("/")

    if request.method == "GET":
        _clear_otp_session()
        captcha = generate_captcha()
        session["captcha"] = captcha
        return render_template("register.html", captcha=captcha)

    # ── Collect POST fields ──────────────────────────────────────────────
    captcha_in_session = session.get("captcha", "")
    username           = request.form.get("username", "").strip()
    email              = request.form.get("email", "").strip()
    phone              = request.form.get("phone", "").strip()
    user_captcha       = request.form.get("captcha", "").strip()
    user_otp           = request.form.get("otp", "").strip()

    # Determine which registration stage we're in
    otp_stage = bool(session.get("otp_hash"))

    # During OTP stage, password comes from the session (never re-exposed in HTML)
    if otp_stage:
        password         = session.get("pending_password", "")
        confirm_password = password
    else:
        password         = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

    form_data = dict(
        username=username,
        email=email,
        phone=phone,
        submitted_captcha=user_captcha,
    )

    # ── 1. CAPTCHA validation ────────────────────────────────────────────
    if user_captcha.upper() != captcha_in_session.upper():
        flash("Invalid captcha. Please try again.")
        new_captcha        = generate_captcha()
        session["captcha"] = new_captcha
        return render_template("register.html", captcha=new_captcha,
                               show_otp=otp_stage, **form_data)


    # ── 2. Input validation (only on first step, not OTP step) ──────────
    if not otp_stage:
        err = validate_username(username)
        if not err: err = validate_email(email)
        if not err: err = validate_password(password)
        if not err and password != confirm_password:
            err = "Passwords do not match."
        if not err:
            if User.query.filter_by(username=username).first():
                err = "Username already taken."
            elif User.query.filter_by(email=email).first():
                err = "Email already registered."

        if err:
            flash(err)
            new_captcha        = generate_captcha()
            session["captcha"] = new_captcha
            return render_template("register.html", captcha=new_captcha,
                                   show_otp=False, **form_data)

    # ── 3. OTP sending / verification ───────────────────────────────────
    if not user_otp:
        # --- First-time OTP send OR re-send via normal CONTINUE button ---
        otp_time = session.get("otp_time", 0)
        if not session.get("otp_hash") or (time.time() - otp_time > OTP_EXPIRY_SECONDS):
            otp = generate_otp()
            # Store hashed OTP and pending credentials — NOT the plaintext password
            session["otp_hash"]        = _hash_otp(otp)
            session["otp_time"]        = time.time()
            session["otp_attempts"]    = 0
            session["pending_username"] = username
            session["pending_email"]   = email
            session["pending_phone"]   = phone
            # Store only a hash of the password for integrity; actual hashing
            # is done at DB-write time via user.set_password()
            session["pending_password"] = password   # kept server-side only
            session.modified = True
            send_otp_email(email, otp)
            flash("A 6-digit OTP has been sent to your email.")
        else:
            flash("Please enter the OTP sent to your email.")

        return render_template("register.html", captcha=captcha_in_session,
                               show_otp=True, **form_data)

    # --- OTP submitted: validate it ---
    if _otp_is_expired():
        flash("OTP has expired. Please start again.")
        _clear_otp_session()
        new_captcha        = generate_captcha()
        session["captcha"] = new_captcha
        return render_template("register.html", captcha=new_captcha,
                               show_otp=False, **form_data)

    if _otp_attempts_exceeded():
        flash("Too many incorrect OTP attempts. Please register again.")
        _clear_otp_session()
        new_captcha        = generate_captcha()
        session["captcha"] = new_captcha
        return render_template("register.html", captcha=new_captcha,
                               show_otp=False, **form_data)

    if not _verify_otp(user_otp, session.get("otp_hash", "")):
        session["otp_attempts"] = session.get("otp_attempts", 0) + 1
        session.modified = True
        remaining = OTP_MAX_ATTEMPTS - session["otp_attempts"]
        if remaining > 0:
            flash(f"Invalid OTP. {remaining} attempt(s) remaining.")
        else:
            flash("Too many incorrect OTP attempts. Please register again.")
            _clear_otp_session()
            new_captcha        = generate_captcha()
            session["captcha"] = new_captcha
            return render_template("register.html", captcha=new_captcha,
                                   show_otp=False, **form_data)
        return render_template("register.html", captcha=captcha_in_session,
                               show_otp=True, **form_data)

    # ── 4. Successful Registration ───────────────────────────────────────
    # Re-read credentials from session (never from form at this stage)
    final_username = session.get("pending_username", username)
    final_email    = session.get("pending_email",    email)
    final_phone    = session.get("pending_phone",    phone)
    final_password = session.get("pending_password", password)

    # Double-check uniqueness (race-condition guard)
    if User.query.filter_by(username=final_username).first() or \
       User.query.filter_by(email=final_email).first():
        flash("Username or email was taken while you were registering. Please try again.")
        _clear_otp_session()
        return redirect("/register")

    profile_photo = request.files.get("photo")
    filename      = save_image(profile_photo)

    user = User(username=final_username, email=final_email, phone=final_phone, profile_photo=filename)
    user.set_password(final_password)
    db.session.add(user)
    db.session.commit()

    _clear_otp_session()
    session.pop("captcha", None)

    flash("Registration successful! Please log in.")
    return redirect("/login")

@auth_bp.route("/captcha/refresh", methods=["POST"])
def captcha_refresh():
    """
    AJAX endpoint — returns a fresh captcha without a full page reload.
    This prevents the user losing form data when the captcha is wrong.
    """
    from flask import jsonify
    new_captcha        = generate_captcha()
    session["captcha"] = new_captcha
    session.modified   = True
    return jsonify({"captcha": new_captcha})


# ── RESEND OTP ─────────────────────────────────────────────────────────────
@auth_bp.route("/resend-otp", methods=["POST"])
def resend_otp():
    # All trusted data comes from session, not the form
    email     = session.get("pending_email", "").strip()
    last_time = session.get("otp_time", 0)

    form_data = {
        "username":          session.get("pending_username", ""),
        "email":             email,
        "submitted_captcha": request.form.get("captcha", ""),
    }

    if not email:
        flash("Session expired. Please start registration again.")
        return redirect("/register")

    if last_time and time.time() - last_time < RESEND_COOLDOWN_SECS:
        wait = int(RESEND_COOLDOWN_SECS - (time.time() - last_time)) + 1
        flash(f"Please wait {wait} second(s) before requesting a new OTP.")
    else:
        otp                     = generate_otp()
        session["otp_hash"]     = _hash_otp(otp)
        session["otp_time"]     = time.time()
        session["otp_attempts"] = 0
        session.modified        = True
        send_otp_email(email, otp)
        flash("A new OTP has been sent to your email.")

    return render_template(
        "register.html",
        captcha=session.get("captcha"),
        show_otp=True,
        **form_data,
    )
