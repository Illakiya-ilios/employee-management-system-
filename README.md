# Employee Management App

## Project Overview

This is a Flask-based Human Resources / Employee Management application. It supports three user roles:
- `SUPERADMIN` — manages HR accounts, employees, and audit logs.
- `HR` — reviews employee profile submissions, approves/rejects them, and uploads payslips.
- `EMPLOYEE` — registers, fills a multi-step profile, submits it for approval, and views their dashboard.

The application uses SQLite (`instance/hr_employee_management.db`) via SQLAlchemy.

## How to Run

1. Install dependencies (Flask, Flask-Login, Flask-SQLAlchemy, Werkzeug).
2. Run `python app.py` from the project root.
3. The app creates the database and a default super admin on startup.
4. Access the app in a browser at `http://127.0.0.1:5000`.

> Default super admin credentials created by `create_super_admin()` in `sql.py`:
> - Email: `admin@company.com`
> - Password: `admin123`

## Main Entry Point

- `app.py`
  - Creates the Flask application and configures:
    - `SECRET_KEY`
    - `SQLALCHEMY_DATABASE_URI`
    - Upload folders and allowed file size
  - Initializes `db` and `LoginManager`
  - Defines the `user_loader` callback for Flask-Login
  - Imports route modules so their routes are registered
  - Calls `db.create_all()` inside app context, then creates the super admin
  - Starts the development server with `app.run(debug=True)`

## Database and Models

- `sql.py`
  - Defines `db = SQLAlchemy()`
  - Defines all ORM models:
    - `User` — login credentials and role state
    - `EmployeeProfile` — employee registration profile data before HR approval
    - `Employee` — approved / live employee record
    - `EmployeePayslip` — uploaded payslip file metadata
    - `AuditLog` — action audit trail
  - Creates a default `SUPERADMIN` user if one does not exist

### Important Models

- `User`
  - `role` values: `SUPERADMIN`, `HR`, `EMPLOYEE`
  - `is_approved` controls whether login is active
  - `is_active` disables accounts when toggled by admin

- `EmployeeProfile`
  - Stores all registration steps and approval status
  - Fields include personal info, address, emergency contacts, employment history, bank/PF data, document metadata
  - Flags `step1_done` through `step6_done` track progress

- `Employee`
  - Live employee record created after HR approval
  - Linked to a `User` and the original `EmployeeProfile`

- `EmployeePayslip`
  - Stores uploaded payslip files with a unique constraint per employee/month/year

- `AuditLog`
  - Stores user actions, target tables, and details for audit tracking

## Authentication and Registration

- `auth.py`
  - Routes:
    - `/` — home route redirects logged-in users to their dashboard or to login
    - `/register` — employee registration
    - `/login` — authentication
    - `/logout` — logout
  - Registration flow:
    - Creates a new `User` with role `EMPLOYEE`
    - Sets `is_approved=True` so the user can log in immediately
    - Creates an associated `EmployeeProfile` in `DRAFT` state
    - Logs the user in and redirects to `profile_step` for step 1
  - Login flow:
    - Verifies credentials
    - Rejects login if `is_approved=False` or `is_active=False`
    - Redirects by role to the correct dashboard

- `utils.py`
  - Helper functions:
    - `role_required(*roles)` — route decorator for role-based access control
    - `log_action()` — writes entries to `AuditLog`
    - `allowed_file()` — checks file extension against allowed upload types
    - `save_upload()` — saves uploaded files under `uploads/` and returns a relative path

## Route Modules and Workflows

### Admin Workflow

- `admindashboard.py`
  - Requires `SUPERADMIN`
  - Routes:
    - `/admin/dashboard` — admin overview with employee count, HR count, pending approvals, and recent logs
    - `/admin/employees` — employee list with search and filters
    - `/admin/employee/<employee_id>` — employee details page
    - `/admin/employee/<employee_id>/toggle_status` — activate/deactivate employee and user account
    - `/admin/hr` — list HR accounts
    - `/admin/hr/create` — create a new HR user
    - `/admin/hr/<user_id>/toggle` — enable or disable an HR account
    - `/admin/logs` — audit log list page
  - Uses `log_action()` for audit tracking when HR/users are created or toggled

