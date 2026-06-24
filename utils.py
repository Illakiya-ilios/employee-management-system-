import os
from functools import wraps
from flask import abort, current_app
from flask_login import current_user
from sql import AuditLog, db


def role_required(*roles):
    """Allow one or more roles."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not current_user.is_authenticated:
                abort(403)
            if current_user.role not in roles:
                abort(403)
            return func(*args, **kwargs)
        return wrapper
    return decorator


def log_action(user_id, action, target_table=None, target_id=None, details=None):
    entry = AuditLog(
        user_id=user_id,
        action=action,
        target_table=target_table,
        target_id=target_id,
        details=details,
    )
    db.session.add(entry)
    db.session.commit()


ALLOWED_EXTENSIONS = {"pdf", "png", "jpg", "jpeg"}


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def save_upload(file, subfolder):
    """Save an uploaded file and return the relative path."""
    from werkzeug.utils import secure_filename
    import uuid
    if not file or file.filename == "":
        return None
    if not allowed_file(file.filename):
        return None
    ext = file.filename.rsplit(".", 1)[1].lower()
    filename = f"{uuid.uuid4().hex}.{ext}"
    dest = os.path.join(current_app.config["UPLOAD_FOLDER"], subfolder)
    os.makedirs(dest, exist_ok=True)
    file.save(os.path.join(dest, filename))
    return os.path.join(subfolder, filename).replace("\\", "/")
