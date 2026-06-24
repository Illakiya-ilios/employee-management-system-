from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash

db = SQLAlchemy()


def create_super_admin():
    admin = User.query.filter_by(role="SUPERADMIN").first()
    if not admin:
        admin = User(
            username="admin",
            email="admin@company.com",
            password_hash=generate_password_hash("admin123"),
            role="SUPERADMIN",
            is_approved=True,
        )
        db.session.add(admin)
        db.session.commit()
        print("Super admin created: admin@company.com / admin123")


# ============================================================
# USER (Login accounts)
# ============================================================
class User(UserMixin, db.Model):
    __tablename__ = "users"

    user_id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False)
    # Roles: SUPERADMIN | HR | EMPLOYEE
    is_approved = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def get_id(self):
        return str(self.user_id)


# ============================================================
# EMPLOYEE PROFILE (pending approval)
# ============================================================
class EmployeeProfile(db.Model):
    """
    Stores the multi-step registration data BEFORE HR approval.
    Once approved, a proper Employee record is created.
    """
    __tablename__ = "employee_profiles"

    profile_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.user_id"), unique=True)
    user = db.relationship(
        "User",
        foreign_keys=[user_id],
        backref=db.backref("profile", uselist=False),
    )

    # Step completion flags
    step1_done = db.Column(db.Boolean, default=False)
    step2_done = db.Column(db.Boolean, default=False)
    step3_done = db.Column(db.Boolean, default=False)
    step4_done = db.Column(db.Boolean, default=False)
    step5_done = db.Column(db.Boolean, default=False)
    step6_done = db.Column(db.Boolean, default=False)
    submitted = db.Column(db.Boolean, default=False)

    # Approval status: DRAFT | PENDING | APPROVED | REJECTED
    status = db.Column(db.String(20), default="DRAFT")
    hr_remarks = db.Column(db.Text)
    reviewed_by = db.Column(db.Integer, db.ForeignKey("users.user_id"), nullable=True)
    reviewed_at = db.Column(db.DateTime, nullable=True)

    submitted_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # ── Step 1: Personal Info ──────────────────────────────
    first_name = db.Column(db.String(100))
    middle_name = db.Column(db.String(100))
    last_name = db.Column(db.String(100))
    date_of_birth = db.Column(db.Date)
    gender = db.Column(db.String(20))
    blood_group = db.Column(db.String(10))
    religion = db.Column(db.String(100))
    nationality = db.Column(db.String(100))
    place_of_birth = db.Column(db.String(200))
    mother_tongue = db.Column(db.String(100))
    marital_status = db.Column(db.String(50))
    personal_email = db.Column(db.String(120))
    mobile_number = db.Column(db.String(20))
    photo_path = db.Column(db.String(500))

    # ── Step 2: Address ────────────────────────────────────
    perm_address_line1 = db.Column(db.String(255))
    perm_address_line2 = db.Column(db.String(255))
    perm_city = db.Column(db.String(100))
    perm_state = db.Column(db.String(100))
    perm_country = db.Column(db.String(100))
    perm_postal_code = db.Column(db.String(20))

    curr_same_as_perm = db.Column(db.Boolean, default=False)
    curr_address_line1 = db.Column(db.String(255))
    curr_address_line2 = db.Column(db.String(255))
    curr_city = db.Column(db.String(100))
    curr_state = db.Column(db.String(100))
    curr_country = db.Column(db.String(100))
    curr_postal_code = db.Column(db.String(20))

    # ── Step 3: Emergency Contacts (JSON) ─────────────────
    emergency_contacts_json = db.Column(db.Text)  # JSON list

    # ── Step 4: Employment & Education ────────────────────
    designation = db.Column(db.String(150))
    department = db.Column(db.String(150))
    joining_date = db.Column(db.Date)
    employment_history_json = db.Column(db.Text)  # JSON list

    # ── Step 5: Bank & PF ─────────────────────────────────
    bank_name = db.Column(db.String(200))
    account_number = db.Column(db.String(100))
    branch_name = db.Column(db.String(150))
    ifsc_code = db.Column(db.String(20))
    pf_number = db.Column(db.String(100))
    uan_number = db.Column(db.String(100))

    # ── Step 6: Documents ─────────────────────────────────
    documents_json = db.Column(db.Text)  # JSON list of {type, number, file_path}


# ============================================================
# EMPLOYEE (approved, live record)
# ============================================================
class Employee(db.Model):
    __tablename__ = "employees"

    employee_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.user_id"), unique=True)
    profile_id = db.Column(db.Integer, db.ForeignKey("employee_profiles.profile_id"))

    employee_code = db.Column(db.String(50), unique=True)
    first_name = db.Column(db.String(100))
    middle_name = db.Column(db.String(100))
    last_name = db.Column(db.String(100))
    date_of_birth = db.Column(db.Date)
    gender = db.Column(db.String(20))
    blood_group = db.Column(db.String(10))
    religion = db.Column(db.String(100))
    nationality = db.Column(db.String(100))
    place_of_birth = db.Column(db.String(200))
    mother_tongue = db.Column(db.String(100))
    marital_status = db.Column(db.String(50))
    personal_email = db.Column(db.String(120))
    mobile_number = db.Column(db.String(20))
    photo_path = db.Column(db.String(500))

    designation = db.Column(db.String(150))
    department = db.Column(db.String(150))
    joining_date = db.Column(db.Date)
    employee_status = db.Column(db.String(20), default="ACTIVE")

    # Address
    perm_address_line1 = db.Column(db.String(255))
    perm_city = db.Column(db.String(100))
    perm_state = db.Column(db.String(100))
    perm_country = db.Column(db.String(100))
    curr_address_line1 = db.Column(db.String(255))
    curr_city = db.Column(db.String(100))

    # Bank
    bank_name = db.Column(db.String(200))
    account_number = db.Column(db.String(100))
    ifsc_code = db.Column(db.String(20))

    # PF
    pf_number = db.Column(db.String(100))
    uan_number = db.Column(db.String(100))

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship("User", backref=db.backref("employee", uselist=False))
    payslips = db.relationship(
        "EmployeePayslip", backref="employee", cascade="all, delete-orphan",
        order_by="desc(EmployeePayslip.year), desc(EmployeePayslip.month)"
    )


# ============================================================
# PAYSLIP
# ============================================================
class EmployeePayslip(db.Model):
    __tablename__ = "employee_payslips"

    payslip_id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey("employees.employee_id"), nullable=False)
    month = db.Column(db.Integer, nullable=False)
    year = db.Column(db.Integer, nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    uploaded_by = db.Column(db.Integer, db.ForeignKey("users.user_id"))
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint("employee_id", "month", "year", name="unique_employee_payslip"),
    )


# ============================================================
# AUDIT LOG
# ============================================================
class AuditLog(db.Model):
    __tablename__ = "audit_logs"

    audit_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.user_id"))
    action = db.Column(db.String(200))
    target_table = db.Column(db.String(100))
    target_id = db.Column(db.Integer)
    details = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship("User", backref="audit_logs")
