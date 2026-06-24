import json
import os
from datetime import datetime

from flask import (
    render_template, request, redirect, url_for,
    flash, current_app, send_from_directory, abort
)
from flask_login import login_required, current_user

from app import app
from sql import db, User, Employee, EmployeeProfile, EmployeePayslip, AuditLog
from utils import role_required, save_upload, log_action


@app.route("/hr/dashboard")
@login_required
@role_required("HR")
def hr_dashboard():
    pending = EmployeeProfile.query.filter_by(status="PENDING").all()
    approved = EmployeeProfile.query.filter_by(status="APPROVED").all()
    rejected = EmployeeProfile.query.filter_by(status="REJECTED").all()

    return render_template(
        "hr_dashboard.html",
        pending=pending,
        approved=approved,
        rejected=rejected,
    )


@app.route("/hr/profile/<int:profile_id>")
@login_required
@role_required("HR")
def hr_view_profile(profile_id):
    profile = EmployeeProfile.query.get_or_404(profile_id)
    ec = json.loads(profile.emergency_contacts_json or "[]")
    history = json.loads(profile.employment_history_json or "[]")
    docs = json.loads(profile.documents_json or "[]")

    return render_template(
        "hr_view_profile.html",
        profile=profile,
        emergency_contacts=ec,
        employment_history=history,
        documents=docs,
    )


@app.route("/hr/profile/<int:profile_id>/approve", methods=["POST"])
@login_required
@role_required("HR")
def hr_approve_profile(profile_id):
    profile = EmployeeProfile.query.get_or_404(profile_id)
    remarks = request.form.get("remarks", "").strip()

    if profile.status != "PENDING":
        flash("Profile is not in pending state.", "warning")
        return redirect(url_for("hr_view_profile", profile_id=profile_id))

    profile.status = "APPROVED"
    profile.hr_remarks = remarks
    profile.reviewed_by = current_user.user_id
    profile.reviewed_at = datetime.utcnow()

    # Create the live Employee record
    employee = Employee.query.filter_by(user_id=profile.user_id).first()
    if not employee:
        # Generate employee code
        count = Employee.query.count() + 1
        emp_code = f"EMP{count:04d}"

        employee = Employee(
            user_id=profile.user_id,
            profile_id=profile.profile_id,
            employee_code=emp_code,
            first_name=profile.first_name,
            middle_name=profile.middle_name,
            last_name=profile.last_name,
            date_of_birth=profile.date_of_birth,
            gender=profile.gender,
            blood_group=profile.blood_group,
            religion=profile.religion,
            nationality=profile.nationality,
            place_of_birth=profile.place_of_birth,
            mother_tongue=profile.mother_tongue,
            marital_status=profile.marital_status,
            personal_email=profile.personal_email,
            mobile_number=profile.mobile_number,
            photo_path=profile.photo_path,
            designation=profile.designation,
            department=profile.department,
            joining_date=profile.joining_date,
            perm_address_line1=profile.perm_address_line1,
            perm_city=profile.perm_city,
            perm_state=profile.perm_state,
            perm_country=profile.perm_country,
            curr_address_line1=profile.curr_address_line1,
            curr_city=profile.curr_city,
            bank_name=profile.bank_name,
            account_number=profile.account_number,
            ifsc_code=profile.ifsc_code,
            pf_number=profile.pf_number,
            uan_number=profile.uan_number,
        )
        db.session.add(employee)

    db.session.commit()

    log_action(
        current_user.user_id,
        "APPROVE_PROFILE",
        "employee_profiles",
        profile_id,
        f"Approved profile for user_id={profile.user_id}",
    )

    flash(f"Profile approved. Employee code: {employee.employee_code}", "success")
    return redirect(url_for("hr_dashboard"))


