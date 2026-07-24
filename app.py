import os

# Try to load .env using python-dotenv when available; otherwise fall back
# to a simple manual loader so credentials from a .env file still work.
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), ".env"), override=True)
    print("DEBUG: python-dotenv loaded .env")
except Exception:
    # Manual .env parsing fallback
    dotenv_path = os.path.join(os.path.dirname(__file__), ".env")
    if os.path.exists(dotenv_path):
        try:
            with open(dotenv_path, "r", encoding="utf-8") as f:
                for raw in f:
                    line = raw.strip()
                    if not line or line.startswith("#"):
                        continue
                    if "=" in line:
                        k, v = line.split("=", 1)
                        k = k.strip()
                        v = v.strip().strip('"').strip("'")
                        if k and k not in os.environ:
                            os.environ[k] = v
            print(f"DEBUG: loaded .env manually from {dotenv_path}")
        except Exception as e:
            print("DEBUG: failed to load .env manually:", e)
    else:
        print(f"DEBUG: no .env found at {dotenv_path}")
import secrets
import smtplib
import sqlite3
import traceback
from email.mime.text import MIMEText

from flask import Flask, flash, redirect, render_template_string, request, url_for, Response
from flask_login import (
    LoginManager,
    UserMixin,
    current_user,
    login_required,
    login_user,
    logout_user,
)
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename
import datetime
import io

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-key")
app.config["DATABASE_PATH"] = os.path.join(app.instance_path, "users.db")

# Update this single mapping when task categories or their predefined tasks change.
TASK_CATEGORIES = {
    "SEO": [
        "Prepare Previous Month's SEO Report", "Analyze GA4 & GSC Data",
        "Review Keyword Rankings", "Share Monthly Report with Client",
        "Finalize Monthly Action Plan", "Perform Technical SEO Audit",
        "Check Broken Links", "Check 404 Errors", "Check Indexing Issues",
        "Check Crawled but Not Indexed Pages", "Sitemap Check", "Generate Backlinks",
        "Perform Competitor Analysis", "Continue Blog Content Creation & Upload",
    ],
    "Social Media Marketing": [
        "Prepare Monthly Performance Report", "Prepare Next Month Social Media Content",
        "Collect Client Approvals", "Story Posting", "Group Sharing", "Social Media Posting",
        "Content Pointers", "Client Reminders",
    ],
    "Google Ads": [
        "Review Monthly Campaign Performance", "Share Daily Reports", "Share Weekly Reports",
        "Optimize Campaigns", "Adjust Bids", "Review Keywords", "Update Negative Keywords",
        "Improve Ad Copy", "Verify Conversion Tracking",
    ],
    "Meta Ads": ["Optimize Meta Ads Campaigns", "Meta Ads Setup"],
    "Website Development": [
        "Domain Name Research", "Domain Registration", "Website Planning", "Site Structure Setup",
        "Homepage Design", "Content Writing", "Website Testing", "Website Launch",
    ],
    "Other (Custom)": [],
}

# Uploads folder for employee documents
app.config['UPLOAD_FOLDER'] = os.path.join(app.instance_path, 'uploads')
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Gmail SMTP configuration
MAIL_SERVER = "smtp.gmail.com"
MAIL_PORT = 587
MAIL_USE_TLS = True
# Enter your Gmail address and App Password here (no env vars)
MAIL_USERNAME = os.getenv("MAIL_USERNAME")
MAIL_PASSWORD = os.getenv("MAIL_PASSWORD")
MAIL_DEFAULT_SENDER = MAIL_USERNAME

# Mirror variables required by the email function
EMAIL_ADDRESS = MAIL_USERNAME
EMAIL_APP_PASSWORD = MAIL_PASSWORD

# Temporary debug prints (masked): show whether env vars were loaded
print(f"DEBUG: MAIL_USERNAME set: {'yes' if MAIL_USERNAME else 'no'}")
print(f"DEBUG: MAIL_PASSWORD set: {'yes' if MAIL_PASSWORD else 'no'} (value hidden)")

os.makedirs(app.instance_path, exist_ok=True)

login_manager = LoginManager(app)
login_manager.login_view = "login"


class User(UserMixin):
    def __init__(self, user_id, username, password_hash, role="user", force_password_change=False):
        self.id = user_id
        self.username = username
        self.password_hash = password_hash
        self.role = role
        self.force_password_change = bool(force_password_change)

    @staticmethod
    def from_db(row):
        if row is None:
            return None
        # row expected: id, username, password_hash, role, [force_password_change]
        try:
            return User(row[0], row[1], row[2], row[3], row[4])
        except Exception:
            return User(row[0], row[1], row[2], row[3], False)


def get_db():
    conn = sqlite3.connect(app.config["DATABASE_PATH"])
    conn.row_factory = sqlite3.Row
    return conn


def get_user_task_names(conn, user):
    """Return the username and employee name that can be used in task assignments."""
    names = {user.username} if user.username else set()
    user_row = conn.execute(
        "SELECT full_name FROM users WHERE id = ?",
        (user.id,),
    ).fetchone()
    if user_row and user_row['full_name']:
        names.add(user_row['full_name'])
    return list(names)


# Helper to save uploaded files and return stored path (relative to instance)
def save_uploaded_file(file_storage):
    if not file_storage:
        return None
    filename = secure_filename(file_storage.filename)
    if not filename:
        return None
    dest_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    # If filename exists, append a short suffix to avoid overwrite
    base, ext = os.path.splitext(filename)
    counter = 1
    while os.path.exists(dest_path):
        filename = f"{base}_{counter}{ext}"
        dest_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        counter += 1
    file_storage.save(dest_path)
    # return path relative to app root (instance path)
    return dest_path




def send_welcome_email(recipient_email, full_name, username, temporary_password):
    server.send_message(msg)
    print("DEBUG: Welcome email sent successfully")
    """Send a welcome email with login info using Gmail SMTP.

    Uses `EMAIL_ADDRESS` and `EMAIL_APP_PASSWORD` for authentication.
    This function prints errors and does not raise on failure.
    """
    subject = "Welcome to the User Management System"
    body = (
        f"Hello {full_name},\n\n"
        "Your account has been created successfully.\n\n"
        f"Username: {username}\n"
        f"Temporary Password: {temporary_password}\n\n"
        "Login here:\nhttp://127.0.0.1:5000/login\n\n"
        "Please change your password after logging in.\n"
    )
    message = MIMEText(body)
    message["Subject"] = subject
    message["From"] = EMAIL_ADDRESS
    message["To"] = recipient_email

    try:
        with smtplib.SMTP(MAIL_SERVER, MAIL_PORT, timeout=10) as server:
            server.starttls()
            server.login(EMAIL_ADDRESS, EMAIL_APP_PASSWORD)
            server.sendmail(EMAIL_ADDRESS, recipient_email, message.as_string())
    except Exception:
        traceback.print_exc()


def ensure_user_columns():
    with get_db() as conn:
        columns = [row[1] for row in conn.execute("PRAGMA table_info(users)").fetchall()]
        if "full_name" not in columns:
            conn.execute("ALTER TABLE users ADD COLUMN full_name TEXT")
        if "email" not in columns:
            conn.execute("ALTER TABLE users ADD COLUMN email TEXT")
        if "force_password_change" not in columns:
            # 0 = false, 1 = true
            conn.execute("ALTER TABLE users ADD COLUMN force_password_change INTEGER DEFAULT 0")
        conn.commit()


def ensure_attendance_table():
    """Create attendance table if it does not exist."""
    with get_db() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS attendance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                username TEXT NOT NULL,
                date TEXT NOT NULL,
                punch_in_time TEXT,
                punch_out_time TEXT,
                total_hours REAL
            )
            """
        )
        conn.commit()


def ensure_employee_table():
    """Create employee table if it does not exist.

    Fields: name, address, education, experience, emergency_contact,
    department (comma-separated), salary, pan_path, aadhaar_path, other_docs_path
    """
    with get_db() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS employees (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                address TEXT,
                education TEXT,
                experience TEXT,
                emergency_contact TEXT,
                department TEXT,
                salary REAL,
                pan_path TEXT,
                aadhaar_path TEXT,
                other_docs_path TEXT
            )
            """
        )
        conn.commit()


def ensure_projects_table():
    """Create projects table if it does not exist and add missing columns safely."""
    with get_db() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_name TEXT,
                services TEXT,
                assigned_to TEXT,
                delivery_details TEXT,
                whatsapp_number TEXT,
                client_email TEXT,
                client_website TEXT,
                client_address TEXT,
                client_gst_number TEXT
            )
            """
        )
        conn.commit()

        columns = {row[1] for row in conn.execute("PRAGMA table_info(projects)").fetchall()}
        required_columns = [
            "client_name",
            "services",
            "assigned_to",
            "delivery_details",
            "whatsapp_number",
            "client_email",
            "client_website",
            "client_address",
            "client_gst_number",
        ]
        for column_name in required_columns:
            if column_name not in columns:
                conn.execute(f"ALTER TABLE projects ADD COLUMN {column_name} TEXT")
        conn.commit()


def ensure_tasks_table():
    """Create the tasks table and add new task fields without removing task data."""
    with get_db() as conn:
        existing_columns = [row[1] for row in conn.execute("PRAGMA table_info(tasks)").fetchall()]
        if not existing_columns:
            conn.execute(
                """
                CREATE TABLE tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    task_category TEXT,
                    description TEXT,
                    project TEXT NOT NULL,
                    assigned_to TEXT NOT NULL,
                    assigned_by TEXT NOT NULL,
                    assigned_date TEXT NOT NULL,
                    deadline TEXT NOT NULL,
                    priority TEXT NOT NULL,
                    estimated_hours REAL,
                    recurring_type TEXT,
                    status TEXT NOT NULL DEFAULT 'Pending',
                    completed_by TEXT
                )
                """
            )
            conn.commit()
            return

        required_columns = [
            "title",
            "description",
            "project",
            "assigned_to",
            "assigned_by",
            "assigned_date",
            "deadline",
            "priority",
            "recurring_type",
            "status",
            "completed_by",
        ]
        for column_name in required_columns:
            if column_name not in existing_columns:
                conn.execute(f"ALTER TABLE tasks ADD COLUMN {column_name} TEXT")
        if "task_category" not in existing_columns:
            conn.execute("ALTER TABLE tasks ADD COLUMN task_category TEXT")
        if "estimated_hours" not in existing_columns:
            conn.execute("ALTER TABLE tasks ADD COLUMN estimated_hours REAL")
        conn.commit()


def ensure_time_logs_table():
    """Create time_logs table if it does not exist."""
    with get_db() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS time_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                logged_date TEXT NOT NULL,
                hours_worked REAL NOT NULL DEFAULT 0,
                notes TEXT
            )
            """
        )
        conn.commit()

        columns = {row[1] for row in conn.execute("PRAGMA table_info(time_logs)").fetchall()}
        required_columns = [
            "task_id",
            "user_id",
            "logged_date",
            "hours_worked",
            "notes",
        ]
        for column_name in required_columns:
            if column_name not in columns:
                conn.execute(f"ALTER TABLE time_logs ADD COLUMN {column_name} TEXT")
        conn.commit()


