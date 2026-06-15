from functools import wraps
from flask import session, redirect, url_for, flash

def admin_required(f):

    @wraps(f)
    def decorated_function(*args, **kwargs):

        if not session.get("admin_logged_in"):

            flash("Admin access required", "danger")

            return redirect(url_for("auth.login"))

        return f(*args, **kwargs)

    return decorated_function