from flask import Blueprint, render_template, redirect, url_for, session, request
from models import db_session, Report, ReportStatus, FacilityType, User

web_bp = Blueprint("web_bp", __name__)

@web_bp.route("/")
def index():
    """Homepage with interactive public WebGIS map."""
    return render_template("index.html")


@web_bp.route("/lapor")
def form_lapor():
    """Step-by-step reporting wizard for citizens."""
    return render_template("lapor.html")


@web_bp.route("/laporan/<int:report_id>")
def report_detail_public(report_id: int):
    """Public report tracking page with status timeline."""
    return render_template("status.html", report_id=report_id)


@web_bp.route("/cek-status")
def cek_status():
    """Status lookup search page."""
    return render_template("status.html", report_id=None)


@web_bp.route("/login")
def login_page():
    """Login page for officers and admin."""
    if session.get("user_id"):
        return redirect(url_for("web_bp.dashboard_page"))
    return render_template("login.html")


@web_bp.route("/dashboard")
def dashboard_page():
    """Officer & Admin Management and Spatial Analytics Dashboard."""
    if not session.get("user_id"):
        return redirect(url_for("web_bp.login_page"))
    return render_template("dashboard.html")


@web_bp.route("/dashboard/laporan/<int:report_id>")
def dashboard_report_detail(report_id: int):
    """Officer report inspection and verification page."""
    if not session.get("user_id"):
        return redirect(url_for("web_bp.login_page"))
    return render_template("dashboard_detail.html", report_id=report_id)


@web_bp.route("/dashboard/pengaturan")
def dashboard_settings():
    """Admin configuration for spatial parameters and users."""
    if not session.get("user_id"):
        return redirect(url_for("web_bp.login_page"))
    if session.get("user_role") != "admin":
        return redirect(url_for("web_bp.dashboard_page"))
    return render_template("dashboard_settings.html")


@web_bp.route("/logout")
def logout():
    """Clear session and redirect to login page."""
    session.clear()
    return redirect(url_for("web_bp.login_page"))
