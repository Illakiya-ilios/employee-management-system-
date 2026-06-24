from flask import render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from werkzeug.security import generate_password_hash

from app import app
from sql import db, User, Employee, EmployeeProfile, EmployeePayslip, AuditLog
from utils import role_required, log_action


@app.route("/admin/dashboard")
@login_required
@role_required("SUPERADMIN")
def admin_dashboard():
    total_employees = Employee.query.count()
    total_hr = User.query.filter_by(role="HR").count()
    pending_hr = User.query.filter_by(role="HR", is_approved=False).count()
    pending_profiles = EmployeeProfile.query.filter_by(status="PENDING").count()
    recent_logs = AuditLog.query.order_by(AuditLog.created_at.desc()).limit(10).all()

    return render_template(
        "admin_dashboard.html",
        total_employees=total_employees,
        total_hr=total_hr,
        pending_hr=pending_hr,
        pending_profiles=pending_profiles,
        recent_logs=recent_logs,
    )


@app.route("/admin/employees")
@login_required
@role_required("SUPERADMIN")
def admin_employees():
    query = request.args.get("q", "").strip()
    dept = request.args.get("dept", "").strip()
    status = request.args.get("status", "").strip()

    emp_q = Employee.query
    if query:
        emp_q = emp_q.filter(
            (Employee.first_name.ilike(f"%{query}%")) |
            (Employee.last_name.ilike(f"%{query}%")) |
            (Employee.employee_code.ilike(f"%{query}%"))
        )
    if dept:
        emp_q = emp_q.filter(Employee.department.ilike(f"%{dept}%"))
    if status:
        emp_q = emp_q.filter_by(employee_status=status)

    employees = emp_q.order_by(Employee.created_at.desc()).all()
    departments = db.session.query(Employee.department).distinct().all()
    departments = [d[0] for d in departments if d[0]]

    return render_template(
        "admin_employees.html",
        employees=employees,
        departments=departments,
        query=query,
        dept=dept,
        status=status,
    )


@app.route("/admin/employee/<int:employee_id>")
@login_required
@role_required("SUPERADMIN")
def admin_view_employee(employee_id):
    employee = Employee.query.get_or_404(employee_id)
    payslips = (
        EmployeePayslip.query
        .filter_by(employee_id=employee_id)
        .order_by(EmployeePayslip.year.desc(), EmployeePayslip.month.desc())
        .all()
    )
    logs = AuditLog.query.filter(
        (AuditLog.target_id == employee_id) |
        (AuditLog.user_id == employee.user_id)
    ).order_by(AuditLog.created_at.desc()).limit(20).all()

    return render_template(
        "admin_view_employee.html",
        employee=employee,
        payslips=payslips,
        logs=logs,
    )


@app.route("/admin/employee/<int:employee_id>/toggle_status", methods=["POST"])
@login_required
@role_required("SUPERADMIN")
def admin_toggle_employee_status(employee_id):
    employee = Employee.query.get_or_404(employee_id)
    new_status = "INACTIVE" if employee.employee_status == "ACTIVE" else "ACTIVE"
    employee.employee_status = new_status

    # Also toggle user account
    if employee.user:
        employee.user.is_active = (new_status == "ACTIVE")

    db.session.commit()
    log_action(current_user.user_id, f"SET_EMPLOYEE_{new_status}", "employees", employee_id)
    flash(f"Employee status set to {new_status}.", "info")
    return redirect(url_for("admin_view_employee", employee_id=employee_id))


# ── HR Management ─────────────────────────────────────────────────────────────

@app.route("/admin/hr")
@login_required
@role_required("SUPERADMIN")
def admin_hr_list():
    hr_users = User.query.filter_by(role="HR").order_by(User.created_at.desc()).all()
    return render_template("admin_hr_list.html", hr_users=hr_users)


@app.route("/admin/hr/create", methods=["GET", "POST"])
@login_required
@role_required("SUPERADMIN")
def admin_create_hr():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not all([username, email, password]):
            flash("All fields required.", "danger")
            return render_template("admin_create_hr.html")

        if User.query.filter_by(email=email).first():
            flash("Email already in use.", "danger")
            return render_template("admin_create_hr.html")

        hr = User(
            username=username,
            email=email,
            password_hash=generate_password_hash(password),
            role="HR",
            is_approved=True,
        )
        db.session.add(hr)
        db.session.commit()
        log_action(current_user.user_id, "CREATE_HR", "users", hr.user_id, f"Created HR: {email}")
        flash(f"HR account created for {email}.", "success")
        return redirect(url_for("admin_hr_list"))

    return render_template("admin_create_hr.html")


@app.route("/admin/hr/<int:user_id>/toggle", methods=["POST"])
@login_required
@role_required("SUPERADMIN")
def admin_toggle_hr(user_id):
    user = User.query.get_or_404(user_id)
    if user.role != "HR":
        abort(400)
    user.is_approved = not user.is_approved
    user.is_active = user.is_approved
    db.session.commit()
    state = "enabled" if user.is_approved else "disabled"
    log_action(current_user.user_id, f"HR_{state.upper()}", "users", user_id)
    flash(f"HR account {state}.", "info")
    return redirect(url_for("admin_hr_list"))


# ── Audit Logs ─────────────────────────────────────────────────────────────────

@app.route("/admin/logs")
@login_required
@role_required("SUPERADMIN")
def admin_logs():
    page = request.args.get("page", 1, type=int)
    logs = AuditLog.query.order_by(AuditLog.created_at.desc()).paginate(page=page, per_page=30)
    return render_template("admin_logs.html", logs=logs)
