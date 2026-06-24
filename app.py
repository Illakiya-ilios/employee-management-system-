import os
from flask import Flask
from flask_login import LoginManager
from sql import db, User

app = Flask(__name__)

app.config["SECRET_KEY"] = "hr-secret-key-2024"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///hr_employee_management.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["UPLOAD_FOLDER"] = os.path.join(os.path.dirname(__file__), "uploads")
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16MB max upload

# Ensure upload directories exist
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
os.makedirs(os.path.join(app.config["UPLOAD_FOLDER"], "payslips"), exist_ok=True)
os.makedirs(os.path.join(app.config["UPLOAD_FOLDER"], "documents"), exist_ok=True)
os.makedirs(os.path.join(app.config["UPLOAD_FOLDER"], "photos"), exist_ok=True)

db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


# Import all route modules
from auth import *
from dashboards import *
from admindashboard import *
from HRdashboard import *
from employeedashboard import *
from approveHR import *

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        from sql import create_super_admin
        create_super_admin()
    app.run(debug=True)