def init_db():
    with get_db() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'user'
            )
            """
        )
        conn.commit()

        ensure_user_columns()
        ensure_attendance_table()
        ensure_employee_table()
        ensure_projects_table()
        ensure_tasks_table()
        ensure_time_logs_table()

        admin_exists = conn.execute(
            "SELECT COUNT(*) FROM users WHERE username = ?",
            ("admin",),
        ).fetchone()[0]
        if admin_exists == 0:
            conn.execute(
                "INSERT INTO users (username, password_hash, role, force_password_change) VALUES (?, ?, ?, ?)",
                ("admin", generate_password_hash("admin123"), "admin", 0),
            )
            conn.commit()


init_db()


@login_manager.user_loader
def load_user(user_id):
    with get_db() as conn:
        row = conn.execute(
            "SELECT id, username, password_hash, role, force_password_change FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()
    return User.from_db(row)


@app.route("/")
def index():
    return render_template_string(
        """
        <!doctype html>
        <html lang="en">
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <title>Flask User Management</title>
            <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
        </head>
        <body class="bg-light">
            <div class="container py-5">
                <div class="card shadow-sm">
                    <div class="card-body">
                        <h1 class="h3 mb-3">Flask User Management</h1>
                        {% if current_user.is_authenticated %}
                            <p>Hello, {{ current_user.username }}!</p>
                            <a class="btn btn-primary" href="{{ url_for('dashboard') }}">Dashboard</a>
                            <a class="btn btn-outline-danger ms-2" href="{{ url_for('logout') }}">Logout</a>
                        {% else %}
                            <p>Please sign in.</p>
                            <a class="btn btn-primary" href="{{ url_for('login') }}">Login</a>
                        {% endif %}
                    </div>
                </div>
            </div>
        </body>
        </html>
        """
    )


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        with get_db() as conn:
            row = conn.execute(
                "SELECT id, username, password_hash, role, force_password_change FROM users WHERE username = ?",
                (username,),
            ).fetchone()

        user = User.from_db(row)
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            # If the user must change their password on first login, redirect there
            if getattr(user, 'role', None) != 'admin' and getattr(user, 'force_password_change', False):
                flash("You must change your temporary password before continuing.", "warning")
                return redirect(url_for('change_password'))
            flash("Login successful.", "success")
            return redirect(url_for("dashboard"))

        flash("Invalid username or password.", "danger")

    return render_template_string(
        """
        <!doctype html>
        <html lang="en">
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <title>Login</title>
            <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
        </head>
        <body class="bg-light">
            <div class="container py-5">
                <div class="card shadow-sm mx-auto" style="max-width: 420px;">
                    <div class="card-body">
                        <h2 class="h4 mb-3">Login</h2>
                        <form method="post">
                            <div class="mb-3">
                                <label class="form-label">Username</label>
                                <input class="form-control" name="username" required>
                            </div>
                            <div class="mb-3">
                                <label class="form-label">Password</label>
                                <input class="form-control" type="password" name="password" required>
                            </div>
                            <button class="btn btn-primary w-100" type="submit">Login</button>
                        </form>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """
    )



# Enforce password change on first login for non-admin users
@app.before_request
def require_password_change():
    try:
        endpoint = request.endpoint or ''
    except Exception:
        endpoint = ''
    # endpoints that must be allowed without changing password
    allowed = {
        'change_password',
        'logout',
        'login',
        'static',
        'create_user',
        'send_welcome_email'
    }
    if current_user.is_authenticated:
        if getattr(current_user, 'role', None) != 'admin' and getattr(current_user, 'force_password_change', False):
            if endpoint not in allowed and not endpoint.startswith('static'):
                return redirect(url_for('change_password'))


@app.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    # Only non-admins can be forced; admins should not be here
    if current_user.role == 'admin':
        flash('Admins do not need to change passwords here.', 'info')
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        current_pw = request.form.get('current_password', '')
        new_pw = request.form.get('new_password', '')
        confirm_pw = request.form.get('confirm_password', '')

        if not current_pw or not new_pw or not confirm_pw:
            flash('All fields are required.', 'danger')
            return redirect(url_for('change_password'))

        # verify current password
        if not check_password_hash(current_user.password_hash, current_pw):
            flash('Current password is incorrect.', 'danger')
            return redirect(url_for('change_password'))

        if new_pw != confirm_pw:
            flash('New passwords do not match.', 'danger')
            return redirect(url_for('change_password'))

        if len(new_pw) < 8:
            flash('New password must be at least 8 characters long.', 'danger')
            return redirect(url_for('change_password'))

        # New password cannot be the same as the temporary/current password
        if check_password_hash(current_user.password_hash, new_pw):
            flash('New password must be different from the current password.', 'danger')
            return redirect(url_for('change_password'))

        # Update password and clear the force flag
        with get_db() as conn:
            conn.execute(
                'UPDATE users SET password_hash = ?, force_password_change = ? WHERE id = ?',
                (generate_password_hash(new_pw), 0, current_user.id),
            )
            conn.commit()

        # refresh current_user password_hash in memory
        current_user.password_hash = generate_password_hash(new_pw)
        current_user.force_password_change = False

        flash('Password changed successfully.', 'success')
        return redirect(url_for('dashboard'))

    return render_template_string(
        """
        <!doctype html>
        <html lang="en">
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <title>Change Password</title>
            <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
        </head>
        <body class="bg-light">
            <div class="container py-5">
                <div class="card shadow-sm mx-auto" style="max-width:540px;">
                    <div class="card-body">
                        <h2 class="h4 mb-3">Change Password</h2>
                        <form method="post">
                            <div class="mb-3">
                                <label class="form-label">Current Password</label>
                                <input class="form-control" type="password" name="current_password" required>
                            </div>
                            <div class="mb-3">
                                <label class="form-label">New Password</label>
                                <input class="form-control" type="password" name="new_password" required>
                            </div>
                            <div class="mb-3">
                                <label class="form-label">Confirm Password</label>
                                <input class="form-control" type="password" name="confirm_password" required>
                            </div>
                            <button class="btn btn-primary w-100" type="submit">Change Password</button>
                        </form>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """
    )


@app.route("/dashboard")
@login_required
def dashboard():
    # Fetch today's attendance and recent records for the current user
    today = datetime.date.today().isoformat()
    with get_db() as conn:
        row = conn.execute(
            "SELECT id, date, punch_in_time, punch_out_time, total_hours FROM attendance WHERE user_id = ? AND date = ?",
            (current_user.id, today),
        ).fetchone()
        records = conn.execute(
            "SELECT date, punch_in_time, punch_out_time, total_hours FROM attendance WHERE user_id = ? ORDER BY date DESC LIMIT 20",
            (current_user.id,),
        ).fetchall()

    return render_template_string(
        """
        {% extends "base.html" %}
        {% block title %}Dashboard{% endblock %}
        {% block page_content %}
                <div class="page-header">
                    <h1>Dashboard</h1>
                    <p>Welcome back, {{ current_user.username }}.</p>
                </div>
                <div class="card shadow-sm mb-4">
                    <div class="card-body">
                        <form method="post" action="{{ url_for('punch_in') }}" style="display:inline-block;">
                            <button class="btn btn-success">Punch In</button>
                        </form>
                        <form method="post" action="{{ url_for('punch_out') }}" style="display:inline-block; margin-left:8px;">
                            <button class="btn btn-danger">Punch Out</button>
                        </form>
                    </div>
                </div>

                <div class="card shadow-sm mb-4">
                    <div class="card-body">
                        <h4 class="h5">Today's Attendance</h4>
                        {% if today_row %}
                            <p>Punch In: {{ today_row.punch_in_time or 'N/A' }}</p>
                            <p>Punch Out: {{ today_row.punch_out_time or 'N/A' }}</p>
                            <p>Total Hours: {{ today_row.total_hours or 'N/A' }}</p>
                        {% else %}
                            <p>You have not punched in today.</p>
                        {% endif %}
                    </div>
                </div>

                <div class="card shadow-sm">
                    <div class="card-body">
                        <h4 class="h5">Recent Attendance</h4>
                        <div class="table-responsive">
                            <table class="table table-striped">
                                <thead>
                                    <tr>
                                        <th>Date</th>
                                        <th>Punch In</th>
                                        <th>Punch Out</th>
                                        <th>Total Hours</th>
                                    </tr>
                                </thead>
                                <tbody>
                                {% for r in records %}
                                    <tr>
                                        <td>{{ r.date }}</td>
                                        <td>{{ r.punch_in_time or '' }}</td>
                                        <td>{{ r.punch_out_time or '' }}</td>
                                        <td>{{ r.total_hours or '' }}</td>
                                    </tr>
                                {% endfor %}
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
        {% endblock %}
        """,
        today_row=row,
        records=records,
    )


@app.route('/my-tasks')
@login_required
def my_tasks():
    if current_user.role == 'admin':
        return redirect(url_for('task_management'))

    today = datetime.date.today().isoformat()
    with get_db() as conn:
        employee_name_filter = get_user_task_names(conn, current_user)

        if not employee_name_filter:
            tasks = []
        else:
            placeholders = ', '.join('?' for _ in employee_name_filter)
            tasks = conn.execute(
                f"""
                SELECT t.id, t.title, t.task_category, t.description, t.project, t.assigned_to, t.assigned_by, t.assigned_date, t.deadline,
                       t.priority, t.estimated_hours, t.recurring_type, t.status, t.completed_by,
                       COALESCE(SUM(l.hours_worked), 0) AS total_logged_hours
                FROM tasks t
                LEFT JOIN time_logs l ON l.task_id = t.id
                WHERE t.assigned_to IN ({placeholders})
                GROUP BY t.id
                ORDER BY t.assigned_date, t.deadline, t.title
                """,
                employee_name_filter,
            ).fetchall()

    current_tasks = []
    future_tasks = []
    recurring_tasks = []
    for task in tasks:
        if task['recurring_type']:
            recurring_tasks.append(task)
        elif task['assigned_date'] > today:
            future_tasks.append(task)
        else:
            current_tasks.append(task)

    return render_template_string(
        """
        <!doctype html>
        <html lang="en">
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <title>My Tasks</title>
            <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
        </head>
        <body class="bg-light">
            <div class="container py-5">
                <div class="d-flex align-items-center mb-4">
                    <h1 class="h3 me-auto mb-0">My Tasks</h1>
                    <a class="btn btn-outline-secondary" href="{{ url_for('dashboard') }}">Back</a>
                </div>
                {% with messages = get_flashed_messages(with_categories=true) %}
                    {% if messages %}
                        {% for category, message in messages %}
                            <div class="alert alert-{{ category }}">{{ message }}</div>
                        {% endfor %}
                    {% endif %}
                {% endwith %}
                {% if not tasks %}
                    <div class="alert alert-info">No tasks assigned to you yet.</div>
                {% endif %}
                {% if current_tasks %}
                    <div class="card shadow-sm mb-4">
                        <div class="card-body">
                            <h2 class="h5">Current Tasks</h2>
                            {% for task in current_tasks %}
                                <div class="border rounded p-3 mb-3">
                                    <div class="row g-3">
                                        <div class="col-md-8">
                                            <h3 class="h6 mb-2">{{ task.title or '' }}</h3>
                                            <p class="mb-1"><strong>Project:</strong> {{ task.project or '' }}</p>
                                            <p class="mb-1"><strong>Assigned By:</strong> {{ task.assigned_by or '' }}</p>
                                            <p class="mb-1"><strong>Assigned Date:</strong> {{ task.assigned_date or '' }}</p>
                                            <p class="mb-1"><strong>Deadline:</strong> {{ task.deadline or '' }}</p>
                                            <p class="mb-1"><strong>Priority:</strong> {{ task.priority or '' }}</p>
                                            <p class="mb-1"><strong>Recurring Type:</strong> {{ task.recurring_type or 'None' }}</p>
                                            <p class="mb-1"><strong>Status:</strong> {{ task.status or 'Pending' }}</p>
                                            <p class="mb-1"><strong>Description:</strong> {{ task.description or '' }}</p>
                                            <p class="mb-1"><strong>Estimated Hours:</strong> {{ '%.2f'|format(task.estimated_hours or 0) }}</p>
                                            <p class="mb-0"><strong>Logged Hours:</strong> {{ '%.2f'|format(task.total_logged_hours or 0) }}</p>
                                        </div>
                                        <div class="col-md-4">
                                            <form method="post" action="{{ url_for('update_task', task_id=task.id) }}">
                                                <div class="mb-2">
                                                    <label class="form-label small">Hours Worked</label>
                                                    <input class="form-control" name="hours_worked" type="number" step="0.25" min="0">
                                                </div>
                                                <div class="mb-2">
                                                    <label class="form-label small">Work Notes</label>
                                                    <input class="form-control" name="work_notes">
                                                </div>
                                                <div class="mb-2">
                                                    <label class="form-label small">Status</label>
                                                    <select class="form-select" name="status">
                                                        <option value="Pending" {% if task.status == 'Pending' %}selected{% endif %}>Pending</option>
                                                        <option value="In Progress" {% if task.status == 'In Progress' %}selected{% endif %}>In Progress</option>
                                                        <option value="Blocked" {% if task.status == 'Blocked' %}selected{% endif %}>Blocked</option>
                                                        <option value="Completed" {% if task.status == 'Completed' %}selected{% endif %}>Completed</option>
                                                    </select>
                                                </div>
                                                <button class="btn btn-primary btn-sm" type="submit">Save Update</button>
                                            </form>
                                        </div>
                                    </div>
                                </div>
                            {% endfor %}
                        </div>
                    </div>
                {% endif %}
                {% if future_tasks %}
                    <div class="card shadow-sm mb-4">
                        <div class="card-body">
                            <h2 class="h5">Future Tasks</h2>
                            {% for task in future_tasks %}
                                <div class="border rounded p-3 mb-3">
                                    <div class="row g-3">
                                        <div class="col-md-8">
                                            <h3 class="h6 mb-2">{{ task.title or '' }}</h3>
                                            <p class="mb-1"><strong>Project:</strong> {{ task.project or '' }}</p>
                                            <p class="mb-1"><strong>Assigned By:</strong> {{ task.assigned_by or '' }}</p>
                                            <p class="mb-1"><strong>Assigned Date:</strong> {{ task.assigned_date or '' }}</p>
                                            <p class="mb-1"><strong>Deadline:</strong> {{ task.deadline or '' }}</p>
                                            <p class="mb-1"><strong>Priority:</strong> {{ task.priority or '' }}</p>
                                            <p class="mb-1"><strong>Recurring Type:</strong> {{ task.recurring_type or 'None' }}</p>
                                            <p class="mb-1"><strong>Status:</strong> {{ task.status or 'Pending' }}</p>
                                            <p class="mb-1"><strong>Description:</strong> {{ task.description or '' }}</p>
                                            <p class="mb-1"><strong>Estimated Hours:</strong> {{ '%.2f'|format(task.estimated_hours or 0) }}</p>
                                            <p class="mb-0"><strong>Logged Hours:</strong> {{ '%.2f'|format(task.total_logged_hours or 0) }}</p>
                                        </div>
                                        <div class="col-md-4">
                                            <form method="post" action="{{ url_for('update_task', task_id=task.id) }}">
                                                <div class="mb-2">
                                                    <label class="form-label small">Hours Worked</label>
                                                    <input class="form-control" name="hours_worked" type="number" step="0.25" min="0">
                                                </div>
                                                <div class="mb-2">
                                                    <label class="form-label small">Work Notes</label>
                                                    <input class="form-control" name="work_notes">
                                                </div>
                                                <div class="mb-2">
                                                    <label class="form-label small">Status</label>
                                                    <select class="form-select" name="status">
                                                        <option value="Pending" {% if task.status == 'Pending' %}selected{% endif %}>Pending</option>
                                                        <option value="In Progress" {% if task.status == 'In Progress' %}selected{% endif %}>In Progress</option>
                                                        <option value="Blocked" {% if task.status == 'Blocked' %}selected{% endif %}>Blocked</option>
                                                        <option value="Completed" {% if task.status == 'Completed' %}selected{% endif %}>Completed</option>
                                                    </select>
                                                </div>
                                                <button class="btn btn-primary btn-sm" type="submit">Save Update</button>
                                            </form>
                                        </div>
                                    </div>
                                </div>
                            {% endfor %}
                        </div>
                    </div>
                {% endif %}
                {% if recurring_tasks %}
                    <div class="card shadow-sm">
                        <div class="card-body">
                            <h2 class="h5">Recurring Tasks</h2>
                            {% for task in recurring_tasks %}
                                <div class="border rounded p-3 mb-3">
                                    <div class="row g-3">
                                        <div class="col-md-8">
                                            <h3 class="h6 mb-2">{{ task.title or '' }}</h3>
                                            <p class="mb-1"><strong>Project:</strong> {{ task.project or '' }}</p>
                                            <p class="mb-1"><strong>Assigned By:</strong> {{ task.assigned_by or '' }}</p>
                                            <p class="mb-1"><strong>Assigned Date:</strong> {{ task.assigned_date or '' }}</p>
                                            <p class="mb-1"><strong>Deadline:</strong> {{ task.deadline or '' }}</p>
                                            <p class="mb-1"><strong>Priority:</strong> {{ task.priority or '' }}</p>
                                            <p class="mb-1"><strong>Recurring Type:</strong> {{ task.recurring_type or 'None' }}</p>
                                            <p class="mb-1"><strong>Status:</strong> {{ task.status or 'Pending' }}</p>
                                            <p class="mb-1"><strong>Description:</strong> {{ task.description or '' }}</p>
                                            <p class="mb-1"><strong>Estimated Hours:</strong> {{ '%.2f'|format(task.estimated_hours or 0) }}</p>
                                            <p class="mb-0"><strong>Logged Hours:</strong> {{ '%.2f'|format(task.total_logged_hours or 0) }}</p>
                                        </div>
                                        <div class="col-md-4">
                                            <form method="post" action="{{ url_for('update_task', task_id=task.id) }}">
                                                <div class="mb-2">
                                                    <label class="form-label small">Hours Worked</label>
                                                    <input class="form-control" name="hours_worked" type="number" step="0.25" min="0">
                                                </div>
                                                <div class="mb-2">
                                                    <label class="form-label small">Work Notes</label>
                                                    <input class="form-control" name="work_notes">
                                                </div>
                                                <div class="mb-2">
                                                    <label class="form-label small">Status</label>
                                                    <select class="form-select" name="status">
                                                        <option value="Pending" {% if task.status == 'Pending' %}selected{% endif %}>Pending</option>
                                                        <option value="In Progress" {% if task.status == 'In Progress' %}selected{% endif %}>In Progress</option>
                                                        <option value="Blocked" {% if task.status == 'Blocked' %}selected{% endif %}>Blocked</option>
                                                        <option value="Completed" {% if task.status == 'Completed' %}selected{% endif %}>Completed</option>
                                                    </select>
                                                </div>
                                                <button class="btn btn-primary btn-sm" type="submit">Save Update</button>
                                            </form>
                                        </div>
                                    </div>
                                </div>
                            {% endfor %}
                        </div>
                    </div>
                {% endif %}
            </div>
        </body>
        </html>
        """,
        tasks=tasks,
        current_tasks=current_tasks,
        future_tasks=future_tasks,
        recurring_tasks=recurring_tasks,
    )


@app.route('/tasks/<int:task_id>/update', methods=['POST'])
@login_required
def update_task(task_id):
    if current_user.role == 'admin':
        flash('Admins manage tasks from the Task Management page.', 'warning')
        return redirect(url_for('task_management'))

    with get_db() as conn:
        task = conn.execute(
            "SELECT id, assigned_to, status FROM tasks WHERE id = ?",
            (task_id,),
        ).fetchone()
        employee_names = get_user_task_names(conn, current_user)

    if task is None:
        flash('Task not found.', 'warning')
        return redirect(url_for('my_tasks'))

    if task['assigned_to'] not in employee_names:
        flash('Only assigned employees may update their own tasks.', 'danger')
        return redirect(url_for('my_tasks'))

    hours_worked = request.form.get('hours_worked', '').strip()
    work_notes = request.form.get('work_notes', '').strip()
    status = request.form.get('status', 'Pending').strip()

    if hours_worked:
        try:
            hours_value = float(hours_worked)
        except ValueError:
            flash('Hours must be a valid number.', 'danger')
            return redirect(url_for('my_tasks'))
        if hours_value <= 0:
            flash('Hours cannot be zero or negative.', 'danger')
            return redirect(url_for('my_tasks'))
    else:
        hours_value = None

    if status not in ['Pending', 'In Progress', 'Blocked', 'Completed']:
        status = 'Pending'

    with get_db() as conn:
        if hours_value is not None:
            conn.execute(
                "INSERT INTO time_logs (task_id, user_id, logged_date, hours_worked, notes) VALUES (?, ?, ?, ?, ?)",
                (task_id, current_user.id, datetime.date.today().isoformat(), hours_value, work_notes or None),
            )
        if status != task['status']:
            completed_by = current_user.username if status == 'Completed' else None
            conn.execute(
                "UPDATE tasks SET status = ?, completed_by = ? WHERE id = ?",
                (status, completed_by, task_id),
            )
            conn.commit()
        elif hours_value is not None:
            conn.commit()

    flash('Task updated successfully.', 'success')
    return redirect(url_for('my_tasks'))


@app.route('/admin/tasks', methods=['GET', 'POST'])
@login_required
def task_management():
    if current_user.role != 'admin':
        flash('Admin access required.', 'danger')
        return redirect(url_for('dashboard'))

    with get_db() as conn:
        employees = conn.execute("SELECT id, name FROM employees ORDER BY name").fetchall()
        projects = conn.execute("SELECT id, client_name FROM projects ORDER BY client_name").fetchall()

    employee_filter = request.args.get('employee_filter', '').strip()
    project_filter = request.args.get('project_filter', '').strip()
    status_filter = request.args.get('status_filter', '').strip()
    edit_id = request.args.get('edit_id', '').strip()

    edit_task = None
    if edit_id:
        with get_db() as conn:
            edit_task = conn.execute(
                "SELECT * FROM tasks WHERE id = ?",
                (edit_id,),
            ).fetchone()

    if request.method == 'POST':
        action = request.form.get('action', 'create').strip()
        task_id = request.form.get('task_id', '').strip()

        if action == 'delete' and task_id:
            with get_db() as conn:
                conn.execute('DELETE FROM time_logs WHERE task_id = ?', (task_id,))
                conn.execute('DELETE FROM tasks WHERE id = ?', (task_id,))
                conn.commit()
            flash('Task deleted successfully.', 'success')
            return redirect(url_for('task_management'))

        task_category = request.form.get('task_category', '').strip()
        selected_task = request.form.get('task_title', '').strip()
        custom_task_title = request.form.get('custom_task_title', '').strip()
        description = request.form.get('description', '').strip()
        project = request.form.get('project', '').strip()
        assigned_to = request.form.get('assigned_to', '').strip()
        assigned_date = request.form.get('assigned_date', '').strip()
        deadline = request.form.get('deadline', '').strip()
        priority = request.form.get('priority', '').strip()
        recurring_type = request.form.get('recurring_type', '').strip() or None
        status = request.form.get('status', 'Pending').strip()
        estimated_hours_input = request.form.get('estimated_hours', '').strip()

        if task_category not in TASK_CATEGORIES:
            flash('Select a valid task category.', 'danger')
            return redirect(url_for('task_management'))
        if task_category == 'Other (Custom)':
            title = custom_task_title
        elif selected_task in TASK_CATEGORIES[task_category]:
            title = selected_task
        else:
            flash('Select a valid task for the selected category.', 'danger')
            return redirect(url_for('task_management'))

        try:
            estimated_hours = float(estimated_hours_input)
        except ValueError:
            flash('Estimated Hours must be a valid number.', 'danger')
            return redirect(url_for('task_management'))

        if not title or not project or not assigned_to or not assigned_date or not deadline or not priority or not status:
            flash('All task fields except description are required.', 'danger')
            return redirect(url_for('task_management'))
        if estimated_hours <= 0:
            flash('Estimated Hours must be greater than zero.', 'danger')
            return redirect(url_for('task_management'))

        if deadline < assigned_date:
            flash('Deadline cannot be before Assigned Date.', 'danger')
            return redirect(url_for('task_management'))

        if action == 'edit' and task_id:
            with get_db() as conn:
                conn.execute(
                    """
                    UPDATE tasks SET title=?, task_category=?, description=?, project=?, assigned_to=?, assigned_by=?, assigned_date=?, deadline=?, priority=?, estimated_hours=?, recurring_type=?, status=?, completed_by=? WHERE id=?
                    """,
                    (
                        title,
                        task_category,
                        description,
                        project,
                        assigned_to,
                        current_user.username,
                        assigned_date,
                        deadline,
                        priority,
                        estimated_hours,
                        recurring_type,
                        status,
                        current_user.username if status == 'Completed' else None,
                        task_id,
                    ),
                )
                conn.commit()
            flash('Task updated successfully.', 'success')
            return redirect(url_for('task_management'))

        with get_db() as conn:
            conn.execute(
                """
                INSERT INTO tasks (title, task_category, description, project, assigned_to, assigned_by, assigned_date, deadline, priority, estimated_hours, recurring_type, status, completed_by)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    title,
                    task_category,
                    description,
                    project,
                    assigned_to,
                    current_user.username,
                    assigned_date,
                    deadline,
                    priority,
                    estimated_hours,
                    recurring_type,
                    status,
                    current_user.username if status == 'Completed' else None,
                ),
            )
            conn.commit()
        flash('Task created successfully.', 'success')
        return redirect(url_for('task_management'))

    query = """
        SELECT t.id, t.title, t.task_category, t.description, t.project, t.assigned_to, t.assigned_by, t.assigned_date, t.deadline,
               t.priority, COALESCE(t.estimated_hours, 0) AS estimated_hours, t.recurring_type, t.status, t.completed_by,
               COALESCE(SUM(l.hours_worked), 0) AS total_logged_hours,
               COALESCE(t.estimated_hours, 0) - COALESCE(SUM(l.hours_worked), 0) AS remaining_hours,
               COALESCE(SUM(l.hours_worked), 0) - COALESCE(t.estimated_hours, 0) AS variance_hours
        FROM tasks t
        LEFT JOIN time_logs l ON l.task_id = t.id
        WHERE 1 = 1
    """
    params = []
    if employee_filter:
        query += " AND t.assigned_to = ?"
        params.append(employee_filter)
    if project_filter:
        query += " AND t.project = ?"
        params.append(project_filter)
    if status_filter:
        query += " AND t.status = ?"
        params.append(status_filter)
    query += " GROUP BY t.id ORDER BY t.assigned_date DESC, t.deadline DESC, t.title"

    with get_db() as conn:
        tasks = conn.execute(query, params).fetchall()

    return render_template_string(
        """
        <!doctype html>
        <html lang="en">
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <title>Task Management</title>
            <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
        </head>
        <body class="bg-light">
            <div class="container py-5">
                <div class="d-flex align-items-center mb-4">
                    <h1 class="h3 me-auto mb-0">Task Management</h1>
                    <a class="btn btn-outline-secondary" href="{{ url_for('dashboard') }}">Back</a>
                </div>
                {% with messages = get_flashed_messages(with_categories=true) %}
                    {% if messages %}
                        {% for category, message in messages %}
                            <div class="alert alert-{{ category }}">{{ message }}</div>
                        {% endfor %}
                    {% endif %}
                {% endwith %}
                <div class="card shadow-sm mb-4">
                    <div class="card-body">
                        <h2 class="h5">Create / Edit Task</h2>
                        <form method="post">
                            <input type="hidden" name="action" value="{% if edit_task %}edit{% else %}create{% endif %}">
                            {% if edit_task %}
                                <input type="hidden" name="task_id" value="{{ edit_task.id }}">
                            {% endif %}
                            <div class="row g-3">
                                <div class="col-md-6">
                                    <label class="form-label">Task Category</label>
                                    <select class="form-select" name="task_category" id="task-category" required>
                                        <option value="">Select category</option>
                                        {% for category in task_categories %}
                                            <option value="{{ category }}" {% if edit_task and edit_task.task_category == category %}selected{% endif %}>{{ category }}</option>
                                        {% endfor %}
                                    </select>
                                </div>
                                <div class="col-md-6">
                                    <label class="form-label">Task</label>
                                    <select class="form-select" name="task_title" id="task-title" required>
                                        <option value="">Select task</option>
                                        {% if edit_task and edit_task.task_category and edit_task.task_category != 'Other (Custom)' %}
                                            {% for task in task_categories.get(edit_task.task_category, []) %}
                                                <option value="{{ task }}" {% if edit_task.title == task %}selected{% endif %}>{{ task }}</option>
                                            {% endfor %}
                                        {% endif %}
                                    </select>
                                </div>
                                <div class="col-md-6 d-none" id="custom-task-container">
                                    <label class="form-label">Custom Task</label>
                                    <input class="form-control" name="custom_task_title" id="custom-task-title" value="{% if edit_task and edit_task.task_category == 'Other (Custom)' %}{{ edit_task.title }}{% endif %}">
                                </div>
                                <div class="col-md-6">
                                    <label class="form-label">Project</label>
                                    <select class="form-select" name="project" required>
                                        <option value="">Select project</option>
                                        {% for project in projects %}
                                            <option value="{{ project.client_name }}" {% if edit_task and edit_task.project == project.client_name %}selected{% endif %}>{{ project.client_name }}</option>
                                        {% endfor %}
                                    </select>
                                </div>
                                <div class="col-md-6">
                                    <label class="form-label">Assigned Employee</label>
                                    <select class="form-select" name="assigned_to" required>
                                        <option value="">Select employee</option>
                                        {% for employee in employees %}
                                            <option value="{{ employee.name }}" {% if edit_task and edit_task.assigned_to == employee.name %}selected{% endif %}>{{ employee.name }}</option>
                                        {% endfor %}
                                    </select>
                                </div>
                                <div class="col-md-6">
                                    <label class="form-label">Priority</label>
                                    <select class="form-select" name="priority" required>
                                        <option value="">Select priority</option>
                                        <option value="Low" {% if edit_task and edit_task.priority == 'Low' %}selected{% endif %}>Low</option>
                                        <option value="Medium" {% if edit_task and edit_task.priority == 'Medium' %}selected{% endif %}>Medium</option>
                                        <option value="High" {% if edit_task and edit_task.priority == 'High' %}selected{% endif %}>High</option>
                                    </select>
                                </div>
                                <div class="col-md-6">
                                    <label class="form-label">Estimated Hours</label>
                                    <input class="form-control" name="estimated_hours" type="number" step="0.25" min="0.25" value="{{ edit_task.estimated_hours if edit_task and edit_task.estimated_hours is not none else '' }}" required>
                                </div>
                                <div class="col-md-6">
                                    <label class="form-label">Assigned Date</label>
                                    <input class="form-control" name="assigned_date" type="date" value="{{ edit_task.assigned_date if edit_task else '' }}" required>
                                </div>
                                <div class="col-md-6">
                                    <label class="form-label">Deadline</label>
                                    <input class="form-control" name="deadline" type="date" value="{{ edit_task.deadline if edit_task else '' }}" required>
                                </div>
                                <div class="col-md-6">
                                    <label class="form-label">Recurring Type</label>
                                    <select class="form-select" name="recurring_type">
                                        <option value="">None</option>
                                        <option value="Daily" {% if edit_task and edit_task.recurring_type == 'Daily' %}selected{% endif %}>Daily</option>
                                        <option value="Weekly" {% if edit_task and edit_task.recurring_type == 'Weekly' %}selected{% endif %}>Weekly</option>
                                        <option value="Monthly" {% if edit_task and edit_task.recurring_type == 'Monthly' %}selected{% endif %}>Monthly</option>
                                    </select>
                                </div>
                                <div class="col-md-6">
                                    <label class="form-label">Status</label>
                                    <select class="form-select" name="status" required>
                                        <option value="Pending" {% if edit_task and edit_task.status == 'Pending' %}selected{% endif %}>Pending</option>
                                        <option value="In Progress" {% if edit_task and edit_task.status == 'In Progress' %}selected{% endif %}>In Progress</option>
                                        <option value="Blocked" {% if edit_task and edit_task.status == 'Blocked' %}selected{% endif %}>Blocked</option>
                                        <option value="Completed" {% if edit_task and edit_task.status == 'Completed' %}selected{% endif %}>Completed</option>
                                    </select>
                                </div>
                                <div class="col-12">
                                    <label class="form-label">Description</label>
                                    <textarea class="form-control" name="description" rows="3">{{ edit_task.description if edit_task else '' }}</textarea>
                                </div>
                            </div>
                            <button class="btn btn-primary mt-3" type="submit">{% if edit_task %}Save Changes{% else %}Create Task{% endif %}</button>
                            {% if edit_task %}
                                <a class="btn btn-outline-secondary ms-2 mt-3" href="{{ url_for('task_management') }}">Cancel</a>
                            {% endif %}
                        </form>
                    </div>
                </div>
                <div class="card shadow-sm">
                    <div class="card-body">
                        <h2 class="h5">Filter Tasks</h2>
                        <form method="get" class="row g-2 align-items-end">
                            <div class="col-md-3">
                                <label class="form-label small">Employee</label>
                                <select class="form-select" name="employee_filter">
                                    <option value="">All</option>
                                    {% for employee in employees %}
                                        <option value="{{ employee.name }}" {% if employee_filter == employee.name %}selected{% endif %}>{{ employee.name }}</option>
                                    {% endfor %}
                                </select>
                            </div>
                            <div class="col-md-3">
                                <label class="form-label small">Project</label>
                                <select class="form-select" name="project_filter">
                                    <option value="">All</option>
                                    {% for project in projects %}
                                        <option value="{{ project.client_name }}" {% if project_filter == project.client_name %}selected{% endif %}>{{ project.client_name }}</option>
                                    {% endfor %}
                                </select>
                            </div>
                            <div class="col-md-3">
                                <label class="form-label small">Status</label>
                                <select class="form-select" name="status_filter">
                                    <option value="">All</option>
                                    <option value="Pending" {% if status_filter == 'Pending' %}selected{% endif %}>Pending</option>
                                    <option value="In Progress" {% if status_filter == 'In Progress' %}selected{% endif %}>In Progress</option>
                                    <option value="Blocked" {% if status_filter == 'Blocked' %}selected{% endif %}>Blocked</option>
                                    <option value="Completed" {% if status_filter == 'Completed' %}selected{% endif %}>Completed</option>
                                </select>
                            </div>
                            <div class="col-auto">
                                <button class="btn btn-primary" type="submit">Filter</button>
                            </div>
                            <div class="col-auto">
                                <a class="btn btn-outline-secondary" href="{{ url_for('task_management') }}">Reset</a>
                            </div>
                        </form>
                        <div class="table-responsive mt-3">
                            <table class="table table-striped align-middle">
                                <thead>
                                    <tr>
                                        <th>Category</th>
                                        <th>Task</th>
                                        <th>Project</th>
                                        <th>Assigned Employee</th>
                                        <th>Assigned By</th>
                                        <th>Assigned Date</th>
                                        <th>Deadline</th>
                                        <th>Priority</th>
                                        <th>Recurring</th>
                                        <th>Status</th>
                                        <th>Estimated Hours</th>
                                        <th>Logged Hours</th>
                                        <th>Remaining Hours</th>
                                        <th>Variance</th>
                                        <th>Completed By</th>
                                        <th>Actions</th>
                                    </tr>
                                </thead>
                                <tbody>
                                {% if tasks %}
                                    {% for task in tasks %}
                                        <tr>
                                            <td>{{ task.task_category or 'Legacy' }}</td>
                                            <td>{{ task.title or '' }}</td>
                                            <td>{{ task.project or '' }}</td>
                                            <td>{{ task.assigned_to or '' }}</td>
                                            <td>{{ task.assigned_by or '' }}</td>
                                            <td>{{ task.assigned_date or '' }}</td>
                                            <td>{{ task.deadline or '' }}</td>
                                            <td>{{ task.priority or '' }}</td>
                                            <td>{{ task.recurring_type or 'None' }}</td>
                                            <td>{{ task.status or 'Pending' }}</td>
                                            <td>{{ '%.2f'|format(task.estimated_hours or 0) }}</td>
                                            <td>{{ '%.2f'|format(task.total_logged_hours or 0) }}</td>
                                            <td>{{ '%.2f'|format(task.remaining_hours or 0) }}</td>
                                            <td>
                                                {% if task.variance_hours > 0 %}
                                                    {{ '%.2f'|format(task.variance_hours) }} Over Estimate
                                                {% elif task.variance_hours < 0 %}
                                                    {{ '%.2f'|format(-task.variance_hours) }} Under Estimate
                                                {% else %}
                                                    On Estimate
                                                {% endif %}
                                            </td>
                                            <td>{{ task.completed_by or '' }}</td>
                                            <td>
                                                <a class="btn btn-sm btn-secondary" href="{{ url_for('task_management', edit_id=task.id) }}">Edit</a>
                                                <form method="post" style="display:inline-block;" onsubmit="return confirm('Delete this task?');">
                                                    <input type="hidden" name="action" value="delete">
                                                    <input type="hidden" name="task_id" value="{{ task.id }}">
                                                    <button class="btn btn-sm btn-danger" type="submit">Delete</button>
                                                </form>
                                            </td>
                                        </tr>
                                    {% endfor %}
                                {% else %}
                                    <tr>
                                        <td colspan="17" class="text-muted">No tasks found.</td>
                                    </tr>
                                {% endif %}
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
            </div>
            <script>
                const taskCategories = {{ task_categories | tojson }};
                const categorySelect = document.getElementById('task-category');
                const taskSelect = document.getElementById('task-title');
                const customTaskContainer = document.getElementById('custom-task-container');
                const customTaskInput = document.getElementById('custom-task-title');

                function updateTaskOptions(keepSelection) {
                    const category = categorySelect.value;
                    const selectedTask = keepSelection ? taskSelect.value : '';
                    const isCustom = category === 'Other (Custom)';
                    taskSelect.innerHTML = '<option value="">Select task</option>';

                    if (!isCustom && taskCategories[category]) {
                        taskCategories[category].forEach((task) => {
                            const option = new Option(task, task, false, task === selectedTask);
                            taskSelect.add(option);
                        });
                    }

                    taskSelect.required = !isCustom;
                    taskSelect.disabled = isCustom;
                    customTaskContainer.classList.toggle('d-none', !isCustom);
                    customTaskInput.required = isCustom;
                }

                categorySelect.addEventListener('change', () => updateTaskOptions(false));
                updateTaskOptions(true);
            </script>
        </body>
        </html>
        """,
        employees=employees,
        projects=projects,
        task_categories=TASK_CATEGORIES,
        tasks=tasks,
        edit_task=edit_task,
        employee_filter=employee_filter,
        project_filter=project_filter,
        status_filter=status_filter,
    )


