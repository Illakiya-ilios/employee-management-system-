from flask import render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from app import app
from sql import db, User, EmployeeProfile


@app.route("/")
def home():
    if current_user.is_authenticated:
        return _redirect_by_role(current_user)
    return redirect(url_for("login"))


@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return _redirect_by_role(current_user)

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")

        if not all([username, email, password]):
            flash("All fields are required.", "danger")
            return render_template("register.html")

        if password != confirm:
            flash("Passwords do not match.", "danger")
            return render_template("register.html")

        if User.query.filter_by(email=email).first():
            flash("An account with that email already exists.", "danger")
            return render_template("register.html")

        if User.query.filter_by(username=username).first():
            flash("Username already taken.", "danger")
            return render_template("register.html")

        user = User(
            username=username,
            email=email,
            password_hash=generate_password_hash(password),
            role="EMPLOYEE",
            is_approved=True,  # Employee accounts are active immediately; profile needs HR approval
        )
        db.session.add(user)
        db.session.flush()  # get user_id

        # Create an empty profile for step-by-step filling
        profile = EmployeeProfile(user_id=user.user_id, status="DRAFT")
        db.session.add(profile)
        db.session.commit()

        flash("Account created! Please complete your profile.", "success")
        login_user(user)
        return redirect(url_for("profile_step", step=1))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return _redirect_by_role(current_user)

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        user = User.query.filter_by(email=email).first()

        if not user or not check_password_hash(user.password_hash, password):
            flash("Invalid email or password.", "danger")
            return render_template("login.html")

        if not user.is_approved:
            flash("Your account is pending approval by the Super Admin.", "warning")
            return render_template("login.html")

        if not user.is_active:
            flash("Your account has been deactivated. Contact admin.", "danger")
            return render_template("login.html")

        login_user(user)
        return _redirect_by_role(user)

    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("login"))


def _redirect_by_role(user):
    if user.role == "SUPERADMIN":
        return redirect(url_for("admin_dashboard"))
    elif user.role == "HR":
        return redirect(url_for("hr_dashboard"))
    else:
        return redirect(url_for("employee_dashboard"))
