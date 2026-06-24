import json
import os
from flask import send_from_directory, current_app, abort
from flask_login import login_required
from app import app


# Jinja2 filter to parse JSON inside templates
@app.template_filter("from_json")
def from_json_filter(value):
    if not value:
        return []
    try:
        return json.loads(value)
    except Exception:
        return []


# Serve uploaded files securely
@app.route("/uploads/<path:filename>")
@login_required
def uploaded_file(filename):
    upload_folder = current_app.config["UPLOAD_FOLDER"]
    # Prevent directory traversal
    safe_path = os.path.normpath(os.path.join(upload_folder, filename))
    if not safe_path.startswith(os.path.normpath(upload_folder)):
        abort(403)
    directory = os.path.dirname(safe_path)
    name = os.path.basename(safe_path)
    return send_from_directory(directory, name)