@app.route("/admin")
@login_required
def admin():
    if current_user.role != "admin":
        flash("Admin access required.", "danger")
        return redirect(url_for("dashboard"))

    return render_template_string(
        """
        <!doctype html>
        <html lang="en">
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <title>Admin Panel</title>
            <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
        </head>
        <body class="bg-light">
            <div class="container py-5">
                <div class="card shadow-sm">
                    <div class="card-body">
                        <h1 class="h3 mb-3">Admin Panel</h1>
                        <p>You are signed in as an administrator.</p>
                        <a class="btn btn-primary" href="{{ url_for('dashboard') }}">Back to dashboard</a>
                        <a class="btn btn-outline-secondary ms-2" href="{{ url_for('create_user') }}">Create User</a>
                        <a class="btn btn-outline-info ms-2" href="{{ url_for('admin_attendance') }}">Manage Attendance</a>
                        <a class="btn btn-outline-primary ms-2" href="{{ url_for('admin_employees') }}">Manage Employees</a>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """
    )


@app.route("/admin/create-user", methods=["GET", "POST"])
@login_required
def create_user():
    if current_user.role != "admin":
        flash("Admin access required.", "danger")
        return redirect(url_for("dashboard"))

    message = None
    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        email = request.form.get("email", "").strip()
        username = request.form.get("username", "").strip()

        if not full_name or not email or not username:
            message = "All fields are required."
        else:
            with get_db() as conn:
                existing = conn.execute(
                    "SELECT id FROM users WHERE username = ?",
                    (username,),
                ).fetchone()
                if existing:
                    message = "Username already exists."
                else:
                    temp_password = secrets.token_urlsafe(12)
                    conn.execute(
                        "INSERT INTO users (username, password_hash, role, full_name, email, force_password_change) VALUES (?, ?, ?, ?, ?, ?)",
                        (username, generate_password_hash(temp_password), "user", full_name, email, 1),
                    )
                    conn.commit()
                    send_welcome_email(email, full_name, username, temp_password)
                    message = (
                        f"User created successfully. Temporary password: {temp_password}"
                    )

    return render_template_string(
        """
        <!doctype html>
        <html lang="en">
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <title>Create User</title>
            <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
        </head>
        <body class="bg-light">
            <div class="container py-5">
                <div class="card shadow-sm mx-auto" style="max-width: 560px;">
                    <div class="card-body">
                        <div class="d-flex align-items-center mb-3">
                            <a class="btn btn-outline-secondary me-3" href="{{ url_for('dashboard') }}">Back</a>
                            <h1 class="h3 mb-0">Create User</h1>
                        </div>
                        {% if message %}
                            <div class="alert alert-success" role="alert">
                                {{ message }}
                            </div>
                        {% endif %}
                        <form method="post">
                            <div class="mb-3">
                                <label class="form-label">Full Name</label>
                                <input class="form-control" name="full_name" required>
                            </div>
                            <div class="mb-3">
                                <label class="form-label">Email</label>
                                <input class="form-control" type="email" name="email" required>
                            </div>
                            <div class="mb-3">
                                <label class="form-label">Username</label>
                                <input class="form-control" name="username" required>
                            </div>
                            <button class="btn btn-primary" type="submit">Create User</button>
                        </form>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """,
        message=message,
    )


