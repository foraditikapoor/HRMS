import os
import secrets
import smtplib
import sqlite3
from email.mime.text import MIMEText

from flask import Flask, flash, redirect, render_template_string, request, url_for
from flask_login import (
    LoginManager,
    UserMixin,
    current_user,
    login_required,
    login_user,
    logout_user,
)
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-key")
app.config["DATABASE_PATH"] = os.path.join(app.instance_path, "users.db")

# Gmail SMTP configuration
MAIL_SERVER = "smtp.gmail.com"
MAIL_PORT = 587
MAIL_USE_TLS = True
MAIL_USERNAME = os.environ.get("MAIL_USERNAME", "your_email@gmail.com")
MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD", "your_app_password")
MAIL_DEFAULT_SENDER = MAIL_USERNAME

# Email configuration (keep together near the top)
# Set these environment variables or replace the defaults for local testing
EMAIL_ADDRESS = os.environ.get("EMAIL_ADDRESS", MAIL_USERNAME)
EMAIL_APP_PASSWORD = os.environ.get("EMAIL_APP_PASSWORD", MAIL_PASSWORD)

print("EMAIL USED:", EMAIL_ADDRESS)
print("PASSWORD LENGTH:", len(EMAIL_APP_PASSWORD))

os.makedirs(app.instance_path, exist_ok=True)

login_manager = LoginManager(app)
login_manager.login_view = "login"


class User(UserMixin):
    def __init__(self, user_id, username, password_hash, role="user"):
        self.id = user_id
        self.username = username
        self.password_hash = password_hash
        self.role = role

    @staticmethod
    def from_db(row):
        if row is None:
            return None
        return User(row[0], row[1], row[2], row[3])


def get_db():
    conn = sqlite3.connect(app.config["DATABASE_PATH"])
    conn.row_factory = sqlite3.Row
    return conn


def send_account_created_email(recipient_email, username, temporary_password):
    subject = "Your account has been created"
    body = (
        "Hello\n\n"
        "Your account has been created.\n\n"
        f"Username: {username}\n"
        f"Temporary Password: {temporary_password}\n\n"
        "Login: http://localhost:5000/login"
    )
    message = MIMEText(body)
    message["Subject"] = subject
    message["From"] = MAIL_DEFAULT_SENDER
    message["To"] = recipient_email
    try:
        with smtplib.SMTP(MAIL_SERVER, MAIL_PORT, timeout=10) as server:
            server.starttls()
            server.login(MAIL_USERNAME, MAIL_PASSWORD)
            server.sendmail(MAIL_DEFAULT_SENDER, recipient_email, message.as_string())
            print("DEBUG: Email sent successfully")
    except Exception as e:
        print(f"EMAIL ERROR: {e}")
        raise
def send_welcome_email(recipient_email, full_name, username, temporary_password):
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
        with smtplib.SMTP(MAIL_SERVER, MAIL_PORT) as server:
            server.starttls()
            server.login(EMAIL_ADDRESS, EMAIL_APP_PASSWORD)
            server.sendmail(EMAIL_ADDRESS, recipient_email, message.as_string())
    except Exception as e:  # noqa: BLE001  # Email send fallback error handling
        print("Failed to send welcome email:", e)


def ensure_user_columns():
    with get_db() as conn:
        columns = [row[1] for row in conn.execute("PRAGMA table_info(users)").fetchall()]
        if "full_name" not in columns:
            conn.execute("ALTER TABLE users ADD COLUMN full_name TEXT")
        if "email" not in columns:
            conn.execute("ALTER TABLE users ADD COLUMN email TEXT")
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

        admin_exists = conn.execute(
            "SELECT COUNT(*) FROM users WHERE username = ?",
            ("admin",),
        ).fetchone()[0]
        if admin_exists == 0:
            conn.execute(
                "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
                ("admin", generate_password_hash("admin123"), "admin"),
            )
            conn.commit()


init_db()


@login_manager.user_loader
def load_user(user_id):
    with get_db() as conn:
        row = conn.execute(
            "SELECT id, username, password_hash, role FROM users WHERE id = ?",
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
                            <p>Please sign in or create an account.</p>
                            <a class="btn btn-primary" href="{{ url_for('login') }}">Login</a>
                            <a class="btn btn-outline-secondary ms-2" href="{{ url_for('register') }}">Register</a>
                        {% endif %}
                    </div>
                </div>
            </div>
        </body>
        </html>
        """
    )


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        if not username or not password:
            flash("Username and password are required.", "danger")
            return redirect(url_for("register"))

        with get_db() as conn:
            existing = conn.execute(
                "SELECT id FROM users WHERE username = ?",
                (username,),
            ).fetchone()
            if existing:
                flash("Username already exists.", "warning")
                return redirect(url_for("register"))

            conn.execute(
                "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
                (username, generate_password_hash(password), "user"),
            )
            conn.commit()

        flash("Registration successful. Please login.", "success")
        return redirect(url_for("login"))

    return render_template_string(
        """
        <!doctype html>
        <html lang="en">
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <title>Register</title>
            <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
        </head>
        <body class="bg-light">
            <div class="container py-5">
                <div class="card shadow-sm mx-auto" style="max-width: 420px;">
                    <div class="card-body">
                        <h2 class="h4 mb-3">Register</h2>
                        <form method="post">
                            <div class="mb-3">
                                <label class="form-label">Username</label>
                                <input class="form-control" name="username" required>
                            </div>
                            <div class="mb-3">
                                <label class="form-label">Password</label>
                                <input class="form-control" type="password" name="password" required>
                            </div>
                            <button class="btn btn-primary w-100" type="submit">Register</button>
                        </form>
                        <p class="mt-3 mb-0"><a href="{{ url_for('login') }}">Back to login</a></p>
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
                "SELECT id, username, password_hash, role FROM users WHERE username = ?",
                (username,),
            ).fetchone()

        user = User.from_db(row)
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
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
                        <p class="mt-3 mb-0"><a href="{{ url_for('register') }}">Create an account</a></p>
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
    return render_template_string(
        """
        <!doctype html>
        <html lang="en">
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <title>Dashboard</title>
            <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
        </head>
        <body class="bg-light">
            <div class="container py-5">
                <div class="card shadow-sm">
                    <div class="card-body">
                        <h1 class="h3 mb-3">Dashboard</h1>
                        <p>Welcome, {{ current_user.username }}.</p>
                        {% if current_user.role == 'admin' %}
                            <a class="btn btn-warning" href="{{ url_for('admin') }}">Admin Panel</a>
                        {% endif %}
                        <a class="btn btn-outline-danger ms-2" href="{{ url_for('logout') }}">Logout</a>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """
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
                        "INSERT INTO users (username, password_hash, role, full_name, email) VALUES (?, ?, ?, ?, ?)",
                        (username, generate_password_hash(temp_password), "user", full_name, email),
                    )
                    conn.commit()
                    try:
                        send_welcome_email(email, full_name, username, temp_password)
                    except Exception as e:  # noqa: BLE001  # Email send fallback error handling
                        print("Failed to send welcome email:", e)
                    message = (
                        f"User created successfully. Temporary password: {temp_password}"
                    )

    return render_template_string(
        """
        <!doctype html>copy app.py app_backup.py
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
                        <h1 class="h3 mb-3">Create User</h1>
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
                            <a class="btn btn-outline-secondary ms-2" href="{{ url_for('admin') }}">Back to Admin</a>
                        </form>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """,
        message=message,
    )


@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(debug=True)
