import json
import os
from datetime import datetime

from flask import (
    render_template, request, redirect, url_for,
    flash, send_from_directory, abort, current_app
)
from flask_login import login_required, current_user

from app import app
from sql import db, Employee, EmployeeProfile, EmployeePayslip
from utils import role_required, save_upload

TOTAL_STEPS = 6


def _get_or_404_profile():
    profile = EmployeeProfile.query.filter_by(user_id=current_user.user_id).first()
    if not profile:
        abort(404)
    return profile


# ── Multi-step profile registration ───────────────────────────────────────────

@app.route("/profile/step/<int:step>", methods=["GET", "POST"])
@login_required
@role_required("EMPLOYEE")
def profile_step(step):
    if step < 1 or step > TOTAL_STEPS:
        abort(404)

    profile = EmployeeProfile.query.filter_by(user_id=current_user.user_id).first()
    if not profile:
        profile = EmployeeProfile(user_id=current_user.user_id, status="DRAFT")
        db.session.add(profile)
        db.session.commit()

    # Approved profiles are read-only
    if profile.status == "APPROVED":
        flash("Your profile has already been approved and cannot be edited.", "info")
        return redirect(url_for("employee_dashboard"))

    if request.method == "POST":
        _save_step(step, profile)
        db.session.commit()

        action = request.form.get("action", "next")
        if action == "next" and step < TOTAL_STEPS:
            return redirect(url_for("profile_step", step=step + 1))
        elif action == "prev" and step > 1:
            return redirect(url_for("profile_step", step=step - 1))
        else:
            return redirect(url_for("profile_review"))

    return render_template(
        f"profile/step{step}.html",
        profile=profile,
        step=step,
        total_steps=TOTAL_STEPS,
    )


def _save_step(step, profile):
    f = request.form

    if step == 1:
        profile.first_name = f.get("first_name", "").strip()
        profile.middle_name = f.get("middle_name", "").strip()
        profile.last_name = f.get("last_name", "").strip()
        dob = f.get("date_of_birth")
        profile.date_of_birth = datetime.strptime(dob, "%Y-%m-%d").date() if dob else None
        profile.gender = f.get("gender")
        profile.blood_group = f.get("blood_group")
        profile.religion = f.get("religion")
        profile.nationality = f.get("nationality")
        profile.place_of_birth = f.get("place_of_birth")
        profile.mother_tongue = f.get("mother_tongue")
        profile.marital_status = f.get("marital_status")
        profile.personal_email = f.get("personal_email")
        profile.mobile_number = f.get("mobile_number")
        # Photo upload
        photo = request.files.get("photo")
        if photo and photo.filename:
            path = save_upload(photo, "photos")
            if path:
                profile.photo_path = path
        profile.step1_done = True

    elif step == 2:
        profile.perm_address_line1 = f.get("perm_address_line1")
        profile.perm_address_line2 = f.get("perm_address_line2")
        profile.perm_city = f.get("perm_city")
        profile.perm_state = f.get("perm_state")
        profile.perm_country = f.get("perm_country")
        profile.perm_postal_code = f.get("perm_postal_code")
        profile.curr_same_as_perm = "curr_same_as_perm" in f
        if profile.curr_same_as_perm:
            profile.curr_address_line1 = profile.perm_address_line1
            profile.curr_address_line2 = profile.perm_address_line2
            profile.curr_city = profile.perm_city
            profile.curr_state = profile.perm_state
            profile.curr_country = profile.perm_country
            profile.curr_postal_code = profile.perm_postal_code
        else:
            profile.curr_address_line1 = f.get("curr_address_line1")
            profile.curr_address_line2 = f.get("curr_address_line2")
            profile.curr_city = f.get("curr_city")
            profile.curr_state = f.get("curr_state")
            profile.curr_country = f.get("curr_country")
            profile.curr_postal_code = f.get("curr_postal_code")
        profile.step2_done = True

    elif step == 3:
        names = f.getlist("ec_name")
        rels = f.getlist("ec_relationship")
        phones = f.getlist("ec_phone")
        contacts = []
        for n, r, p in zip(names, rels, phones):
            if n.strip():
                contacts.append({"name": n.strip(), "relationship": r.strip(), "phone": p.strip()})
        profile.emergency_contacts_json = json.dumps(contacts)
        profile.step3_done = True

    elif step == 4:
        profile.designation = f.get("designation")
        profile.department = f.get("department")
        jd = f.get("joining_date")
        profile.joining_date = datetime.strptime(jd, "%Y-%m-%d").date() if jd else None
        # Employment history rows
        employers = f.getlist("employer_name")
        positions = f.getlist("position_held")
        from_dates = f.getlist("emp_from")
        to_dates = f.getlist("emp_to")
        history = []
        for emp, pos, fr, to in zip(employers, positions, from_dates, to_dates):
            if emp.strip():
                history.append({
                    "employer": emp.strip(),
                    "position": pos.strip(),
                    "from": fr,
                    "to": to,
                })
        profile.employment_history_json = json.dumps(history)
        profile.step4_done = True

    elif step == 5:
        profile.bank_name = f.get("bank_name")
        profile.account_number = f.get("account_number")
        profile.branch_name = f.get("branch_name")
        profile.ifsc_code = f.get("ifsc_code")
        profile.pf_number = f.get("pf_number")
        profile.uan_number = f.get("uan_number")
        profile.step5_done = True

    elif step == 6:
        doc_types = f.getlist("doc_type")
        doc_numbers = f.getlist("doc_number")
        doc_files = request.files.getlist("doc_file")
        docs = []
        existing = json.loads(profile.documents_json or "[]")
        existing_map = {d["type"]: d for d in existing}
        for dtype, dnum, dfile in zip(doc_types, doc_numbers, doc_files):
            if not dtype:
                continue
            path = None
            if dfile and dfile.filename:
                path = save_upload(dfile, "documents")
            if path is None:
                path = existing_map.get(dtype, {}).get("file_path")
            docs.append({"type": dtype, "number": dnum, "file_path": path})
        profile.documents_json = json.dumps(docs)
        profile.step6_done = True