# Attendance actions
@app.route('/attendance/punch-in', methods=['POST'])
@login_required
def punch_in():
    today = datetime.date.today().isoformat()
    user_id = current_user.id
    username = current_user.username
    with get_db() as conn:
        existing = conn.execute(
            "SELECT id, punch_in_time FROM attendance WHERE user_id = ? AND date = ?",
            (user_id, today),
        ).fetchone()
        if existing and existing['punch_in_time']:
            flash('You have already punched in today.', 'warning')
            return redirect(url_for('dashboard'))
        now = datetime.datetime.now().isoformat()
        if existing:
            conn.execute(
                "UPDATE attendance SET punch_in_time = ? WHERE id = ?",
                (now, existing['id']),
            )
        else:
            conn.execute(
                "INSERT INTO attendance (user_id, username, date, punch_in_time) VALUES (?, ?, ?, ?)",
                (user_id, username, today, now),
            )
        conn.commit()
    flash('Punch in recorded.', 'success')
    return redirect(url_for('dashboard'))


@app.route('/attendance/punch-out', methods=['POST'])
@login_required
def punch_out():
    today = datetime.date.today().isoformat()
    user_id = current_user.id
    with get_db() as conn:
        rec = conn.execute(
            "SELECT id, punch_in_time, punch_out_time FROM attendance WHERE user_id = ? AND date = ?",
            (user_id, today),
        ).fetchone()
        if not rec or not rec['punch_in_time']:
            flash('Cannot punch out before punching in.', 'danger')
            return redirect(url_for('dashboard'))
        if rec['punch_out_time']:
            flash('You have already punched out today.', 'warning')
            return redirect(url_for('dashboard'))
        now = datetime.datetime.now().isoformat()
        # calculate total hours
        try:
            t_in = datetime.datetime.fromisoformat(rec['punch_in_time'])
            t_out = datetime.datetime.fromisoformat(now)
            delta = t_out - t_in
            total_hours = round(delta.total_seconds() / 3600, 2)
        except Exception:
            total_hours = None
        conn.execute(
            "UPDATE attendance SET punch_out_time = ?, total_hours = ? WHERE id = ?",
            (now, total_hours, rec['id']),
        )
        conn.commit()
    flash('Punch out recorded.', 'success')
    return redirect(url_for('dashboard'))


