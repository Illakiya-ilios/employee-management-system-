# Legacy route kept for compatibility — HR approval is now handled in admindashboard.py
# This file is intentionally minimal.

from flask import redirect, url_for, flash
from flask_login import login_required
from app import app
from sql import db, User
from utils import role_required


@app.route("/approve_hr/<int:user_id>", methods=["POST"])
@login_required
@role_required("SUPERADMIN")
def approve_hr(user_id):
    user = User.query.get_or_404(user_id)
    user.is_approved = True
    db.session.commit()
    flash("HR Approved.", "success")
    return redirect(url_for("admin_hr_list"))
