import os
from pathlib import Path
from flask import Flask, send_from_directory, jsonify, session, abort
from flask_cors import CORS

from config import Config
from models import init_db, db_session, Report, Photo, AIPrediction, FacilityType, ReportStatus, User
from services.spatial_service import get_boundary_polygon
from services.auth_service import get_current_user

# Import route blueprints
from routes.auth_routes import auth_bp
from routes.report_routes import report_bp
from routes.map_routes import map_bp
from routes.dashboard_routes import dashboard_bp
from routes.admin_routes import admin_bp
from routes.web_routes import web_bp


def create_app():
    app = Flask(__name__, static_folder="static", template_folder="templates")
    app.config.from_object(Config)
    
    CORS(app)
    
    # Initialize DB
    init_db()
    
    # Register blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(report_bp)
    app.register_blueprint(map_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(web_bp)
    
    # Static serving for public photos
    @app.route("/uploads/photos/public/<path:filename>")
    def serve_public_photos(filename):
        return send_from_directory(Config.UPLOAD_FOLDER_PUBLIC, filename)
        
    # Restricted serving for original photos (pengelola/admin only)
    @app.route("/uploads/photos/original/<path:filename>")
    def serve_original_photos(filename):
        user = get_current_user()
        if not user or user.role not in ["pengelola", "admin"]:
            abort(403)
        return send_from_directory(Config.UPLOAD_FOLDER_ORIGINAL, filename)
        
    @app.teardown_appcontext
    def shutdown_session(exception=None):
        db_session.remove()
        
    # Error handlers
    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"error": "Resource tidak ditemukan."}), 404
        
    @app.errorhandler(413)
    def file_too_large(e):
        return jsonify({"error": "Ukuran berkas melebihi batas maksimal (5 MB)."}), 413
        
    @app.errorhandler(500)
    def internal_error(e):
        return jsonify({"error": "Terjadi kesalahan internal server."}), 500
        
    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