@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("index"))


@app.route('/admin/attendance')
@login_required
def admin_attendance():
    if current_user.role != 'admin':
        flash('Admin access required.', 'danger')
        return redirect(url_for('dashboard'))
    with get_db() as conn:
        rows = conn.execute(
            "SELECT user_id, username, date, punch_in_time, punch_out_time, total_hours FROM attendance ORDER BY date DESC, username"
        ).fetchall()
    return render_template_string(
        """
        <!doctype html>
        <html lang="en">
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <title>Attendance Management</title>
            <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
        </head>
        <body class="bg-light">
            <div class="container py-5">
                <div class="d-flex align-items-center mb-3">
                    <a class="btn btn-outline-secondary me-3" href="{{ url_for('dashboard') }}">Back</a>
                    <h1 class="h3 me-auto mb-0">Attendance Management</h1>
                    <a class="btn btn-success" href="{{ url_for('download_attendance') }}">Download Attendance Report</a>
                </div>
                <div class="card shadow-sm">
                    <div class="card-body">
                        <div class="table-responsive">
                            <table class="table table-striped">
                                <thead>
                                    <tr>
                                        <th>Username</th>
                                        <th>Date</th>
                                        <th>Punch In</th>
                                        <th>Punch Out</th>
                                        <th>Total Hours</th>
                                    </tr>
                                </thead>
                                <tbody>
                                {% for r in rows %}
                                    <tr>
                                        <td>{{ r.username }}</td>
                                        <td>{{ r.date }}</td>
                                        <td>{{ r.punch_in_time or '' }}</td>
                                        <td>{{ r.punch_out_time or '' }}</td>
                                        <td>{{ r.total_hours or '' }}</td>
                                    </tr>
                                {% endfor %}
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """,
        rows=rows,
    )


@app.route('/admin/employees')
@login_required
def admin_employees():
    if current_user.role != 'admin':
        flash('Admin access required.', 'danger')
        return redirect(url_for('dashboard'))
    with get_db() as conn:
        rows = conn.execute(
            "SELECT id, name, department, salary FROM employees ORDER BY name"
        ).fetchall()
    return render_template_string(
        """
        <!doctype html>
        <html lang="en">
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <title>Employee Management</title>
            <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
        </head>
        <body class="bg-light">
            <div class="container py-5">
                <div class="d-flex align-items-center mb-3">
                    <a class="btn btn-outline-secondary me-3" href="{{ url_for('dashboard') }}">Back</a>
                    <h1 class="h3 me-auto mb-0">Employee Management</h1>
                    <a class="btn btn-success" href="{{ url_for('add_employee') }}">Add Employee</a>
                </div>
                <div class="card shadow-sm">
                    <div class="card-body">
                        <div class="table-responsive">
                            <table class="table table-striped">
                                <thead>
                                    <tr>
                                        <th>Name</th>
                                        <th>Department</th>
                                        <th>Salary</th>
                                        <th>Actions</th>
                                    </tr>
                                </thead>
                                <tbody>
                                {% for r in rows %}
                                    <tr>
                                        <td>{{ r.name }}</td>
                                        <td>{{ r.department or '' }}</td>
                                        <td>{{ r.salary or '' }}</td>
                                        <td>
                                            <a class="btn btn-sm btn-primary" href="{{ url_for('view_employee', emp_id=r.id) }}">View</a>
                                            <a class="btn btn-sm btn-secondary" href="{{ url_for('edit_employee', emp_id=r.id) }}">Edit</a>
                                            <form method="post" action="{{ url_for('delete_employee', emp_id=r.id) }}" style="display:inline-block;" onsubmit="return confirm('Delete this employee?');">
                                                <button class="btn btn-sm btn-danger" type="submit">Delete</button>
                                            </form>
                                        </td>
                                    </tr>
                                {% endfor %}
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """,
        rows=rows,
    )


@app.route('/admin/employees/add', methods=['GET', 'POST'])
@login_required
def add_employee():
    if current_user.role != 'admin':
        flash('Admin access required.', 'danger')
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        address = request.form.get('address', '').strip()
        education = request.form.get('education', '').strip()
        experience = request.form.get('experience', '').strip()
        emergency_contact = request.form.get('emergency_contact', '').strip()
        departments = request.form.getlist('department')
        department = ','.join(departments)
        salary = request.form.get('salary') or None
        pan_file = request.files.get('pan')
        aadhaar_file = request.files.get('aadhaar')
        other_file = request.files.get('other')
        pan_path = save_uploaded_file(pan_file)
        aadhaar_path = save_uploaded_file(aadhaar_file)
        other_path = save_uploaded_file(other_file)
        with get_db() as conn:
            conn.execute(
                "INSERT INTO employees (name, address, education, experience, emergency_contact, department, salary, pan_path, aadhaar_path, other_docs_path) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (name, address, education, experience, emergency_contact, department, salary, pan_path, aadhaar_path, other_path),
            )
            conn.commit()
        flash('Employee added.', 'success')
        return redirect(url_for('admin_employees'))
    return render_template_string(
        """
        <!doctype html>
        <html lang="en">
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <title>Add Employee</title>
            <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
        </head>
        <body class="bg-light">
            <div class="container py-5">
                <div class="card shadow-sm mx-auto" style="max-width: 800px;">
                    <div class="card-body">
                        <div class="d-flex align-items-center mb-3">
                            <a class="btn btn-outline-secondary me-3" href="{{ url_for('admin_employees') }}">Back</a>
                            <h1 class="h3 mb-0">Add Employee</h1>
                        </div>
                        <form method="post" enctype="multipart/form-data">
                            <div class="mb-3">
                                <label class="form-label">Name</label>
                                <input class="form-control" name="name" required>
                            </div>
                            <div class="mb-3">
                                <label class="form-label">Address</label>
                                <textarea class="form-control" name="address"></textarea>
                            </div>
                            <div class="mb-3">
                                <label class="form-label">Education</label>
                                <input class="form-control" name="education">
                            </div>
                            <div class="mb-3">
                                <label class="form-label">Experience</label>
                                <input class="form-control" name="experience">
                            </div>
                            <div class="mb-3">
                                <label class="form-label">Emergency Contact Number</label>
                                <input class="form-control" name="emergency_contact">
                            </div>
                            <div class="mb-3">
                                <label class="form-label">Department</label><br>
                                <label class="form-check form-check-inline"><input class="form-check-input" type="checkbox" name="department" value="Google"> Google</label>
                                <label class="form-check form-check-inline"><input class="form-check-input" type="checkbox" name="department" value="Social"> Social</label>
                                <label class="form-check form-check-inline"><input class="form-check-input" type="checkbox" name="department" value="Website"> Website</label>
                            </div>
                            <div class="mb-3">
                                <label class="form-label">Salary</label>
                                <input class="form-control" name="salary" type="number" step="0.01">
                            </div>
                            <div class="mb-3">
                                <label class="form-label">PAN Card (upload)</label>
                                <input class="form-control" type="file" name="pan">
                            </div>
                            <div class="mb-3">
                                <label class="form-label">Aadhaar Card (upload)</label>
                                <input class="form-control" type="file" name="aadhaar">
                            </div>
                            <div class="mb-3">
                                <label class="form-label">Other Documents (upload)</label>
                                <input class="form-control" type="file" name="other">
                            </div>
                            <button class="btn btn-primary" type="submit">Add Employee</button>
                        </form>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """,
    )


