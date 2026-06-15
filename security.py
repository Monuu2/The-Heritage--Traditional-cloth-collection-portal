from flask_talisman import Talisman
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_bcrypt import Bcrypt
from flask_wtf.csrf import CSRFProtect
from werkzeug.utils import secure_filename
import os

bcrypt = Bcrypt()
csrf = CSRFProtect()


# RATE LIMITER


limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)


# SECURITY HEADERS (CSP)


csp = {
    'default-src': [
        '\'self\''
    ],
    'img-src': [
        '\'self\'',
        'data:'
    ],
    'script-src': [
        '\'self\'',
        'https://cdn.jsdelivr.net'
    ],
    'style-src': [
        '\'self\'',
        'https://cdn.jsdelivr.net',
        '\'unsafe-inline\''
    ]
}


# FILE VALIDATION


ALLOWED_EXTENSIONS = {
    "png",
    "jpg",
    "jpeg",
    "gif",
    "webp"
}

def allowed_file(filename):

    return (
        "." in filename and
        filename.rsplit(".", 1)[1].lower()
        in ALLOWED_EXTENSIONS
    )

def secure_upload(file, upload_folder):

    if file and allowed_file(file.filename):

        filename = secure_filename(file.filename)

        filepath = os.path.join(upload_folder, filename)

        file.save(filepath)

        return filename

    return None


# INIT FUNCTION


def init_security(app):

    # Initialize Extensions
    bcrypt.init_app(app)
    csrf.init_app(app)
    limiter.init_app(app)

    # HTTPS + Security Headers
    Talisman(
        app,
        content_security_policy=csp,
        force_https=False
    )

    # Additional headers
    @app.after_request
    def add_security_headers(response):

        response.headers["X-Frame-Options"] = "SAMEORIGIN"

        response.headers["X-Content-Type-Options"] = "nosniff"

        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        response.headers["Permissions-Policy"] = (
            "geolocation=(), microphone=(), camera=()"
        )

        return response