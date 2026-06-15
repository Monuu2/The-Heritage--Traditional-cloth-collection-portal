from flask import Blueprint, render_template
from flask_login import login_required

pages_bp = Blueprint("pages", __name__)

@pages_bp.route("/faq")
def faq():
    return render_template("pages/faq.html")

@pages_bp.route("/help")
def help_center():
    return render_template("pages/help.html")

@pages_bp.route("/privacy")
def privacy():
    return render_template("pages/privacy.html")

@pages_bp.route("/terms")
def terms():
    return render_template("pages/terms.html")

@pages_bp.route("/licenses")
def licenses():
    return render_template("pages/licenses.html")

@pages_bp.route("/feedback", methods=["GET", "POST"])
@login_required
def feedback():
    from flask import request, flash
    if request.method == "POST":
        flash("Thank you for your feedback!")
    return render_template("pages/feedback.html")

@pages_bp.route("/dashboard")
@login_required
def dashboard():
    return render_template("user/dashboard.html")

@pages_bp.route("/contact_us", methods=["GET", "POST"])
def contact_us():
    from flask import request, flash
    if request.method == "POST":
        flash("Message sent! We will get back to you soon.")
    return render_template("contact_us.html")