@app.route('/admin/employees/<int:emp_id>')
@login_required
def view_employee(emp_id):
        if current_user.role != 'admin':
            flash('Admin access required.', 'danger')
            return redirect(url_for('dashboard'))
        with get_db() as conn:
            r = conn.execute('SELECT * FROM employees WHERE id = ?', (emp_id,)).fetchone()
            if not r:
                flash('Employee not found.', 'warning')
                return redirect(url_for('admin_employees'))
        return render_template_string(
            """
            <!doctype html>
            <html lang="en">
            <head>
                <meta charset="utf-8">
                <meta name="viewport" content="width=device-width, initial-scale=1">
                <title>View Employee</title>
                <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
            </head>
            <body class="bg-light">
                <div class="container py-5">
                    <div class="card shadow-sm mx-auto" style="max-width: 800px;">
                        <div class="card-body">
                            <div class="d-flex align-items-center mb-3">
                                <a class="btn btn-outline-secondary me-3" href="{{ url_for('admin_employees') }}">Back</a>
                                <h1 class="h3 mb-0">{{ r.name }}</h1>
                            </div>
                            <p><strong>Department:</strong> {{ r.department }}</p>
                            <p><strong>Address:</strong><br>{{ r.address }}</p>
                            <p><strong>Education:</strong> {{ r.education }}</p>
                            <p><strong>Experience:</strong> {{ r.experience }}</p>
                            <p><strong>Emergency Contact:</strong> {{ r.emergency_contact }}</p>
                            <p><strong>Salary:</strong> {{ r.salary }}</p>
                            <p><strong>PAN:</strong> {% if r.pan_path %}<a href="/{{ r.pan_path }}">Download</a>{% else %}N/A{% endif %}</p>
                            <p><strong>Aadhaar:</strong> {% if r.aadhaar_path %}<a href="/{{ r.aadhaar_path }}">Download</a>{% else %}N/A{% endif %}</p>
                            <p><strong>Other Docs:</strong> {% if r.other_docs_path %}<a href="/{{ r.other_docs_path }}">Download</a>{% else %}N/A{% endif %}</p>
                        </div>
                    </div>
                </div>
            </body>
            </html>
            """,
            r=r,
        )