@app.route("/hr/profile/<int:profile_id>/reject", methods=["POST"])
@login_required
@role_required("HR")
def hr_reject_profile(profile_id):
    profile = EmployeeProfile.query.get_or_404(profile_id)
    remarks = request.form.get("remarks", "").strip()

    if not remarks:
        flash("Please provide rejection remarks.", "danger")
        return redirect(url_for("hr_view_profile", profile_id=profile_id))

    profile.status = "REJECTED"
    profile.hr_remarks = remarks
    profile.reviewed_by = current_user.user_id
    profile.reviewed_at = datetime.utcnow()
    db.session.commit()

    log_action(
        current_user.user_id,
        "REJECT_PROFILE",
        "employee_profiles",
        profile_id,
        f"Rejected profile for user_id={profile.user_id}. Reason: {remarks}",
    )

    flash("Profile rejected. Employee will be notified.", "warning")
    return redirect(url_for("hr_dashboard"))


# ── Payslip Management ─────────────────────────────────────────────────────────

@app.route("/hr/payslips")
@login_required
@role_required("HR")
def hr_payslips():
    employees = Employee.query.filter_by(employee_status="ACTIVE").all()
    return render_template("hr_payslips.html", employees=employees)


@app.route("/hr/payslip/upload/<int:employee_id>", methods=["GET", "POST"])
@login_required
@role_required("HR")
def hr_upload_payslip(employee_id):
    employee = Employee.query.get_or_404(employee_id)

    if request.method == "POST":
        month = request.form.get("month", type=int)
        year = request.form.get("year", type=int)
        payslip_file = request.files.get("payslip_file")

        if not all([month, year, payslip_file]):
            flash("Month, year and file are all required.", "danger")
            return redirect(request.url)

        if payslip_file.filename == "":
            flash("No file selected.", "danger")
            return redirect(request.url)

        path = save_upload(payslip_file, "payslips")
        if not path:
            flash("Invalid file type. Only PDF, PNG, JPG allowed.", "danger")
            return redirect(request.url)

        # Upsert — replace if same month/year already exists
        existing = EmployeePayslip.query.filter_by(
            employee_id=employee_id, month=month, year=year
        ).first()
        if existing:
            # Delete old file
            old_path = os.path.join(current_app.config["UPLOAD_FOLDER"], existing.file_path)
            if os.path.exists(old_path):
                os.remove(old_path)
            existing.file_path = path
            existing.uploaded_by = current_user.user_id
            existing.uploaded_at = datetime.utcnow()
        else:
            ps = EmployeePayslip(
                employee_id=employee_id,
                month=month,
                year=year,
                file_path=path,
                uploaded_by=current_user.user_id,
            )
            db.session.add(ps)

        db.session.commit()

        log_action(
            current_user.user_id,
            "UPLOAD_PAYSLIP",
            "employee_payslips",
            employee_id,
            f"Uploaded payslip {month}/{year} for employee_id={employee_id}",
        )

        flash(f"Payslip for {month}/{year} uploaded successfully.", "success")
        return redirect(url_for("hr_payslips"))

    # All payslips for this employee (for display)
    all_payslips = (
        EmployeePayslip.query
        .filter_by(employee_id=employee_id)
        .order_by(EmployeePayslip.year.desc(), EmployeePayslip.month.desc())
        .all()
    )
    months = [
        (1, "January"), (2, "February"), (3, "March"), (4, "April"),
        (5, "May"), (6, "June"), (7, "July"), (8, "August"),
        (9, "September"), (10, "October"), (11, "November"), (12, "December"),
    ]
    current_year = datetime.utcnow().year
    years = list(range(current_year - 3, current_year + 2))

    return render_template(
        "hr_upload_payslip.html",
        employee=employee,
        all_payslips=all_payslips,
        months=months,
        years=years,
    )


@app.route("/hr/payslip/delete/<int:payslip_id>", methods=["POST"])
@login_required
@role_required("HR")
def hr_delete_payslip(payslip_id):
    ps = EmployeePayslip.query.get_or_404(payslip_id)
    employee_id = ps.employee_id
    old_path = os.path.join(current_app.config["UPLOAD_FOLDER"], ps.file_path)
    if os.path.exists(old_path):
        os.remove(old_path)
    db.session.delete(ps)
    db.session.commit()
    flash("Payslip deleted.", "info")
    return redirect(url_for("hr_upload_payslip", employee_id=employee_id))