### HR Workflow

- `HRdashboard.py`
  - Requires `HR`
  - Routes:
    - `/hr/dashboard` — lists pending, approved, and rejected employee profiles
    - `/hr/profile/<profile_id>` — view detailed profile submission
    - `/hr/profile/<profile_id>/approve` — approve a submitted profile
    - `/hr/profile/<profile_id>/reject` — reject a profile with remarks
    - `/hr/payslips` — show active employees for payslip upload
    - `/hr/payslip/upload/<employee_id>` — upload or update a payslip file for an employee
    - `/hr/payslip/delete/<payslip_id>` — delete an uploaded payslip
  - Approval logic:
    - HR approval marks the profile `APPROVED`
    - Creates a new `Employee` record from the approved `EmployeeProfile`
    - Generates an `EMPxxxx` employee code

### Employee Workflow

- `employeedashboard.py`
  - Requires `EMPLOYEE`
  - Route:
    - `/employee/dashboard` — employee home page and profile status summary
  - The employee dashboard shows:
    - `DRAFT` or `PENDING` profile status
    - rejection remarks when rejected
    - an option to continue the multi-step profile
    - approved profile summary and payslip downloads once approved

### File Serving and Uploads

- `approveHR.py`
  - Legacy route for approving HR users at `/approve_hr/<user_id>`
  - The code is minimal and only used by `SUPERADMIN`

- `dashboards.py`
  - Contains file-serving route:
    - `/uploads/<path:filename>` — serves uploaded files with path traversal protection
  - This route is used by templates to display uploaded images or download files

## Template Mapping

- `templates/base.html` — shared layout, navigation, flash messages, role-specific sidebar
- `templates/login.html` — login page
- `templates/register.html` — new employee registration page
- `templates/admin_*.html` — admin pages
- `templates/hr_*.html` — HR pages
- `templates/employee_dashboard.html` — employee dashboard
- `templates/profile/step_base.html` — shared layout for profile steps
- `templates/profile/step1.html` through `step6.html` — multi-step employee registration forms
- `templates/profile/review.html` — profile review and submit page

## Employee Profile Workflow

1. Employee registers at `/register`
2. A `User` and `EmployeeProfile` are created
3. User is redirected to `profile_step` step 1
4. Employee completes:
   - Step 1: personal info
   - Step 2: address
   - Step 3: emergency contacts
   - Step 4: employment and education
   - Step 5: bank and PF details
   - Step 6: documents
5. Employee reviews and submits the profile for HR approval
6. HR reviews at `/hr/profile/<profile_id>` and approves or rejects
7. Approved profile becomes a live `Employee` record

## Important Notes and Missing Pieces

- The templates and `auth.py` refer to a `profile_step` route, but this route implementation was not found in the current Python source files.
- `templates/employee_dashboard.html` references a `download_payslip` route, but that route also does not appear in the current source files.

These missing route handlers should be added for the employee profile flow and payslip download behavior to work end-to-end.

## File-by-File Summary

- `app.py` — Flask app setup, route imports, DB initialization, startup server
- `sql.py` — database models, ORM setup, default super admin creator
- `auth.py` — login, registration, logout, role-based redirect
- `utils.py` — access control, file upload helpers, audit logging
- `admindashboard.py` — super admin dashboards, employee & HR account management, logs
- `HRdashboard.py` — HR profile review and payslip upload workflows
- `employeedashboard.py` — employee dashboard route
- `approveHR.py` — legacy HR approval route
- `templates/` — HTML templates for all pages and profile steps
- `uploads/` — destination for uploaded files (photos, documents, payslips)
- `instance/hr_employee_management.db` — SQLite database file

## Suggested Improvements

- Implement missing `profile_step` and `download_payslip` route handlers
- Add explicit validation for step forms and required profile fields
- Centralize approval rules for employees and HR accounts
- Add a dedicated `static/` folder if you need custom CSS or JS beyond Bootstrap