@app.route('/admin/employees/<int:emp_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_employee(emp_id):
        if current_user.role != 'admin':
            flash('Admin access required.', 'danger')
            return redirect(url_for('dashboard'))
        with get_db() as conn:
            r = conn.execute('SELECT * FROM employees WHERE id = ?', (emp_id,)).fetchone()
            if not r:
                flash('Employee not found.', 'warning')
                return redirect(url_for('admin_employees'))
        if request.method == 'POST':
            name = request.form.get('name', '').strip()
            address = request.form.get('address', '').strip()
            education = request.form.get('education', '').strip()
            experience = request.form.get('experience', '').strip()
            emergency_contact = request.form.get('emergency_contact', '').strip()
            departments = request.form.getlist('department')
            department = ','.join(departments)
            salary = request.form.get('salary') or None
            pan_file = request.files.get('pan')
            aadhaar_file = request.files.get('aadhaar')
            other_file = request.files.get('other')
            pan_path = r['pan_path']
            aadhaar_path = r['aadhaar_path']
            other_path = r['other_docs_path']
            if pan_file and pan_file.filename:
                pan_path = save_uploaded_file(pan_file)
            if aadhaar_file and aadhaar_file.filename:
                aadhaar_path = save_uploaded_file(aadhaar_file)
            if other_file and other_file.filename:
                other_path = save_uploaded_file(other_file)
            with get_db() as conn:
                conn.execute(
                    """
                    UPDATE employees SET name=?, address=?, education=?, experience=?, emergency_contact=?, department=?, salary=?, pan_path=?, aadhaar_path=?, other_docs_path=? WHERE id=?
                    """,
                    (name, address, education, experience, emergency_contact, department, salary, pan_path, aadhaar_path, other_path, emp_id),
                )
                conn.commit()
            flash('Employee updated.', 'success')
            return redirect(url_for('view_employee', emp_id=emp_id))
        current_depts = (r['department'] or '').split(',') if r['department'] else []
        return render_template_string(
            """
            <!doctype html>
            <html lang="en">
            <head>
                <meta charset="utf-8">
                <meta name="viewport" content="width=device-width, initial-scale=1">
                <title>Edit Employee</title>
                <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
            </head>
            <body class="bg-light">
                <div class="container py-5">
                    <div class="card shadow-sm mx-auto" style="max-width: 800px;">
                        <div class="card-body">
                            <div class="d-flex align-items-center mb-3">
                                <a class="btn btn-outline-secondary me-3" href="{{ url_for('admin_employees') }}">Back</a>
                                <h1 class="h3 mb-0">Edit Employee</h1>
                            </div>
                            <form method="post" enctype="multipart/form-data">
                                <div class="mb-3">
                                    <label class="form-label">Name</label>
                                    <input class="form-control" name="name" value="{{ r.name }}" required>
                                </div>
                                <div class="mb-3">
                                    <label class="form-label">Address</label>
                                    <textarea class="form-control" name="address">{{ r.address }}</textarea>
                                </div>
                                <div class="mb-3">
                                    <label class="form-label">Education</label>
                                    <input class="form-control" name="education" value="{{ r.education }}">
                                </div>
                                <div class="mb-3">
                                    <label class="form-label">Experience</label>
                                    <input class="form-control" name="experience" value="{{ r.experience }}">
                                </div>
                                <div class="mb-3">
                                    <label class="form-label">Emergency Contact Number</label>
                                    <input class="form-control" name="emergency_contact" value="{{ r.emergency_contact }}">
                                </div>
                                <div class="mb-3">
                                    <label class="form-label">Department</label><br>
                                    {% for dep in ['Google','Social','Website'] %}
                                        <label class="form-check form-check-inline"><input class="form-check-input" type="checkbox" name="department" value="{{ dep }}" {% if dep in current_depts %}checked{% endif %}> {{ dep }}</label>
                                    {% endfor %}
                                </div>
                                <div class="mb-3">
                                    <label class="form-label">Salary</label>
                                    <input class="form-control" name="salary" type="number" step="0.01" value="{{ r.salary }}">
                                </div>
                                <div class="mb-3">
                                    <label class="form-label">PAN Card (upload)</label>
                                    <input class="form-control" type="file" name="pan">
                                </div>
                                <div class="mb-3">
                                    <label class="form-label">Aadhaar Card (upload)</label>
                                    <input class="form-control" type="file" name="aadhaar">
                                </div>
                                <div class="mb-3">
                                    <label class="form-label">Other Documents (upload)</label>
                                    <input class="form-control" type="file" name="other">
                                </div>
                                <button class="btn btn-primary" type="submit">Save</button>
                                <a class="btn btn-outline-secondary ms-2" href="{{ url_for('view_employee', emp_id=r.id) }}">Cancel</a>
                            </form>
                        </div>
                    </div>
                </div>
            </body>
            </html>
            """,
            r=r,
            current_depts=current_depts,
        )


@app.route('/admin/employees/<int:emp_id>/delete', methods=['POST'])
@login_required
def delete_employee(emp_id):
        if current_user.role != 'admin':
            flash('Admin access required.', 'danger')
            return redirect(url_for('dashboard'))
        with get_db() as conn:
            r = conn.execute('SELECT * FROM employees WHERE id = ?', (emp_id,)).fetchone()
            if not r:
                flash('Employee not found.', 'warning')
                return redirect(url_for('admin_employees'))
            for p in (r['pan_path'], r['aadhaar_path'], r['other_docs_path']):
                try:
                    if p and os.path.exists(p):
                        os.remove(p)
                except Exception:
                    pass
            conn.execute('DELETE FROM employees WHERE id = ?', (emp_id,))
            conn.commit()
        flash('Employee deleted.', 'success')
        return redirect(url_for('admin_employees'))


@app.route('/admin/projects')
@login_required
def admin_projects():
    if current_user.role != 'admin':
        flash('Admin access required.', 'danger')
        return redirect(url_for('dashboard'))

    search = request.args.get('search', '').strip()
    service_filter = request.args.get('service_filter', 'All').strip()
    page = request.args.get('page', 1, type=int)
    if page < 1:
        page = 1

    per_page = 10
    query = """
        SELECT id, client_name, assigned_to, services, client_email, whatsapp_number
        FROM projects
        WHERE 1 = 1
    """
    params = []

    if search:
        search_term = f"%{search.lower()}%"
        query += """
            AND (
                lower(client_name) LIKE ? OR
                lower(assigned_to) LIKE ? OR
                lower(client_email) LIKE ? OR
                lower(whatsapp_number) LIKE ?
            )
        """
        params.extend([search_term, search_term, search_term, search_term])

    if service_filter != 'All':
        query += " AND lower(services) LIKE ?"
        params.append(f"%{service_filter.lower()}%")

    query += " ORDER BY lower(client_name) ASC, client_name ASC, id ASC"

    with get_db() as conn:
        all_projects = conn.execute(query, params).fetchall()

    total_projects = len(all_projects)
    total_pages = max(1, (total_projects + per_page - 1) // per_page)
    if page > total_pages:
        page = total_pages

    start = (page - 1) * per_page
    projects = all_projects[start:start + per_page]

    return render_template_string(
        """
        <!doctype html>
        <html lang="en">
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <title>Project Management</title>
            <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
        </head>
        <body class="bg-light">
            <div class="container py-5">
                <div class="d-flex align-items-center mb-3">
                    <a class="btn btn-outline-secondary me-3" href="{{ url_for('dashboard') }}">Back</a>
                    <h1 class="h3 me-auto mb-0">Project Management</h1>
                    <a class="btn btn-success" href="{{ url_for('add_project') }}">Add Project</a>
                </div>
                <div class="card shadow-sm">
                    <div class="card-body">
                        <div class="d-flex justify-content-between align-items-center mb-3 flex-wrap gap-2">
                            <div class="text-muted">Total Projects: {{ total_projects }}</div>
                            <form class="row g-2 align-items-end" method="get">
                                <div class="col">
                                    <label class="form-label small mb-1" for="search">Search</label>
                                    <input class="form-control" id="search" name="search" type="text" value="{{ search }}" placeholder="Client, employee, email, WhatsApp">
                                </div>
                                <div class="col">
                                    <label class="form-label small mb-1" for="service_filter">Services</label>
                                    <select class="form-select" id="service_filter" name="service_filter">
                                        <option value="All" {% if service_filter == 'All' %}selected{% endif %}>All</option>
                                        <option value="Social Media" {% if service_filter == 'Social Media' %}selected{% endif %}>Social Media</option>
                                        <option value="SEO" {% if service_filter == 'SEO' %}selected{% endif %}>SEO</option>
                                        <option value="Meta Ads" {% if service_filter == 'Meta Ads' %}selected{% endif %}>Meta Ads</option>
                                        <option value="Google Ads" {% if service_filter == 'Google Ads' %}selected{% endif %}>Google Ads</option>
                                        <option value="Website Development" {% if service_filter == 'Website Development' %}selected{% endif %}>Website Development</option>
                                    </select>
                                </div>
                                <div class="col-auto">
                                    <button class="btn btn-primary" type="submit">Filter</button>
                                </div>
                                <div class="col-auto">
                                    <a class="btn btn-outline-secondary" href="{{ url_for('admin_projects') }}">Reset</a>
                                </div>
                            </form>
                        </div>
                        <div class="table-responsive">
                            <table class="table table-striped align-middle">
                                <thead>
                                    <tr>
                                        <th>Client Name</th>
                                        <th>Assigned Employee</th>
                                        <th>Services</th>
                                        <th>Client Email</th>
                                        <th>Client WhatsApp Number</th>
                                        <th>Actions</th>
                                    </tr>
                                </thead>
                                <tbody>
                                {% if projects %}
                                    {% for project in projects %}
                                        <tr>
                                            <td>{{ project.client_name or '' }}</td>
                                            <td>{{ project.assigned_to or '' }}</td>
                                            <td>{{ project.services or '' }}</td>
                                            <td>{{ project.client_email or '' }}</td>
                                            <td>{{ project.whatsapp_number or '' }}</td>
                                            <td>
                                                <a class="btn btn-sm btn-primary" href="{{ url_for('view_project', project_id=project.id) }}">View</a>
                                                <a class="btn btn-sm btn-secondary" href="{{ url_for('edit_project', project_id=project.id) }}">Edit</a>
                                                <a class="btn btn-sm btn-danger" href="{{ url_for('delete_project', project_id=project.id) }}">Delete</a>
                                            </td>
                                        </tr>
                                    {% endfor %}
                                {% else %}
                                    <tr>
                                        <td colspan="6">
                                            <div class="alert alert-info mb-0">
                                                {% if search or service_filter != 'All' %}
                                                    No matching projects found.
                                                {% else %}
                                                    No projects found.
                                                {% endif %}
                                            </div>
                                        </td>
                                    </tr>
                                {% endif %}
                                </tbody>
                            </table>
                        </div>
                        {% if total_pages > 1 %}
                        <nav aria-label="Project pagination">
                            <ul class="pagination justify-content-center mb-0">
                                <li class="page-item {% if page <= 1 %}disabled{% endif %}">
                                    <a class="page-link" href="{{ url_for('admin_projects', page=page-1, search=search or None, service_filter=service_filter if service_filter != 'All' else None) }}">Previous</a>
                                </li>
                                {% for page_num in range(1, total_pages + 1) %}
                                <li class="page-item {% if page_num == page %}active{% endif %}">
                                    <a class="page-link" href="{{ url_for('admin_projects', page=page_num, search=search or None, service_filter=service_filter if service_filter != 'All' else None) }}">{{ page_num }}</a>
                                </li>
                                {% endfor %}
                                <li class="page-item {% if page >= total_pages %}disabled{% endif %}">
                                    <a class="page-link" href="{{ url_for('admin_projects', page=page+1, search=search or None, service_filter=service_filter if service_filter != 'All' else None) }}">Next</a>
                                </li>
                            </ul>
                        </nav>
                        {% endif %}
                    </div>
                </div>
            </div>
        </body>
        </html>
        """,
        projects=projects,
        total_projects=total_projects,
        search=search,
        service_filter=service_filter,
        page=page,
        total_pages=total_pages,
    )


@app.route('/admin/projects/add', methods=['GET', 'POST'])
@login_required
def add_project():
    if current_user.role != 'admin':
        flash('Admin access required.', 'danger')
        return redirect(url_for('dashboard'))

    with get_db() as conn:
        employees = conn.execute("SELECT id, name FROM employees ORDER BY name").fetchall()

    if request.method == 'POST':
        client_name = request.form.get('client_name', '').strip()
        services = request.form.getlist('services')
        assigned_to = request.form.get('assigned_to', '').strip()
        delivery_details = request.form.get('delivery_details', '').strip()
        whatsapp_number = request.form.get('whatsapp_number', '').strip()
        client_email = request.form.get('client_email', '').strip()
        client_website = request.form.get('client_website', '').strip()
        client_address = request.form.get('client_address', '').strip()
        client_gst_number = request.form.get('client_gst_number', '').strip()

        required_fields = [
            ('Client Name', client_name),
            ('Services', services),
            ('Assigned To', assigned_to),
            ('Delivery Details', delivery_details),
            ('Client WhatsApp Number', whatsapp_number),
            ('Client Email', client_email),
            ('Client Website', client_website),
            ('Client Address', client_address),
            ('Client GST Number', client_gst_number),
        ]
        if any(not value for _, value in required_fields):
            flash('All fields are required.', 'danger')
            return render_template_string(
                """
                <!doctype html>
                <html lang="en">
                <head>
                    <meta charset="utf-8">
                    <meta name="viewport" content="width=device-width, initial-scale=1">
                    <title>Add Project</title>
                    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
                </head>
                <body class="bg-light">
                    <div class="container py-5">
                        <div class="card shadow-sm mx-auto" style="max-width: 900px;">
                            <div class="card-body">
                                <div class="d-flex align-items-center mb-3">
                                    <a class="btn btn-outline-secondary me-3" href="{{ url_for('admin_projects') }}">Back</a>
                                    <h1 class="h3 mb-0">Add Project</h1>
                                </div>
                                {% with messages = get_flashed_messages(with_categories=true) %}
                                    {% if messages %}
                                        {% for category, message in messages %}
                                            <div class="alert alert-{{ category }}">{{ message }}</div>
                                        {% endfor %}
                                    {% endif %}
                                {% endwith %}
                                <form method="post">
                                    <div class="mb-3">
                                        <label class="form-label">Client Name</label>
                                        <input class="form-control" name="client_name" value="{{ client_name }}" required>
                                    </div>
                                    <div class="mb-3">
                                        <label class="form-label">Services</label><br>
                                        <label class="form-check form-check-inline"><input class="form-check-input" type="checkbox" name="services" value="Social Media" {% if 'Social Media' in services %}checked{% endif %}> Social Media</label>
                                        <label class="form-check form-check-inline"><input class="form-check-input" type="checkbox" name="services" value="SEO" {% if 'SEO' in services %}checked{% endif %}> SEO</label>
                                        <label class="form-check form-check-inline"><input class="form-check-input" type="checkbox" name="services" value="Meta Ads" {% if 'Meta Ads' in services %}checked{% endif %}> Meta Ads</label>
                                        <label class="form-check form-check-inline"><input class="form-check-input" type="checkbox" name="services" value="Google Ads" {% if 'Google Ads' in services %}checked{% endif %}> Google Ads</label>
                                        <label class="form-check form-check-inline"><input class="form-check-input" type="checkbox" name="services" value="Website Development" {% if 'Website Development' in services %}checked{% endif %}> Website Development</label>
                                    </div>
                                    <div class="mb-3">
                                        <label class="form-label">Assigned To</label>
                                        <select class="form-select" name="assigned_to" required>
                                            <option value="">Select employee</option>
                                            {% for employee in employees %}
                                                <option value="{{ employee.name }}" {% if employee.name == assigned_to %}selected{% endif %}>{{ employee.name }}</option>
                                            {% endfor %}
                                        </select>
                                    </div>
                                    <div class="mb-3">
                                        <label class="form-label">Delivery Details</label>
                                        <textarea class="form-control" name="delivery_details" rows="3" required>{{ delivery_details }}</textarea>
                                    </div>
                                    <div class="mb-3">
                                        <label class="form-label">Client WhatsApp Number</label>
                                        <input class="form-control" name="whatsapp_number" value="{{ whatsapp_number }}" required>
                                    </div>
                                    <div class="mb-3">
                                        <label class="form-label">Client Email</label>
                                        <input class="form-control" type="email" name="client_email" value="{{ client_email }}" required>
                                    </div>
                                    <div class="mb-3">
                                        <label class="form-label">Client Website</label>
                                        <input class="form-control" name="client_website" value="{{ client_website }}" required>
                                    </div>
                                    <div class="mb-3">
                                        <label class="form-label">Client Address</label>
                                        <textarea class="form-control" name="client_address" rows="2" required>{{ client_address }}</textarea>
                                    </div>
                                    <div class="mb-3">
                                        <label class="form-label">Client GST Number</label>
                                        <input class="form-control" name="client_gst_number" value="{{ client_gst_number }}" required>
                                    </div>
                                    <button class="btn btn-primary" type="submit">Save Project</button>
                                </form>
                            </div>
                        </div>
                    </div>
                </body>
                </html>
                """,
                client_name=client_name,
                services=services,
                assigned_to=assigned_to,
                delivery_details=delivery_details,
                whatsapp_number=whatsapp_number,
                client_email=client_email,
                client_website=client_website,
                client_address=client_address,
                client_gst_number=client_gst_number,
                employees=employees,
            )

        services_text = ','.join(services)
        with get_db() as conn:
            conn.execute(
                """
                INSERT INTO projects (
                    client_name,
                    services,
                    assigned_to,
                    delivery_details,
                    whatsapp_number,
                    client_email,
                    client_website,
                    client_address,
                    client_gst_number
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    client_name,
                    services_text,
                    assigned_to,
                    delivery_details,
                    whatsapp_number,
                    client_email,
                    client_website,
                    client_address,
                    client_gst_number,
                ),
            )
            conn.commit()

        flash('Project created successfully.', 'success')
        return redirect(url_for('admin_projects'))

    return render_template_string(
        """
        <!doctype html>
        <html lang="en">
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <title>Add Project</title>
            <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
        </head>
        <body class="bg-light">
            <div class="container py-5">
                <div class="card shadow-sm mx-auto" style="max-width: 900px;">
                    <div class="card-body">
                        <h1 class="h3 mb-3">Add Project</h1>
                        {% with messages = get_flashed_messages(with_categories=true) %}
                            {% if messages %}
                                {% for category, message in messages %}
                                    <div class="alert alert-{{ category }}">{{ message }}</div>
                                {% endfor %}
                            {% endif %}
                        {% endwith %}
                        <form method="post">
                            <div class="mb-3">
                                <label class="form-label">Client Name</label>
                                <input class="form-control" name="client_name" required>
                            </div>
                            <div class="mb-3">
                                <label class="form-label">Services</label><br>
                                <label class="form-check form-check-inline"><input class="form-check-input" type="checkbox" name="services" value="Social Media"> Social Media</label>
                                <label class="form-check form-check-inline"><input class="form-check-input" type="checkbox" name="services" value="SEO"> SEO</label>
                                <label class="form-check form-check-inline"><input class="form-check-input" type="checkbox" name="services" value="Meta Ads"> Meta Ads</label>
                                <label class="form-check form-check-inline"><input class="form-check-input" type="checkbox" name="services" value="Google Ads"> Google Ads</label>
                                <label class="form-check form-check-inline"><input class="form-check-input" type="checkbox" name="services" value="Website Development"> Website Development</label>
                            </div>
                            <div class="mb-3">
                                <label class="form-label">Assigned To</label>
                                <select class="form-select" name="assigned_to" required>
                                    <option value="">Select employee</option>
                                    {% for employee in employees %}
                                        <option value="{{ employee.name }}">{{ employee.name }}</option>
                                    {% endfor %}
                                </select>
                            </div>
                            <div class="mb-3">
                                <label class="form-label">Delivery Details</label>
                                <textarea class="form-control" name="delivery_details" rows="3" required></textarea>
                            </div>
                            <div class="mb-3">
                                <label class="form-label">Client WhatsApp Number</label>
                                <input class="form-control" name="whatsapp_number" required>
                            </div>
                            <div class="mb-3">
                                <label class="form-label">Client Email</label>
                                <input class="form-control" type="email" name="client_email" required>
                            </div>
                            <div class="mb-3">
                                <label class="form-label">Client Website</label>
                                <input class="form-control" name="client_website" required>
                            </div>
                            <div class="mb-3">
                                <label class="form-label">Client Address</label>
                                <textarea class="form-control" name="client_address" rows="2" required></textarea>
                            </div>
                            <div class="mb-3">
                                <label class="form-label">Client GST Number</label>
                                <input class="form-control" name="client_gst_number" required>
                            </div>
                            <button class="btn btn-primary" type="submit">Save Project</button>
                            <a class="btn btn-outline-secondary ms-2" href="{{ url_for('admin_projects') }}">Back</a>
                        </form>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """,
        employees=employees,
    )


@app.route('/admin/projects/<int:project_id>')
@login_required
def view_project(project_id):
    if current_user.role != 'admin':
        flash('Admin access required.', 'danger')
        return redirect(url_for('dashboard'))
    return render_template_string(
        """
        <!doctype html>
        <html lang="en">
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <title>View Project</title>
            <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
        </head>
        <body class="bg-light">
            <div class="container py-5">
                <div class="card shadow-sm mx-auto" style="max-width: 700px;">
                    <div class="card-body">
                        <div class="d-flex align-items-center mb-3">
                            <a class="btn btn-outline-secondary me-3" href="{{ url_for('admin_projects') }}">Back</a>
                            <h1 class="h3 mb-0">View Project</h1>
                        </div>
                        <p class="text-muted">Project details will be shown here later.</p>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """
    )


@app.route('/admin/projects/<int:project_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_project(project_id):
    if current_user.role != 'admin':
        flash('Admin access required.', 'danger')
        return redirect(url_for('dashboard'))

    with get_db() as conn:
        project = conn.execute(
            "SELECT * FROM projects WHERE id = ?",
            (project_id,),
        ).fetchone()
        employees = conn.execute("SELECT id, name FROM employees ORDER BY name").fetchall()

    if project is None:
        flash('Project not found.', 'warning')
        return redirect(url_for('admin_projects'))

    current_services = []
    if project['services']:
        current_services = [item.strip() for item in str(project['services']).split(',') if item.strip()]

    if request.method == 'POST':
        client_name = request.form.get('client_name', '').strip()
        services = request.form.getlist('services')
        assigned_to = request.form.get('assigned_to', '').strip()
        delivery_details = request.form.get('delivery_details', '').strip()
        whatsapp_number = request.form.get('whatsapp_number', '').strip()
        client_email = request.form.get('client_email', '').strip()
        client_website = request.form.get('client_website', '').strip()
        client_address = request.form.get('client_address', '').strip()
        client_gst_number = request.form.get('client_gst_number', '').strip()

        required_fields = [
            ('Client Name', client_name),
            ('Services', services),
            ('Assigned To', assigned_to),
            ('Delivery Details', delivery_details),
            ('Client WhatsApp Number', whatsapp_number),
            ('Client Email', client_email),
            ('Client Website', client_website),
            ('Client Address', client_address),
            ('Client GST Number', client_gst_number),
        ]
        if any(not value for _, value in required_fields):
            flash('All fields are required.', 'danger')
            return render_template_string(
                """
                <!doctype html>
                <html lang="en">
                <head>
                    <meta charset="utf-8">
                    <meta name="viewport" content="width=device-width, initial-scale=1">
                    <title>Edit Project</title>
                    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
                </head>
                <body class="bg-light">
                    <div class="container py-5">
                        <div class="card shadow-sm mx-auto" style="max-width: 900px;">
                            <div class="card-body">
                                <h1 class="h3 mb-3">Edit Project</h1>
                                {% with messages = get_flashed_messages(with_categories=true) %}
                                    {% if messages %}
                                        {% for category, message in messages %}
                                            <div class="alert alert-{{ category }}">{{ message }}</div>
                                        {% endfor %}
                                    {% endif %}
                                {% endwith %}
                                <form method="post">
                                    <div class="mb-3">
                                        <label class="form-label">Client Name</label>
                                        <input class="form-control" name="client_name" value="{{ client_name }}" required>
                                    </div>
                                    <div class="mb-3">
                                        <label class="form-label">Services</label><br>
                                        <label class="form-check form-check-inline"><input class="form-check-input" type="checkbox" name="services" value="Social Media" {% if 'Social Media' in services %}checked{% endif %}> Social Media</label>
                                        <label class="form-check form-check-inline"><input class="form-check-input" type="checkbox" name="services" value="SEO" {% if 'SEO' in services %}checked{% endif %}> SEO</label>
                                        <label class="form-check form-check-inline"><input class="form-check-input" type="checkbox" name="services" value="Meta Ads" {% if 'Meta Ads' in services %}checked{% endif %}> Meta Ads</label>
                                        <label class="form-check form-check-inline"><input class="form-check-input" type="checkbox" name="services" value="Google Ads" {% if 'Google Ads' in services %}checked{% endif %}> Google Ads</label>
                                        <label class="form-check form-check-inline"><input class="form-check-input" type="checkbox" name="services" value="Website Development" {% if 'Website Development' in services %}checked{% endif %}> Website Development</label>
                                    </div>
                                    <div class="mb-3">
                                        <label class="form-label">Assigned To</label>
                                        <select class="form-select" name="assigned_to" required>
                                            <option value="">Select employee</option>
                                            {% for employee in employees %}
                                                <option value="{{ employee.name }}" {% if employee.name == assigned_to %}selected{% endif %}>{{ employee.name }}</option>
                                            {% endfor %}
                                        </select>
                                    </div>
                                    <div class="mb-3">
                                        <label class="form-label">Delivery Details</label>
                                        <textarea class="form-control" name="delivery_details" rows="3" required>{{ delivery_details }}</textarea>
                                    </div>
                                    <div class="mb-3">
                                        <label class="form-label">Client WhatsApp Number</label>
                                        <input class="form-control" name="whatsapp_number" value="{{ whatsapp_number }}" required>
                                    </div>
                                    <div class="mb-3">
                                        <label class="form-label">Client Email</label>
                                        <input class="form-control" type="email" name="client_email" value="{{ client_email }}" required>
                                    </div>
                                    <div class="mb-3">
                                        <label class="form-label">Client Website</label>
                                        <input class="form-control" name="client_website" value="{{ client_website }}" required>
                                    </div>
                                    <div class="mb-3">
                                        <label class="form-label">Client Address</label>
                                        <textarea class="form-control" name="client_address" rows="2" required>{{ client_address }}</textarea>
                                    </div>
                                    <div class="mb-3">
                                        <label class="form-label">Client GST Number</label>
                                        <input class="form-control" name="client_gst_number" value="{{ client_gst_number }}" required>
                                    </div>
                                    <button class="btn btn-primary" type="submit">Save Changes</button>
                                    <a class="btn btn-outline-secondary ms-2" href="{{ url_for('admin_projects') }}">Back</a>
                                </form>
                            </div>
                        </div>
                    </div>
                </body>
                </html>
                """,
                client_name=client_name,
                services=services,
                assigned_to=assigned_to,
                delivery_details=delivery_details,
                whatsapp_number=whatsapp_number,
                client_email=client_email,
                client_website=client_website,
                client_address=client_address,
                client_gst_number=client_gst_number,
                employees=employees,
            )

        services_text = ','.join(services)
        with get_db() as conn:
            conn.execute(
                """
                UPDATE projects
                SET client_name = ?,
                    services = ?,
                    assigned_to = ?,
                    delivery_details = ?,
                    whatsapp_number = ?,
                    client_email = ?,
                    client_website = ?,
                    client_address = ?,
                    client_gst_number = ?
                WHERE id = ?
                """,
                (
                    client_name,
                    services_text,
                    assigned_to,
                    delivery_details,
                    whatsapp_number,
                    client_email,
                    client_website,
                    client_address,
                    client_gst_number,
                    project_id,
                ),
            )
            conn.commit()

        flash('Project updated successfully.', 'success')
        return redirect(url_for('admin_projects'))

    return render_template_string(
        """
        <!doctype html>
        <html lang="en">
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <title>Edit Project</title>
            <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
        </head>
        <body class="bg-light">
            <div class="container py-5">
                <div class="card shadow-sm mx-auto" style="max-width: 900px;">
                    <div class="card-body">
                        <div class="d-flex align-items-center mb-3">
                            <a class="btn btn-outline-secondary me-3" href="{{ url_for('admin_projects') }}">Back</a>
                            <h1 class="h3 mb-0">Edit Project</h1>
                        </div>
                        {% with messages = get_flashed_messages(with_categories=true) %}
                            {% if messages %}
                                {% for category, message in messages %}
                                    <div class="alert alert-{{ category }}">{{ message }}</div>
                                {% endfor %}
                            {% endif %}
                        {% endwith %}
                        <form method="post">
                            <div class="mb-3">
                                <label class="form-label">Client Name</label>
                                <input class="form-control" name="client_name" value="{{ project.client_name or '' }}" required>
                            </div>
                            <div class="mb-3">
                                <label class="form-label">Services</label><br>
                                <label class="form-check form-check-inline"><input class="form-check-input" type="checkbox" name="services" value="Social Media" {% if 'Social Media' in current_services %}checked{% endif %}> Social Media</label>
                                <label class="form-check form-check-inline"><input class="form-check-input" type="checkbox" name="services" value="SEO" {% if 'SEO' in current_services %}checked{% endif %}> SEO</label>
                                <label class="form-check form-check-inline"><input class="form-check-input" type="checkbox" name="services" value="Meta Ads" {% if 'Meta Ads' in current_services %}checked{% endif %}> Meta Ads</label>
                                <label class="form-check form-check-inline"><input class="form-check-input" type="checkbox" name="services" value="Google Ads" {% if 'Google Ads' in current_services %}checked{% endif %}> Google Ads</label>
                                <label class="form-check form-check-inline"><input class="form-check-input" type="checkbox" name="services" value="Website Development" {% if 'Website Development' in current_services %}checked{% endif %}> Website Development</label>
                            </div>
                            <div class="mb-3">
                                <label class="form-label">Assigned To</label>
                                <select class="form-select" name="assigned_to" required>
                                    <option value="">Select employee</option>
                                    {% for employee in employees %}
                                        <option value="{{ employee.name }}" {% if employee.name == project.assigned_to %}selected{% endif %}>{{ employee.name }}</option>
                                    {% endfor %}
                                </select>
                            </div>
                            <div class="mb-3">
                                <label class="form-label">Delivery Details</label>
                                <textarea class="form-control" name="delivery_details" rows="3" required>{{ project.delivery_details or '' }}</textarea>
                            </div>
                            <div class="mb-3">
                                <label class="form-label">Client WhatsApp Number</label>
                                <input class="form-control" name="whatsapp_number" value="{{ project.whatsapp_number or '' }}" required>
                            </div>
                            <div class="mb-3">
                                <label class="form-label">Client Email</label>
                                <input class="form-control" type="email" name="client_email" value="{{ project.client_email or '' }}" required>
                            </div>
                            <div class="mb-3">
                                <label class="form-label">Client Website</label>
                                <input class="form-control" name="client_website" value="{{ project.client_website or '' }}" required>
                            </div>
                            <div class="mb-3">
                                <label class="form-label">Client Address</label>
                                <textarea class="form-control" name="client_address" rows="2" required>{{ project.client_address or '' }}</textarea>
                            </div>
                            <div class="mb-3">
                                <label class="form-label">Client GST Number</label>
                                <input class="form-control" name="client_gst_number" value="{{ project.client_gst_number or '' }}" required>
                            </div>
                            <button class="btn btn-primary" type="submit">Save Changes</button>
                        </form>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """,
        project=project,
        employees=employees,
        current_services=current_services,
    )


@app.route('/admin/projects/<int:project_id>/delete', methods=['GET', 'POST'])
@login_required
def delete_project(project_id):
    if current_user.role != 'admin':
        flash('Admin access required.', 'danger')
        return redirect(url_for('dashboard'))

    with get_db() as conn:
        project = conn.execute(
            "SELECT id, client_name, assigned_to FROM projects WHERE id = ?",
            (project_id,),
        ).fetchone()

    if project is None:
        flash('Project not found.', 'warning')
        return redirect(url_for('admin_projects'))

    if request.method == 'POST':
        with get_db() as conn:
            conn.execute('DELETE FROM projects WHERE id = ?', (project_id,))
            conn.commit()
        flash('Project deleted successfully.', 'success')
        return redirect(url_for('admin_projects'))

    return render_template_string(
        """
        <!doctype html>
        <html lang="en">
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <title>Delete Project</title>
            <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
        </head>
        <body class="bg-light">
            <div class="container py-5">
                <div class="card shadow-sm mx-auto" style="max-width: 600px;">
                    <div class="card-body">
                        <h1 class="h3 mb-3">Delete Project</h1>
                        <div class="alert alert-warning">
                            <p class="mb-2"><strong>Client Name:</strong> {{ project.client_name or '' }}</p>
                            <p class="mb-0"><strong>Assigned Employee:</strong> {{ project.assigned_to or '' }}</p>
                        </div>
                        <p class="text-muted">This action cannot be undone.</p>
                        <form method="post">
                            <button class="btn btn-danger" type="submit">Confirm Delete</button>
                            <a class="btn btn-outline-secondary ms-2" href="{{ url_for('admin_projects') }}">Cancel</a>
                        </form>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """,
        project=project,
    )


@app.route('/admin/attendance/download')
@login_required
def download_attendance():
    if current_user.role != 'admin':
        flash('Admin access required.', 'danger')
        return redirect(url_for('dashboard'))
    with get_db() as conn:
        rows = conn.execute(
            "SELECT username, date, punch_in_time, punch_out_time, total_hours FROM attendance ORDER BY date DESC, username"
        ).fetchall()
    # Generate Excel file using openpyxl
    try:
        from openpyxl import Workbook
    except Exception:
        flash('openpyxl is not installed on the server.', 'danger')
        return redirect(url_for('admin_attendance'))

    wb = Workbook()
    ws = wb.active
    ws.title = 'Attendance'
    headers = ['Username', 'Date', 'Punch In', 'Punch Out', 'Total Hours']
    ws.append(headers)
    for r in rows:
        ws.append([r['username'], r['date'], r['punch_in_time'], r['punch_out_time'], r['total_hours']])

    bio = io.BytesIO()
    wb.save(bio)
    bio.seek(0)
    payload = bio.getvalue()
    headers = {
        'Content-Disposition': 'attachment; filename="attendance_report.xlsx"',
        'Content-Type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'Content-Length': str(len(payload)),
    }
    return Response(payload, headers=headers)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
    app.run(debug=True)