@app.route("/profile/review", methods=["GET", "POST"])
@login_required
@role_required("EMPLOYEE")
def profile_review():
    profile = _get_or_404_profile()

    if request.method == "POST":
        if profile.status in ("APPROVED",):
            flash("Already approved.", "info")
            return redirect(url_for("employee_dashboard"))

        profile.status = "PENDING"
        profile.submitted = True
        profile.submitted_at = datetime.utcnow()
        db.session.commit()
        flash("Profile submitted for HR review!", "success")
        return redirect(url_for("employee_dashboard"))

    ec = json.loads(profile.emergency_contacts_json or "[]")
    history = json.loads(profile.employment_history_json or "[]")
    docs = json.loads(profile.documents_json or "[]")

    return render_template(
        "profile/review.html",
        profile=profile,
        emergency_contacts=ec,
        employment_history=history,
        documents=docs,
        total_steps=TOTAL_STEPS,
    )


# ── Employee Dashboard ─────────────────────────────────────────────────────────

@app.route("/employee/dashboard")
@login_required
@role_required("EMPLOYEE")
def employee_dashboard():
    profile = EmployeeProfile.query.filter_by(user_id=current_user.user_id).first()
    employee = Employee.query.filter_by(user_id=current_user.user_id).first()

    payslips = []
    if employee:
        # Show only last 3 payslips
        payslips = (
            EmployeePayslip.query
            .filter_by(employee_id=employee.employee_id)
            .order_by(EmployeePayslip.year.desc(), EmployeePayslip.month.desc())
            .limit(3)
            .all()
        )

    return render_template(
        "employee_dashboard.html",
        profile=profile,
        employee=employee,
        payslips=payslips,
    )


@app.route("/employee/payslip/download/<int:payslip_id>")
@login_required
@role_required("EMPLOYEE")
def download_payslip(payslip_id):
    employee = Employee.query.filter_by(user_id=current_user.user_id).first()
    if not employee:
        abort(403)

    payslip = EmployeePayslip.query.filter_by(
        payslip_id=payslip_id,
        employee_id=employee.employee_id,
    ).first_or_404()

    # Only allow last 3
    all_ps = (
        EmployeePayslip.query
        .filter_by(employee_id=employee.employee_id)
        .order_by(EmployeePayslip.year.desc(), EmployeePayslip.month.desc())
        .limit(3)
        .all()
    )
    allowed_ids = [p.payslip_id for p in all_ps]
    if payslip_id not in allowed_ids:
        abort(403)

    upload_folder = current_app.config["UPLOAD_FOLDER"]
    directory = os.path.dirname(os.path.join(upload_folder, payslip.file_path))
    filename = os.path.basename(payslip.file_path)
    return send_from_directory(directory, filename, as_attachment=True)
