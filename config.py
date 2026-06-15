import os

class Config:

    # Secure Secret Key 
   
    SECRET_KEY = os.environ.get("SECRET_KEY", os.urandom(32).hex())

    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    INSTANCE_DIR = os.path.join(BASE_DIR, "instance")
    os.makedirs(INSTANCE_DIR, exist_ok=True)

    # Database Configuration
    # Use DATABASE_URL when supplied. Use MYSQL_* only when USE_MYSQL=true.
    # Otherwise default to a local SQLite database so Flask's automatic .env
    # loading cannot accidentally force a broken local MySQL connection.
    DATABASE_URL = os.environ.get("DATABASE_URL")
    USE_MYSQL = os.environ.get("USE_MYSQL", "").lower() in ("1", "true", "yes", "on")

    if DATABASE_URL:
        SQLALCHEMY_DATABASE_URI = DATABASE_URL
    elif USE_MYSQL:
        MYSQL_USER     = os.environ.get("MYSQL_USER",     "heritage_user")
        MYSQL_PASSWORD = os.environ.get("MYSQL_PASSWORD", "heritage_pass")
        MYSQL_HOST     = os.environ.get("MYSQL_HOST",     "localhost")
        MYSQL_PORT     = os.environ.get("MYSQL_PORT",     "3306")
        MYSQL_DB       = os.environ.get("MYSQL_DB",       "heritage_db")
        SQLALCHEMY_DATABASE_URI = (
            f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}"
            f"@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DB}"
        )
    else:
        SQLALCHEMY_DATABASE_URI = "sqlite:///" + os.path.join(INSTANCE_DIR, "heritage.db")

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}

    UPLOAD_FOLDER = os.path.join(BASE_DIR, "static/uploads")

    MAX_CONTENT_LENGTH = 5 * 1024 * 1024

    # ─── Mail (SMTP) 
    MAIL_SERVER = "smtp.gmail.com"
    MAIL_PORT = 587
    MAIL_USERNAME = "theheritagesite319@gmail.com"
    MAIL_PASSWORD = "tyyp svwj srbh dzwu"
    MAIL_USE_TLS = True
    MAIL_USE_SSL = False
    MAIL_DEFAULT_SENDER = ("Heritage", "theheritagesite319@gmail.com")

    # ─── CSRF Protection 
    WTF_CSRF_ENABLED = True

    # ─── Session Security 
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = False       
