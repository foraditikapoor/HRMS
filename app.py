import os

# Try to load .env using python-dotenv when available; otherwise fall back
# to a simple manual loader so credentials from a .env file still work.
try:
    from dotenv import load_dotenv

    load_dotenv(os.path.join(os.path.dirname(__file__), ".env"), override=True)
    print("DEBUG: python-dotenv loaded .env")
except Exception:  # noqa: BLE001  # Fallback manual env loader on import error
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
        except Exception as e:  # noqa: BLE001  # Fallback manual env loader on file error
            print("DEBUG: failed to load .env manually:", e)
    else:
        print(f"DEBUG: no .env found at {dotenv_path}")
import calendar  # noqa: I001
import hashlib
import json
import secrets
import smtplib
import sqlite3
import time
import traceback
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


def send_email_with_attachment(to_email, subject, html_content, attachment_bytes, filename, text_content=None):
    """Send an HTML email with a file attachment using Gmail SMTP configuration."""
    if not to_email:
        print("DEBUG SMTP: No recipient email provided.")
        return False, "No recipient email address provided."
    if not MAIL_USERNAME or not MAIL_PASSWORD:
        print("DEBUG SMTP: MAIL_USERNAME or MAIL_PASSWORD not configured.")
        return False, "SMTP email server configuration missing."

    try:
        msg = MIMEMultipart("mixed")
        msg["Subject"] = subject
        msg["From"] = MAIL_DEFAULT_SENDER or EMAIL_ADDRESS or MAIL_USERNAME
        msg["To"] = to_email

        if text_content:
            msg.attach(MIMEText(text_content, "plain"))
        else:
            import re
            plain_text = re.sub(r'<[^>]+>', '', html_content)
            msg.attach(MIMEText(plain_text, "plain"))

        msg.attach(MIMEText(html_content, "html"))

        if attachment_bytes and filename:
            part = MIMEApplication(attachment_bytes, Name=filename)
            part['Content-Disposition'] = f'attachment; filename="{filename}"'
            msg.attach(part)

        print(f"DEBUG SMTP: Sending email with attachment to {to_email} via {MAIL_SERVER}:{MAIL_PORT}")
        with smtplib.SMTP(MAIL_SERVER, MAIL_PORT, timeout=10) as server:
            if MAIL_USE_TLS:
                server.starttls()
            server.login(MAIL_USERNAME, MAIL_PASSWORD)
            server.send_message(msg)
        print(f"DEBUG SMTP: Email with attachment successfully sent to {to_email}")
        return True, "Email sent successfully."
    except Exception as e:  # noqa: BLE001
        print(f"ERROR SMTP: Failed to send email to {to_email}: {e}")
        traceback.print_exc()
        return False, str(e)


def amount_to_words(amount):
    """Convert numeric amount to words (Indian numbering system)."""
    try:
        num = int(round(amount))
        if num == 0:
            return "Zero Rupees Only"

        units = ["", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine", "Ten",
                 "Eleven", "Twelve", "Thirteen", "Fourteen", "Fifteen", "Sixteen", "Seventeen", "Eighteen", "Nineteen"]
        tens = ["", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy", "Eighty", "Ninety"]

        def convert_below_thousand(n):
            if n == 0:
                return ""
            elif n < 20:
                return units[n]
            elif n < 100:
                return tens[n // 10] + (" " + units[n % 10] if n % 10 != 0 else "")
            else:
                return units[n // 100] + " Hundred" + (" and " + convert_below_thousand(n % 100) if n % 100 != 0 else "")

        parts = []
        if num >= 10000000:
            crore = num // 10000000
            num %= 10000000
            parts.append(convert_below_thousand(crore) + " Crore")
        if num >= 100000:
            lakh = num // 100000
            num %= 100000
            parts.append(convert_below_thousand(lakh) + " Lakh")
        if num >= 1000:
            thousand = num // 1000
            num %= 1000
            parts.append(convert_below_thousand(thousand) + " Thousand")
        if num > 0:
            parts.append(convert_below_thousand(num))

        return " ".join(parts) + " Rupees Only"
    except Exception:
        return f"{amount:,.2f} Rupees Only"


def generate_payslip_pdf(payroll_data):
    """Generate professional PDF payslip using ReportLab from existing payroll dict."""
    import os
    import io
    import datetime
    from reportlab.lib.pagesizes import letter
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, Image as RLImage
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        'CompanyTitle',
        parent=styles['Heading1'],
        fontSize=20,
        leading=24,
        textColor=colors.HexColor('#1e293b'),
        fontName='Helvetica-Bold'
    )
    subtitle_style = ParagraphStyle(
        'CompanySubtitle',
        parent=styles['Normal'],
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#64748b'),
        fontName='Helvetica'
    )
    badge_style = ParagraphStyle(
        'PayslipBadge',
        parent=styles['Normal'],
        fontSize=14,
        leading=18,
        textColor=colors.HexColor('#4f46e5'),
        fontName='Helvetica-Bold',
        alignment=2
    )
    header_cell_style = ParagraphStyle(
        'HeaderCell',
        parent=styles['Normal'],
        fontSize=9,
        leading=11,
        textColor=colors.HexColor('#475569'),
        fontName='Helvetica-Bold'
    )
    body_cell_style = ParagraphStyle(
        'BodyCell',
        parent=styles['Normal'],
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#1e293b'),
        fontName='Helvetica'
    )
    bold_cell_style = ParagraphStyle(
        'BoldCell',
        parent=styles['Normal'],
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#0f172a'),
        fontName='Helvetica-Bold'
    )
    net_cell_style = ParagraphStyle(
        'NetCell',
        parent=styles['Normal'],
        fontSize=13,
        leading=16,
        textColor=colors.HexColor('#15803d'),
        fontName='Helvetica-Bold'
    )

    elements = []

    # Bizznex Logo Asset Integration
    logo_path = os.path.join(os.path.dirname(__file__), "static", "images", "bizznex-logo.png")
    logo_img = None
    if os.path.exists(logo_path):
        try:
            logo_img = RLImage(logo_path, width=38, height=38)
        except Exception:
            logo_img = None

    p_month = payroll_data.get('payroll_month', '')
    p_status = payroll_data.get('payroll_status', 'Finalized')
    pay_date = payroll_data.get('pay_date') or datetime.date.today().strftime("%d %b %Y")

    if logo_img:
        brand_cell = Table(
            [[logo_img, Paragraph("<b>BIZZNEX</b>", title_style)]],
            colWidths=[44, 290]
        )
        brand_cell.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('LEFTPADDING', (0,0), (-1,-1), 0),
            ('RIGHTPADDING', (0,0), (-1,-1), 0),
            ('TOPPADDING', (0,0), (-1,-1), 0),
            ('BOTTOMPADDING', (0,0), (-1,-1), 0),
        ]))
    else:
        brand_cell = Paragraph("<b>BIZZNEX</b>", title_style)

    header_data = [
        [
            brand_cell,
            Paragraph(f"<b>PAYSLIP</b><br/><font size=10 color='#64748b'>{p_month}</font>", badge_style)
        ],
        [
            Paragraph("Enterprise Salary & Compensation Statement", subtitle_style),
            Paragraph(f"<font size=9 color='#64748b'>Status: <b>{p_status}</b></font>", ParagraphStyle('StatusR', parent=styles['Normal'], alignment=2))
        ]
    ]
    t_header = Table(header_data, colWidths=[340, 200])
    t_header.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2),
    ]))
    elements.append(t_header)
    elements.append(Spacer(1, 10))
    elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#cbd5e1'), spaceBefore=2, spaceAfter=12))

    # Employee Summary Section
    emp_summary_data = [
        [
            Paragraph("<b>Employee Name:</b>", header_cell_style),
            Paragraph(str(payroll_data.get("name", "N/A")), body_cell_style),
            Paragraph("<b>Pay Period:</b>", header_cell_style),
            Paragraph(str(p_month), body_cell_style),
        ],
        [
            Paragraph("<b>Employee ID:</b>", header_cell_style),
            Paragraph(str(payroll_data.get("employee_code") or f"EMP-{payroll_data.get('emp_id', 0):04d}"), body_cell_style),
            Paragraph("<b>Pay Date:</b>", header_cell_style),
            Paragraph(str(pay_date), body_cell_style),
        ],
        [
            Paragraph("<b>Department:</b>", header_cell_style),
            Paragraph(str(payroll_data.get("department", "N/A")), body_cell_style),
            Paragraph("<b>Working Days:</b>", header_cell_style),
            Paragraph(f"{payroll_data.get('working_days', 0)} Days", body_cell_style),
        ],
        [
            Paragraph("<b>Per Day Salary:</b>", header_cell_style),
            Paragraph(f"INR {payroll_data.get('per_day_salary', 0.0):,.2f}", body_cell_style),
            Paragraph("<b>LOP / Unpaid Days:</b>", header_cell_style),
            Paragraph(f"{payroll_data.get('unpaid_leave_days', 0.0)} Days", body_cell_style),
        ]
    ]
    t_emp = Table(emp_summary_data, colWidths=[110, 160, 110, 160])
    t_emp.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f8fafc')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#e2e8f0')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#f1f5f9')),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
    ]))
    elements.append(t_emp)
    elements.append(Spacer(1, 16))

    # Salary Components Section
    base_sal = float(payroll_data.get("base_salary", 0.0))
    lop_ded = float(payroll_data.get("leave_deduction", 0.0))
    adj = float(payroll_data.get("adjustments", 0.0))
    final_sal = float(payroll_data.get("final_salary", 0.0))

    components_data = [
        [
            Paragraph("<b>EARNINGS</b>", ParagraphStyle('EHead', parent=header_cell_style, textColor=colors.HexColor('#1e40af'))),
            Paragraph("<b>AMOUNT (INR)</b>", ParagraphStyle('AHead', parent=header_cell_style, alignment=2, textColor=colors.HexColor('#1e40af'))),
            Paragraph("<b>DEDUCTIONS</b>", ParagraphStyle('DHead', parent=header_cell_style, textColor=colors.HexColor('#991b1b'))),
            Paragraph("<b>AMOUNT (INR)</b>", ParagraphStyle('ADHead', parent=header_cell_style, alignment=2, textColor=colors.HexColor('#991b1b'))),
        ],
        [
            Paragraph("Basic Salary", body_cell_style),
            Paragraph(f"{base_sal:,.2f}", ParagraphStyle('R1', parent=body_cell_style, alignment=2)),
            Paragraph("Loss of Pay (LOP) Deduction", body_cell_style),
            Paragraph(f"{lop_ded:,.2f}", ParagraphStyle('R2', parent=body_cell_style, alignment=2)),
        ],
        [
            Paragraph("Allowances / Bonus", body_cell_style),
            Paragraph("0.00", ParagraphStyle('R3', parent=body_cell_style, alignment=2)),
            Paragraph("Adjustments", body_cell_style),
            Paragraph(f"{adj:,.2f}", ParagraphStyle('R4', parent=body_cell_style, alignment=2)),
        ],
        [
            Paragraph("<b>Gross Earnings</b>", bold_cell_style),
            Paragraph(f"<b>{base_sal:,.2f}</b>", ParagraphStyle('R5', parent=bold_cell_style, alignment=2)),
            Paragraph("<b>Total Deductions</b>", bold_cell_style),
            Paragraph(f"<b>{lop_ded:,.2f}</b>", ParagraphStyle('R6', parent=bold_cell_style, alignment=2)),
        ]
    ]

    t_comp = Table(components_data, colWidths=[170, 100, 170, 100])
    t_comp.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (1,0), colors.HexColor('#eff6ff')),
        ('BACKGROUND', (2,0), (3,0), colors.HexColor('#fef2f2')),
        ('LINEBELOW', (0,0), (-1,0), 1, colors.HexColor('#cbd5e1')),
        ('LINEBELOW', (0,-1), (-1,-1), 1, colors.HexColor('#cbd5e1')),
        ('BACKGROUND', (0,-1), (-1,-1), colors.HexColor('#f8fafc')),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#e2e8f0')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#f1f5f9')),
    ]))
    elements.append(t_comp)
    elements.append(Spacer(1, 16))

    # Net Payable Banner
    words_str = amount_to_words(final_sal)
    net_data = [
        [
            Paragraph("<b>TOTAL NET PAYABLE</b>", ParagraphStyle('NetL', parent=bold_cell_style, fontSize=11)),
            Paragraph(f"<b>INR {final_sal:,.2f}</b>", net_cell_style)
        ],
        [
            Paragraph(f"<b>Amount in Words:</b> {words_str}", ParagraphStyle('Words', parent=body_cell_style, fontSize=9, textColor=colors.HexColor('#475569'))),
            Paragraph("", body_cell_style)
        ]
    ]
    t_net = Table(net_data, colWidths=[370, 170])
    t_net.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f0fdf4')),
        ('BOX', (0,0), (-1,-1), 1.5, colors.HexColor('#22c55e')),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ('LEFTPADDING', (0,0), (-1,-1), 10),
        ('RIGHTPADDING', (0,0), (-1,-1), 10),
    ]))
    elements.append(t_net)
    elements.append(Spacer(1, 24))

    # Footer note
    footer_text = Paragraph(
        "<i>Note: This is an official computer-generated payslip from Bizznex. No physical signature is required.</i>",
        ParagraphStyle('Foot', parent=styles['Normal'], fontSize=8, textColor=colors.HexColor('#94a3b8'), alignment=1)
    )
    elements.append(footer_text)

    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()


def send_email(to_email, subject, html_content, text_content=None):
    """Send an HTML email using SMTP configuration.

    Catches all exceptions and logs them without interrupting application flow.
    """
    if not to_email:
        print("DEBUG SMTP: No recipient email provided. Skipping email send.")
        return False
    if not MAIL_USERNAME or not MAIL_PASSWORD:
        print("DEBUG SMTP: MAIL_USERNAME or MAIL_PASSWORD not configured. Skipping email send.")
        return False

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = MAIL_DEFAULT_SENDER or EMAIL_ADDRESS or MAIL_USERNAME
        msg["To"] = to_email

        if text_content:
            msg.attach(MIMEText(text_content, "plain"))
        else:
            import re
            plain_text = re.sub(r'<[^>]+>', '', html_content)
            msg.attach(MIMEText(plain_text, "plain"))

        msg.attach(MIMEText(html_content, "html"))

        print(f"DEBUG SMTP: Sending email to {to_email} via {MAIL_SERVER}:{MAIL_PORT}")
        with smtplib.SMTP(MAIL_SERVER, MAIL_PORT, timeout=10) as server:
            if MAIL_USE_TLS:
                server.starttls()
            server.login(MAIL_USERNAME, MAIL_PASSWORD)
            server.send_message(msg)
        print(f"DEBUG SMTP: Email successfully sent to {to_email}")
        return True
    except Exception as e:  # noqa: BLE001
        print(f"ERROR SMTP: Failed to send email to {to_email}: {e}")
        traceback.print_exc()
        return False


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
        "Login here:\nhttps://hrmsapp.pythonanywhere.com/login\n\n"
        "Please change your password after logging in.\n"
    )
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = EMAIL_ADDRESS
    msg["To"] = recipient_email
    try:
        print(f"DEBUG SMTP: {MAIL_SERVER}:{MAIL_PORT}")
        with smtplib.SMTP(MAIL_SERVER, MAIL_PORT, timeout=10) as server:
            server.starttls()
            server.login(MAIL_USERNAME, MAIL_PASSWORD)
            server.send_message(msg)
        print("DEBUG: Welcome email sent successfully")
    except Exception:  # noqa: BLE001  # Email send fallback error handling
        traceback.print_exc()


def send_leave_submission_email_to_admin(req_details):
    """Send email notification to admin(s) when an employee submits a leave request."""
    try:
        with get_db() as conn:
            admins = conn.execute(
                "SELECT email FROM users WHERE role = 'admin' AND email IS NOT NULL AND email != ''"
            ).fetchall()

        admin_emails = list({a["email"].strip() for a in admins if a["email"] and a["email"].strip()})
        if not admin_emails and MAIL_USERNAME:
            admin_emails = [MAIL_USERNAME]

        if not admin_emails:
            print("DEBUG SMTP: No admin email found for leave submission notification.")
            return

        subject = f"New Leave Request - {req_details.get('employee_name', 'Employee')}"
        emp_name = req_details.get("employee_name", "N/A")
        emp_id = req_details.get("employee_id", "N/A")
        leave_type = req_details.get("leave_type", "N/A")
        start_date = req_details.get("start_date", "N/A")
        end_date = req_details.get("end_date", "N/A")
        total_days = req_details.get("total_days", "N/A")
        reason = req_details.get("reason", "N/A")
        submission_time = req_details.get("applied_date", "N/A")

        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
          <meta charset="utf-8">
          <style>
            body {{ font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background-color: #f8fafc; color: #1e293b; margin: 0; padding: 20px; }}
            .container {{ max-width: 600px; margin: 0 auto; background: #ffffff; border: 1px solid #e2e8f0; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); }}
            .header {{ background-color: #4f46e5; color: #ffffff; padding: 20px 24px; font-size: 18px; font-weight: 600; }}
            .content {{ padding: 24px; font-size: 14px; line-height: 1.6; }}
            .table-details {{ width: 100%; border-collapse: collapse; margin-top: 16px; margin-bottom: 16px; }}
            .table-details td {{ padding: 10px 12px; border-bottom: 1px solid #f1f5f9; }}
            .table-details td.label {{ font-weight: 600; color: #64748b; width: 35%; background-color: #f8fafc; }}
            .table-details td.value {{ color: #0f172a; font-weight: 500; }}
            .footer {{ background-color: #f8fafc; padding: 16px 24px; font-size: 12px; color: #64748b; text-align: center; border-top: 1px solid #e2e8f0; }}
          </style>
        </head>
        <body>
          <div class="container">
            <div class="header">📋 New Leave Request Submitted</div>
            <div class="content">
              <p>A new leave request has been submitted and is pending review:</p>
              <table class="table-details">
                <tr><td class="label">Employee Name</td><td class="value">{emp_name}</td></tr>
                <tr><td class="label">Employee ID</td><td class="value">{emp_id}</td></tr>
                <tr><td class="label">Leave Type</td><td class="value">{leave_type}</td></tr>
                <tr><td class="label">Start Date</td><td class="value">{start_date}</td></tr>
                <tr><td class="label">End Date</td><td class="value">{end_date}</td></tr>
                <tr><td class="label">Total Duration</td><td class="value">{total_days} day(s)</td></tr>
                <tr><td class="label">Reason</td><td class="value">{reason}</td></tr>
                <tr><td class="label">Submitted At</td><td class="value">{submission_time}</td></tr>
              </table>
              <p>Please log in to the HRMS portal to review and approve or reject this request.</p>
            </div>
            <div class="footer">HRMS Notification System &bull; Automated Email</div>
          </div>
        </body>
        </html>
        """

        for admin_email in admin_emails:
            send_email(admin_email, subject, html_body)
    except Exception as e:  # noqa: BLE001
        print(f"ERROR: Exception in send_leave_submission_email_to_admin: {e}")
        traceback.print_exc()


def send_leave_approval_email_to_employee(user_id, req_details, comments=""):
    """Send email notification to employee when leave is approved."""
    try:
        with get_db() as conn:
            user = conn.execute("SELECT email, username, full_name FROM users WHERE id = ?", (user_id,)).fetchone()
            emp = conn.execute("SELECT name FROM employees WHERE user_id = ?", (user_id,)).fetchone()

        if not user or not user["email"]:
            print(f"DEBUG SMTP: No email found for user_id={user_id}. Skipping approval email.")
            return

        recipient_email = user["email"].strip()

        # Database greeting logic:
        # If Full Name exists (users.full_name or employees.name), use "Dear <Full Name>,"
        # Else use "Dear <Username>,"
        full_name = (user["full_name"].strip() if user["full_name"] and user["full_name"].strip() else None)
        if not full_name and emp and emp["name"] and emp["name"].strip():
            full_name = emp["name"].strip()

        if full_name:
            greeting = f"Dear {full_name},"
        else:
            username = user["username"].strip() if user["username"] else "Employee"
            greeting = f"Dear {username},"

        subject = "Leave Request Approved"
        leave_type = req_details.get("leave_type", "Leave")
        start_date = req_details.get("start_date", "")
        end_date = req_details.get("end_date", "")
        approved_dates = f"{start_date} to {end_date}" if start_date and end_date else "N/A"
        comments_str = comments if comments else "None"

        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
          <meta charset="utf-8">
          <style>
            body {{ font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background-color: #f8fafc; color: #1e293b; margin: 0; padding: 20px; }}
            .container {{ max-width: 600px; margin: 0 auto; background: #ffffff; border: 1px solid #e2e8f0; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); }}
            .header {{ background-color: #10b981; color: #ffffff; padding: 20px 24px; font-size: 18px; font-weight: 600; }}
            .content {{ padding: 24px; font-size: 14px; line-height: 1.6; }}
            .table-details {{ width: 100%; border-collapse: collapse; margin-top: 16px; margin-bottom: 16px; }}
            .table-details td {{ padding: 10px 12px; border-bottom: 1px solid #f1f5f9; }}
            .table-details td.label {{ font-weight: 600; color: #64748b; width: 35%; background-color: #f8fafc; }}
            .table-details td.value {{ color: #0f172a; font-weight: 500; }}
            .footer {{ background-color: #f8fafc; padding: 16px 24px; font-size: 12px; color: #64748b; text-align: center; border-top: 1px solid #e2e8f0; }}
          </style>
        </head>
        <body>
          <div class="container">
            <div class="header">✅ Leave Request Approved</div>
            <div class="content">
              <p>{greeting}</p>
              <p>Your leave request has been <strong>APPROVED</strong> by the administration.</p>
              <table class="table-details">
                <tr><td class="label">Leave Type</td><td class="value">{leave_type}</td></tr>
                <tr><td class="label">Approved Dates</td><td class="value">{approved_dates}</td></tr>
                <tr><td class="label">Admin Comments</td><td class="value">{comments_str}</td></tr>
              </table>
              <p>Enjoy your leave!</p>
            </div>
            <div class="footer">HRMS Notification System &bull; Automated Email</div>
          </div>
        </body>
        </html>
        """

        send_email(recipient_email, subject, html_body)
    except Exception as e:  # noqa: BLE001
        print(f"ERROR: Exception in send_leave_approval_email_to_employee: {e}")
        traceback.print_exc()


def send_leave_rejection_email_to_employee(user_id, req_details, rejection_reason="", comments=""):
    """Send email notification to employee when leave is rejected."""
    try:
        with get_db() as conn:
            user = conn.execute("SELECT email, username, full_name FROM users WHERE id = ?", (user_id,)).fetchone()
            emp = conn.execute("SELECT name FROM employees WHERE user_id = ?", (user_id,)).fetchone()

        if not user or not user["email"]:
            print(f"DEBUG SMTP: No email found for user_id={user_id}. Skipping rejection email.")
            return

        recipient_email = user["email"].strip()

        # Database greeting logic:
        # If Full Name exists (users.full_name or employees.name), use "Dear <Full Name>,"
        # Else use "Dear <Username>,"
        full_name = (user["full_name"].strip() if user["full_name"] and user["full_name"].strip() else None)
        if not full_name and emp and emp["name"] and emp["name"].strip():
            full_name = emp["name"].strip()

        if full_name:
            greeting = f"Dear {full_name},"
        else:
            username = user["username"].strip() if user["username"] else "Employee"
            greeting = f"Dear {username},"

        subject = "Leave Request Rejected"
        leave_type = req_details.get("leave_type", "Leave")
        start_date = req_details.get("start_date", "")
        end_date = req_details.get("end_date", "")
        requested_dates = f"{start_date} to {end_date}" if start_date and end_date else "N/A"

        reason_display = rejection_reason if rejection_reason else "N/A"
        if comments:
            reason_display += f" ({comments})"

        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
          <meta charset="utf-8">
          <style>
            body {{ font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background-color: #f8fafc; color: #1e293b; margin: 0; padding: 20px; }}
            .container {{ max-width: 600px; margin: 0 auto; background: #ffffff; border: 1px solid #e2e8f0; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); }}
            .header {{ background-color: #ef4444; color: #ffffff; padding: 20px 24px; font-size: 18px; font-weight: 600; }}
            .content {{ padding: 24px; font-size: 14px; line-height: 1.6; }}
            .table-details {{ width: 100%; border-collapse: collapse; margin-top: 16px; margin-bottom: 16px; }}
            .table-details td {{ padding: 10px 12px; border-bottom: 1px solid #f1f5f9; }}
            .table-details td.label {{ font-weight: 600; color: #64748b; width: 35%; background-color: #f8fafc; }}
            .table-details td.value {{ color: #0f172a; font-weight: 500; }}
            .footer {{ background-color: #f8fafc; padding: 16px 24px; font-size: 12px; color: #64748b; text-align: center; border-top: 1px solid #e2e8f0; }}
          </style>
        </head>
        <body>
          <div class="container">
            <div class="header">❌ Leave Request Rejected</div>
            <div class="content">
              <p>{greeting}</p>
              <p>Your leave request has been <strong>REJECTED</strong> by the administration.</p>
              <table class="table-details">
                <tr><td class="label">Leave Type</td><td class="value">{leave_type}</td></tr>
                <tr><td class="label">Requested Dates</td><td class="value">{requested_dates}</td></tr>
                <tr><td class="label">Reason / Comments</td><td class="value">{reason_display}</td></tr>
              </table>
              <p>Please contact HR/Management if you have any questions.</p>
            </div>
            <div class="footer">HRMS Notification System &bull; Automated Email</div>
          </div>
        </body>
        </html>
        """

        send_email(recipient_email, subject, html_body)
    except Exception as e:  # noqa: BLE001
        print(f"ERROR: Exception in send_leave_rejection_email_to_employee: {e}")
        traceback.print_exc()


import datetime
import io
from zoneinfo import ZoneInfo

from flask import (
    Flask,
    Response,
    flash,
    jsonify,
    redirect,
    render_template_string,
    request,
    send_file,
    url_for,
)
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

try:
    IST = ZoneInfo("Asia/Kolkata")
except Exception:  # noqa: BLE001  # Fallback when tzdata database is absent
    IST = datetime.timezone(datetime.timedelta(hours=5, minutes=30))

# Central Attendance Policy Configuration (IST)
LATE_PUNCH_IN_TIME = datetime.time(10, 15)       # Punch-in strictly after 10:15 AM IST is LATE
HALF_DAY_PUNCH_OUT_TIME = datetime.time(15, 0)   # Punch-out strictly before 3:00 PM IST is HALF DAY

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-key")
app.config["DATABASE_PATH"] = os.path.join(app.instance_path, "users.db")

# Update this single mapping when task categories or their predefined tasks change.
TASK_CATEGORIES = {
    "SEO": [
        "Prepare Previous Month's SEO Report",
        "Analyze GA4 & GSC Data",
        "Review Keyword Rankings",
        "Share Monthly Report with Client",
        "Finalize Monthly Action Plan",
        "Perform Technical SEO Audit",
        "Check Broken Links",
        "Check 404 Errors",
        "Check Indexing Issues",
        "Check Crawled but Not Indexed Pages",
        "Sitemap Check",
        "Generate Backlinks",
        "Perform Competitor Analysis",
        "Continue Blog Content Creation & Upload",
    ],
    "Social Media Marketing": [
        "Prepare Monthly Performance Report",
        "Prepare Next Month Social Media Content",
        "Collect Client Approvals",
        "Story Posting",
        "Group Sharing",
        "Social Media Posting",
        "Content Pointers",
        "Client Reminders",
    ],
    "Google Ads": [
        "Review Monthly Campaign Performance",
        "Share Daily Reports",
        "Share Weekly Reports",
        "Optimize Campaigns",
        "Adjust Bids",
        "Review Keywords",
        "Update Negative Keywords",
        "Improve Ad Copy",
        "Verify Conversion Tracking",
    ],
    "Meta Ads": ["Optimize Meta Ads Campaigns", "Meta Ads Setup"],
    "Website Development": [
        "Domain Name Research",
        "Domain Registration",
        "Website Planning",
        "Site Structure Setup",
        "Homepage Design",
        "Content Writing",
        "Website Testing",
        "Website Launch",
    ],
    "Other (Custom)": [],
}

# Uploads folder for employee documents
app.config["UPLOAD_FOLDER"] = os.path.join(app.instance_path, "uploads")
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

# Gmail SMTP configuration
MAIL_SERVER = "smtp.gmail.com"
MAIL_PORT = 587
MAIL_USE_TLS = True
# Enter your Gmail address and App Password here (no env vars)
MAIL_USERNAME = os.getenv("MAIL_USERNAME") or ""
MAIL_PASSWORD = os.getenv("MAIL_PASSWORD") or ""
MAIL_DEFAULT_SENDER = MAIL_USERNAME

# Mirror variables required by the email function
EMAIL_ADDRESS = MAIL_USERNAME
EMAIL_APP_PASSWORD = MAIL_PASSWORD

# Temporary debug prints (masked): show whether env vars were loaded
import logging

logging.basicConfig(level=logging.INFO)

app.logger.info(f"MAIL_USERNAME loaded: {'yes' if MAIL_USERNAME else 'no'}")
app.logger.info(f"MAIL_PASSWORD loaded: {'yes' if MAIL_PASSWORD else 'no'}")

os.makedirs(app.instance_path, exist_ok=True)

login_manager = LoginManager(app)
login_manager.login_view = "login"  # pyright: ignore[reportAttributeAccessIssue]


class User(UserMixin):
    def __init__(
        self, user_id, username, password_hash, role="user", force_password_change=False, profile_pic=None, last_active_at=None
    ):
        self.id = user_id
        self.username = username
        self.password_hash = password_hash
        self.role = (role or "user").lower()
        self.force_password_change = bool(force_password_change)
        self.profile_pic = profile_pic
        self.last_active_at = last_active_at

    @staticmethod
    def from_db(row):
        if row is None:
            return None
        try:
            r = dict(row)
            return User(
                r.get("id"),
                r.get("username"),
                r.get("password_hash"),
                r.get("role", "user"),
                r.get("force_password_change", False),
                r.get("profile_pic"),
                r.get("last_active_at"),
            )
        except Exception:  # noqa: BLE001
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
    if user_row and user_row["full_name"]:
        names.add(user_row["full_name"])
    emp_row = conn.execute(
        "SELECT name FROM employees WHERE user_id = ?",
        (user.id,),
    ).fetchone()
    if emp_row and emp_row["name"]:
        names.add(emp_row["name"])
    return list(names)


def resolve_date_range(date_filter, start_date_input="", end_date_input=""):
    """Calculate start and end ISO dates for date range presets."""
    today = datetime.date.today()  # noqa: DTZ011
    df = (date_filter or "all").strip().lower()
    start_str = (start_date_input or "").strip()
    end_str = (end_date_input or "").strip()

    if df == "today":
        return today.isoformat(), today.isoformat()
    if df == "last_7":
        return (today - datetime.timedelta(days=6)).isoformat(), today.isoformat()
    if df == "last_30":
        return (today - datetime.timedelta(days=29)).isoformat(), today.isoformat()
    if df == "this_month":
        start_of_month = today.replace(day=1).isoformat()
        return start_of_month, today.isoformat()
    if df == "custom" or start_str or end_str:
        return start_str or None, end_str or None
    return None, None


# Helper to save uploaded files and return stored path (relative to instance)
def save_uploaded_file(file_storage):
    if not file_storage:
        return None
    filename = secure_filename(file_storage.filename)
    if not filename:
        return None
    dest_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    # If filename exists, append a short suffix to avoid overwrite
    base, ext = os.path.splitext(filename)
    counter = 1
    while os.path.exists(dest_path):
        filename = f"{base}_{counter}{ext}"
        dest_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        counter += 1
    file_storage.save(dest_path)
    # return path relative to app root (instance path)
    return dest_path



def ensure_user_columns():
    with get_db() as conn:
        columns = [
            row[1] for row in conn.execute("PRAGMA table_info(users)").fetchall()
        ]
        if "full_name" not in columns:
            conn.execute("ALTER TABLE users ADD COLUMN full_name TEXT")
        if "email" not in columns:
            conn.execute("ALTER TABLE users ADD COLUMN email TEXT")
        if "force_password_change" not in columns:
            # 0 = false, 1 = true
            conn.execute(
                "ALTER TABLE users ADD COLUMN force_password_change INTEGER DEFAULT 0"
            )
        if "profile_pic" not in columns:
            conn.execute("ALTER TABLE users ADD COLUMN profile_pic TEXT")
        if "last_active_at" not in columns:
            conn.execute("ALTER TABLE users ADD COLUMN last_active_at TEXT")
        conn.commit()


def ensure_password_reset_tokens_table():
    with get_db() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS password_reset_tokens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                token_hash TEXT NOT NULL,
                expires_at INTEGER NOT NULL,
                used_at INTEGER,
                created_at INTEGER NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_reset_token_hash ON password_reset_tokens(token_hash)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_reset_token_user ON password_reset_tokens(user_id)"
        )
        conn.commit()


def is_user_online(last_active_at_str):
    if not last_active_at_str:
        return False
    try:
        dt = datetime.datetime.strptime(last_active_at_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=IST)
        now = datetime.datetime.now(tz=IST)
        return (now - dt).total_seconds() < 300
    except (ValueError, TypeError):
        return False


UPLOAD_PROFILE_PICS_DIR = os.path.join(app.root_path, "static", "uploads", "profile_pics")
os.makedirs(UPLOAD_PROFILE_PICS_DIR, exist_ok=True)
ALLOWED_IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}
MAX_IMAGE_SIZE = 2 * 1024 * 1024  # 2 MB


def process_and_save_profile_pic(file_storage, user_id):
    if not file_storage or not file_storage.filename:
        return None, "No file selected."

    ext = file_storage.filename.rsplit(".", 1)[-1].lower() if "." in file_storage.filename else ""
    if ext not in ALLOWED_IMAGE_EXTENSIONS:
        return None, "Invalid file format. Please upload a JPG, JPEG, PNG, or WEBP image."

    file_storage.seek(0, os.SEEK_END)
    file_length = file_storage.tell()
    file_storage.seek(0)

    if file_length > MAX_IMAGE_SIZE:
        return None, "File size exceeds maximum limit of 2 MB."

    unique_name = f"user_{user_id}_{int(time.time())}_{secrets.token_hex(4)}.{ext}"
    dest_path = os.path.join(UPLOAD_PROFILE_PICS_DIR, unique_name)

    try:
        from PIL import Image
        img = Image.open(file_storage)
        if ext in ("jpg", "jpeg"):
            img = img.convert("RGB")
        width, height = img.size
        if width != 256 or height != 256:
            resample_mode = getattr(getattr(Image, "Resampling", Image), "LANCZOS", 1)
            img = img.resize((256, 256), resample_mode)
        img.save(dest_path)
    except Exception as e:  # noqa: BLE001
        app.logger.warning("Failed to process profile picture with PIL: %s", e)
        file_storage.seek(0)
        file_storage.save(dest_path)

    rel_path = f"uploads/profile_pics/{unique_name}"
    return rel_path, None


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


def ensure_holidays_table():
    """Create holidays table if it does not exist and populate default company holidays."""
    with get_db() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS holidays (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                date TEXT UNIQUE NOT NULL,
                description TEXT,
                holiday_type TEXT DEFAULT 'Public Holiday',
                is_paid INTEGER DEFAULT 1
            )
            """
        )
        conn.commit()

        cols = [r[1] for r in conn.execute("PRAGMA table_info(holidays)").fetchall()]
        if "holiday_type" not in cols:
            conn.execute("ALTER TABLE holidays ADD COLUMN holiday_type TEXT DEFAULT 'Public Holiday'")
        if "is_paid" not in cols:
            conn.execute("ALTER TABLE holidays ADD COLUMN is_paid INTEGER DEFAULT 1")
        conn.commit()

        # Seed default Indian company holidays if empty
        row_count = conn.execute("SELECT COUNT(*) FROM holidays").fetchone()[0]
        if row_count == 0:
            current_yr = datetime.datetime.now(tz=IST).year
            default_holidays = [
                ("New Year's Day", f"{current_yr}-01-01", "Official Holiday", "Public Holiday", 1),
                ("Republic Day", f"{current_yr}-01-26", "National Holiday", "Public Holiday", 1),
                ("Labor Day", f"{current_yr}-05-01", "Official Holiday", "Public Holiday", 1),
                ("Independence Day", f"{current_yr}-08-15", "National Holiday", "Public Holiday", 1),
                ("Gandhi Jayanti", f"{current_yr}-10-02", "National Holiday", "Public Holiday", 1),
                ("Diwali", f"{current_yr}-11-01", "Festival Holiday", "Company Holiday", 1),
                ("Christmas Day", f"{current_yr}-12-25", "Official Holiday", "Public Holiday", 1),
            ]
            conn.executemany(
                "INSERT OR IGNORE INTO holidays (title, date, description, holiday_type, is_paid) VALUES (?, ?, ?, ?, ?)",
                default_holidays,
            )
            conn.commit()


def ensure_employee_table():
    """Create employee table if it does not exist.

    Fields: user_id, name, address, education, experience, contact_number, emergency_contact,
    department (comma-separated), salary, pan_path, aadhaar_path, other_docs_path
    """
    with get_db() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS employees (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                name TEXT NOT NULL,
                address TEXT,
                education TEXT,
                experience TEXT,
                contact_number TEXT,
                emergency_contact TEXT,
                department TEXT,
                salary REAL,
                pan_path TEXT,
                aadhaar_path TEXT,
                other_docs_path TEXT
            )
            """
        )
        columns = {
            row[1] for row in conn.execute("PRAGMA table_info(employees)").fetchall()
        }
        if "user_id" not in columns:
            conn.execute("ALTER TABLE employees ADD COLUMN user_id INTEGER")
        if "contact_number" not in columns:
            conn.execute("ALTER TABLE employees ADD COLUMN contact_number TEXT")
        if "paid_leave_entitlement" not in columns:
            conn.execute("ALTER TABLE employees ADD COLUMN paid_leave_entitlement REAL DEFAULT 12.0")
        if "date_of_joining" not in columns:
            conn.execute("ALTER TABLE employees ADD COLUMN date_of_joining TEXT")
        if "date_of_birth" not in columns:
            conn.execute("ALTER TABLE employees ADD COLUMN date_of_birth TEXT")
        if "employee_code" not in columns:
            conn.execute("ALTER TABLE employees ADD COLUMN employee_code TEXT")
        # Existing employee records have no linked user and remain untouched.
        conn.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_employees_user_id "
            "ON employees(user_id) WHERE user_id IS NOT NULL"
        )
        conn.commit()


def validate_employee_code(conn, code, current_emp_id=None):
    """Validates employee code for emptiness and uniqueness."""
    code = (code or "").strip()
    if not code:
        return False, "Employee ID cannot be empty."

    if current_emp_id:
        existing = conn.execute(
            "SELECT id FROM employees WHERE LOWER(employee_code) = LOWER(?) AND id != ?",
            (code, current_emp_id),
        ).fetchone()
    else:
        existing = conn.execute(
            "SELECT id FROM employees WHERE LOWER(employee_code) = LOWER(?)",
            (code,),
        ).fetchone()

    if existing:
        return False, f"Employee ID '{code}' is already assigned to another employee."

    return True, None


def calculate_permanent_date(joining_date_str):
    """Calculates the exact 6-month calendar permanent date for a given joining date (YYYY-MM-DD)."""
    if not joining_date_str:
        return None
    try:
        parts = [int(p) for p in joining_date_str.strip().split("-")]
        if len(parts) != 3:
            return None
        year, month, day = parts
        target_month = month + 6
        target_year = year + (target_month - 1) // 12
        target_month = (target_month - 1) % 12 + 1

        max_day = calendar.monthrange(target_year, target_month)[1]
        target_day = min(day, max_day)

        return datetime.date(target_year, target_month, target_day).isoformat()
    except (ValueError, TypeError, AttributeError):
        return None


def compute_employee_role(date_of_joining_str, current_role=None):
    """Computes whether an employee is 'temporary employee' or 'permanent employee' based on date_of_joining.

    Admin, HR, and Permanent Employee roles are preserved.
    """
    norm_role = (current_role or "").lower().strip()
    if norm_role in ("admin", "hr", "permanent employee", "permanent"):
        return norm_role if norm_role != "permanent" else "permanent employee"

    if not date_of_joining_str:
        return "temporary employee"

    perm_date_str = calculate_permanent_date(date_of_joining_str)
    if not perm_date_str:
        return "temporary employee"

    today_str = datetime.datetime.now(IST).date().isoformat()
    if today_str >= perm_date_str:
        return "permanent employee"
    else:
        return "temporary employee"


def get_birthday_date_for_year(dob_str, year):
    """Returns the birthday date string (YYYY-MM-DD) in the given year for a DOB (YYYY-MM-DD).

    Handles Feb 29 birthdays in non-leap years deterministically by placing them on Feb 28.
    """
    if not dob_str:
        return None
    try:
        parts = [int(p) for p in dob_str.strip().split("-")]
        if len(parts) != 3:
            return None
        _, month, day = parts
        try:
            return datetime.date(year, month, day).isoformat()
        except ValueError:
            if month == 2 and day == 29:
                return datetime.date(year, 2, 28).isoformat()
            return None
    except (ValueError, TypeError, AttributeError):
        return None


def ensure_birthday_paid_leaves(conn=None):
    """Automatically generates ONE Birthday Paid Leave entry for each employee who has a Date of Birth for the current year.

    Idempotent: Checked against existing leave_requests to prevent duplicate creation.
    """
    close_conn = False
    if conn is None:
        conn = get_db()
        close_conn = True

    try:
        current_year = datetime.datetime.now(IST).year
        employees = conn.execute(
            "SELECT e.id, e.user_id, e.name, e.date_of_birth FROM employees e WHERE e.user_id IS NOT NULL AND e.date_of_birth IS NOT NULL AND e.date_of_birth != ''"
        ).fetchall()

        for emp in employees:
            user_id = emp["user_id"]
            name = emp["name"] or "Employee"
            dob_str = emp["date_of_birth"]

            bday_date_str = get_birthday_date_for_year(dob_str, current_year)
            if not bday_date_str:
                continue

            existing = conn.execute(
                """
                SELECT id FROM leave_requests
                WHERE user_id = ?
                  AND LOWER(leave_type) = 'birthday leave'
                  AND strftime('%Y', start_date) = ?
                """,
                (user_id, str(current_year)),
            ).fetchone()

            if not existing:
                conn.execute(
                    """
                    INSERT INTO leave_requests (
                        user_id, employee_name, leave_type, start_date, end_date,
                        total_days, reason, status, applied_date, approved_by, approval_date
                    )
                    VALUES (?, ?, 'Birthday Leave', ?, ?, 1.0, 'Birthday Paid Leave', 'Approved', ?, 'System Policy', ?)
                    """,
                    (
                        user_id,
                        name,
                        bday_date_str,
                        bday_date_str,
                        bday_date_str,
                        bday_date_str,
                    ),
                )
        conn.commit()
    finally:
        if close_conn:
            conn.close()


def sync_all_employee_roles(conn=None):
    """Synchronizes user roles for all employees in the database based on Date of Joining and 6-month threshold."""
    close_conn = False
    if conn is None:
        conn = get_db()
        close_conn = True

    try:
        conn.execute(
            "UPDATE users SET role = 'temporary employee' WHERE LOWER(role) IN ('user', 'employee')"
        )

        employees = conn.execute(
            "SELECT e.id, e.user_id, e.date_of_joining, u.role FROM employees e JOIN users u ON e.user_id = u.id"
        ).fetchall()

        for emp in employees:
            user_id = emp["user_id"]
            current_role = emp["role"]
            doj = emp["date_of_joining"]
            new_role = compute_employee_role(doj, current_role)
            if new_role != current_role:
                conn.execute(
                    "UPDATE users SET role = ? WHERE id = ?",
                    (new_role, user_id),
                )
        conn.commit()

        ensure_birthday_paid_leaves(conn)
    finally:
        if close_conn:
            conn.close()


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

        columns = {
            row[1] for row in conn.execute("PRAGMA table_info(projects)").fetchall()
        }
        required_columns = [
            "client_id",
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
                column_type = "INTEGER" if column_name == "client_id" else "TEXT"
                conn.execute(
                    f"ALTER TABLE projects ADD COLUMN {column_name} {column_type}"
                )
        conn.commit()


def ensure_clients_table():
    """Create the client source-of-truth table without replacing existing data."""
    with get_db() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS clients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                address TEXT,
                city TEXT,
                services TEXT,
                gst_number TEXT,
                contact_number TEXT,
                email TEXT,
                website TEXT
            )
        """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_projects_client_id ON projects(client_id)"
        )

        # Safely preserve legacy project client details by converting them to clients.
        legacy_projects = conn.execute(
            """
            SELECT id, client_name, client_address, services, client_gst_number,
                   whatsapp_number, client_email, client_website
            FROM projects WHERE client_id IS NULL AND trim(coalesce(client_name, '')) != ''
        """
        ).fetchall()
        for project in legacy_projects:
            client = conn.execute(
                "SELECT id FROM clients WHERE name = ? ORDER BY id LIMIT 1",
                (project["client_name"],),
            ).fetchone()
            if client is None:
                cursor = conn.execute(
                    """
                    INSERT INTO clients (name, address, services, gst_number, contact_number, email, website)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        project["client_name"],
                        project["client_address"],
                        project["services"],
                        project["client_gst_number"],
                        project["whatsapp_number"],
                        project["client_email"],
                        project["client_website"],
                    ),
                )
                client_id = cursor.lastrowid
            else:
                client_id = client["id"]
            conn.execute(
                "UPDATE projects SET client_id = ? WHERE id = ?",
                (client_id, project["id"]),
            )
        conn.commit()


def ensure_tasks_table():
    """Create the tasks table and add new task fields without removing task data."""
    with get_db() as conn:
        existing_columns = [
            row[1] for row in conn.execute("PRAGMA table_info(tasks)").fetchall()
        ]
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
                    progress INTEGER DEFAULT 0,
                    completed_by TEXT,
                    completion_date TEXT
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
            "completion_date",
        ]
        for column_name in required_columns:
            if column_name not in existing_columns:
                conn.execute(f"ALTER TABLE tasks ADD COLUMN {column_name} TEXT")
        if "task_category" not in existing_columns:
            conn.execute("ALTER TABLE tasks ADD COLUMN task_category TEXT")
        if "estimated_hours" not in existing_columns:
            conn.execute("ALTER TABLE tasks ADD COLUMN estimated_hours REAL")
        if "progress" not in existing_columns:
            conn.execute("ALTER TABLE tasks ADD COLUMN progress INTEGER DEFAULT 0")
        
        # Migrate existing completed tasks to 100% progress
        conn.execute("UPDATE tasks SET progress = 100 WHERE status = 'Completed' AND (progress IS NULL OR progress = 0)")
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

        columns = {
            row[1] for row in conn.execute("PRAGMA table_info(time_logs)").fetchall()
        }
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


def ensure_leave_requests_table():
    """Create leave_requests table if it does not exist."""
    with get_db() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS leave_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                employee_name TEXT NOT NULL,
                leave_type TEXT NOT NULL,
                start_date TEXT NOT NULL,
                end_date TEXT NOT NULL,
                total_days REAL NOT NULL,
                reason TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'Pending',
                applied_date TEXT NOT NULL,
                approved_by TEXT,
                approval_date TEXT,
                comments TEXT,
                rejection_reason TEXT
            )
            """
        )
        conn.commit()


def get_user_paid_leave_balance(conn, user_id):
    """Calculates paid leave entitlement, approved paid leave used, and remaining balance for a user.

    Balance = Entitlement - Approved Paid Leave Used.
    Only Approved paid leave requests count as used.
    Pending, Rejected, and Cancelled requests do not reduce balance.
    """
    close_conn = False
    if conn is None:
        conn = get_db()
        close_conn = True

    try:
        emp = conn.execute(
            "SELECT paid_leave_entitlement FROM employees WHERE user_id = ?",
            (user_id,),
        ).fetchone()

        if emp and emp["paid_leave_entitlement"] is not None:
            entitlement = float(emp["paid_leave_entitlement"])
        else:
            entitlement = 12.0

        row = conn.execute(
            """
            SELECT COALESCE(SUM(total_days), 0.0) AS used_days
            FROM leave_requests
            WHERE user_id = ?
              AND status = 'Approved'
              AND LOWER(leave_type) NOT IN ('unpaid leave', 'birthday leave')
            """,
            (user_id,),
        ).fetchone()

        used = float(row["used_days"]) if row else 0.0
        remaining = max(0.0, round(entitlement - used, 1))

        return {
            "entitlement": entitlement,
            "used": used,
            "remaining": remaining,
        }
    finally:
        if close_conn:
            conn.close()


def set_user_paid_leave_entitlement(conn, target_user_id, entitlement_value):
    """Sets or updates the paid leave entitlement for a user within a transaction."""
    close_conn = False
    if conn is None:
        conn = get_db()
        close_conn = True

    try:
        entitlement_val = max(0.0, float(entitlement_value))
        emp = conn.execute(
            "SELECT id FROM employees WHERE user_id = ?", (target_user_id,)
        ).fetchone()

        if emp:
            conn.execute(
                "UPDATE employees SET paid_leave_entitlement = ? WHERE user_id = ?",
                (entitlement_val, target_user_id),
            )
        else:
            user = conn.execute(
                "SELECT username, full_name FROM users WHERE id = ?", (target_user_id,)
            ).fetchone()
            name = (user["full_name"] if user and user["full_name"] else user["username"]) if user else "Employee"
            conn.execute(
                "INSERT INTO employees (user_id, name, paid_leave_entitlement) VALUES (?, ?, ?)",
                (target_user_id, name, entitlement_val),
            )
        conn.commit()
    finally:
        if close_conn:
            conn.close()



def ensure_performance_reviews_table():
    """Create performance_reviews table if it does not exist."""
    with get_db() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS performance_reviews (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_user_id INTEGER NOT NULL,
                employee_name TEXT NOT NULL,
                reviewer_username TEXT NOT NULL,
                review_period TEXT NOT NULL,
                overall_rating REAL NOT NULL,
                technical_skills_score REAL DEFAULT 0,
                communication_score REAL DEFAULT 0,
                productivity_score REAL DEFAULT 0,
                teamwork_score REAL DEFAULT 0,
                strengths TEXT,
                areas_for_improvement TEXT,
                comments TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (employee_user_id) REFERENCES users (id)
            )
            """
        )
        conn.commit()


def ensure_notifications_table():
    """Create notifications table if it does not exist.
    Notifications are linked to login users (users.id), NOT employee records.
    """
    with get_db() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                message TEXT NOT NULL,
                link TEXT,
                is_read INTEGER DEFAULT 0,
                created_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            )
            """
        )
        conn.commit()


def create_notification(user_id, title, message, link=None):
    """Helper to push an in-app notification to a specific user (by user_id)."""
    try:
        created_at = datetime.datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S")
        with get_db() as conn:
            conn.execute(
                """
                INSERT INTO notifications (user_id, title, message, link, is_read, created_at)
                VALUES (?, ?, ?, ?, 0, ?)
                """,
                (user_id, title, message, link, created_at),
            )
            conn.commit()
    except Exception as e:  # noqa: BLE001  # Catch notification error
        app.logger.error(f"Error creating notification: {e}")


def notify_admins(title, message, link=None):
    """Helper to push an in-app notification to all admin and manager users."""
    try:
        with get_db() as conn:
            admin_rows = conn.execute(
                "SELECT id FROM users WHERE role IN ('admin', 'manager')"
            ).fetchall()
            admin_ids = [r["id"] for r in admin_rows]
        for aid in admin_ids:
            create_notification(aid, title, message, link)
    except Exception as e:  # noqa: BLE001  # Catch notification error
        app.logger.error(f"Error notifying admins: {e}")


def notify_user_by_name_or_username(identifier, title, message, link=None):
    """Centralized helper: maps a username, full_name, or employee name (including comma-separated lists)
    to underlying login user_id records and pushes notifications consistently.
    """
    if not identifier:
        return
    try:
        raw_list = [n.strip() for n in str(identifier).split(",") if n.strip()]
        for name in raw_list:
            with get_db() as conn:
                # 1. Match users table username or full_name
                user = conn.execute(
                    "SELECT id FROM users WHERE username = ? OR full_name = ? ORDER BY id LIMIT 1",
                    (name, name),
                ).fetchone()
                if user and user["id"]:
                    create_notification(user["id"], title, message, link)
                    continue

                # 2. Match employees table name -> user_id
                emp = conn.execute(
                    "SELECT user_id FROM employees WHERE name = ? AND user_id IS NOT NULL ORDER BY id LIMIT 1",
                    (name,),
                ).fetchone()
                if emp and emp["user_id"]:
                    create_notification(emp["user_id"], title, message, link)
    except Exception as e:  # noqa: BLE001  # Catch notification error
        app.logger.error(
            f"Error in notify_user_by_name_or_username for '{identifier}': {e}"
        )


def ensure_settings_tables():
    with get_db() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS company_settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_name TEXT DEFAULT 'HRMS Enterprise Solutions',
                company_email TEXT DEFAULT 'contact@hrms.com',
                company_address TEXT DEFAULT '123 Business Park, Tech Zone, India',
                currency TEXT DEFAULT 'INR (₹)',
                working_hours TEXT DEFAULT '09:00 - 18:00 (Mon-Fri)',
                gst_number TEXT DEFAULT '27AAAAA0000A1Z5'
            )
        """
        )
        row = conn.execute("SELECT COUNT(*) FROM company_settings").fetchone()[0]
        if row == 0:
            conn.execute(
                """
                INSERT INTO company_settings (company_name, company_email, company_address, currency, working_hours, gst_number)
                VALUES ('HRMS Enterprise Solutions', 'contact@hrms.com', '123 Business Park, Tech Zone, India', 'INR (₹)', '09:00 - 18:00 (Mon-Fri)', '27AAAAA0000A1Z5')
            """
            )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS user_preferences (
                user_id INTEGER PRIMARY KEY,
                theme TEXT DEFAULT 'light',
                sidebar_style TEXT DEFAULT 'default',
                email_notifications INTEGER DEFAULT 1,
                in_app_notifications INTEGER DEFAULT 1,
                dashboard_reset_at TEXT,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            )
        """
        )
        cols = [col["name"] for col in conn.execute("PRAGMA table_info(user_preferences)").fetchall()]
        if "dashboard_reset_at" not in cols:
            conn.execute("ALTER TABLE user_preferences ADD COLUMN dashboard_reset_at TEXT")
        conn.commit()


def ensure_payroll_table():
    """Create payroll_records table if it does not exist to store finalized payroll history."""
    with get_db() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS payroll_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_id INTEGER NOT NULL,
                user_id INTEGER,
                month_year TEXT NOT NULL,
                base_salary REAL NOT NULL,
                working_days INTEGER NOT NULL,
                present_days INTEGER NOT NULL,
                attendance_pct REAL NOT NULL,
                approved_leave_days REAL NOT NULL,
                unpaid_leave_days REAL NOT NULL,
                performance_score REAL DEFAULT 0.0,
                leave_deduction REAL NOT NULL,
                adjustments REAL DEFAULT 0.0,
                final_salary REAL NOT NULL,
                status TEXT DEFAULT 'Calculated',
                salary_breakdown TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (employee_id) REFERENCES employees (id) ON DELETE CASCADE,
                UNIQUE(employee_id, month_year)
            )
            """
        )
        conn.commit()


@app.template_filter("inr")
def format_inr(amount):
    """Format numeric salary/currency amounts into Indian Rupee (INR / ₹) standard format."""
    if amount is None or amount == "":
        return "₹0.00"
    try:
        val = float(amount)
        s, *decimal = f"{val:.2f}".split(".")
        dec = f".{decimal[0]}" if decimal else ""
        if len(s) <= 3:
            return f"₹{s}{dec}"
        last_three = s[-3:]
        other_digits = s[:-3]
        res = ""
        while len(other_digits) > 2:
            res = "," + other_digits[-2:] + res
            other_digits = other_digits[:-2]
        if other_digits:
            res = other_digits + res
        return f"₹{res},{last_three}{dec}"
    except Exception:  # noqa: BLE001  # Formatting fallback on any error
        return f"₹{amount}"


@app.template_filter("format_timestamp")
def format_attendance_timestamp(val):
    """Format a datetime object or ISO 8601 string timestamp into 'DD Mon YYYY, hh:mm AM/PM'.
    Returns '-' for None, empty, or invalid timestamp values.
    """
    if not val:
        return "-"
    try:
        if isinstance(val, datetime.datetime):
            dt = val
        elif isinstance(val, datetime.date):
            dt = datetime.datetime.combine(val, datetime.time.min)
        elif isinstance(val, str):
            val_str = val.strip()
            if not val_str:
                return "-"
            dt = datetime.datetime.fromisoformat(val_str)
        else:
            return "-"

        if dt.tzinfo:
            dt = dt.astimezone(IST)

        return dt.strftime("%d %b %Y, %I:%M %p")
    except Exception:  # noqa: BLE001  # Safe fallback for invalid timestamp strings or parsing errors
        return "-"


@app.template_filter("month_name_filter")
def month_name_filter(month_num):
    """Format month integer (1-12) to month name string."""
    try:
        m = int(month_num)
        return datetime.date(2000, m, 1).strftime("%B")
    except Exception:  # noqa: BLE001
        return str(month_num)


def calculate_employee_performance(conn, user_id):
    """Calculate an Employee Performance Score (0-100%) automatically using existing HRMS data.

    Weights:
    - Attendance: 40%
    - Task Completion: 40%
    - Leave Behaviour: 10%
    - Overdue Tasks: 10%
    """
    if not user_id:
        now = datetime.datetime.now(tz=IST)
        return {
            "user_id": None,
            "performance_score": 0.0,
            "performance_score_int": 0,
            "performance_label": "Needs Improvement",
            "badge_class": "bg-danger text-white",
            "bar_class": "bg-danger",
            "attendance_pct": 0.0,
            "task_completion_pct": 0.0,
            "approved_leaves": 0,
            "approved_leave_days": 0.0,
            "completed_tasks": 0,
            "pending_tasks": 0,
            "overdue_tasks": 0,
            "total_tasks": 0,
            "last_updated": now.strftime("%d %b %Y, %I:%M %p"),
        }

    close_conn = False
    if conn is None:
        conn = get_db()
        close_conn = True

    try:
        now = datetime.datetime.now(tz=IST)
        today_iso = now.date().isoformat()
        last_updated = now.strftime("%d %b %Y, %I:%M %p")

        user_row = conn.execute(
            "SELECT id, username, full_name, role FROM users WHERE id = ?", (user_id,)
        ).fetchone()

        if not user_row:
            return {
                "user_id": user_id,
                "performance_score": 0.0,
                "performance_score_int": 0,
                "performance_label": "Needs Improvement",
                "badge_class": "bg-danger text-white",
                "bar_class": "bg-danger",
                "attendance_pct": 0.0,
                "task_completion_pct": 0.0,
                "approved_leaves": 0,
                "approved_leave_days": 0.0,
                "completed_tasks": 0,
                "pending_tasks": 0,
                "overdue_tasks": 0,
                "total_tasks": 0,
                "last_updated": last_updated,
            }

        # 1. Attendance Calculation (40% weight)
        cal_data = get_monthly_attendance_calendar_data(now.year, now.month, user_id)
        month_stats = cal_data.get("stats", {}) if cal_data else {}
        tot_workdays = month_stats.get("present_count", 0) + month_stats.get("absent_count", 0)

        if tot_workdays > 0:
            attendance_pct = float(month_stats.get("attendance_rate", 100.0))
        else:
            attendance_pct = 100.0

        attendance_component = (attendance_pct / 100.0) * 40.0

        # 2. Task Completion (40%) & Overdue Tasks (10%)
        class TempUser:
            def __init__(self, uid, uname):
                self.id = uid
                self.username = uname

        temp_user = TempUser(user_id, user_row["username"])
        task_names = get_user_task_names(conn, temp_user)

        if task_names:
            placeholders = ", ".join("?" for _ in task_names)
            tasks_rows = conn.execute(
                f"SELECT id, status, deadline FROM tasks WHERE assigned_to IN ({placeholders})",
                list(task_names),
            ).fetchall()
        else:
            tasks_rows = []

        total_tasks = len(tasks_rows)
        completed_tasks = sum(1 for t in tasks_rows if (t["status"] or "").strip() == "Completed")
        pending_tasks = sum(1 for t in tasks_rows if (t["status"] or "").strip() != "Completed")

        overdue_tasks = sum(
            1 for t in tasks_rows
            if (t["status"] or "").strip() != "Completed"
            and t["deadline"]
            and str(t["deadline"]).strip() < today_iso
        )

        if total_tasks > 0:
            task_completion_pct = (completed_tasks / total_tasks) * 100.0
        else:
            task_completion_pct = 100.0

        task_component = (task_completion_pct / 100.0) * 40.0
        overdue_component = max(0.0, 10.0 - (overdue_tasks * 2.5))

        # 3. Leave Behaviour (10% weight)
        approved_leave_row = conn.execute(
            "SELECT COUNT(*), COALESCE(SUM(total_days), 0) FROM leave_requests WHERE user_id = ? AND status = 'Approved'",
            (user_id,),
        ).fetchone()

        approved_leaves_count = approved_leave_row[0] if approved_leave_row else 0
        approved_leave_days = float(approved_leave_row[1]) if approved_leave_row else 0.0

        if approved_leave_days <= 3.0:
            leave_component = 10.0
        else:
            excess_days = approved_leave_days - 3.0
            leave_component = max(0.0, 10.0 - (excess_days * 0.5))

        # Final Score Calculation (Clamped between 0 and 100)
        raw_score = attendance_component + task_component + leave_component + overdue_component
        final_score = round(max(0.0, min(100.0, raw_score)), 1)

        if final_score >= 85.0:
            label = "Excellent"
            badge_class = "bg-success text-white"
            bar_class = "bg-success"
        elif final_score >= 70.0:
            label = "Good"
            badge_class = "bg-info text-dark"
            bar_class = "bg-info"
        elif final_score >= 50.0:
            label = "Average"
            badge_class = "bg-warning text-dark"
            bar_class = "bg-warning"
        else:
            label = "Needs Improvement"
            badge_class = "bg-danger text-white"
            bar_class = "bg-danger"

        return {
            "user_id": user_id,
            "performance_score": final_score,
            "performance_score_int": round(final_score),
            "performance_label": label,
            "badge_class": badge_class,
            "bar_class": bar_class,
            "attendance_pct": round(attendance_pct, 1),
            "task_completion_pct": round(task_completion_pct, 1),
            "approved_leaves": approved_leaves_count,
            "approved_leave_days": approved_leave_days,
            "completed_tasks": completed_tasks,
            "pending_tasks": pending_tasks,
            "overdue_tasks": overdue_tasks,
            "total_tasks": total_tasks,
            "last_updated": last_updated,
        }
    finally:
        if close_conn:
            conn.close()


def calculate_employee_payroll(conn, emp_id, year=None, month=None):
    """Calculates payroll for an employee for the given month/year automatically.

    Reuses existing Attendance, Leave, Performance and Employee data.
    If a finalized payroll record exists in payroll_records, returns the frozen record.
    Otherwise, dynamically calculates payroll values using current Base Salary and real-time attendance/leave.
    """
    now = datetime.datetime.now(tz=IST)
    if year is None:
        year = now.year
    if month is None:
        month = now.month

    close_conn = False
    if conn is None:
        conn = get_db()
        close_conn = True

    try:
        month_year_str = f"{year:04d}-{month:02d}"

        emp = conn.execute("SELECT * FROM employees WHERE id = ?", (emp_id,)).fetchone()
        if not emp:
            return None

        user_id = dict(emp).get("user_id") or None
        if not user_id and emp["name"]:
            u = conn.execute(
                "SELECT id FROM users WHERE full_name = ? OR username = ?",
                (emp["name"], emp["name"]),
            ).fetchone()
            if u:
                user_id = u["id"]

        # 1. Check if a finalized payroll record exists
        payroll_rec = conn.execute(
            "SELECT * FROM payroll_records WHERE employee_id = ? AND month_year = ? AND status IN ('Finalized', 'Paid')",
            (emp_id, month_year_str),
        ).fetchone()

        if payroll_rec:
            month_date = datetime.date(year, month, 1)
            month_name = month_date.strftime("%B %Y")
            breakdown = {}
            if payroll_rec["salary_breakdown"]:
                try:
                    breakdown = json.loads(payroll_rec["salary_breakdown"])
                except (json.JSONDecodeError, TypeError, ValueError):
                    breakdown = {}

            base_sal = float(payroll_rec["base_salary"])
            work_days = int(payroll_rec["working_days"])
            per_day = round(base_sal / work_days, 2) if work_days > 0 else 0.0

            return {
                "emp_id": emp["id"],
                "employee_code": dict(emp).get("employee_code") or f"EMP-{emp['id']:04d}",
                "user_id": user_id,
                "name": emp["name"],
                "department": emp["department"] or "N/A",
                "month_year": month_year_str,
                "payroll_month": month_name,
                "base_salary": base_sal,
                "working_days": work_days,
                "present_days": int(payroll_rec["present_days"]),
                "attendance_pct": float(payroll_rec["attendance_pct"]),
                "approved_leave_days": float(payroll_rec["approved_leave_days"]),
                "unpaid_leave_days": float(payroll_rec["unpaid_leave_days"]),
                "performance_score": float(payroll_rec["performance_score"]),
                "per_day_salary": per_day,
                "leave_deduction": float(payroll_rec["leave_deduction"]),
                "adjustments": float(payroll_rec["adjustments"]),
                "final_salary": float(payroll_rec["final_salary"]),
                "payroll_status": payroll_rec["status"],
                "salary_breakdown": breakdown,
                "is_finalized": True,
            }

        # 2. Dynamic Calculation using current Base Salary
        base_salary = float(emp["salary"] or 0.0)

        num_days = calendar.monthrange(year, month)[1]
        start_date_str = f"{year:04d}-{month:02d}-01"
        end_date_str = f"{year:04d}-{month:02d}-{num_days:02d}"

        # Exclude weekends and existing HRMS holidays from working days
        holiday_rows = conn.execute(
            "SELECT date FROM holidays WHERE date >= ? AND date <= ?",
            (start_date_str, end_date_str),
        ).fetchall()
        holiday_dates = {h["date"] for h in holiday_rows}

        working_days = 0
        for d in range(1, num_days + 1):
            d_obj = datetime.date(year, month, d)
            if d_obj.weekday() != 6 and d_obj.isoformat() not in holiday_dates:
                working_days += 1

        # Attendance & Present days calculation using existing helper
        present_days = 0
        attendance_pct = 100.0
        if user_id:
            cal_data = get_monthly_attendance_calendar_data(year, month, user_id)
            stats = cal_data.get("stats", {}) if cal_data else {}
            present_days = int(stats.get("present_count", 0))
            tot_workdays = present_days + int(stats.get("absent_count", 0))
            if tot_workdays > 0:
                attendance_pct = float(stats.get("attendance_rate", 100.0))

        # Approved Leave Days & Unpaid Leave Days calculation
        approved_leave_days = 0.0
        unpaid_leave_days = 0.0
        if user_id:
            leave_rows = conn.execute(
                """
                SELECT leave_type, start_date, end_date, total_days 
                FROM leave_requests 
                WHERE user_id = ? AND status = 'Approved' 
                  AND start_date <= ? AND end_date >= ?
                """,
                (user_id, end_date_str, start_date_str),
            ).fetchall()

            for d in range(1, num_days + 1):
                d_str = datetime.date(year, month, d).isoformat()
                for l in leave_rows:
                    if l["start_date"] <= d_str <= l["end_date"]:
                        approved_leave_days += 1.0
                        l_type = (l["leave_type"] or "").lower().strip()
                        if "unpaid" in l_type or "loss of pay" in l_type or l_type == "lop":
                            unpaid_leave_days += 1.0
                        break

        per_day_salary = (base_salary / working_days) if working_days > 0 else 0.0
        leave_deduction = round(per_day_salary * unpaid_leave_days, 2)
        adjustments = 0.0
        final_salary = round(max(0.0, base_salary - leave_deduction + adjustments), 2)

        performance_score = 0.0
        if user_id:
            perf = calculate_employee_performance(conn, user_id)
            performance_score = float(perf.get("performance_score", 0.0))

        month_date = datetime.date(year, month, 1)
        month_name = month_date.strftime("%B %Y")

        breakdown = {
            "base_salary": base_salary,
            "working_days": working_days,
            "per_day_salary": round(per_day_salary, 2),
            "unpaid_leave_days": unpaid_leave_days,
            "leave_deduction": leave_deduction,
            "adjustments": adjustments,
            "final_salary": final_salary,
        }

        return {
            "emp_id": emp["id"],
            "employee_code": dict(emp).get("employee_code") or f"EMP-{emp['id']:04d}",
            "user_id": user_id,
            "name": emp["name"],
            "department": emp["department"] or "N/A",
            "month_year": month_year_str,
            "payroll_month": month_name,
            "base_salary": base_salary,
            "working_days": working_days,
            "present_days": present_days,
            "attendance_pct": round(attendance_pct, 1),
            "approved_leave_days": approved_leave_days,
            "unpaid_leave_days": unpaid_leave_days,
            "performance_score": round(performance_score, 1),
            "per_day_salary": round(per_day_salary, 2),
            "leave_deduction": leave_deduction,
            "adjustments": adjustments,
            "final_salary": final_salary,
            "payroll_status": "Auto-Calculated",
            "salary_breakdown": breakdown,
            "is_finalized": False,
        }
    finally:
        if close_conn:
            conn.close()


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
        ensure_password_reset_tokens_table()
        ensure_attendance_table()
        ensure_holidays_table()
        ensure_employee_table()
        ensure_projects_table()
        ensure_clients_table()
        ensure_tasks_table()
        ensure_time_logs_table()
        ensure_leave_requests_table()
        ensure_performance_reviews_table()
        ensure_notifications_table()
        ensure_settings_tables()
        ensure_payroll_table()
        sync_all_employee_roles(conn)

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
            "SELECT * FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()
    return User.from_db(row)


@app.before_request
def update_user_activity():
    if current_user.is_authenticated:
        try:
            now_str = datetime.datetime.now(tz=IST).strftime("%Y-%m-%d %H:%M:%S")
            with get_db() as conn:
                conn.execute(
                    "UPDATE users SET last_active_at = ? WHERE id = ?",
                    (now_str, current_user.id),
                )
                conn.commit()
        except Exception as e:  # noqa: BLE001
            app.logger.debug("Failed to update user last_active_at: %s", e)


@app.context_processor
def inject_user_preferences():
    if current_user.is_authenticated:
        try:
            with get_db() as conn:
                pref = conn.execute(
                    "SELECT theme, sidebar_style FROM user_preferences WHERE user_id = ?",
                    (current_user.id,),
                ).fetchone()
                user_row = conn.execute(
                    "SELECT profile_pic, last_active_at FROM users WHERE id = ?",
                    (current_user.id,),
                ).fetchone()
                pic = user_row["profile_pic"] if (user_row and user_row["profile_pic"]) else None
                last_act = user_row["last_active_at"] if user_row else None
                return {
                    "current_user_theme": pref["theme"] if (pref and pref["theme"]) else "light",
                    "current_user_sidebar_style": pref["sidebar_style"] if (pref and pref["sidebar_style"]) else "default",
                    "current_user_profile_pic": pic,
                    "current_user_is_online": is_user_online(last_act),
                }
        except Exception:  # noqa: BLE001, S110
            pass
    return {
        "current_user_theme": "light",
        "current_user_sidebar_style": "default",
        "current_user_profile_pic": None,
        "current_user_is_online": False,
    }


@app.route("/api/user-preferences/theme", methods=["POST"])
@login_required
def api_update_theme_preference():
    data = request.get_json(silent=True) or {}
    theme = (data.get("theme") or request.form.get("theme") or "light").strip()
    if theme not in ["light", "dark", "system"]:
        theme = "light"
    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO user_preferences (user_id, theme)
            VALUES (?, ?)
            ON CONFLICT(user_id) DO UPDATE SET theme = excluded.theme
            """,
            (current_user.id, theme),
        )
        conn.commit()
    return jsonify({"status": "success", "theme": theme})


@app.route("/api/user-preferences/sidebar", methods=["POST"])
@login_required
def api_update_sidebar_preference():
    data = request.get_json(silent=True) or {}
    sidebar_style = (data.get("sidebar_style") or request.form.get("sidebar_style") or "default").strip()
    if sidebar_style not in ["default", "compact"]:
        sidebar_style = "default"
    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO user_preferences (user_id, sidebar_style)
            VALUES (?, ?)
            ON CONFLICT(user_id) DO UPDATE SET sidebar_style = excluded.sidebar_style
            """,
            (current_user.id, sidebar_style),
        )
        conn.commit()
    return jsonify({"status": "success", "sidebar_style": sidebar_style})


@app.route("/api/search", methods=["GET"])
@login_required
def api_global_search():
    q = (request.args.get("q") or "").strip()
    if not q:
        return jsonify({"status": "success", "query": "", "results": []})

    results = []
    role = (getattr(current_user, "role", None) or "user").lower()
    user_id = current_user.id
    q_like = f"%{q}%"

    try:
        with get_db() as conn:
            # 1. EMPLOYEES
            if role in ("admin", "hr"):
                emp_rows = conn.execute(
                    """
                    SELECT e.id AS emp_id, e.user_id, e.name, e.department, e.contact_number, u.username
                    FROM employees e
                    LEFT JOIN users u ON e.user_id = u.id
                    WHERE e.name LIKE ? OR e.department LIKE ? OR e.contact_number LIKE ? OR u.username LIKE ?
                    ORDER BY e.name LIMIT 5
                    """,
                    (q_like, q_like, q_like, q_like),
                ).fetchall()
                for row in emp_rows:
                    results.append({
                        "category": "Employee",
                        "title": row["name"] or row["username"] or "Employee",
                        "sub": f"Dept: {row['department'] or 'General'} | User: {row['username'] or 'N/A'}",
                        "icon": "bi-person-badge",
                        "bg_class": "bg-primary-subtle text-primary",
                        "badge_class": "bg-primary text-white",
                        "url": url_for("view_employee", emp_id=row["emp_id"]),
                    })
            else:
                emp_rows = conn.execute(
                    """
                    SELECT e.id AS emp_id, e.user_id, e.name, e.department, u.username
                    FROM employees e
                    JOIN users u ON e.user_id = u.id
                    WHERE u.id = ? AND (e.name LIKE ? OR e.department LIKE ? OR u.username LIKE ?)
                    LIMIT 1
                    """,
                    (user_id, q_like, q_like, q_like),
                ).fetchall()
                for row in emp_rows:
                    results.append({
                        "category": "Employee",
                        "title": row["name"] or row["username"],
                        "sub": f"My Profile | Dept: {row['department'] or 'General'}",
                        "icon": "bi-person-badge",
                        "bg_class": "bg-primary-subtle text-primary",
                        "badge_class": "bg-primary text-white",
                        "url": url_for("settings_profile"),
                    })

            # 2. TASKS
            if role == "admin":
                task_rows = conn.execute(
                    """
                    SELECT id, title, task_category, project, assigned_to, priority, status, deadline
                    FROM tasks
                    WHERE title LIKE ? OR description LIKE ? OR project LIKE ? OR assigned_to LIKE ?
                    ORDER BY id DESC LIMIT 5
                    """,
                    (q_like, q_like, q_like, q_like),
                ).fetchall()
                for r in task_rows:
                    results.append({
                        "category": "Task",
                        "title": r["title"],
                        "sub": f"Status: {r['status'] or 'Pending'} | Assigned: {r['assigned_to'] or 'N/A'} | Due: {r['deadline'] or '-'}",
                        "icon": "bi-check2-square",
                        "bg_class": "bg-success-subtle text-success",
                        "badge_class": "bg-success text-white",
                        "url": url_for("task_management", q=q),
                    })
            else:
                user_names = get_user_task_names(conn, current_user)
                if user_names:
                    placeholders = ", ".join("?" for _ in user_names)
                    sql = f"""
                        SELECT id, title, task_category, project, assigned_to, priority, status, deadline
                        FROM tasks
                        WHERE (assigned_to IN ({placeholders}) OR assigned_by IN ({placeholders}))
                          AND (title LIKE ? OR description LIKE ? OR project LIKE ?)
                        ORDER BY id DESC LIMIT 5
                    """
                    params = list(user_names) + list(user_names) + [q_like, q_like, q_like]
                    task_rows = conn.execute(sql, params).fetchall()
                    for r in task_rows:
                        results.append({
                            "category": "Task",
                            "title": r["title"],
                            "sub": f"Status: {r['status'] or 'Pending'} | Priority: {r['priority'] or 'Normal'} | Due: {r['deadline'] or '-'}",
                            "icon": "bi-check2-square",
                            "bg_class": "bg-success-subtle text-success",
                            "badge_class": "bg-success text-white",
                            "url": url_for("my_tasks", q=q),
                        })

            # 3. PROJECTS (Admin Only)
            if role == "admin":
                proj_rows = conn.execute(
                    """
                    SELECT p.id, p.client_name, p.services, p.assigned_to, c.name AS client_name_from_table
                    FROM projects p
                    LEFT JOIN clients c ON p.client_id = c.id
                    WHERE p.client_name LIKE ? OR p.services LIKE ? OR p.assigned_to LIKE ? OR c.name LIKE ? OR p.delivery_details LIKE ?
                    ORDER BY p.id DESC LIMIT 5
                    """,
                    (q_like, q_like, q_like, q_like, q_like),
                ).fetchall()
                for r in proj_rows:
                    cname = r["client_name_from_table"] or r["client_name"] or "Project"
                    results.append({
                        "category": "Project",
                        "title": f"Project: {cname}",
                        "sub": f"Services: {r['services'] or 'N/A'} | Team: {r['assigned_to'] or 'N/A'}",
                        "icon": "bi-kanban",
                        "bg_class": "bg-warning-subtle text-warning-emphasis",
                        "badge_class": "bg-warning text-dark",
                        "url": url_for("admin_projects", search=q),
                    })

            # 4. CLIENTS (Admin Only)
            if role == "admin":
                client_rows = conn.execute(
                    """
                    SELECT id, name, services, contact_number, email, city
                    FROM clients
                    WHERE name LIKE ? OR services LIKE ? OR email LIKE ? OR contact_number LIKE ? OR city LIKE ?
                    ORDER BY name LIMIT 5
                    """,
                    (q_like, q_like, q_like, q_like, q_like),
                ).fetchall()
                for r in client_rows:
                    results.append({
                        "category": "Client",
                        "title": r["name"],
                        "sub": f"Services: {r['services'] or 'N/A'} | Contact: {r['contact_number'] or r['email'] or 'N/A'}",
                        "icon": "bi-building",
                        "bg_class": "bg-info-subtle text-info-emphasis",
                        "badge_class": "bg-info text-white",
                        "url": url_for("edit_client", client_id=r["id"]),
                    })

            # 5. LEAVE REQUESTS
            if role in ("admin", "hr"):
                leave_rows = conn.execute(
                    """
                    SELECT id, user_id, employee_name, leave_type, start_date, end_date, total_days, reason, status
                    FROM leave_requests
                    WHERE employee_name LIKE ? OR leave_type LIKE ? OR reason LIKE ? OR status LIKE ? OR start_date LIKE ? OR end_date LIKE ?
                    ORDER BY id DESC LIMIT 5
                    """,
                    (q_like, q_like, q_like, q_like, q_like, q_like),
                ).fetchall()
                for r in leave_rows:
                    results.append({
                        "category": "Leave",
                        "title": f"Leave: {r['employee_name']} ({r['leave_type']})",
                        "sub": f"Status: {r['status']} | Dates: {r['start_date']} to {r['end_date']} ({r['total_days']}d)",
                        "icon": "bi-calendar2-range",
                        "bg_class": "bg-danger-subtle text-danger",
                        "badge_class": "bg-danger text-white",
                        "url": url_for("view_all_leave_requests"),
                    })
            else:
                leave_rows = conn.execute(
                    """
                    SELECT id, user_id, employee_name, leave_type, start_date, end_date, total_days, reason, status
                    FROM leave_requests
                    WHERE user_id = ? AND (leave_type LIKE ? OR reason LIKE ? OR status LIKE ? OR start_date LIKE ? OR end_date LIKE ?)
                    ORDER BY id DESC LIMIT 5
                    """,
                    (user_id, q_like, q_like, q_like, q_like, q_like),
                ).fetchall()
                for r in leave_rows:
                    results.append({
                        "category": "Leave",
                        "title": f"My Leave: {r['leave_type']}",
                        "sub": f"Status: {r['status']} | Dates: {r['start_date']} to {r['end_date']} ({r['total_days']}d)",
                        "icon": "bi-calendar2-range",
                        "bg_class": "bg-danger-subtle text-danger",
                        "badge_class": "bg-danger text-white",
                        "url": url_for("my_leave_requests"),
                    })

            # 6. ATTENDANCE
            if role in ("admin", "hr"):
                att_rows = conn.execute(
                    """
                    SELECT id, user_id, username, date, punch_in_time, punch_out_time, total_hours
                    FROM attendance
                    WHERE username LIKE ? OR date LIKE ? OR punch_in_time LIKE ? OR punch_out_time LIKE ?
                    ORDER BY id DESC LIMIT 5
                    """,
                    (q_like, q_like, q_like, q_like),
                ).fetchall()
                for r in att_rows:
                    results.append({
                        "category": "Attendance",
                        "title": f"Attendance: {r['username']} ({r['date']})",
                        "sub": f"In: {r['punch_in_time'] or '-'} | Out: {r['punch_out_time'] or '-'} | Hrs: {r['total_hours'] or '0'}",
                        "icon": "bi-clock-history",
                        "bg_class": "bg-secondary-subtle text-secondary-emphasis",
                        "badge_class": "bg-secondary text-white",
                        "url": url_for("admin_attendance"),
                    })
            else:
                att_rows = conn.execute(
                    """
                    SELECT id, user_id, username, date, punch_in_time, punch_out_time, total_hours
                    FROM attendance
                    WHERE user_id = ? AND (date LIKE ? OR punch_in_time LIKE ? OR punch_out_time LIKE ?)
                    ORDER BY id DESC LIMIT 5
                    """,
                    (user_id, q_like, q_like, q_like),
                ).fetchall()
                for r in att_rows:
                    results.append({
                        "category": "Attendance",
                        "title": f"My Attendance ({r['date']})",
                        "sub": f"In: {r['punch_in_time'] or '-'} | Out: {r['punch_out_time'] or '-'} | Hrs: {r['total_hours'] or '0'}",
                        "icon": "bi-clock-history",
                        "bg_class": "bg-secondary-subtle text-secondary-emphasis",
                        "badge_class": "bg-secondary text-white",
                        "url": url_for("attendance_calendar"),
                    })

            # 7. PERFORMANCE RECORDS
            if role in ("admin", "hr"):
                perf_rows = conn.execute(
                    """
                    SELECT id, employee_user_id, employee_name, reviewer_username, review_period, overall_rating, comments
                    FROM performance_reviews
                    WHERE employee_name LIKE ? OR reviewer_username LIKE ? OR review_period LIKE ? OR comments LIKE ?
                    ORDER BY id DESC LIMIT 5
                    """,
                    (q_like, q_like, q_like, q_like),
                ).fetchall()
                for r in perf_rows:
                    results.append({
                        "category": "Performance",
                        "title": f"Review: {r['employee_name']} ({r['review_period']})",
                        "sub": f"Rating: {r['overall_rating']}/5.0 | Reviewer: {r['reviewer_username']}",
                        "icon": "bi-graph-up-arrow",
                        "bg_class": "bg-primary-subtle text-primary",
                        "badge_class": "bg-dark text-white",
                        "url": url_for("employee_performance_profile", user_id=r["employee_user_id"]),
                    })
            else:
                perf_rows = conn.execute(
                    """
                    SELECT id, employee_user_id, employee_name, reviewer_username, review_period, overall_rating, comments
                    FROM performance_reviews
                    WHERE employee_user_id = ? AND (review_period LIKE ? OR comments LIKE ? OR reviewer_username LIKE ?)
                    ORDER BY id DESC LIMIT 5
                    """,
                    (user_id, q_like, q_like, q_like),
                ).fetchall()
                for r in perf_rows:
                    results.append({
                        "category": "Performance",
                        "title": f"My Review ({r['review_period']})",
                        "sub": f"Rating: {r['overall_rating']}/5.0 | Reviewer: {r['reviewer_username']}",
                        "icon": "bi-graph-up-arrow",
                        "bg_class": "bg-primary-subtle text-primary",
                        "badge_class": "bg-dark text-white",
                        "url": url_for("employee_performance_profile", user_id=user_id),
                    })

            # 8. NOTIFICATIONS (User's own notifications)
            notif_rows = conn.execute(
                """
                SELECT id, title, message, link, created_at
                FROM notifications
                WHERE user_id = ? AND (title LIKE ? OR message LIKE ?)
                ORDER BY id DESC LIMIT 5
                """,
                (user_id, q_like, q_like),
            ).fetchall()
            for r in notif_rows:
                link_url = r["link"] if (r["link"] and r["link"] != "#") else url_for("user_notifications")
                results.append({
                    "category": "Notification",
                    "title": r["title"],
                    "sub": f"{r['message']} ({r['created_at']})",
                    "icon": "bi-bell",
                    "bg_class": "bg-warning-subtle text-warning-emphasis",
                    "badge_class": "bg-warning text-dark",
                    "url": link_url,
                })

            # 9. SYSTEM SHORTCUTS / REPORTS
            q_lower = q.lower()
            if "att" in q_lower or "clock" in q_lower:
                results.append({
                    "category": "Report",
                    "title": "Attendance Reports",
                    "sub": "View full company attendance analytics and logs",
                    "icon": "bi-file-earmark-bar-graph",
                    "bg_class": "bg-info-subtle text-info",
                    "badge_class": "bg-info text-white",
                    "url": url_for("reports_attendance"),
                })
            if "leave" in q_lower or "vacation" in q_lower:
                results.append({
                    "category": "Report",
                    "title": "Leave Reports",
                    "sub": "View leave utilization and request summaries",
                    "icon": "bi-file-earmark-bar-graph",
                    "bg_class": "bg-info-subtle text-info",
                    "badge_class": "bg-info text-white",
                    "url": url_for("reports_leave"),
                })
            if "perf" in q_lower or "review" in q_lower:
                results.append({
                    "category": "Report",
                    "title": "Performance Reports",
                    "sub": "View performance scores and ratings analysis",
                    "icon": "bi-file-earmark-bar-graph",
                    "bg_class": "bg-info-subtle text-info",
                    "badge_class": "bg-info text-white",
                    "url": url_for("reports_performance"),
                })

    except Exception as e:  # noqa: BLE001
        app.logger.error("Error in api_global_search: %s", e)
        return jsonify({"status": "error", "query": q, "results": [], "message": "Search error"}), 200

    return jsonify({"status": "success", "query": q, "results": results[:25]})


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
            if getattr(user, "role", None) != "admin" and getattr(
                user, "force_password_change", False
            ):
                flash(
                    "You must change your temporary password before continuing.",
                    "warning",
                )
                return redirect(url_for("change_password"))
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
            <script>
                (function() {
                    var themePref = localStorage.getItem('hrms-theme-preference') || 'light';
                    var effectiveTheme = themePref;
                    if (!effectiveTheme || effectiveTheme === 'system') {
                        effectiveTheme = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
                    }
                    document.documentElement.setAttribute('data-bs-theme', effectiveTheme);
                    document.documentElement.setAttribute('data-theme', effectiveTheme);
                })();
            </script>
            <title>Login - Bizznex</title>
            <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
            <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css" rel="stylesheet">
            <link href="{{ url_for('static', filename='css/hrms-ui.css', v='1.0.5') }}" rel="stylesheet">
        </head>
        <body class="bg-light">
            <div class="container py-5">
                <div class="card shadow-sm mx-auto" style="max-width: 420px;">
                    <div class="card-body">
                        <div class="text-center mb-4">
                            <img src="{{ url_for('static', filename='images/bizznex-logo.png') }}" alt="Bizznex Logo" style="height: 48px; width: auto;" class="mb-2">
                            <h2 class="h4 mb-0 fw-bold">Bizznex Login</h2>
                        </div>
                        {% with messages = get_flashed_messages(with_categories=true) %}
                            {% if messages %}
                                {% for category, message in messages %}
                                    <div class="alert alert-{{ category }} alert-dismissible fade show" role="alert">
                                        {{ message }}
                                        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
                                    </div>
                                {% endfor %}
                            {% endif %}
                        {% endwith %}
                        <form method="post">
                            <div class="mb-3">
                                <label class="form-label">Username</label>
                                <input class="form-control" name="username" required>
                            </div>
                            <div class="mb-3">
                                <div class="d-flex justify-content-between align-items-center mb-1">
                                    <label class="form-label mb-0">Password</label>
                                    <a href="{{ url_for('forgot_password') }}" class="small text-primary text-decoration-none">Forgot Password?</a>
                                </div>
                                <input class="form-control" type="password" name="password" required>
                            </div>
                            <button class="btn btn-primary w-100" type="submit">Login</button>
                        </form>
                    </div>
                </div>
            </div>
            <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>
            <script src="{{ url_for('static', filename='js/hrms-ui.js') }}"></script>
        </body>
        </html>
        """
    )


@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        identifier = request.form.get("identifier", "").strip()
        if identifier:
            user_row = None
            with get_db() as conn:
                user_row = conn.execute(
                    "SELECT id, username, email, full_name FROM users WHERE (LOWER(email) = LOWER(?) OR LOWER(username) = LOWER(?)) AND role != 'disabled'",
                    (identifier, identifier),
                ).fetchone()

            if user_row and user_row["email"]:
                now_ts = int(time.time())
                expires_at = now_ts + 1800  # 30 minutes validity
                raw_token = secrets.token_urlsafe(32)
                token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()

                try:
                    with get_db() as conn:
                        # Invalidate previous unused reset tokens for this user
                        conn.execute(
                            "UPDATE password_reset_tokens SET used_at = ? WHERE user_id = ? AND used_at IS NULL",
                            (now_ts, user_row["id"]),
                        )
                        conn.execute(
                            """
                            INSERT INTO password_reset_tokens (user_id, token_hash, expires_at, created_at)
                            VALUES (?, ?, ?, ?)
                            """,
                            (user_row["id"], token_hash, expires_at, now_ts),
                        )
                        conn.commit()

                    reset_url = url_for("reset_password", token=raw_token, _external=True)
                    recipient_name = user_row["full_name"] or user_row["username"]
                    subject = "HRMS - Password Reset Request"
                    html_body = f"""
                    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 24px; border: 1px solid #e7ebf3; border-radius: 8px;">
                        <h2 style="color: #4f46e5; margin-top: 0;">HRMS Password Reset</h2>
                        <p>Hello <strong>{recipient_name}</strong>,</p>
                        <p>We received a request to reset your HRMS account password.</p>
                        <p style="margin: 24px 0;">
                            <a href="{reset_url}" style="background-color: #4f46e5; color: #ffffff; padding: 12px 24px; text-decoration: none; border-radius: 6px; display: inline-block; font-weight: bold;">Reset Password</a>
                        </p>
                        <p style="color: #64748b; font-size: 14px;">Or copy and paste this URL into your browser:</p>
                        <p style="word-break: break-all; font-size: 13px; color: #4f46e5;"><a href="{reset_url}">{reset_url}</a></p>
                        <p style="color: #64748b; font-size: 13px;">This reset link will expire in <strong>30 minutes</strong>.</p>
                        <hr style="border: 0; border-top: 1px solid #e7ebf3; margin: 20px 0;">
                        <p style="color: #94a3b8; font-size: 12px;">If you did not request a password reset, please ignore this email. Your password will remain unchanged.</p>
                    </div>
                    """
                    text_body = f"""Hello {recipient_name},

We received a request to reset your HRMS account password.

To reset your password, visit the following link:
{reset_url}

This link is valid for 30 minutes.

If you did not request a password reset, please ignore this email.
"""
                    send_email(user_row["email"], subject, html_body, text_content=text_body)
                except Exception as e:  # noqa: BLE001
                    print(f"ERROR: Failed to process password reset request for {identifier}: {e}")
                    traceback.print_exc()

        # Always return generic security response
        flash("If an account exists with those details, a password reset link has been sent.", "info")
        return redirect(url_for("forgot_password"))

    return render_template_string(
        """
        <!doctype html>
        <html lang="en">
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <title>Forgot Password - Bizznex</title>
            <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
        </head>
        <body class="bg-light">
            <div class="container py-5">
                <div class="card shadow-sm mx-auto" style="max-width: 420px;">
                    <div class="card-body">
                        <h2 class="h4 mb-2">Forgot Password</h2>
                        <p class="text-muted small mb-3">Enter your username or email address and we'll send you a password reset link.</p>
                        {% with messages = get_flashed_messages(with_categories=true) %}
                            {% if messages %}
                                {% for category, message in messages %}
                                    <div class="alert alert-{{ category }} alert-dismissible fade show" role="alert">
                                        {{ message }}
                                        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
                                    </div>
                                {% endfor %}
                            {% endif %}
                        {% endwith %}
                        <form method="post">
                            <div class="mb-3">
                                <label class="form-label">Username or Email Address</label>
                                <input class="form-control" name="identifier" required placeholder="Enter username or email">
                            </div>
                            <button class="btn btn-primary w-100 mb-3" type="submit">Send Reset Link</button>
                            <div class="text-center">
                                <a href="{{ url_for('login') }}" class="small text-primary text-decoration-none">&larr; Back to Login</a>
                            </div>
                        </form>
                    </div>
                </div>
            </div>
            <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>
        </body>
        </html>
        """
    )


@app.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))

    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    now_ts = int(time.time())

    tok_row = None
    with get_db() as conn:
        tok_row = conn.execute(
            """
            SELECT id, user_id, expires_at, used_at
            FROM password_reset_tokens
            WHERE token_hash = ?
            """,
            (token_hash,),
        ).fetchone()

    is_valid = bool(
        tok_row
        and tok_row["used_at"] is None
        and tok_row["expires_at"] > now_ts
    )

    if not is_valid:
        return render_template_string(
            """
            <!doctype html>
            <html lang="en">
            <head>
                <meta charset="utf-8">
                <meta name="viewport" content="width=device-width, initial-scale=1">
                <title>Reset Password - Invalid Link</title>
                <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
            </head>
            <body class="bg-light">
                <div class="container py-5">
                    <div class="card shadow-sm mx-auto" style="max-width: 460px;">
                        <div class="card-body text-center p-4">
                            <div class="text-danger mb-3" style="font-size: 2.5rem;">&#9888;</div>
                            <h2 class="h4 mb-3">Link Invalid or Expired</h2>
                            <p class="text-muted mb-4">This password reset link is invalid or has expired. Please request a new one.</p>
                            <a href="{{ url_for('forgot_password') }}" class="btn btn-primary w-100 mb-2">Request New Reset Link</a>
                            <a href="{{ url_for('login') }}" class="btn btn-outline-secondary w-100">Back to Login</a>
                        </div>
                    </div>
                </div>
            </body>
            </html>
            """
        ), 400

    if request.method == "POST":
        new_password = request.form.get("new_password", "")
        confirm_password = request.form.get("confirm_password", "")

        if not new_password or not confirm_password:
            flash("All fields are required.", "danger")
        elif new_password != confirm_password:
            flash("Passwords do not match.", "danger")
        elif len(new_password) < 8:
            flash("New password must be at least 8 characters long.", "danger")
        else:
            with get_db() as conn:
                # Re-verify token validity within transaction
                tok = conn.execute(
                    "SELECT id, user_id, expires_at, used_at FROM password_reset_tokens WHERE token_hash = ?",
                    (token_hash,),
                ).fetchone()

                if not tok or tok["used_at"] is not None or tok["expires_at"] <= int(time.time()):
                    flash("This password reset link is invalid or has expired. Please request a new one.", "danger")
                    return redirect(url_for("forgot_password"))

                user_id = tok["user_id"]
                token_id = tok["id"]
                now_time = int(time.time())
                new_hash = generate_password_hash(new_password)

                # Atomically update password and mark all reset tokens for user as used
                conn.execute(
                    "UPDATE users SET password_hash = ?, force_password_change = 0 WHERE id = ?",
                    (new_hash, user_id),
                )
                conn.execute(
                    "UPDATE password_reset_tokens SET used_at = ? WHERE id = ?",
                    (now_time, token_id),
                )
                conn.execute(
                    "UPDATE password_reset_tokens SET used_at = ? WHERE user_id = ? AND used_at IS NULL",
                    (now_time, user_id),
                )
                conn.commit()

            flash("Your password has been reset successfully. Please log in with your new password.", "success")
            return redirect(url_for("login"))

    return render_template_string(
        """
        <!doctype html>
        <html lang="en">
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <script>
                (function() {
                    var themePref = localStorage.getItem('hrms-theme-preference') || 'light';
                    var effectiveTheme = themePref;
                    if (!effectiveTheme || effectiveTheme === 'system') {
                        effectiveTheme = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
                    }
                    document.documentElement.setAttribute('data-bs-theme', effectiveTheme);
                    document.documentElement.setAttribute('data-theme', effectiveTheme);
                })();
            </script>
            <title>Reset Password - Bizznex</title>
            <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
            <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css" rel="stylesheet">
            <link href="{{ url_for('static', filename='css/hrms-ui.css', v='1.0.5') }}" rel="stylesheet">
        </head>
        <body class="bg-light">
            <div class="container py-5">
                <div class="card shadow-sm mx-auto" style="max-width: 420px;">
                    <div class="card-body">
                        <h2 class="h4 mb-3">Reset Password</h2>
                        {% with messages = get_flashed_messages(with_categories=true) %}
                            {% if messages %}
                                {% for category, message in messages %}
                                    <div class="alert alert-{{ category }} alert-dismissible fade show" role="alert">
                                        {{ message }}
                                        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
                                    </div>
                                {% endfor %}
                            {% endif %}
                        {% endwith %}
                        <form method="post">
                            <div class="mb-3">
                                <label class="form-label">New Password</label>
                                <input class="form-control" type="password" name="new_password" required minlength="8">
                                <div class="form-text text-muted">Must be at least 8 characters long.</div>
                            </div>
                            <div class="mb-3">
                                <label class="form-label">Confirm New Password</label>
                                <input class="form-control" type="password" name="confirm_password" required minlength="8">
                            </div>
                            <button class="btn btn-primary w-100 mb-3" type="submit">Reset Password</button>
                            <div class="text-center">
                                <a href="{{ url_for('login') }}" class="small text-primary text-decoration-none">&larr; Back to Login</a>
                            </div>
                        </form>
                    </div>
                </div>
            </div>
            <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>
            <script src="{{ url_for('static', filename='js/hrms-ui.js') }}"></script>
        </body>
        </html>
        """
    )


# Enforce password change on first login for non-admin users
@app.before_request
def require_password_change():
    try:
        endpoint = request.endpoint or ""
    except Exception:  # noqa: BLE001  # Safe fallback for endpoint lookup
        endpoint = ""
    # endpoints that must be allowed without changing password
    allowed = {
        "change_password",
        "logout",
        "login",
        "forgot_password",
        "reset_password",
        "static",
        "create_user",
        "send_welcome_email",
    }
    if (
        current_user.is_authenticated
        and getattr(current_user, "role", None) != "admin"
        and getattr(current_user, "force_password_change", False)
        and endpoint not in allowed
        and not endpoint.startswith("static")
    ):
        return redirect(url_for("change_password"))


@app.route("/change-password", methods=["GET", "POST"])
@login_required
def change_password():
    # Only non-admins can be forced; admins should not be here
    if current_user.role == "admin":
        flash("Admins do not need to change passwords here.", "info")
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        current_pw = request.form.get("current_password", "")
        new_pw = request.form.get("new_password", "")
        confirm_pw = request.form.get("confirm_password", "")

        if not current_pw or not new_pw or not confirm_pw:
            flash("All fields are required.", "danger")
            return redirect(url_for("change_password"))

        # verify current password
        if not check_password_hash(current_user.password_hash, current_pw):
            flash("Current password is incorrect.", "danger")
            return redirect(url_for("change_password"))

        if new_pw != confirm_pw:
            flash("New passwords do not match.", "danger")
            return redirect(url_for("change_password"))

        if len(new_pw) < 8:
            flash("New password must be at least 8 characters long.", "danger")
            return redirect(url_for("change_password"))

        # New password cannot be the same as the temporary/current password
        if check_password_hash(current_user.password_hash, new_pw):
            flash("New password must be different from the current password.", "danger")
            return redirect(url_for("change_password"))

        # Update password and clear the force flag
        with get_db() as conn:
            conn.execute(
                "UPDATE users SET password_hash = ?, force_password_change = ? WHERE id = ?",
                (generate_password_hash(new_pw), 0, current_user.id),
            )
            conn.commit()

        # refresh current_user password_hash in memory
        current_user.password_hash = generate_password_hash(new_pw)
        current_user.force_password_change = False

        create_notification(
            current_user.id,
            "Security Alert: Password Changed",
            "Your account password was updated successfully. If you did not make this change, please contact HR.",
            url_for("dashboard"),
        )
        flash("Password changed successfully.", "success")
        return redirect(url_for("dashboard"))

    return render_template_string(
        """
        <!doctype html>
        <html lang="en">
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <title>Change Password</title>
            <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
            <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css" rel="stylesheet">
            <link href="{{ url_for('static', filename='css/hrms-ui.css') }}" rel="stylesheet">
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
            <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>
            <script src="{{ url_for('static', filename='js/hrms-ui.js') }}"></script>
        </body>
        </html>
        """
    )


@app.route("/admin/dashboard/reset", methods=["POST"])
@login_required
def reset_today_dashboard():
    if current_user.role != "admin":
        flash("Admin access required.", "danger")
        return redirect(url_for("dashboard"))

    now_iso = datetime.datetime.now().isoformat()  # noqa: DTZ005
    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO user_preferences (user_id, dashboard_reset_at)
            VALUES (?, ?)
            ON CONFLICT(user_id) DO UPDATE SET dashboard_reset_at = excluded.dashboard_reset_at
            """,
            (current_user.id, now_iso),
        )
        conn.commit()

    flash("Today's dashboard summary counters have been reset. New employee activity will update the dashboard in real-time.", "success")
    return redirect(url_for("dashboard"))


@app.route("/dashboard")
@login_required
def dashboard():
    # Fetch today's attendance and recent records for the current user
    today = datetime.date.today().isoformat()  # noqa: DTZ011  # Naive date check for attendance
    with get_db() as conn:
        row = conn.execute(
            "SELECT id, date, punch_in_time, punch_out_time, total_hours FROM attendance WHERE user_id = ? AND date = ?",
            (current_user.id, today),
        ).fetchone()
        records = conn.execute(
            "SELECT date, punch_in_time, punch_out_time, total_hours FROM attendance WHERE user_id = ? ORDER BY date DESC LIMIT 20",
            (current_user.id,),
        ).fetchall()

    admin_summary = None
    admin_pending_tasks = []
    if current_user.role in ("admin", "hr"):
        with get_db() as conn:
            pref = conn.execute(
                "SELECT dashboard_reset_at FROM user_preferences WHERE user_id = ?",
                (current_user.id,),
            ).fetchone()
            reset_at = pref["dashboard_reset_at"] if pref and pref["dashboard_reset_at"] and pref["dashboard_reset_at"].startswith(today) else None

            total_employees = conn.execute("SELECT COUNT(*) FROM employees").fetchone()[0]

            if reset_at:
                punched_in = conn.execute(
                    "SELECT COUNT(DISTINCT user_id) FROM attendance WHERE date = ? AND punch_in_time >= ?",
                    (today, reset_at),
                ).fetchone()[0]
                punched_out = conn.execute(
                    "SELECT COUNT(DISTINCT user_id) FROM attendance WHERE date = ? AND punch_out_time >= ?",
                    (today, reset_at),
                ).fetchone()[0]
            else:
                punched_in = conn.execute(
                    "SELECT COUNT(DISTINCT user_id) FROM attendance WHERE date = ? AND punch_in_time IS NOT NULL",
                    (today,),
                ).fetchone()[0]
                punched_out = conn.execute(
                    "SELECT COUNT(DISTINCT user_id) FROM attendance WHERE date = ? AND punch_out_time IS NOT NULL",
                    (today,),
                ).fetchone()[0]

            on_leave = conn.execute(
                "SELECT COUNT(*) FROM leave_requests WHERE status = 'Approved' AND start_date <= ? AND end_date >= ?",
                (today, today),
            ).fetchone()[0]

            pending_punch_in = max(0, total_employees - punched_in - on_leave)

            admin_summary = {
                "total_employees": total_employees,
                "punched_in": punched_in,
                "punched_out": punched_out,
                "pending_punch_in": pending_punch_in,
                "on_leave": on_leave,
                "reset_at": reset_at,
            }

            raw_tasks = conn.execute(
                """
                SELECT id, title, assigned_to, priority, deadline, status, project, task_category
                FROM tasks
                WHERE status IS NULL OR status != 'Completed'
                """
            ).fetchall()

            tasks_list = [dict(t) for t in raw_tasks]
            def task_sort_key(t):
                dl = t.get("deadline") or ""
                is_overdue = 0 if (dl and dl < today and t.get("status") != "Completed") else 1
                deadline_val = dl if dl else "9999-12-31"
                return (is_overdue, deadline_val, -t["id"])

            tasks_list.sort(key=task_sort_key)
            admin_pending_tasks = tasks_list[:10]

    return render_template_string(
        """
        {% extends "base.html" %}
        {% block title %}Dashboard{% endblock %}
        {% block page_content %}
                <div class="page-header d-flex flex-wrap justify-content-between align-items-center gap-3 mb-4">
                    <div>
                        <h1 class="h3 mb-1">Dashboard</h1>
                        <p class="text-muted mb-0">Welcome back, <strong>{{ current_user.username }}</strong>.</p>
                    </div>
                    {% if current_user.role == 'admin' %}
                        <div>
                            <form id="resetDashboardForm" method="post" action="{{ url_for('reset_today_dashboard') }}" style="display:none;"></form>
                            <button type="button" class="btn btn-outline-warning shadow-sm" onclick="confirmResetDashboard()">
                                <i class="bi bi-arrow-counterclockwise me-1"></i>Reset Today's Dashboard
                            </button>
                        </div>
                    {% endif %}
                </div>

                {% with messages = get_flashed_messages(with_categories=true) %}
                    {% if messages %}
                        {% for category, message in messages %}
                            <div class="alert alert-{{ category }} alert-dismissible fade show" role="alert">
                                {{ message }}
                                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                            </div>
                        {% endfor %}
                    {% endif %}
                {% endwith %}

                {% if admin_summary %}
                <div class="card shadow-sm mb-4 border-0">
                    <div class="card-header bg-white py-3 border-0 d-flex justify-content-between align-items-center">
                        <h5 class="card-title mb-0 fw-bold text-primary"><i class="bi bi-speedometer2 me-2"></i>Today's Organization Attendance Summary</h5>
                        {% if admin_summary.reset_at %}
                            <span class="badge bg-secondary">Summary reset at {{ admin_summary.reset_at[11:16] }}</span>
                        {% endif %}
                    </div>
                    <div class="card-body">
                        <div class="row g-3 text-center">
                            <div class="col-md-2 col-6">
                                <div class="p-3 border rounded bg-light">
                                    <div class="text-muted small fw-semibold">Total Employees</div>
                                    <div class="fs-3 fw-bold text-dark">{{ admin_summary.total_employees }}</div>
                                </div>
                            </div>
                            <div class="col-md-2 col-6">
                                <div class="p-3 border rounded bg-success bg-opacity-10 border-success border-opacity-25">
                                    <div class="text-success small fw-semibold">Punched In Today</div>
                                    <div class="fs-3 fw-bold text-success">{{ admin_summary.punched_in }}</div>
                                </div>
                            </div>
                            <div class="col-md-2 col-6">
                                <div class="p-3 border rounded bg-info bg-opacity-10 border-info border-opacity-25">
                                    <div class="text-info small fw-semibold">Punched Out Today</div>
                                    <div class="fs-3 fw-bold text-info">{{ admin_summary.punched_out }}</div>
                                </div>
                            </div>
                            <div class="col-md-3 col-6">
                                <div class="p-3 border rounded bg-warning bg-opacity-10 border-warning border-opacity-25">
                                    <div class="text-warning small fw-semibold">Pending Punch-In</div>
                                    <div class="fs-3 fw-bold text-warning">{{ admin_summary.pending_punch_in }}</div>
                                </div>
                            </div>
                            <div class="col-md-3 col-12">
                                <div class="p-3 border rounded bg-primary bg-opacity-10 border-primary border-opacity-25">
                                    <div class="text-primary small fw-semibold">On Approved Leave</div>
                                    <div class="fs-3 fw-bold text-primary">{{ admin_summary.on_leave }}</div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                <div class="card shadow-sm mb-4 border-0">
                    <div class="card-header bg-white py-3 border-0 d-flex flex-wrap justify-content-between align-items-center gap-2">
                        <h5 class="card-title mb-0 fw-bold text-primary"><i class="bi bi-clock-history me-2"></i>Pending Tasks</h5>
                        <a href="{{ url_for('task_management') }}" class="btn btn-sm btn-outline-primary"><i class="bi bi-arrow-right-circle me-1"></i>View All Tasks</a>
                    </div>
                    <div class="card-body p-0">
                        {% if admin_pending_tasks %}
                        <div class="table-responsive">
                            <table class="table table-hover align-middle mb-0">
                                <thead class="table-light small">
                                    <tr>
                                        <th>Task Title</th>
                                        <th>Assigned Employee</th>
                                        <th>Priority</th>
                                        <th>Due Date</th>
                                        <th>Status</th>
                                        <th class="text-end">Action</th>
                                    </tr>
                                </thead>
                                <tbody class="small">
                                    {% for task in admin_pending_tasks %}
                                    <tr>
                                        <td>
                                            <a href="{{ url_for('task_management', edit_id=task.id) }}" class="text-decoration-none fw-bold text-dark me-1">{{ task.title or '' }}</a>
                                            {% if task.deadline and task.deadline < today_str and task.status != 'Completed' %}
                                                <span class="badge badge-overdue"><i class="bi bi-exclamation-circle-fill me-1"></i>OVERDUE</span>
                                            {% endif %}
                                        </td>
                                        <td>
                                            <span class="fw-semibold text-dark">{{ task.assigned_to or 'Unassigned' }}</span>
                                        </td>
                                        <td>
                                            {% if task.priority == 'Critical' %}
                                                <span class="badge badge-priority-critical"><i class="bi bi-exclamation-triangle-fill me-1"></i>Critical</span>
                                            {% elif task.priority == 'High' %}
                                                <span class="badge badge-priority-high"><i class="bi bi-arrow-up me-1"></i>High</span>
                                            {% elif task.priority == 'Medium' %}
                                                <span class="badge badge-priority-medium"><i class="bi bi-dash-lg me-1"></i>Medium</span>
                                            {% else %}
                                                <span class="badge badge-priority-low"><i class="bi bi-arrow-down me-1"></i>Low</span>
                                            {% endif %}
                                        </td>
                                        <td>
                                            <span class="{% if task.deadline and task.deadline < today_str and task.status != 'Completed' %}text-danger fw-bold{% else %}text-muted{% endif %}">
                                                {{ task.deadline or 'N/A' }}
                                            </span>
                                        </td>
                                        <td>
                                            {% if task.status == 'In Progress' %}
                                                <span class="badge bg-primary"><i class="bi bi-play-circle me-1"></i>In Progress</span>
                                            {% elif task.status == 'Blocked' %}
                                                <span class="badge bg-danger"><i class="bi bi-slash-circle me-1"></i>Blocked</span>
                                            {% else %}
                                                <span class="badge bg-warning text-dark"><i class="bi bi-clock me-1"></i>Pending</span>
                                            {% endif %}
                                        </td>
                                        <td class="text-end">
                                            <a href="{{ url_for('task_management', edit_id=task.id) }}" class="btn btn-sm btn-outline-primary" title="View / Edit Details">
                                                <i class="bi bi-pencil-square me-1"></i>Details
                                            </a>
                                        </td>
                                    </tr>
                                    {% endfor %}
                                </tbody>
                            </table>
                        </div>
                        {% else %}
                        <div class="text-center py-4 text-muted">
                            <p class="fs-5 mb-0 fw-medium">🎉 No pending tasks.</p>
                        </div>
                        {% endif %}
                    </div>
                </div>
                {% endif %}

                <div class="card shadow-sm mb-4">
                    <div class="card-body">
                        <h5 class="card-title fw-bold mb-3">Quick Punch Action</h5>
                        <form method="post" action="{{ url_for('punch_in') }}" style="display:inline-block;">
                            <button class="btn btn-success"><i class="bi bi-box-arrow-in-right me-1"></i>Punch In</button>
                        </form>
                        <form method="post" action="{{ url_for('punch_out') }}" style="display:inline-block; margin-left:8px;">
                            <button class="btn btn-danger"><i class="bi bi-box-arrow-right me-1"></i>Punch Out</button>
                        </form>
                    </div>
                </div>

                <div class="card shadow-sm mb-4">
                    <div class="card-body">
                        <h4 class="h5">Today's Attendance</h4>
                        {% if today_row %}
                            <p>Punch In: {{ today_row.punch_in_time | format_timestamp }}</p>
                            <p>Punch Out: {{ today_row.punch_out_time | format_timestamp }}</p>
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
                                        <td>{{ r.punch_in_time | format_timestamp }}</td>
                                        <td>{{ r.punch_out_time | format_timestamp }}</td>
                                        <td>{{ r.total_hours or '' }}</td>
                                    </tr>
                                {% endfor %}
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>

                <script>
                    function confirmResetDashboard() {
                        if (confirm("Are you sure you want to reset today's dashboard summary view? This will only reset the active dashboard summary counters and will NOT delete or alter any attendance records in the database.")) {
                            document.getElementById('resetDashboardForm').submit();
                        }
                    }
                </script>
        {% endblock %}
        """,
        today_row=row,
        records=records,
        admin_summary=admin_summary,
        admin_pending_tasks=admin_pending_tasks,
        today_str=today,
    )


@app.route("/my-tasks")
@login_required
def my_tasks():
    if current_user.role == "admin":
        return redirect(url_for("task_management"))

    today = datetime.date.today().isoformat()  # noqa: DTZ011
    date_filter = (request.args.get("date_filter") or "all").strip()
    start_date = (request.args.get("start_date") or "").strip()
    end_date = (request.args.get("end_date") or "").strip()
    status_filter = (request.args.get("status_filter") or "").strip()
    priority_filter = (request.args.get("priority_filter") or "").strip()
    overdue_filter = (request.args.get("overdue_filter") or "").strip()
    q = (request.args.get("q") or "").strip()

    calc_start, calc_end = resolve_date_range(date_filter, start_date, end_date)

    with get_db() as conn:
        employee_name_filter = get_user_task_names(conn, current_user)

        if not employee_name_filter:
            tasks = []
        else:
            placeholders = ", ".join("?" for _ in employee_name_filter)
            sql = f"""
                SELECT t.id, t.title, t.task_category, t.description, t.project, t.assigned_to, t.assigned_by, t.assigned_date, t.deadline,
                       t.priority, t.estimated_hours, t.recurring_type, t.status, COALESCE(t.progress, 0) AS progress, t.completed_by,
                       COALESCE(SUM(l.hours_worked), 0) AS total_logged_hours
                FROM tasks t
                LEFT JOIN time_logs l ON l.task_id = t.id
                WHERE t.assigned_to IN ({placeholders})
            """
            params = list(employee_name_filter)
            if status_filter:
                sql += " AND t.status = ?"
                params.append(status_filter)
            if priority_filter:
                sql += " AND t.priority = ?"
                params.append(priority_filter)
            if overdue_filter == "overdue":
                sql += " AND t.deadline < ? AND (t.status IS NULL OR t.status != 'Completed')"
                params.append(today)
            elif overdue_filter == "not_overdue":
                sql += " AND (t.deadline >= ? OR t.status = 'Completed')"
                params.append(today)
            if q:
                sql += " AND (t.title LIKE ? OR t.description LIKE ? OR t.project LIKE ?)"
                pattern = f"%{q}%"
                params.extend([pattern, pattern, pattern])
            if calc_start:
                sql += " AND t.assigned_date >= ?"
                params.append(calc_start)
            if calc_end:
                sql += " AND t.assigned_date <= ?"
                params.append(calc_end)

            sql += " GROUP BY t.id ORDER BY t.assigned_date DESC, t.deadline ASC, t.title"
            tasks = conn.execute(sql, params).fetchall()

    total_tasks_count = len(tasks)
    pending_tasks_count = sum(1 for t in tasks if t["status"] != "Completed")
    completed_tasks_count = sum(1 for t in tasks if t["status"] == "Completed")
    overdue_tasks_count = sum(1 for t in tasks if t["deadline"] < today and t["status"] != "Completed")
    due_today_tasks_count = sum(1 for t in tasks if t["deadline"] == today and t["status"] != "Completed")

    current_tasks = []
    future_tasks = []
    recurring_tasks = []
    for task in tasks:
        if task["recurring_type"]:
            recurring_tasks.append(task)
        elif task["assigned_date"] > today:
            future_tasks.append(task)
        else:
            current_tasks.append(task)

    return render_template_string(
        """
        {% extends "base.html" %}
        {% block title %}My Tasks{% endblock %}
        {% block page_content %}
        <div class="container-fluid py-4">
            <div class="d-flex flex-wrap justify-content-between align-items-center gap-3 mb-4">
                <div>
                    <h1 class="h3 mb-1"><i class="bi bi-check2-square text-primary me-2"></i>My Tasks</h1>
                    <p class="text-muted mb-0">Manage your assigned tasks, update progress, and log working hours.</p>
                </div>
                <a class="btn btn-outline-secondary" href="{{ url_for('dashboard') }}"><i class="bi bi-arrow-left me-1"></i>Back to Dashboard</a>
            </div>

            {% with messages = get_flashed_messages(with_categories=true) %}
                {% if messages %}
                    {% for category, message in messages %}
                        <div class="alert alert-{{ category }}">{{ message }}</div>
                    {% endfor %}
                {% endif %}
            {% endwith %}

            <!-- 5 KPI Summary Widgets -->
            <div class="row g-3 mb-4">
                <div class="col-6 col-md">
                    <div class="card shadow-sm border-0 border-start border-4 border-primary h-100">
                        <div class="card-body p-3">
                            <div class="text-muted small fw-bold mb-1"><i class="bi bi-list-task me-1 text-primary"></i>TOTAL TASKS</div>
                            <div class="display-6 fw-bold text-dark">{{ total_tasks_count }}</div>
                        </div>
                    </div>
                </div>
                <div class="col-6 col-md">
                    <div class="card shadow-sm border-0 border-start border-4 border-warning h-100">
                        <div class="card-body p-3">
                            <div class="text-muted small fw-bold mb-1"><i class="bi bi-clock-history me-1 text-warning"></i>PENDING</div>
                            <div class="display-6 fw-bold text-warning">{{ pending_tasks_count }}</div>
                        </div>
                    </div>
                </div>
                <div class="col-6 col-md">
                    <div class="card shadow-sm border-0 border-start border-4 border-success h-100">
                        <div class="card-body p-3">
                            <div class="text-muted small fw-bold mb-1"><i class="bi bi-check-circle me-1 text-success"></i>COMPLETED</div>
                            <div class="display-6 fw-bold text-success">{{ completed_tasks_count }}</div>
                        </div>
                    </div>
                </div>
                <div class="col-6 col-md">
                    <div class="card shadow-sm border-0 border-start border-4 border-danger h-100">
                        <div class="card-body p-3">
                            <div class="text-muted small fw-bold mb-1"><i class="bi bi-exclamation-octagon me-1 text-danger"></i>OVERDUE</div>
                            <div class="display-6 fw-bold text-danger">{{ overdue_tasks_count }}</div>
                        </div>
                    </div>
                </div>
                <div class="col-6 col-md">
                    <div class="card shadow-sm border-0 border-start border-4 border-info h-100">
                        <div class="card-body p-3">
                            <div class="text-muted small fw-bold mb-1"><i class="bi bi-calendar-event me-1 text-info"></i>DUE TODAY</div>
                            <div class="display-6 fw-bold text-info">{{ due_today_tasks_count }}</div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Search & Filter Card -->
            <div class="card shadow-sm border-0 mb-4">
                <div class="card-body">
                    <form method="get" class="row g-3 align-items-end">
                        <div class="col-md-3">
                            <label class="form-label small fw-bold text-muted mb-1"><i class="bi bi-search me-1"></i>Search</label>
                            <input type="text" name="q" class="form-control form-control-sm" placeholder="Task title, project..." value="{{ q or '' }}">
                        </div>
                        <div class="col-md-2">
                            <label class="form-label small fw-bold text-muted mb-1"><i class="bi bi-flag me-1"></i>Priority</label>
                            <select class="form-select form-select-sm" name="priority_filter">
                                <option value="">All Priorities</option>
                                <option value="Low" {% if priority_filter == 'Low' %}selected{% endif %}>Low</option>
                                <option value="Medium" {% if priority_filter == 'Medium' %}selected{% endif %}>Medium</option>
                                <option value="High" {% if priority_filter == 'High' %}selected{% endif %}>High</option>
                                <option value="Critical" {% if priority_filter == 'Critical' %}selected{% endif %}>Critical</option>
                            </select>
                        </div>
                        <div class="col-md-2">
                            <label class="form-label small fw-bold text-muted mb-1"><i class="bi bi-activity me-1"></i>Status</label>
                            <select class="form-select form-select-sm" name="status_filter">
                                <option value="">All Statuses</option>
                                <option value="Pending" {% if status_filter == 'Pending' %}selected{% endif %}>Pending</option>
                                <option value="In Progress" {% if status_filter == 'In Progress' %}selected{% endif %}>In Progress</option>
                                <option value="Blocked" {% if status_filter == 'Blocked' %}selected{% endif %}>Blocked</option>
                                <option value="Completed" {% if status_filter == 'Completed' %}selected{% endif %}>Completed</option>
                            </select>
                        </div>
                        <div class="col-md-2">
                            <label class="form-label small fw-bold text-muted mb-1"><i class="bi bi-exclamation-triangle me-1"></i>Overdue Filter</label>
                            <select class="form-select form-select-sm" name="overdue_filter">
                                <option value="">All Tasks</option>
                                <option value="overdue" {% if overdue_filter == 'overdue' %}selected{% endif %}>Overdue Only</option>
                                <option value="not_overdue" {% if overdue_filter == 'not_overdue' %}selected{% endif %}>Not Overdue</option>
                            </select>
                        </div>
                        <div class="col-md-3 d-flex gap-2">
                            <button type="submit" class="btn btn-sm btn-primary w-100"><i class="bi bi-funnel me-1"></i>Filter</button>
                            <a href="{{ url_for('my_tasks') }}" class="btn btn-sm btn-outline-secondary w-100">Reset</a>
                        </div>
                    </form>
                </div>
            </div>

            {% if not tasks %}
                <div class="alert alert-info shadow-sm"><i class="bi bi-info-circle me-2"></i>No tasks match the selected filter criteria.</div>
            {% endif %}

            {% macro render_task_cards(task_list, section_title) %}
                {% if task_list %}
                    <div class="card shadow-sm border-0 mb-4">
                        <div class="card-header bg-white py-3 border-0">
                            <h2 class="h5 card-title mb-0 fw-bold"><i class="bi bi-card-checklist me-2 text-primary"></i>{{ section_title }}</h2>
                        </div>
                        <div class="card-body p-3">
                            {% for task in task_list %}
                                <div class="card border mb-3 shadow-sm rounded-3">
                                    <div class="card-body p-3">
                                        <div class="row g-3">
                                            <div class="col-md-7 col-lg-8">
                                                <div class="d-flex align-items-center gap-2 flex-wrap mb-2">
                                                    <span class="badge bg-light text-dark border">{{ task.task_category or 'General' }}</span>
                                                    <h3 class="h6 mb-0 fw-bold text-dark me-2">{{ task.title or '' }}</h3>
                                                    
                                                    <!-- Priority Badge -->
                                                    {% if task.priority == 'Critical' %}
                                                        <span class="badge badge-priority-critical"><i class="bi bi-exclamation-triangle-fill me-1"></i>Critical</span>
                                                    {% elif task.priority == 'High' %}
                                                        <span class="badge badge-priority-high"><i class="bi bi-arrow-up me-1"></i>High</span>
                                                    {% elif task.priority == 'Medium' %}
                                                        <span class="badge badge-priority-medium"><i class="bi bi-dash-lg me-1"></i>Medium</span>
                                                    {% else %}
                                                        <span class="badge badge-priority-low"><i class="bi bi-arrow-down me-1"></i>Low</span>
                                                    {% endif %}

                                                    <!-- Status Badge -->
                                                    {% if task.status == 'Completed' %}
                                                        <span class="badge bg-success"><i class="bi bi-check-circle me-1"></i>Completed</span>
                                                    {% elif task.status == 'In Progress' %}
                                                        <span class="badge bg-primary"><i class="bi bi-play-circle me-1"></i>In Progress</span>
                                                    {% elif task.status == 'Blocked' %}
                                                        <span class="badge bg-danger"><i class="bi bi-slash-circle me-1"></i>Blocked</span>
                                                    {% else %}
                                                        <span class="badge bg-warning text-dark"><i class="bi bi-clock me-1"></i>Pending</span>
                                                    {% endif %}

                                                    <!-- Automatic Overdue Badge -->
                                                    {% if task.deadline < today and task.status != 'Completed' %}
                                                        <span class="badge badge-overdue"><i class="bi bi-clock-history me-1"></i>OVERDUE</span>
                                                    {% endif %}
                                                </div>

                                                <div class="small text-muted mb-2">
                                                    <span class="me-3"><i class="bi bi-building me-1 text-primary"></i><strong>Project:</strong> {{ task.project or 'N/A' }}</span>
                                                    <span class="me-3"><i class="bi bi-person me-1 text-secondary"></i><strong>Assigned By:</strong> {{ task.assigned_by or 'Admin' }}</span>
                                                    <span class="me-3"><i class="bi bi-calendar-event me-1 text-info"></i><strong>Due Date:</strong> {{ task.deadline or 'N/A' }}</span>
                                                    {% if task.recurring_type %}<span class="badge bg-info text-dark ms-1"><i class="bi bi-repeat me-1"></i>{{ task.recurring_type }}</span>{% endif %}
                                                </div>

                                                {% if task.description %}
                                                    <p class="small text-secondary mb-3 bg-light p-2 rounded border">{{ task.description }}</p>
                                                {% endif %}

                                                <!-- Progress Bar -->
                                                <div class="mb-2">
                                                    <div class="d-flex justify-content-between align-items-center small fw-semibold text-muted mb-1">
                                                        <span>Task Progress</span>
                                                        <span class="text-dark fw-bold">{{ task.progress }}%</span>
                                                    </div>
                                                    <div class="task-progress-container" style="height: 10px;">
                                                        <div class="progress-bar {% if task.progress == 100 %}bg-success{% elif task.progress >= 50 %}bg-info{% else %}bg-primary{% endif %}" role="progressbar" style="width: {{ task.progress }}%; height: 100%;" aria-valuenow="{{ task.progress }}" aria-valuemin="0" aria-valuemax="100"></div>
                                                    </div>
                                                </div>

                                                <div class="d-flex gap-3 small text-muted">
                                                    <span><i class="bi bi-hourglass-top me-1"></i>Est: {{ '%.2f'|format(task.estimated_hours or 0) }} hrs</span>
                                                    <span><i class="bi bi-hourglass-split me-1"></i>Logged: {{ '%.2f'|format(task.total_logged_hours or 0) }} hrs</span>
                                                </div>
                                            </div>

                                            <div class="col-md-5 col-lg-4 border-start ps-md-3">
                                                <h4 class="small fw-bold text-dark mb-2"><i class="bi bi-pencil-square me-1 text-primary"></i>Update Task & Progress</h4>
                                                <form method="post" action="{{ url_for('update_task', task_id=task.id) }}">
                                                    <div class="mb-2">
                                                        <label class="form-label small mb-1">Progress (%): <strong class="text-primary">{{ task.progress }}%</strong></label>
                                                        <input class="form-control form-control-sm" name="progress" type="number" min="0" max="100" value="{{ task.progress }}" placeholder="0 - 100">
                                                    </div>
                                                    <div class="mb-2">
                                                        <label class="form-label small mb-1">Log Hours Worked</label>
                                                        <input class="form-control form-control-sm" name="hours_worked" type="number" step="0.25" min="0" placeholder="e.g. 2.5">
                                                    </div>
                                                    <div class="mb-2">
                                                        <label class="form-label small mb-1">Work Notes</label>
                                                        <input class="form-control form-control-sm" name="work_notes" placeholder="Notes...">
                                                    </div>
                                                    <div class="mb-2">
                                                        <label class="form-label small mb-1">Status</label>
                                                        <select class="form-select form-select-sm" name="status">
                                                            <option value="Pending" {% if task.status == 'Pending' %}selected{% endif %}>Pending</option>
                                                            <option value="In Progress" {% if task.status == 'In Progress' %}selected{% endif %}>In Progress</option>
                                                            <option value="Blocked" {% if task.status == 'Blocked' %}selected{% endif %}>Blocked</option>
                                                            <option value="Completed" {% if task.status == 'Completed' %}selected{% endif %}>Completed</option>
                                                        </select>
                                                    </div>
                                                    <button class="btn btn-primary btn-sm w-100" type="submit"><i class="bi bi-save me-1"></i>Save Progress Update</button>
                                                </form>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            {% endfor %}
                        </div>
                    </div>
                {% endif %}
            {% endmacro %}

            {{ render_task_cards(current_tasks, "Current Tasks") }}
            {{ render_task_cards(future_tasks, "Future Tasks") }}
            {{ render_task_cards(recurring_tasks, "Recurring Tasks") }}
        </div>
        {% endblock %}
        """,
        tasks=tasks,
        current_tasks=current_tasks,
        future_tasks=future_tasks,
        recurring_tasks=recurring_tasks,
        date_filter=date_filter,
        start_date=start_date,
        end_date=end_date,
        status_filter=status_filter,
        priority_filter=priority_filter,
        overdue_filter=overdue_filter,
        q=q,
        today=today,
        total_tasks_count=total_tasks_count,
        pending_tasks_count=pending_tasks_count,
        completed_tasks_count=completed_tasks_count,
        overdue_tasks_count=overdue_tasks_count,
        due_today_tasks_count=due_today_tasks_count,
    )


@app.route("/tasks/<int:task_id>/update", methods=["POST"])
@login_required
def update_task(task_id):
    if current_user.role == "admin":
        flash("Admins manage tasks from the Task Management page.", "warning")
        return redirect(url_for("task_management"))

    with get_db() as conn:
        task = conn.execute(
            "SELECT id, title, assigned_to, assigned_by, status, COALESCE(progress, 0) AS progress FROM tasks WHERE id = ?",
            (task_id,),
        ).fetchone()
        employee_names = get_user_task_names(conn, current_user)

    if task is None:
        flash("Task not found.", "warning")
        return redirect(url_for("my_tasks"))

    if task["assigned_to"] not in employee_names:
        flash("Only assigned employees may update their own tasks.", "danger")
        return redirect(url_for("my_tasks"))

    hours_worked = request.form.get("hours_worked", "").strip()
    work_notes = request.form.get("work_notes", "").strip()
    status = request.form.get("status", "Pending").strip()
    progress_input = request.form.get("progress", "").strip()

    progress = None
    if progress_input != "":
        try:
            progress = max(0, min(100, int(progress_input)))
        except ValueError:
            pass

    if progress is not None and progress >= 100:
        status = "Completed"
    elif status == "Completed":
        progress = 100

    if hours_worked:
        try:
            hours_value = float(hours_worked)
        except ValueError:
            flash("Hours must be a valid number.", "danger")
            return redirect(url_for("my_tasks"))
        if hours_value <= 0:
            flash("Hours cannot be zero or negative.", "danger")
            return redirect(url_for("my_tasks"))
    else:
        hours_value = None

    if status not in ["Pending", "In Progress", "Blocked", "Completed"]:
        status = "Pending"

    with get_db() as conn:
        if hours_value is not None:
            conn.execute(
                "INSERT INTO time_logs (task_id, user_id, logged_date, hours_worked, notes) VALUES (?, ?, ?, ?, ?)",
                (
                    task_id,
                    current_user.id,
                    datetime.date.today().isoformat(),  # noqa: DTZ011
                    hours_value,
                    work_notes or None,
                ),
            )
        completed_by = current_user.username if status == "Completed" else None
        completion_date = datetime.date.today().isoformat() if status == "Completed" else None  # noqa: DTZ011
        if progress is not None:
            conn.execute(
                "UPDATE tasks SET status = ?, progress = ?, completed_by = ?, completion_date = ? WHERE id = ?",
                (status, progress, completed_by, completion_date, task_id),
            )
        else:
            conn.execute(
                "UPDATE tasks SET status = ?, completed_by = ?, completion_date = ? WHERE id = ?",
                (status, completed_by, completion_date, task_id),
            )
        conn.commit()
        if status != task["status"]:
            notify_admins(
                "Task Status Update",
                f"Task '{task['title']}' status updated to '{status}' by {current_user.username}.",
                url_for("task_management"),
            )
            notify_user_by_name_or_username(
                task["assigned_by"],
                "Task Status Update",
                f"Task '{task['title']}' status updated to '{status}' by {current_user.username}.",
                url_for("task_management"),
            )

    flash("Task updated successfully.", "success")
    return redirect(url_for("my_tasks"))


@app.route("/admin/tasks", methods=["GET", "POST"])
@login_required
def task_management():
    if current_user.role != "admin":
        flash("Admin access required.", "danger")
        return redirect(url_for("dashboard"))

    with get_db() as conn:
        employees = conn.execute(
            "SELECT id, name FROM employees ORDER BY name"
        ).fetchall()
        conn.execute(
            "SELECT id, name FROM clients ORDER BY lower(name), id"
        )
        projects = conn.execute(
            """
            SELECT projects.id, clients.name AS client_name
            FROM projects
            LEFT JOIN clients ON clients.id = projects.client_id
            ORDER BY clients.name
        """
        ).fetchall()

    employee_filter = (request.args.get("employee_filter") or "").strip()
    project_filter = (request.args.get("project_filter") or "").strip()
    status_filter = (request.args.get("status_filter") or "").strip()
    priority_filter = (request.args.get("priority_filter") or "").strip()
    overdue_filter = (request.args.get("overdue_filter") or "").strip()
    date_filter = (request.args.get("date_filter") or "all").strip()
    start_date = (request.args.get("start_date") or "").strip()
    end_date = (request.args.get("end_date") or "").strip()
    q = (request.args.get("q") or "").strip()
    edit_id = (request.args.get("edit_id") or "").strip()
    today_str = datetime.date.today().isoformat()  # noqa: DTZ011

    calc_start, calc_end = resolve_date_range(date_filter, start_date, end_date)

    edit_task = None
    if edit_id:
        with get_db() as conn:
            edit_task = conn.execute(
                "SELECT id, title, task_category, description, project, assigned_to, assigned_by, assigned_date, deadline, priority, estimated_hours, recurring_type, status, COALESCE(progress, 0) AS progress, completed_by, completion_date FROM tasks WHERE id = ?",
                (edit_id,),
            ).fetchone()

    if request.method == "POST":
        action = request.form.get("action", "create").strip()
        task_id = request.form.get("task_id", "").strip()

        if action == "delete" and task_id:
            with get_db() as conn:
                conn.execute("DELETE FROM time_logs WHERE task_id = ?", (task_id,))
                conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
                conn.commit()
            flash("Task deleted successfully.", "success")
            return redirect(url_for("task_management"))

        task_category = request.form.get("task_category", "").strip()
        selected_task = request.form.get("task_title", "").strip()
        custom_task_title = request.form.get("custom_task_title", "").strip()
        description = request.form.get("description", "").strip()
        project = request.form.get("project", "").strip()
        assigned_to = request.form.get("assigned_to", "").strip()
        assigned_date = request.form.get("assigned_date", "").strip()
        deadline = request.form.get("deadline", "").strip()
        priority = request.form.get("priority", "Medium").strip()
        recurring_type = request.form.get("recurring_type", "").strip() or None
        status = request.form.get("status", "Pending").strip()
        estimated_hours_input = request.form.get("estimated_hours", "").strip()
        progress_input = request.form.get("progress", "0").strip()

        try:
            progress = max(0, min(100, int(progress_input))) if progress_input != "" else 0
        except ValueError:
            progress = 0

        if progress >= 100 or status == "Completed":
            progress = 100
            status = "Completed"

        if task_category not in TASK_CATEGORIES:
            flash("Select a valid task category.", "danger")
            return redirect(url_for("task_management"))
        if task_category == "Other (Custom)":
            title = custom_task_title
        elif selected_task in TASK_CATEGORIES[task_category]:
            title = selected_task
        else:
            flash("Select a valid task for the selected category.", "danger")
            return redirect(url_for("task_management"))

        try:
            estimated_hours = float(estimated_hours_input)
        except ValueError:
            flash("Estimated Hours must be a valid number.", "danger")
            return redirect(url_for("task_management"))

        if (
            not title
            or not project
            or not assigned_to
            or not assigned_date
            or not deadline
            or not priority
            or not status
        ):
            flash("All task fields except description are required.", "danger")
            return redirect(url_for("task_management"))
        if estimated_hours <= 0:
            flash("Estimated Hours must be greater than zero.", "danger")
            return redirect(url_for("task_management"))

        if deadline < assigned_date:
            flash("Deadline cannot be before Assigned Date.", "danger")
            return redirect(url_for("task_management"))

        if action == "edit" and task_id:
            with get_db() as conn:
                completion_date = (
                    datetime.date.today().isoformat() if status == "Completed" else None  # noqa: DTZ011
                )
                conn.execute(
                    """
                    UPDATE tasks SET title=?, task_category=?, description=?, project=?, assigned_to=?, assigned_by=?, assigned_date=?, deadline=?, priority=?, estimated_hours=?, recurring_type=?, status=?, progress=?, completed_by=?, completion_date=? WHERE id=?
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
                        progress,
                        current_user.username if status == "Completed" else None,
                        completion_date,
                        task_id,
                    ),
                )
                conn.commit()
            notify_user_by_name_or_username(
                assigned_to,
                "Task Assignment Updated",
                f"Your assigned task '{title}' for project '{project}' was updated.",
                url_for("my_tasks"),
            )
            flash("Task updated successfully.", "success")
            return redirect(url_for("task_management"))

        with get_db() as conn:
            completion_date = (
                datetime.date.today().isoformat() if status == "Completed" else None  # noqa: DTZ011
            )
            conn.execute(
                """
                INSERT INTO tasks (title, task_category, description, project, assigned_to, assigned_by, assigned_date, deadline, priority, estimated_hours, recurring_type, status, progress, completed_by, completion_date)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                    progress,
                    current_user.username if status == "Completed" else None,
                    completion_date,
                ),
            )
            conn.commit()
        notify_user_by_name_or_username(
            assigned_to,
            "New Task Assigned",
            f"You were assigned task '{title}' for project '{project}' (Deadline: {deadline}).",
            url_for("my_tasks"),
        )
        flash("Task created successfully.", "success")
        return redirect(url_for("task_management"))

    query = """
        SELECT t.id, t.title, t.task_category, t.description, t.project, t.assigned_to, t.assigned_by, t.assigned_date, t.deadline,
               t.priority, COALESCE(t.estimated_hours, 0) AS estimated_hours, t.recurring_type, t.status, COALESCE(t.progress, 0) AS progress, t.completed_by,
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
    if priority_filter:
        query += " AND t.priority = ?"
        params.append(priority_filter)
    if overdue_filter == "overdue":
        query += " AND t.deadline < ? AND (t.status IS NULL OR t.status != 'Completed')"
        params.append(today_str)
    elif overdue_filter == "not_overdue":
        query += " AND (t.deadline >= ? OR t.status = 'Completed')"
        params.append(today_str)
    if q:
        query += " AND (t.title LIKE ? OR t.description LIKE ? OR t.project LIKE ? OR t.assigned_to LIKE ?)"
        pattern = f"%{q}%"
        params.extend([pattern, pattern, pattern, pattern])
    if calc_start:
        query += " AND t.assigned_date >= ?"
        params.append(calc_start)
    if calc_end:
        query += " AND t.assigned_date <= ?"
        params.append(calc_end)
    query += " GROUP BY t.id ORDER BY t.assigned_date DESC, t.deadline DESC, t.title"

    with get_db() as conn:
        tasks = conn.execute(query, params).fetchall()

    total_tasks_count = len(tasks)
    pending_tasks_count = sum(1 for t in tasks if t["status"] != "Completed")
    completed_tasks_count = sum(1 for t in tasks if t["status"] == "Completed")
    overdue_tasks_count = sum(1 for t in tasks if t["deadline"] < today_str and t["status"] != "Completed")
    due_today_tasks_count = sum(1 for t in tasks if t["deadline"] == today_str and t["status"] != "Completed")

    return render_template_string(
        """
        {% extends "base.html" %}
        {% block title %}Task Management{% endblock %}
        {% block page_content %}
        <div class="container-fluid py-4">
            <div class="d-flex flex-wrap justify-content-between align-items-center gap-3 mb-4">
                <div>
                    <h1 class="h3 mb-1"><i class="bi bi-kanban text-primary me-2"></i>Task Management</h1>
                    <p class="text-muted mb-0">Create, assign, track employee task progress, priorities, and deadlines.</p>
                </div>
                <div class="d-flex gap-2">
                    <a class="btn btn-outline-primary" href="{{ url_for('completed_tasks_archive') }}"><i class="bi bi-archive me-1"></i>Completed Tasks Archive</a>
                    <a class="btn btn-outline-secondary" href="{{ url_for('dashboard') }}"><i class="bi bi-arrow-left me-1"></i>Back</a>
                </div>
            </div>

            {% with messages = get_flashed_messages(with_categories=true) %}
                {% if messages %}
                    {% for category, message in messages %}
                        <div class="alert alert-{{ category }}">{{ message }}</div>
                    {% endfor %}
                {% endif %}
            {% endwith %}

            <!-- 5 KPI Summary Widgets -->
            <div class="row g-3 mb-4">
                <div class="col-6 col-md">
                    <div class="card shadow-sm border-0 border-start border-4 border-primary h-100">
                        <div class="card-body p-3">
                            <div class="text-muted small fw-bold mb-1"><i class="bi bi-list-task me-1 text-primary"></i>TOTAL TASKS</div>
                            <div class="display-6 fw-bold text-dark">{{ total_tasks_count }}</div>
                        </div>
                    </div>
                </div>
                <div class="col-6 col-md">
                    <div class="card shadow-sm border-0 border-start border-4 border-warning h-100">
                        <div class="card-body p-3">
                            <div class="text-muted small fw-bold mb-1"><i class="bi bi-clock-history me-1 text-warning"></i>PENDING</div>
                            <div class="display-6 fw-bold text-warning">{{ pending_tasks_count }}</div>
                        </div>
                    </div>
                </div>
                <div class="col-6 col-md">
                    <div class="card shadow-sm border-0 border-start border-4 border-success h-100">
                        <div class="card-body p-3">
                            <div class="text-muted small fw-bold mb-1"><i class="bi bi-check-circle me-1 text-success"></i>COMPLETED</div>
                            <div class="display-6 fw-bold text-success">{{ completed_tasks_count }}</div>
                        </div>
                    </div>
                </div>
                <div class="col-6 col-md">
                    <div class="card shadow-sm border-0 border-start border-4 border-danger h-100">
                        <div class="card-body p-3">
                            <div class="text-muted small fw-bold mb-1"><i class="bi bi-exclamation-octagon me-1 text-danger"></i>OVERDUE</div>
                            <div class="display-6 fw-bold text-danger">{{ overdue_tasks_count }}</div>
                        </div>
                    </div>
                </div>
                <div class="col-6 col-md">
                    <div class="card shadow-sm border-0 border-start border-4 border-info h-100">
                        <div class="card-body p-3">
                            <div class="text-muted small fw-bold mb-1"><i class="bi bi-calendar-event me-1 text-info"></i>DUE TODAY</div>
                            <div class="display-6 fw-bold text-info">{{ due_today_tasks_count }}</div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Create / Edit Task Form Card -->
            <div class="card shadow-sm border-0 mb-4">
                <div class="card-header bg-white py-3 border-0">
                    <h2 class="h5 card-title mb-0 fw-bold"><i class="bi bi-pencil-square text-primary me-2"></i>{% if edit_task %}Edit Task #{{ edit_task.id }}{% else %}Create New Task{% endif %}</h2>
                </div>
                <div class="card-body">
                    <form method="post">
                        <input type="hidden" name="action" value="{% if edit_task %}edit{% else %}create{% endif %}">
                        {% if edit_task %}
                            <input type="hidden" name="task_id" value="{{ edit_task.id }}">
                        {% endif %}
                        <div class="row g-3">
                            <div class="col-md-6">
                                <label class="form-label small fw-bold text-muted mb-1">Task Category</label>
                                <select class="form-select" name="task_category" id="task-category" required>
                                    <option value="">Select category</option>
                                    {% for category in task_categories %}
                                        <option value="{{ category }}" {% if edit_task and edit_task.task_category == category %}selected{% endif %}>{{ category }}</option>
                                    {% endfor %}
                                </select>
                            </div>
                            <div class="col-md-6">
                                <label class="form-label small fw-bold text-muted mb-1">Task Title</label>
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
                                <label class="form-label small fw-bold text-muted mb-1">Custom Task Title</label>
                                <input class="form-control" name="custom_task_title" id="custom-task-title" value="{% if edit_task and edit_task.task_category == 'Other (Custom)' %}{{ edit_task.title }}{% endif %}">
                            </div>
                            <div class="col-md-6">
                                <label class="form-label small fw-bold text-muted mb-1">Project</label>
                                <select class="form-select" name="project" required>
                                    <option value="">Select project</option>
                                    {% for project in projects %}
                                        <option value="{{ project.client_name }}" {% if edit_task and edit_task.project == project.client_name %}selected{% endif %}>{{ project.client_name }}</option>
                                    {% endfor %}
                                </select>
                            </div>
                            <div class="col-md-6">
                                <label class="form-label small fw-bold text-muted mb-1">Assigned Employee</label>
                                <select class="form-select" name="assigned_to" required>
                                    <option value="">Select employee</option>
                                    {% for employee in employees %}
                                        <option value="{{ employee.name }}" {% if edit_task and edit_task.assigned_to == employee.name %}selected{% endif %}>{{ employee.name }}</option>
                                    {% endfor %}
                                </select>
                            </div>
                            <div class="col-md-4">
                                <label class="form-label small fw-bold text-muted mb-1">Priority</label>
                                <select class="form-select" name="priority" required>
                                    <option value="Low" {% if edit_task and edit_task.priority == 'Low' %}selected{% endif %}>Low</option>
                                    <option value="Medium" {% if edit_task and (not edit_task.priority or edit_task.priority == 'Medium') %}selected{% endif %}>Medium</option>
                                    <option value="High" {% if edit_task and edit_task.priority == 'High' %}selected{% endif %}>High</option>
                                    <option value="Critical" {% if edit_task and edit_task.priority == 'Critical' %}selected{% endif %}>Critical</option>
                                </select>
                            </div>
                            <div class="col-md-4">
                                <label class="form-label small fw-bold text-muted mb-1">Estimated Hours</label>
                                <input class="form-control" name="estimated_hours" type="number" step="0.25" min="0.25" value="{{ edit_task.estimated_hours if edit_task and edit_task.estimated_hours is not none else '' }}" required>
                            </div>
                            <div class="col-md-4">
                                <label class="form-label small fw-bold text-muted mb-1">Progress (%)</label>
                                <input class="form-control" name="progress" type="number" min="0" max="100" value="{{ edit_task.progress if edit_task and edit_task.progress is not none else 0 }}" placeholder="0 - 100">
                            </div>
                            <div class="col-md-4">
                                <label class="form-label small fw-bold text-muted mb-1">Assigned Date</label>
                                <input class="form-control" name="assigned_date" type="date" value="{{ edit_task.assigned_date if edit_task else '' }}" required>
                            </div>
                            <div class="col-md-4">
                                <label class="form-label small fw-bold text-muted mb-1">Deadline / Due Date</label>
                                <input class="form-control" name="deadline" type="date" value="{{ edit_task.deadline if edit_task else '' }}" required>
                            </div>
                            <div class="col-md-4">
                                <label class="form-label small fw-bold text-muted mb-1">Recurring Type</label>
                                <select class="form-select" name="recurring_type">
                                    <option value="">None</option>
                                    <option value="Daily" {% if edit_task and edit_task.recurring_type == 'Daily' %}selected{% endif %}>Daily</option>
                                    <option value="Weekly" {% if edit_task and edit_task.recurring_type == 'Weekly' %}selected{% endif %}>Weekly</option>
                                    <option value="Monthly" {% if edit_task and edit_task.recurring_type == 'Monthly' %}selected{% endif %}>Monthly</option>
                                </select>
                            </div>
                            <div class="col-md-6">
                                <label class="form-label small fw-bold text-muted mb-1">Status</label>
                                <select class="form-select" name="status" required>
                                    <option value="Pending" {% if edit_task and edit_task.status == 'Pending' %}selected{% endif %}>Pending</option>
                                    <option value="In Progress" {% if edit_task and edit_task.status == 'In Progress' %}selected{% endif %}>In Progress</option>
                                    <option value="Blocked" {% if edit_task and edit_task.status == 'Blocked' %}selected{% endif %}>Blocked</option>
                                    <option value="Completed" {% if edit_task and edit_task.status == 'Completed' %}selected{% endif %}>Completed</option>
                                </select>
                            </div>
                            <div class="col-12">
                                <label class="form-label small fw-bold text-muted mb-1">Description</label>
                                <textarea class="form-control" name="description" rows="2">{{ edit_task.description if edit_task else '' }}</textarea>
                            </div>
                        </div>
                        <div class="mt-3">
                            <button class="btn btn-primary" type="submit">{% if edit_task %}<i class="bi bi-save me-1"></i>Save Changes{% else %}<i class="bi bi-plus-circle me-1"></i>Create Task{% endif %}</button>
                            {% if edit_task %}
                                <a class="btn btn-outline-secondary ms-2" href="{{ url_for('task_management') }}">Cancel</a>
                            {% endif %}
                        </div>
                    </form>
                </div>
            </div>

            <!-- Search & Filter Card -->
            <div class="card shadow-sm border-0 mb-4">
                <div class="card-header bg-white py-3 border-0">
                    <h2 class="h5 card-title mb-0 fw-bold"><i class="bi bi-funnel text-primary me-2"></i>Filter & Search Tasks</h2>
                </div>
                <div class="card-body">
                    <form method="get" class="row g-3 align-items-end">
                        <div class="col-md-3">
                            <label class="form-label small fw-semibold text-muted">Search Query</label>
                            <input type="text" name="q" class="form-control form-control-sm" placeholder="Title, project, employee..." value="{{ q or '' }}">
                        </div>
                        <div class="col-md-2">
                            <label class="form-label small fw-semibold text-muted">Employee</label>
                            <select class="form-select form-select-sm" name="employee_filter">
                                <option value="">All Employees</option>
                                {% for employee in employees %}
                                    <option value="{{ employee.name }}" {% if employee_filter == employee.name %}selected{% endif %}>{{ employee.name }}</option>
                                {% endfor %}
                            </select>
                        </div>
                        <div class="col-md-2">
                            <label class="form-label small fw-semibold text-muted">Project</label>
                            <select class="form-select form-select-sm" name="project_filter">
                                <option value="">All Projects</option>
                                {% for project in projects %}
                                    <option value="{{ project.client_name }}" {% if project_filter == project.client_name %}selected{% endif %}>{{ project.client_name }}</option>
                                {% endfor %}
                            </select>
                        </div>
                        <div class="col-md-2">
                            <label class="form-label small fw-semibold text-muted">Status</label>
                            <select class="form-select form-select-sm" name="status_filter">
                                <option value="">All Statuses</option>
                                <option value="Pending" {% if status_filter == 'Pending' %}selected{% endif %}>Pending</option>
                                <option value="In Progress" {% if status_filter == 'In Progress' %}selected{% endif %}>In Progress</option>
                                <option value="Blocked" {% if status_filter == 'Blocked' %}selected{% endif %}>Blocked</option>
                                <option value="Completed" {% if status_filter == 'Completed' %}selected{% endif %}>Completed</option>
                            </select>
                        </div>
                        <div class="col-md-3">
                            <label class="form-label small fw-semibold text-muted">Priority</label>
                            <select class="form-select form-select-sm" name="priority_filter">
                                <option value="">All Priorities</option>
                                <option value="Low" {% if priority_filter == 'Low' %}selected{% endif %}>Low</option>
                                <option value="Medium" {% if priority_filter == 'Medium' %}selected{% endif %}>Medium</option>
                                <option value="High" {% if priority_filter == 'High' %}selected{% endif %}>High</option>
                                <option value="Critical" {% if priority_filter == 'Critical' %}selected{% endif %}>Critical</option>
                            </select>
                        </div>
                        <div class="col-md-2">
                            <label class="form-label small fw-semibold text-muted">Overdue Filter</label>
                            <select class="form-select form-select-sm" name="overdue_filter">
                                <option value="">All Tasks</option>
                                <option value="overdue" {% if overdue_filter == 'overdue' %}selected{% endif %}>Overdue Only</option>
                                <option value="not_overdue" {% if overdue_filter == 'not_overdue' %}selected{% endif %}>Not Overdue</option>
                            </select>
                        </div>
                        <div class="col-md-3">
                            <label class="form-label small fw-semibold text-muted">Date Filter</label>
                            <select class="form-select form-select-sm" name="date_filter" id="adminDateFilterSelect">
                                <option value="all" {% if date_filter == 'all' %}selected{% endif %}>All Tasks</option>
                                <option value="today" {% if date_filter == 'today' %}selected{% endif %}>Today</option>
                                <option value="last_7" {% if date_filter == 'last_7' %}selected{% endif %}>Last 7 Days</option>
                                <option value="last_30" {% if date_filter == 'last_30' %}selected{% endif %}>Last 30 Days</option>
                                <option value="this_month" {% if date_filter == 'this_month' %}selected{% endif %}>This Month</option>
                                <option value="custom" {% if date_filter == 'custom' %}selected{% endif %}>Custom Date Range</option>
                            </select>
                        </div>
                        <div class="col-md-2">
                            <label class="form-label small fw-semibold text-muted">Start Date</label>
                            <input type="date" class="form-control form-control-sm" name="start_date" id="adminStartDateInput" value="{{ start_date or '' }}">
                        </div>
                        <div class="col-md-2">
                            <label class="form-label small fw-semibold text-muted">End Date</label>
                            <input type="date" class="form-control form-control-sm" name="end_date" id="adminEndDateInput" value="{{ end_date or '' }}">
                        </div>
                        <div class="col-md-3 d-flex gap-2">
                            <button class="btn btn-sm btn-primary w-100" type="submit"><i class="bi bi-funnel me-1"></i>Apply Filters</button>
                            <a class="btn btn-sm btn-outline-secondary w-100" href="{{ url_for('task_management') }}">Reset</a>
                        </div>
                    </form>
                </div>
            </div>

            <!-- Task List Table Card -->
            <div class="card shadow-sm border-0 mb-4">
                <div class="card-header bg-white py-3 border-0 d-flex justify-content-between align-items-center">
                    <h2 class="h5 card-title mb-0 fw-bold"><i class="bi bi-list-columns me-2 text-primary"></i>Task Directory ({{ tasks|length }})</h2>
                </div>
                <div class="card-body p-0">
                    <div class="table-responsive">
                        <table class="table table-hover align-middle mb-0">
                            <thead class="table-light small">
                                <tr>
                                    <th>Category</th>
                                    <th>Task Title</th>
                                    <th>Project</th>
                                    <th>Assigned Employee</th>
                                    <th>Due Date</th>
                                    <th>Priority</th>
                                    <th>Progress</th>
                                    <th>Status</th>
                                    <th>Logged / Est</th>
                                    <th class="text-end">Actions</th>
                                </tr>
                            </thead>
                            <tbody class="small">
                            {% if tasks %}
                                {% for task in tasks %}
                                    <tr>
                                        <td><span class="badge bg-light text-dark border">{{ task.task_category or 'General' }}</span></td>
                                        <td>
                                            <strong class="text-dark d-block">{{ task.title or '' }}</strong>
                                            {% if task.recurring_type %}<span class="badge bg-info text-dark small me-1"><i class="bi bi-repeat me-1"></i>{{ task.recurring_type }}</span>{% endif %}
                                            {% if task.deadline < today_str and task.status != 'Completed' %}
                                                <span class="badge badge-overdue"><i class="bi bi-clock-history me-1"></i>OVERDUE</span>
                                            {% endif %}
                                        </td>
                                        <td>{{ task.project or 'N/A' }}</td>
                                        <td>
                                            <span class="fw-semibold text-dark">{{ task.assigned_to or 'Unassigned' }}</span>
                                            <small class="text-muted d-block">By: {{ task.assigned_by or 'Admin' }}</small>
                                        </td>
                                        <td>
                                            <span class="{% if task.deadline < today_str and task.status != 'Completed' %}text-danger fw-bold{% endif %}">{{ task.deadline or 'N/A' }}</span>
                                            <small class="text-muted d-block">From: {{ task.assigned_date or 'N/A' }}</small>
                                        </td>
                                        <td>
                                            {% if task.priority == 'Critical' %}
                                                <span class="badge badge-priority-critical"><i class="bi bi-exclamation-triangle-fill me-1"></i>Critical</span>
                                            {% elif task.priority == 'High' %}
                                                <span class="badge badge-priority-high"><i class="bi bi-arrow-up me-1"></i>High</span>
                                            {% elif task.priority == 'Medium' %}
                                                <span class="badge badge-priority-medium"><i class="bi bi-dash-lg me-1"></i>Medium</span>
                                            {% else %}
                                                <span class="badge badge-priority-low"><i class="bi bi-arrow-down me-1"></i>Low</span>
                                            {% endif %}
                                        </td>
                                        <td style="min-width: 120px;">
                                            <div class="d-flex justify-content-between align-items-center small fw-semibold text-muted mb-1">
                                                <span>{{ task.progress }}%</span>
                                            </div>
                                            <div class="task-progress-container" style="height: 8px;">
                                                <div class="progress-bar {% if task.progress == 100 %}bg-success{% elif task.progress >= 50 %}bg-info{% else %}bg-primary{% endif %}" role="progressbar" style="width: {{ task.progress }}%; height: 100%;" aria-valuenow="{{ task.progress }}" aria-valuemin="0" aria-valuemax="100"></div>
                                            </div>
                                        </td>
                                        <td>
                                            {% if task.status == 'Completed' %}
                                                <span class="badge bg-success"><i class="bi bi-check-circle me-1"></i>Completed</span>
                                            {% elif task.status == 'In Progress' %}
                                                <span class="badge bg-primary"><i class="bi bi-play-circle me-1"></i>In Progress</span>
                                            {% elif task.status == 'Blocked' %}
                                                <span class="badge bg-danger"><i class="bi bi-slash-circle me-1"></i>Blocked</span>
                                            {% else %}
                                                <span class="badge bg-warning text-dark"><i class="bi bi-clock me-1"></i>Pending</span>
                                            {% endif %}
                                        </td>
                                        <td>
                                            <span class="fw-bold text-dark">{{ '%.2f'|format(task.total_logged_hours or 0) }}</span> / {{ '%.2f'|format(task.estimated_hours or 0) }} hrs
                                        </td>
                                        <td class="text-end">
                                            <a class="btn btn-sm btn-outline-primary me-1" href="{{ url_for('task_management', edit_id=task.id) }}" title="Edit Task"><i class="bi bi-pencil"></i></a>
                                            <form method="post" style="display:inline-block;" onsubmit="return confirm('Delete this task?');">
                                                <input type="hidden" name="action" value="delete">
                                                <input type="hidden" name="task_id" value="{{ task.id }}">
                                                <button class="btn btn-sm btn-outline-danger" type="submit" title="Delete Task"><i class="bi bi-trash"></i></button>
                                            </form>
                                        </td>
                                    </tr>
                                {% endfor %}
                            {% else %}
                                <tr>
                                    <td colspan="10" class="text-center py-4 text-muted"><i class="bi bi-inbox fs-4 d-block mb-1"></i>No tasks found.</td>
                                </tr>
                            {% endif %}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </div>
        <script>
        document.addEventListener('DOMContentLoaded', function() {
            var catSelect = document.getElementById('task-category');
            var titleSelect = document.getElementById('task-title');
            var customContainer = document.getElementById('custom-task-container');
            var customTitle = document.getElementById('custom-task-title');
            var categories = {{ task_categories | tojson }};

            if (catSelect) {
                catSelect.addEventListener('change', function() {
                    var category = this.value;
                    titleSelect.innerHTML = '<option value="">Select task</option>';
                    if (category === 'Other (Custom)') {
                        customContainer.classList.remove('d-none');
                        customTitle.setAttribute('required', 'required');
                        titleSelect.removeAttribute('required');
                    } else if (categories[category]) {
                        customContainer.classList.add('d-none');
                        customTitle.removeAttribute('required');
                        titleSelect.setAttribute('required', 'required');
                        categories[category].forEach(function(t) {
                            var opt = document.createElement('option');
                            opt.value = t;
                            opt.textContent = t;
                            titleSelect.appendChild(opt);
                        });
                    }
                });
            }
        });
        </script>
        {% endblock %}
        """,
        employees=employees,
        projects=projects,
        tasks=tasks,
        edit_task=edit_task,
        task_categories=TASK_CATEGORIES,
        employee_filter=employee_filter,
        project_filter=project_filter,
        status_filter=status_filter,
        priority_filter=priority_filter,
        overdue_filter=overdue_filter,
        date_filter=date_filter,
        start_date=start_date,
        end_date=end_date,
        q=q,
        today_str=today_str,
        total_tasks_count=total_tasks_count,
        pending_tasks_count=pending_tasks_count,
        completed_tasks_count=completed_tasks_count,
        overdue_tasks_count=overdue_tasks_count,
        due_today_tasks_count=due_today_tasks_count,
    )


def fetch_completed_tasks_records(conn, args):
    q = (args.get("q") or "").strip()
    employee_filter = (args.get("employee_filter") or "").strip()
    project_filter = (args.get("project_filter") or "").strip()
    status_filter = (args.get("status_filter") or "Completed").strip()
    start_date = (args.get("start_date") or "").strip()
    end_date = (args.get("end_date") or "").strip()

    sql = """
        SELECT t.id, t.title, t.task_category, t.description, t.project, t.assigned_to, t.assigned_by,
               t.assigned_date, t.deadline, t.priority, COALESCE(t.estimated_hours, 0) AS estimated_hours,
               t.recurring_type, t.status, t.completed_by, t.completion_date,
               COALESCE(SUM(l.hours_worked), 0) AS total_logged_hours
        FROM tasks t
        LEFT JOIN time_logs l ON l.task_id = t.id
        WHERE 1=1
    """
    params = []
    if status_filter and status_filter.lower() != "all":
        sql += " AND t.status = ?"
        params.append(status_filter)

    if employee_filter:
        sql += " AND t.assigned_to = ?"
        params.append(employee_filter)

    if project_filter:
        sql += " AND t.project = ?"
        params.append(project_filter)

    if start_date:
        sql += " AND (COALESCE(t.completion_date, t.assigned_date) >= ?)"
        params.append(start_date)

    if end_date:
        sql += " AND (COALESCE(t.completion_date, t.assigned_date) <= ?)"
        params.append(end_date)

    if q:
        sql += " AND (t.title LIKE ? OR t.project LIKE ? OR t.assigned_to LIKE ? OR t.assigned_by LIKE ? OR t.description LIKE ?)"
        term = f"%{q}%"
        params.extend([term, term, term, term, term])

    sql += " GROUP BY t.id ORDER BY COALESCE(t.completion_date, t.assigned_date) DESC, t.id DESC"

    tasks = conn.execute(sql, params).fetchall()

    task_notes = {}
    if tasks:
        task_ids = [t["id"] for t in tasks]
        placeholders = ",".join("?" for _ in task_ids)
        logs = conn.execute(
            f"SELECT task_id, logged_date, hours_worked, notes FROM time_logs WHERE task_id IN ({placeholders}) AND notes IS NOT NULL AND notes != '' ORDER BY id ASC",
            task_ids,
        ).fetchall()
        for log in logs:
            tid = log["task_id"]
            if tid not in task_notes:
                task_notes[tid] = []
            task_notes[tid].append({
                "date": log["logged_date"],
                "hours": log["hours_worked"],
                "notes": log["notes"]
            })

    results = []
    for t in tasks:
        item = dict(t)
        tid = t["id"]
        logs_list = task_notes.get(tid, [])
        item["logs"] = logs_list
        item["notes_summary"] = " | ".join(f"{l['date']}: {l['notes']}" for l in logs_list) if logs_list else (t["description"] or "N/A")
        results.append(item)

    return results


@app.route("/admin/tasks/completed")
@login_required
def completed_tasks_archive():
    if current_user.role != "admin":
        flash("Admin access required.", "danger")
        return redirect(url_for("dashboard"))

    start_date = (request.args.get("start_date") or request.args.get("from_date") or "").strip()
    end_date = (request.args.get("end_date") or request.args.get("to_date") or "").strip()

    if start_date and end_date and start_date > end_date:
        flash("From Date cannot be after To Date.", "warning")

    with get_db() as conn:
        employees = conn.execute("SELECT name FROM employees ORDER BY name").fetchall()
        task_projects = conn.execute("SELECT DISTINCT project FROM tasks WHERE project IS NOT NULL AND project != '' ORDER BY project").fetchall()
        tasks = fetch_completed_tasks_records(conn, request.args)

    return render_template_string(
        """
        {% extends "base.html" %}
        {% block title %}Completed Tasks Archive{% endblock %}
        {% block page_content %}
        <div class="container-fluid py-4">
            <div class="d-flex align-items-center justify-content-between mb-4">
                <div>
                    <h1 class="h3 mb-1"><i class="bi bi-archive-fill text-primary me-2"></i>Completed Tasks Archive</h1>
                    <p class="text-muted mb-0">View, search, filter, and export records of completed employee tasks.</p>
                </div>
                <div class="d-flex gap-2">
                    <a href="{{ url_for('task_management') }}" class="btn btn-outline-secondary"><i class="bi bi-arrow-left me-1"></i>Active Tasks</a>
                    <a href="{{ url_for('export_completed_tasks_csv', **request.args) }}" class="btn btn-outline-success"><i class="bi bi-file-earmark-spreadsheet me-1"></i>Export CSV</a>
                    <a href="{{ url_for('export_completed_tasks_excel', **request.args) }}" class="btn btn-outline-primary"><i class="bi bi-file-earmark-excel me-1"></i>Export Excel</a>
                    <a href="{{ url_for('export_completed_tasks_pdf', **request.args) }}" class="btn btn-outline-danger"><i class="bi bi-file-earmark-pdf me-1"></i>Export PDF</a>
                </div>
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
                    <form method="get" class="row g-3">
                        <div class="col-md-3">
                            <label class="form-label small fw-semibold">Search</label>
                            <input type="text" name="q" class="form-control form-control-sm" placeholder="Title, employee, project..." value="{{ request.args.get('q', '') }}">
                        </div>
                        <div class="col-md-2">
                            <label class="form-label small fw-semibold">Employee</label>
                            <select name="employee_filter" class="form-select form-select-sm">
                                <option value="">All Employees</option>
                                {% for emp in employees %}
                                    <option value="{{ emp.name }}" {% if request.args.get('employee_filter') == emp.name %}selected{% endif %}>{{ emp.name }}</option>
                                {% endfor %}
                            </select>
                        </div>
                        <div class="col-md-2">
                            <label class="form-label small fw-semibold">Project</label>
                            <select name="project_filter" class="form-select form-select-sm">
                                <option value="">All Projects</option>
                                {% for proj in task_projects %}
                                    <option value="{{ proj.project }}" {% if request.args.get('project_filter') == proj.project %}selected{% endif %}>{{ proj.project }}</option>
                                {% endfor %}
                            </select>
                        </div>
                        <div class="col-md-2">
                            <label class="form-label small fw-semibold">Status</label>
                            <select name="status_filter" class="form-select form-select-sm">
                                <option value="Completed" {% if request.args.get('status_filter', 'Completed') == 'Completed' %}selected{% endif %}>Completed</option>
                                <option value="All" {% if request.args.get('status_filter') == 'All' %}selected{% endif %}>All Statuses</option>
                                <option value="Pending" {% if request.args.get('status_filter') == 'Pending' %}selected{% endif %}>Pending</option>
                                <option value="In Progress" {% if request.args.get('status_filter') == 'In Progress' %}selected{% endif %}>In Progress</option>
                                <option value="Blocked" {% if request.args.get('status_filter') == 'Blocked' %}selected{% endif %}>Blocked</option>
                            </select>
                        </div>
                        <div class="col-md-3">
                            <label class="form-label small fw-semibold">Date Range</label>
                            <div class="input-group input-group-sm">
                                <input type="date" name="start_date" class="form-control" value="{{ request.args.get('start_date', '') }}">
                                <span class="input-group-text">to</span>
                                <input type="date" name="end_date" class="form-control" value="{{ request.args.get('end_date', '') }}">
                            </div>
                        </div>
                        <div class="col-12 d-flex justify-content-end gap-2">
                            <a href="{{ url_for('completed_tasks_archive') }}" class="btn btn-sm btn-light border">Reset Filters</a>
                            <button type="submit" class="btn btn-sm btn-primary"><i class="bi bi-funnel me-1"></i>Apply Filters</button>
                        </div>
                    </form>
                </div>
            </div>

            <div class="card shadow-sm">
                <div class="card-body p-0">
                    <div class="table-responsive">
                        <table class="table table-hover table-striped mb-0 align-middle">
                            <thead class="table-light">
                                <tr>
                                    <th>#</th>
                                    <th>Employee</th>
                                    <th>Task Title</th>
                                    <th>Project</th>
                                    <th>Assigned By</th>
                                    <th>Assigned Date</th>
                                    <th>Completion Date</th>
                                    <th>Time Taken</th>
                                    <th>Status</th>
                                    <th>Notes / Comments</th>
                                    <th class="text-end">Action</th>
                                </tr>
                            </thead>
                            <tbody>
                                {% if tasks %}
                                    {% for task in tasks %}
                                        <tr>
                                            <td><small class="text-muted">#{{ task.id }}</small></td>
                                            <td><strong>{{ task.assigned_to }}</strong></td>
                                            <td>{{ task.title }}</td>
                                            <td><span class="badge bg-secondary-subtle text-secondary border">{{ task.project }}</span></td>
                                            <td>{{ task.assigned_by }}</td>
                                            <td>{{ task.assigned_date or 'N/A' }}</td>
                                            <td>{{ task.completion_date or 'N/A' }}</td>
                                            <td><span class="badge bg-info-subtle text-info-emphasis">{{ '%.2f'|format(task.total_logged_hours or 0) }} hrs</span></td>
                                            <td>
                                                {% if task.status == 'Completed' %}
                                                    <span class="badge bg-success"><i class="bi bi-check-circle me-1"></i>Completed</span>
                                                {% elif task.status == 'In Progress' %}
                                                    <span class="badge bg-primary">In Progress</span>
                                                {% elif task.status == 'Blocked' %}
                                                    <span class="badge bg-danger">Blocked</span>
                                                {% else %}
                                                    <span class="badge bg-warning text-dark">Pending</span>
                                                {% endif %}
                                            </td>
                                            <td>
                                                <small class="text-truncate d-inline-block" style="max-width: 200px;" title="{{ task.notes_summary }}">
                                                    {{ task.notes_summary }}
                                                </small>
                                            </td>
                                            <td class="text-end">
                                                <button type="button" class="btn btn-sm btn-outline-primary" data-bs-toggle="modal" data-bs-target="#taskModal{{ task.id }}">
                                                    <i class="bi bi-eye me-1"></i>View Details
                                                </button>
                                            </td>
                                        </tr>
                                    {% endfor %}
                                {% else %}
                                    <tr>
                                        <td colspan="11" class="text-center text-muted py-4">No task records found matching the filter criteria.</td>
                                    </tr>
                                {% endif %}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </div>

        {% for task in tasks %}
        <div class="modal fade" id="taskModal{{ task.id }}" tabindex="-1" aria-labelledby="taskModalLabel{{ task.id }}" aria-hidden="true">
            <div class="modal-dialog modal-lg modal-dialog-centered">
                <div class="modal-content">
                    <div class="modal-header bg-light">
                        <h5 class="modal-title" id="taskModalLabel{{ task.id }}"><i class="bi bi-info-circle text-primary me-2"></i>Task Details #{{ task.id }}</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                    </div>
                    <div class="modal-body">
                        <div class="row g-3 mb-3">
                            <div class="col-md-8">
                                <h4 class="h5 text-primary mb-1">{{ task.title }}</h4>
                                <p class="text-muted small mb-2">Category: {{ task.task_category or 'General' }} | Project: <strong>{{ task.project }}</strong></p>
                            </div>
                            <div class="col-md-4 text-md-end">
                                <span class="badge bg-success fs-6 p-2"><i class="bi bi-check-circle me-1"></i>{{ task.status }}</span>
                            </div>
                        </div>

                        <div class="row g-3 mb-4">
                            <div class="col-md-4">
                                <div class="p-2 border rounded bg-light">
                                    <small class="text-muted d-block">Assigned To</small>
                                    <strong>{{ task.assigned_to }}</strong>
                                </div>
                            </div>
                            <div class="col-md-4">
                                <div class="p-2 border rounded bg-light">
                                    <small class="text-muted d-block">Assigned By</small>
                                    <strong>{{ task.assigned_by }}</strong>
                                </div>
                            </div>
                            <div class="col-md-4">
                                <div class="p-2 border rounded bg-light">
                                    <small class="text-muted d-block">Completed By</small>
                                    <strong>{{ task.completed_by or task.assigned_to }}</strong>
                                </div>
                            </div>
                            <div class="col-md-4">
                                <div class="p-2 border rounded bg-light">
                                    <small class="text-muted d-block">Assigned Date</small>
                                    <strong>{{ task.assigned_date or 'N/A' }}</strong>
                                </div>
                            </div>
                            <div class="col-md-4">
                                <div class="p-2 border rounded bg-light">
                                    <small class="text-muted d-block">Deadline</small>
                                    <strong>{{ task.deadline or 'N/A' }}</strong>
                                </div>
                            </div>
                            <div class="col-md-4">
                                <div class="p-2 border rounded bg-light">
                                    <small class="text-muted d-block">Completion Date</small>
                                    <strong>{{ task.completion_date or 'N/A' }}</strong>
                                </div>
                            </div>
                            <div class="col-md-4">
                                <div class="p-2 border rounded bg-light">
                                    <small class="text-muted d-block">Estimated Hours</small>
                                    <strong>{{ '%.2f'|format(task.estimated_hours or 0) }} hrs</strong>
                                </div>
                            </div>
                            <div class="col-md-4">
                                <div class="p-2 border rounded bg-light">
                                    <small class="text-muted d-block">Total Time Logged</small>
                                    <strong class="text-success">{{ '%.2f'|format(task.total_logged_hours or 0) }} hrs</strong>
                                </div>
                            </div>
                            <div class="col-md-4">
                                <div class="p-2 border rounded bg-light">
                                    <small class="text-muted d-block">Priority / Recurring</small>
                                    <strong>{{ task.priority }} {% if task.recurring_type %}({{ task.recurring_type }}){% endif %}</strong>
                                </div>
                            </div>
                        </div>

                        {% if task.description %}
                        <div class="mb-4">
                            <h6>Description / Instructions</h6>
                            <div class="p-3 bg-light border rounded small">{{ task.description }}</div>
                        </div>
                        {% endif %}

                        <div>
                            <h6>Work Notes & Time Logs</h6>
                            {% if task.logs %}
                                <ul class="list-group list-group-flush border rounded">
                                    {% for log in task.logs %}
                                        <li class="list-group-item d-flex justify-content-between align-items-start">
                                            <div>
                                                <small class="fw-semibold text-primary">{{ log.date }}</small>
                                                <p class="mb-0 small">{{ log.notes }}</p>
                                            </div>
                                            <span class="badge bg-secondary rounded-pill">{{ log.hours }} hrs</span>
                                        </li>
                                    {% endfor %}
                                </ul>
                            {% else %}
                                <div class="text-muted small">No detailed work notes logged for this task.</div>
                            {% endif %}
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary btn-sm" data-bs-dismiss="modal">Close</button>
                    </div>
                </div>
            </div>
        </div>
        {% endfor %}
        {% endblock %}
        """,
        employees=employees,
        task_projects=task_projects,
        tasks=tasks,
    )


@app.route("/admin/tasks/completed/export/csv")
@login_required
def export_completed_tasks_csv():
    import csv

    if current_user.role != "admin":
        flash("Admin access required.", "danger")
        return redirect(url_for("dashboard"))

    with get_db() as conn:
        tasks = fetch_completed_tasks_records(conn, request.args)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Task ID",
        "Employee Name",
        "Task Title",
        "Category",
        "Project",
        "Assigned By",
        "Assigned Date",
        "Completion Date",
        "Deadline",
        "Status",
        "Estimated Hours",
        "Time Taken (Hours)",
        "Notes / Comments"
    ])

    for t in tasks:
        writer.writerow([
            t["id"],
            t["assigned_to"],
            t["title"],
            t["task_category"] or "",
            t["project"],
            t["assigned_by"],
            t["assigned_date"] or "",
            t["completion_date"] or "",
            t["deadline"] or "",
            t["status"],
            f"{t['estimated_hours']:.2f}",
            f"{t['total_logged_hours']:.2f}",
            t["notes_summary"]
        ])

    response = Response(output.getvalue(), mimetype="text/csv")
    response.headers["Content-Disposition"] = 'attachment; filename="completed_tasks_archive.csv"'
    return response


@app.route("/admin/tasks/completed/export/excel")
@login_required
def export_completed_tasks_excel():
    if current_user.role != "admin":
        flash("Admin access required.", "danger")
        return redirect(url_for("dashboard"))

    with get_db() as conn:
        tasks = fetch_completed_tasks_records(conn, request.args)

    try:
        from openpyxl import Workbook  # type: ignore[import-untyped]
    except Exception:  # noqa: BLE001
        flash("openpyxl dependency is missing.", "danger")
        return redirect(url_for("completed_tasks_archive"))

    wb = Workbook()
    ws = wb.active
    assert ws is not None
    ws.title = "Completed Tasks Archive"

    headers = [
        "Task ID",
        "Employee Name",
        "Task Title",
        "Category",
        "Project",
        "Assigned By",
        "Assigned Date",
        "Completion Date",
        "Deadline",
        "Status",
        "Estimated Hours",
        "Time Taken (Hours)",
        "Notes / Comments"
    ]
    ws.append(headers)

    for t in tasks:
        ws.append([
            t["id"],
            t["assigned_to"],
            t["title"],
            t["task_category"] or "",
            t["project"],
            t["assigned_by"],
            t["assigned_date"] or "",
            t["completion_date"] or "",
            t["deadline"] or "",
            t["status"],
            t["estimated_hours"],
            t["total_logged_hours"],
            t["notes_summary"]
        ])

    bio = io.BytesIO()
    wb.save(bio)
    bio.seek(0)
    payload = bio.getvalue()

    headers = {
        "Content-Disposition": 'attachment; filename="completed_tasks_archive.xlsx"',
        "Content-Type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "Content-Length": str(len(payload)),
    }
    return Response(payload, headers=headers)


@app.route("/admin/tasks/completed/export/pdf")
@login_required
def export_completed_tasks_pdf():
    if current_user.role != "admin":
        flash("Admin access required.", "danger")
        return redirect(url_for("dashboard"))

    with get_db() as conn:
        tasks = fetch_completed_tasks_records(conn, request.args)

    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import landscape, letter
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Table, TableStyle
    except Exception as e:  # noqa: BLE001
        flash(f"PDF generation failed: {e}", "danger")
        return redirect(url_for("completed_tasks_archive"))

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(letter),
        rightMargin=30,
        leftMargin=30,
        topMargin=30,
        bottomMargin=30,
    )
    elements = []
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "TitleStyle",
        parent=styles["Heading1"],
        fontSize=18,
        leading=22,
        textColor=colors.HexColor("#1e293b"),
        spaceAfter=6,
    )
    subtitle_style = ParagraphStyle(
        "SubtitleStyle",
        parent=styles["Normal"],
        fontSize=10,
        textColor=colors.HexColor("#64748b"),
        spaceAfter=15,
    )
    cell_style = ParagraphStyle(
        "CellStyle",
        parent=styles["Normal"],
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#334155"),
    )
    header_style = ParagraphStyle(
        "HeaderStyle",
        parent=styles["Normal"],
        fontSize=9,
        leading=11,
        fontName="Helvetica-Bold",
        textColor=colors.white,
    )

    elements.append(Paragraph("Completed Tasks Archive Report", title_style))
    today_str = datetime.date.today().isoformat()  # noqa: DTZ011
    elements.append(Paragraph(f"Generated on {today_str} | Total Records: {len(tasks)}", subtitle_style))

    table_data = [[
        Paragraph("Employee", header_style),
        Paragraph("Task Title", header_style),
        Paragraph("Project", header_style),
        Paragraph("Assigned By", header_style),
        Paragraph("Assigned Date", header_style),
        Paragraph("Completion Date", header_style),
        Paragraph("Time Taken", header_style),
        Paragraph("Status", header_style),
        Paragraph("Notes/Comments", header_style),
    ]]

    for t in tasks:
        table_data.append([
            Paragraph(t["assigned_to"], cell_style),
            Paragraph(t["title"], cell_style),
            Paragraph(t["project"], cell_style),
            Paragraph(t["assigned_by"], cell_style),
            Paragraph(t["assigned_date"] or "N/A", cell_style),
            Paragraph(t["completion_date"] or "N/A", cell_style),
            Paragraph(f"{t['total_logged_hours']:.2f} hrs", cell_style),
            Paragraph(t["status"], cell_style),
            Paragraph(t["notes_summary"][:120], cell_style),
        ])

    col_widths = [80, 110, 80, 75, 65, 65, 55, 55, 145]
    table = Table(table_data, colWidths=col_widths, repeatRows=1)
    table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e40af")),
            ("ALIGN", (0, 0), (-1, -1), "LEFT"),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ])
    )
    elements.append(table)
    doc.build(elements)

    buffer.seek(0)
    pdf_data = buffer.getvalue()
    headers = {
        "Content-Disposition": 'attachment; filename="completed_tasks_archive.pdf"',
        "Content-Type": "application/pdf",
        "Content-Length": str(len(pdf_data)),
    }
    return Response(pdf_data, headers=headers)


@app.route("/admin")
@login_required
def admin():
    if current_user.role != "admin":
        flash("Admin access required.", "danger")
        return redirect(url_for("dashboard"))
    return redirect(url_for("admin_users"))


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
        role = request.form.get("role", "").strip()

        if not full_name or not email or not username or not role:
            message = "All fields are required."
        elif role not in {"temporary employee", "permanent employee", "employee", "user", "admin", "hr"}:
            message = "Invalid role selected."
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
                    cursor = conn.execute(
                        "INSERT INTO users (username, password_hash, role, full_name, email, force_password_change) VALUES (?, ?, ?, ?, ?, ?)",
                        (
                            username,
                            generate_password_hash(temp_password),
                            role,
                            full_name,
                            email,
                            1,
                        ),
                    )
                    new_user_id = cursor.lastrowid
                    if role in ("temporary employee", "permanent employee", "employee", "user"):
                        conn.execute(
                            "INSERT INTO employees (user_id, name) VALUES (?, ?)",
                            (new_user_id, full_name),
                        )
                    conn.commit()
                    sync_all_employee_roles(conn)
                    create_notification(
                        new_user_id,
                        "Welcome to HRMS",
                        f"Hello {full_name}, your account (@{username}) has been created.",
                        url_for("dashboard"),
                    )
                    notify_admins(
                        "New User Account Created",
                        f"Account created for {full_name} (@{username}) with role {role}.",
                        url_for("admin_users"),
                    )
                    send_welcome_email(email, full_name, username, temp_password)
                    message = f"User created successfully. Temporary password: {temp_password}"

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
                            <div class="mb-3">
                                <label class="form-label">Role</label>
                                <select class="form-select" name="role" required>
                                    <option value="temporary employee" selected>Temporary Employee</option>
                                    <option value="permanent employee">Permanent Employee</option>
                                    <option value="hr">HR</option>
                                    <option value="admin">Admin</option>
                                </select>
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
@app.route("/attendance/punch-in", methods=["POST"])
@login_required
def punch_in():
    today = datetime.datetime.now(IST).date().isoformat()
    user_id = current_user.id
    username = current_user.username
    with get_db() as conn:
        existing = conn.execute(
            "SELECT id, punch_in_time FROM attendance WHERE user_id = ? AND date = ?",
            (user_id, today),
        ).fetchone()
        if existing and existing["punch_in_time"]:
            flash("You have already punched in today.", "warning")
            return redirect(url_for("dashboard"))
        now = datetime.datetime.now(IST).isoformat()
        if existing:
            conn.execute(
                "UPDATE attendance SET punch_in_time = ? WHERE id = ?",
                (now, existing["id"]),
            )
        else:
            conn.execute(
                "INSERT INTO attendance (user_id, username, date, punch_in_time) VALUES (?, ?, ?, ?)",
                (user_id, username, today, now),
            )
        conn.commit()
    create_notification(
        current_user.id,
        "Attendance: Punched In",
        f"Punch-in recorded for today ({today}). Have a productive day!",
        url_for("dashboard"),
    )
    flash("Punch in recorded.", "success")
    return redirect(url_for("dashboard"))


@app.route("/attendance/punch-out", methods=["POST"])
@login_required
def punch_out():
    today = datetime.datetime.now(IST).date().isoformat()
    user_id = current_user.id
    now_dt = datetime.datetime.now(IST)
    now = now_dt.isoformat()
    with get_db() as conn:
        rec = conn.execute(
            "SELECT id, punch_in_time, punch_out_time FROM attendance WHERE user_id = ? AND date = ?",
            (user_id, today),
        ).fetchone()
        if not rec or not rec["punch_in_time"]:
            flash("Cannot punch out before punching in.", "danger")
            return redirect(url_for("dashboard"))
        if rec["punch_out_time"]:
            flash("You have already punched out today.", "warning")
            return redirect(url_for("dashboard"))
        # calculate total hours
        try:
            t_in = datetime.datetime.fromisoformat(rec["punch_in_time"])
            t_out = datetime.datetime.fromisoformat(now)
            delta = t_out - t_in
            total_hours = round(delta.total_seconds() / 3600, 2)
        except Exception:  # noqa: BLE001  # Total hours calculation fallback
            total_hours = None
        conn.execute(
            "UPDATE attendance SET punch_out_time = ?, total_hours = ? WHERE id = ?",
            (now, total_hours, rec["id"]),
        )
        conn.commit()

        # Check for active unfinished tasks assigned to this employee
        user_names = get_user_task_names(conn, current_user)
        emp_name = None
        emp_row = conn.execute("SELECT name FROM employees WHERE user_id = ?", (user_id,)).fetchone()
        if emp_row and emp_row["name"]:
            emp_name = emp_row["name"]
        if not emp_name:
            user_row = conn.execute("SELECT full_name FROM users WHERE id = ?", (user_id,)).fetchone()
            if user_row and user_row["full_name"]:
                emp_name = user_row["full_name"]
        if not emp_name:
            emp_name = current_user.username

        placeholders = ", ".join("?" for _ in user_names)
        active_tasks = conn.execute(
            f"SELECT id, title, project, status FROM tasks WHERE assigned_to IN ({placeholders}) AND (status IS NULL OR status != 'Completed')",
            user_names,
        ).fetchall()

        if active_tasks:
            count = len(active_tasks)
            titles = [f"'{t['title']}'" for t in active_tasks if t["title"]]
            if len(titles) <= 3:
                titles_summary = ", ".join(titles)
            else:
                titles_summary = ", ".join(titles[:3]) + f", and {len(titles) - 3} more"

            punch_out_display = now_dt.strftime("%I:%M %p")
            notif_title = "Unfinished Tasks at Punch-Out"
            notif_msg = (
                f"Employee {emp_name} punched out at {punch_out_display} with {count} active "
                f"task(s) remaining: {titles_summary}."
            )
            notify_admins(notif_title, notif_msg, url_for("task_management"))

    hrs_str = f" ({total_hours:.1f} hrs logged)" if total_hours is not None else ""
    create_notification(
        current_user.id,
        "Attendance: Punched Out",
        f"Punch-out recorded for today ({today}){hrs_str}.",
        url_for("dashboard"),
    )
    flash("Punch out recorded.", "success")
    return redirect(url_for("dashboard"))


@app.route("/logout")
@login_required
def logout():
    try:
        with get_db() as conn:
            conn.execute("UPDATE users SET last_active_at = NULL WHERE id = ?", (current_user.id,))
            conn.commit()
    except Exception as e:  # noqa: BLE001
        app.logger.debug("Failed to clear last_active_at on logout: %s", e)
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("index"))


def is_late_punch(punch_in_str):
    """Check if punch in time is strictly after LATE_PUNCH_IN_TIME (10:15 AM IST)."""
    if not punch_in_str:
        return False
    try:
        dt = datetime.datetime.fromisoformat(punch_in_str.strip())
        if dt.tzinfo is not None:
            dt = dt.astimezone(IST)
        else:
            dt = dt.replace(tzinfo=IST)
        return (dt.hour, dt.minute) > (LATE_PUNCH_IN_TIME.hour, LATE_PUNCH_IN_TIME.minute)
    except Exception:  # noqa: BLE001
        return False


def is_half_day_punch(punch_out_str):
    """Check if punch out time is strictly before HALF_DAY_PUNCH_OUT_TIME (3:00 PM IST). Returns False if no punch-out."""
    if not punch_out_str:
        return False
    try:
        dt = datetime.datetime.fromisoformat(punch_out_str.strip())
        if dt.tzinfo is not None:
            dt = dt.astimezone(IST)
        else:
            dt = dt.replace(tzinfo=IST)
        return (dt.hour, dt.minute) < (HALF_DAY_PUNCH_OUT_TIME.hour, HALF_DAY_PUNCH_OUT_TIME.minute)
    except Exception:  # noqa: BLE001
        return False


def get_monthly_attendance_calendar_data(year, month, target_user_id):
    """Calculate and return monthly attendance calendar days, statistics, late arrivals, and modal metadata."""
    num_days = calendar.monthrange(year, month)[1]
    first_weekday = calendar.monthrange(year, month)[0]  # 0 = Monday ... 6 = Sunday
    start_date_str = f"{year:04d}-{month:02d}-01"
    end_date_str = f"{year:04d}-{month:02d}-{num_days:02d}"
    today_str = datetime.datetime.now(tz=IST).date().isoformat()

    with get_db() as conn:
        user_info = conn.execute(
            "SELECT id, username, full_name FROM users WHERE id = ?", (target_user_id,)
        ).fetchone()

        emp_info = conn.execute(
            "SELECT name, department FROM employees WHERE user_id = ?", (target_user_id,)
        ).fetchone()

        att_rows = conn.execute(
            "SELECT date, punch_in_time, punch_out_time, total_hours FROM attendance WHERE user_id = ? AND date >= ? AND date <= ?",
            (target_user_id, start_date_str, end_date_str),
        ).fetchall()
        att_dict = {r["date"]: r for r in att_rows}

        leave_rows = conn.execute(
            "SELECT leave_type, start_date, end_date, status, reason FROM leave_requests WHERE user_id = ? AND status IN ('Approved', 'Pending') AND start_date <= ? AND end_date >= ?",
            (target_user_id, end_date_str, start_date_str),
        ).fetchall()

        holiday_rows = conn.execute(
            "SELECT date, title, description, holiday_type, is_paid FROM holidays WHERE date >= ? AND date <= ?",
            (start_date_str, end_date_str),
        ).fetchall()
        holiday_dict = {r["date"]: r for r in holiday_rows}

    def get_leave_for_date(d_str):
        for l in leave_rows:
            if l["start_date"] <= d_str <= l["end_date"]:
                return l
        return None

    days_list = []
    present_count = 0
    absent_count = 0
    leave_count = 0
    holiday_count = 0
    late_count = 0
    half_day_count = 0
    total_hours_sum = 0.0

    for day in range(1, num_days + 1):
        d_obj = datetime.date(year, month, day)
        d_str = d_obj.isoformat()
        weekday = d_obj.weekday()  # 0=Mon, 5=Sat, 6=Sun
        is_weekend = (weekday == 6)

        att_entry = att_dict.get(d_str)
        leave_entry = get_leave_for_date(d_str)
        holiday_entry = holiday_dict.get(d_str)

        status = "Future"
        status_code = "F"
        status_label = "Upcoming"
        badge_class = "bg-light text-muted border"
        is_late = False
        is_half_day = False

        if att_entry and att_entry["punch_in_time"]:
            status = "Present"
            status_code = "P"
            status_label = "Present"
            badge_class = "bg-success text-white"
            present_count += 1
            if is_late_punch(att_entry["punch_in_time"]):
                is_late = True
                late_count += 1
            if is_half_day_punch(att_entry["punch_out_time"]):
                is_half_day = True
                half_day_count += 1
            if att_entry["total_hours"]:
                try:
                    total_hours_sum += float(att_entry["total_hours"])
                except (ValueError, TypeError):
                    pass
        elif holiday_entry:
            status = "Holiday"
            status_code = "H"
            status_label = f"Holiday ({holiday_entry['title']})"
            badge_class = "bg-primary text-white"
            holiday_count += 1
        elif leave_entry and leave_entry["status"] == "Approved":
            status = "Leave"
            status_code = "L"
            status_label = f"Leave ({leave_entry['leave_type']})"
            badge_class = "bg-warning text-dark"
            leave_count += 1
        elif leave_entry and leave_entry["status"] == "Pending":
            status = "Pending Leave"
            status_code = "PL"
            status_label = f"Pending Leave ({leave_entry['leave_type']})"
            badge_class = "bg-warning bg-opacity-50 text-dark"
            leave_count += 1
        elif is_weekend:
            status = "Weekend"
            status_code = "W"
            status_label = "Weekend"
            badge_class = "bg-secondary text-white opacity-75"
            holiday_count += 1
        elif d_str <= today_str:
            status = "Absent"
            status_code = "A"
            status_label = "Absent"
            badge_class = "bg-danger text-white"
            absent_count += 1

        # Format timestamps for date click modal popup
        in_fmt = format_attendance_timestamp(att_entry["punch_in_time"]) if att_entry else "-"
        out_fmt = format_attendance_timestamp(att_entry["punch_out_time"]) if att_entry else "-"
        hrs_fmt = (
            f"{att_entry['total_hours']} Hours"
            if att_entry and att_entry["total_hours"]
            else (
                "Active Session"
                if att_entry and att_entry["punch_in_time"] and not att_entry["punch_out_time"]
                else "-"
            )
        )

        notes_txt = ""
        if holiday_entry:
            h_dict = dict(holiday_entry)
            h_type = h_dict.get("holiday_type") or "Public Holiday"
            h_paid = "Paid" if (h_dict.get("is_paid") in (1, "1", "Yes")) else "Unpaid"
            h_desc = h_dict.get("description") or ""
            desc = f" - {h_desc}" if h_desc else ""
            notes_txt = f"Holiday: {h_dict.get('title', 'Holiday')} ({h_type}, {h_paid}){desc}"
        elif leave_entry:
            notes_txt = f"Leave Reason: {leave_entry['reason'] or leave_entry['leave_type']}"

        days_list.append(
            {
                "day": day,
                "date": d_str,
                "date_formatted": d_obj.strftime("%d %b %Y"),
                "weekday_name": d_obj.strftime("%A"),
                "is_weekend": is_weekend,
                "is_today": (d_str == today_str),
                "status": status,
                "status_code": status_code,
                "status_label": status_label,
                "badge_class": badge_class,
                "is_late": is_late,
                "is_half_day": is_half_day,
                "punch_in": att_entry["punch_in_time"] if att_entry else None,
                "punch_in_fmt": in_fmt,
                "punch_out": att_entry["punch_out_time"] if att_entry else None,
                "punch_out_fmt": out_fmt,
                "total_hours": att_entry["total_hours"] if att_entry else None,
                "total_hours_fmt": hrs_fmt,
                "leave_type": leave_entry["leave_type"] if leave_entry else None,
                "holiday_name": dict(holiday_entry).get("title") if holiday_entry else None,
                "holiday_type": dict(holiday_entry).get("holiday_type", "Public Holiday") if holiday_entry else None,
                "is_paid": ("Paid" if dict(holiday_entry).get("is_paid") in (1, "1", "Yes") else "Unpaid") if holiday_entry else None,
                "notes": notes_txt,
            }
        )

    month_date = datetime.date(year, month, 1)
    month_name = month_date.strftime("%B")
    prev_month_date = (month_date - datetime.timedelta(days=1)).replace(day=1)
    next_month_date = (month_date + datetime.timedelta(days=32)).replace(day=1)

    display_name = (
        (emp_info["name"] if emp_info and emp_info["name"] else None)
        or (user_info["full_name"] if user_info and user_info["full_name"] else None)
        or (user_info["username"] if user_info else "Employee")
    )

    tot_workdays = present_count + absent_count
    attendance_rate = (
        round((present_count / tot_workdays * 100), 1) if tot_workdays > 0 else 0.0
    )

    return {
        "user_id": target_user_id,
        "display_name": display_name,
        "department": (emp_info["department"] if emp_info else "General") or "General",
        "year": year,
        "month": month,
        "month_name": month_name,
        "prev_year": prev_month_date.year,
        "prev_month": prev_month_date.month,
        "next_year": next_month_date.year,
        "next_month": next_month_date.month,
        "num_days": num_days,
        "first_weekday": first_weekday,
        "days": days_list,
        "stats": {
            "present_count": present_count,
            "absent_count": absent_count,
            "leave_count": leave_count,
            "holiday_count": holiday_count,
            "late_count": late_count,
            "half_day_count": half_day_count,
            "total_hours": round(total_hours_sum, 2),
            "attendance_rate": attendance_rate,
        },
    }


def get_admin_monthly_matrix_data(year, month):
    """Returns company-wide monthly attendance summary matrix for all active employees."""
    num_days = calendar.monthrange(year, month)[1]
    with get_db() as conn:
        user_rows = conn.execute(
            """
            SELECT u.id as user_id, u.username, u.full_name, e.name as emp_name, e.department
            FROM users u
            LEFT JOIN employees e ON u.id = e.user_id
            WHERE u.role != 'disabled'
            ORDER BY COALESCE(e.name, u.full_name, u.username) ASC
            """
        ).fetchall()

    matrix_employees = []
    tot_pres = 0
    tot_abs = 0
    tot_leaves = 0
    tot_lates = 0
    tot_half_days = 0

    for u in user_rows:
        cal = get_monthly_attendance_calendar_data(year, month, u["user_id"])
        matrix_employees.append(
            {
                "user_id": u["user_id"],
                "name": u["emp_name"] or u["full_name"] or u["username"],
                "username": u["username"],
                "department": u["department"] or "General",
                "days": cal["days"],
                "stats": cal["stats"],
            }
        )
        tot_pres += cal["stats"]["present_count"]
        tot_abs += cal["stats"]["absent_count"]
        tot_leaves += cal["stats"]["leave_count"]
        tot_lates += cal["stats"]["late_count"]
        tot_half_days += cal["stats"]["half_day_count"]

    tot_workdays = tot_pres + tot_abs
    avg_rate = (
        round((tot_pres / tot_workdays * 100), 1) if tot_workdays > 0 else 0.0
    )

    month_date = datetime.date(year, month, 1)
    month_name = month_date.strftime("%B")
    prev_m = (month_date - datetime.timedelta(days=1)).replace(day=1)
    next_m = (month_date + datetime.timedelta(days=32)).replace(day=1)

    return {
        "year": year,
        "month": month,
        "month_name": month_name,
        "prev_year": prev_m.year,
        "prev_month": prev_m.month,
        "next_year": next_m.year,
        "next_month": next_m.month,
        "num_days": num_days,
        "day_numbers": list(range(1, num_days + 1)),
        "employees": matrix_employees,
        "summary": {
            "total_employees": len(matrix_employees),
            "total_present": tot_pres,
            "total_absent": tot_abs,
            "total_leaves": tot_leaves,
            "total_lates": tot_lates,
            "total_half_days": tot_half_days,
            "avg_attendance_rate": avg_rate,
        },
    }


@app.route("/attendance/calendar")
@login_required
def employee_attendance_calendar():
    """Employee Attendance Calendar View"""
    today = datetime.datetime.now(tz=IST).date()
    year = request.args.get("year", type=int, default=today.year)
    month = request.args.get("month", type=int, default=today.month)

    # Permission Guard: Employees can ONLY view their own attendance
    if current_user.role != "admin":
        target_user_id = current_user.id
    else:
        target_user_id = request.args.get("user_id", type=int, default=current_user.id)

    # Sanitize month and year
    if month < 1 or month > 12:
        month = today.month
    if year < 2000 or year > 2100:
        year = today.year

    cal_data = get_monthly_attendance_calendar_data(year, month, target_user_id)

    return render_template_string(
        """
        {% extends "base.html" %}
        {% block title %}My Attendance Calendar{% endblock %}
        {% block page_content %}
        <div class="page-header d-flex flex-wrap justify-content-between align-items-center gap-3 mb-4">
            <div>
                <h1 class="h3 mb-1"><i class="bi bi-calendar3 me-2 text-primary"></i>My Attendance Calendar</h1>
                <p class="text-muted mb-0">Track your daily punch logs, leaves, holidays, and monthly work statistics.</p>
            </div>
            <div class="d-flex align-items-center gap-2">
                <a href="{{ url_for('employee_attendance_calendar', year=cal_data.prev_year, month=cal_data.prev_month) }}" class="btn btn-outline-secondary btn-sm" title="Previous Month">
                    <i class="bi bi-chevron-left"></i> Prev
                </a>
                <span class="fw-bold px-3 py-1 bg-white border rounded shadow-sm text-dark">{{ cal_data.month_name }} {{ cal_data.year }}</span>
                <a href="{{ url_for('employee_attendance_calendar', year=cal_data.next_year, month=cal_data.next_month) }}" class="btn btn-outline-secondary btn-sm" title="Next Month">
                    Next <i class="bi bi-chevron-right"></i>
                </a>
                <a href="{{ url_for('employee_attendance_calendar', year=today_year, month=today_month) }}" class="btn btn-primary btn-sm ms-2">
                    <i class="bi bi-clock-history me-1"></i>Today
                </a>
            </div>
        </div>

        <!-- 5 Summary Widgets -->
        <div class="row g-3 mb-4">
            <div class="col-6 col-md-4 col-lg flex-fill">
                <div class="card shadow-sm border-0 border-start border-4 border-success h-100">
                    <div class="card-body p-3 text-center">
                        <div class="text-muted small fw-bold mb-1"><i class="bi bi-check-circle me-1 text-success"></i>PRESENT DAYS</div>
                        <div class="display-6 fw-bold text-success">{{ cal_data.stats.present_count }}</div>
                    </div>
                </div>
            </div>
            <div class="col-6 col-md-4 col-lg flex-fill">
                <div class="card shadow-sm border-0 border-start border-4 border-danger h-100">
                    <div class="card-body p-3 text-center">
                        <div class="text-muted small fw-bold mb-1"><i class="bi bi-x-circle me-1 text-danger"></i>ABSENT DAYS</div>
                        <div class="display-6 fw-bold text-danger">{{ cal_data.stats.absent_count }}</div>
                    </div>
                </div>
            </div>
            <div class="col-6 col-md-4 col-lg flex-fill">
                <div class="card shadow-sm border-0 border-start border-4 border-warning h-100">
                    <div class="card-body p-3 text-center">
                        <div class="text-muted small fw-bold mb-1"><i class="bi bi-calendar-minus me-1 text-warning"></i>LEAVE DAYS</div>
                        <div class="display-6 fw-bold text-warning">{{ cal_data.stats.leave_count }}</div>
                    </div>
                </div>
            </div>
            <div class="col-6 col-md-4 col-lg flex-fill">
                <div class="card shadow-sm border-0 border-start border-4 border-orange h-100" style="border-left-color: #f97316 !important;">
                    <div class="card-body p-3 text-center">
                        <div class="text-muted small fw-bold mb-1" style="color: #f97316;"><i class="bi bi-alarm me-1"></i>LATE ARRIVALS</div>
                        <div class="display-6 fw-bold" style="color: #f97316;">{{ cal_data.stats.late_count }}</div>
                    </div>
                </div>
            </div>
            <div class="col-6 col-md-4 col-lg flex-fill">
                <div class="card shadow-sm border-0 border-start border-4 border-info h-100">
                    <div class="card-body p-3 text-center">
                        <div class="text-muted small fw-bold mb-1"><i class="bi bi-hourglass-split me-1 text-info"></i>HALF DAYS</div>
                        <div class="display-6 fw-bold text-info">{{ cal_data.stats.half_day_count }}</div>
                    </div>
                </div>
            </div>
            <div class="col-6 col-md-4 col-lg flex-fill">
                <div class="card shadow-sm border-0 border-start border-4 border-primary h-100">
                    <div class="card-body p-3 text-center">
                        <div class="text-muted small fw-bold mb-1"><i class="bi bi-graph-up me-1 text-primary"></i>ATTENDANCE %</div>
                        <div class="display-6 fw-bold text-primary">{{ cal_data.stats.attendance_rate }}%</div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Color Legend Bar & Calendar Container -->
        <div class="card shadow-sm border-0 mb-4">
            <div class="card-header bg-white py-3 border-0 d-flex justify-content-between align-items-center flex-wrap gap-2">
                <h5 class="card-title mb-0 fw-bold"><i class="bi bi-grid-3x3-gap me-2 text-primary"></i>Month Grid View</h5>
                <div class="d-flex gap-3 flex-wrap align-items-center text-muted small">
                    <span class="fw-bold me-1 text-dark">Color Legend:</span>
                    <span><span class="badge bg-success p-2 me-1">Green</span> Present</span>
                    <span><span class="badge bg-danger p-2 me-1">Red</span> Absent</span>
                    <span><span class="badge bg-warning text-dark p-2 me-1">Yellow</span> Leave</span>
                    <span><span class="badge bg-primary p-2 me-1">Blue</span> Holiday</span>
                    <span><span class="badge bg-secondary p-2 me-1">Gray</span> Weekend</span>
                </div>
            </div>
            <div class="card-body p-3">
                <div class="attendance-calendar-grid">
                    <!-- Weekday Headers -->
                    <div class="calendar-weekday-header">Mon</div>
                    <div class="calendar-weekday-header">Tue</div>
                    <div class="calendar-weekday-header">Wed</div>
                    <div class="calendar-weekday-header">Thu</div>
                    <div class="calendar-weekday-header">Fri</div>
                    <div class="calendar-weekday-header">Sat</div>
                    <div class="calendar-weekday-header text-danger">Sun</div>

                    <!-- Offset Empty Cells -->
                    {% for _ in range(cal_data.first_weekday) %}
                        <div class="calendar-day-cell empty"></div>
                    {% endfor %}

                    <!-- Days of Month -->
                    {% for d in cal_data.days %}
                        <div class="calendar-day-cell {% if d.is_today %}today-cell{% endif %} {% if d.is_weekend %}weekend-cell{% endif %} clickable-day-cell"
                             onclick="openAttendanceModal(this)"
                             data-date="{{ d.date_formatted }}"
                             data-weekday="{{ d.weekday_name }}"
                             data-status="{{ d.status }}"
                             data-badge="{{ d.badge_class }}"
                             data-punchin="{{ d.punch_in_fmt }}"
                             data-punchout="{{ d.punch_out_fmt }}"
                             data-hours="{{ d.total_hours_fmt }}"
                             data-late="{{ '1' if d.is_late else '0' }}"
                             data-halfday="{{ '1' if d.is_half_day else '0' }}"
                             data-notes="{{ d.notes }}">
                            <div class="day-header d-flex justify-content-between align-items-center mb-2">
                                <span class="day-number {% if d.is_today %}badge bg-primary rounded-pill px-2 py-1{% else %}fw-bold{% endif %}">{{ d.day }}</span>
                                <span class="badge {{ d.badge_class }} small-badge">{{ d.status }}</span>
                            </div>
                            <div class="day-body small">
                                {% if d.status == 'Present' %}
                                    <div class="text-success fw-semibold"><i class="bi bi-clock me-1"></i>In: {{ d.punch_in_fmt }}</div>
                                    {% if d.is_late %}
                                        <span class="badge bg-warning text-dark border style-badge mt-1"><i class="bi bi-alarm me-1"></i>Late</span>
                                    {% endif %}
                                    {% if d.is_half_day %}
                                        <span class="badge bg-info text-dark border style-badge mt-1"><i class="bi bi-hourglass-split me-1"></i>Half Day</span>
                                    {% endif %}
                                    {% if d.total_hours %}
                                        <div class="badge bg-light text-dark border mt-1"><i class="bi bi-hourglass me-1"></i>{{ d.total_hours }} hrs</div>
                                    {% endif %}
                                {% elif d.status == 'Leave' or d.status == 'Pending Leave' %}
                                    <div class="text-warning fw-semibold"><i class="bi bi-calendar-range me-1"></i>{{ d.leave_type or 'Leave' }}</div>
                                {% elif d.status == 'Holiday' %}
                                    <div class="text-primary fw-semibold"><i class="bi bi-gift me-1"></i>{{ d.holiday_name }}</div>
                                {% elif d.status == 'Weekend' %}
                                    <div class="text-muted italic"><i class="bi bi-cup-hot me-1"></i>Weekend</div>
                                {% elif d.status == 'Absent' %}
                                    <div class="text-danger"><i class="bi bi-exclamation-octagon me-1"></i>No Log</div>
                                {% else %}
                                    <div class="text-muted opacity-50">-</div>
                                {% endif %}
                            </div>
                        </div>
                    {% endfor %}
                </div>
            </div>
        </div>

        <!-- Date Detail Modal Popup -->
        <div class="modal fade" id="attendanceDayModal" tabindex="-1" aria-hidden="true">
            <div class="modal-dialog modal-dialog-centered">
                <div class="modal-content shadow-lg border-0 rounded-4">
                    <div class="modal-header bg-light py-3 border-bottom">
                        <h5 class="modal-header-title mb-0 fw-bold">
                            <i class="bi bi-calendar-event me-2 text-primary"></i><span id="modalDateTitle">Date Details</span>
                        </h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                    </div>
                    <div class="modal-body p-4">
                        <div class="d-flex justify-content-between align-items-center mb-4 p-3 bg-light rounded border">
                            <div>
                                <span class="text-muted small d-block">WEEKDAY</span>
                                <h4 class="fw-bold mb-0 text-dark" id="modalWeekday">Monday</h4>
                            </div>
                            <span id="modalStatusBadge" class="badge fs-6 px-3 py-2">Present</span>
                        </div>

                        <div id="modalLateAlert" class="alert alert-warning py-2 mb-3 d-none">
                            <i class="bi bi-exclamation-triangle-fill me-2"></i><strong>Late Arrival:</strong> Punched in after 10:15 AM IST.
                        </div>
                        <div id="modalHalfDayAlert" class="alert alert-info py-2 mb-3 d-none">
                            <i class="bi bi-clock-history me-2"></i><strong>Half Day:</strong> Punched out before 3:00 PM IST.
                        </div>

                        <div class="row g-3 text-center mb-3">
                            <div class="col-6">
                                <div class="p-3 border rounded bg-white shadow-sm">
                                    <i class="bi bi-box-arrow-in-right fs-4 text-success d-block mb-1"></i>
                                    <span class="text-muted small d-block">CHECK IN</span>
                                    <strong id="modalPunchIn" class="fs-6 text-dark">-</strong>
                                </div>
                            </div>
                            <div class="col-6">
                                <div class="p-3 border rounded bg-white shadow-sm">
                                    <i class="bi bi-box-arrow-right fs-4 text-danger d-block mb-1"></i>
                                    <span class="text-muted small d-block">CHECK OUT</span>
                                    <strong id="modalPunchOut" class="fs-6 text-dark">-</strong>
                                </div>
                            </div>
                        </div>

                        <div class="p-3 border rounded bg-light mb-3 text-center">
                            <span class="text-muted small d-block mb-1">TOTAL LOGGED HOURS</span>
                            <h3 id="modalHours" class="fw-bold text-primary mb-0">0 Hours</h3>
                        </div>

                        <div id="modalNotesContainer" class="p-3 bg-white border rounded d-none">
                            <span class="text-muted small d-block fw-bold mb-1">NOTES / DETAILS</span>
                            <p id="modalNotesText" class="mb-0 small text-dark"></p>
                        </div>
                    </div>
                    <div class="modal-footer bg-light border-0 py-2">
                        <button type="button" class="btn btn-secondary btn-sm px-4" data-bs-dismiss="modal">Close</button>
                    </div>
                </div>
            </div>
        </div>

        <script>
        function openAttendanceModal(el) {
            var date = el.getAttribute('data-date');
            var weekday = el.getAttribute('data-weekday');
            var status = el.getAttribute('data-status');
            var badgeClass = el.getAttribute('data-badge');
            var punchIn = el.getAttribute('data-punchin');
            var punchOut = el.getAttribute('data-punchout');
            var hours = el.getAttribute('data-hours');
            var isLate = el.getAttribute('data-late') === '1';
            var isHalfDay = el.getAttribute('data-halfday') === '1';
            var notes = el.getAttribute('data-notes');

            document.getElementById('modalDateTitle').innerText = date;
            document.getElementById('modalWeekday').innerText = weekday;
            
            var badgeEl = document.getElementById('modalStatusBadge');
            badgeEl.className = 'badge fs-6 px-3 py-2 ' + badgeClass;
            badgeEl.innerText = status;

            document.getElementById('modalPunchIn').innerText = punchIn;
            document.getElementById('modalPunchOut').innerText = punchOut;
            document.getElementById('modalHours').innerText = hours;

            var lateAlert = document.getElementById('modalLateAlert');
            if (isLate) {
                lateAlert.classList.remove('d-none');
            } else {
                lateAlert.classList.add('d-none');
            }

            var halfDayAlert = document.getElementById('modalHalfDayAlert');
            if (halfDayAlert) {
                if (isHalfDay) {
                    halfDayAlert.classList.remove('d-none');
                } else {
                    halfDayAlert.classList.add('d-none');
                }
            }

            var notesContainer = document.getElementById('modalNotesContainer');
            var notesText = document.getElementById('modalNotesText');
            if (notes && notes.trim() !== '') {
                notesText.innerText = notes;
                notesContainer.classList.remove('d-none');
            } else {
                notesContainer.classList.add('d-none');
            }

            var myModal = new bootstrap.Modal(document.getElementById('attendanceDayModal'));
            myModal.show();
        }
        </script>
        {% endblock %}
        """,
        cal_data=cal_data,
        today_year=today.year,
        today_month=today.month,
    )


@app.route("/admin/attendance")
@app.route("/admin/attendance/calendar")
@login_required
def admin_attendance():
    """Admin Attendance Calendar & Monthly Report Dashboard"""
    if current_user.role not in ("admin", "hr"):
        flash("Access denied.", "danger")
        return redirect(url_for("dashboard"))

    today = datetime.datetime.now(tz=IST).date()
    year = request.args.get("year", type=int, default=today.year)
    month = request.args.get("month", type=int, default=today.month)
    selected_user_id = request.args.get("user_id", type=str, default="all").strip()

    if month < 1 or month > 12:
        month = today.month
    if year < 2000 or year > 2100:
        year = today.year

    with get_db() as conn:
        employees_list = conn.execute(
            """
            SELECT u.id as user_id, u.username, u.full_name, e.name as emp_name, e.department
            FROM users u
            LEFT JOIN employees e ON u.id = e.user_id
            WHERE u.role != 'disabled'
            ORDER BY COALESCE(e.name, u.full_name, u.username) ASC
            """
        ).fetchall()

    # Determine if single employee or company matrix
    single_cal_data = None
    matrix_data = None

    if selected_user_id != "all" and selected_user_id.isdigit():
        target_uid = int(selected_user_id)
        single_cal_data = get_monthly_attendance_calendar_data(year, month, target_uid)
    else:
        matrix_data = get_admin_monthly_matrix_data(year, month)

    return render_template_string(
        """
        {% extends "base.html" %}
        {% block title %}Admin Attendance Calendar & Reports{% endblock %}
        {% block page_content %}
        <div class="page-header d-flex flex-wrap justify-content-between align-items-center gap-3 mb-4">
            <div>
                <h1 class="h3 mb-1"><i class="bi bi-calendar-check me-2 text-primary"></i>Attendance Calendar & Monthly Report</h1>
                <p class="text-muted mb-0">Overview employee attendance calendars, status matrix, and export monthly records.</p>
            </div>
            <div class="d-flex gap-2 flex-wrap">
                <a class="btn btn-success" href="{{ url_for('download_attendance') }}">
                    <i class="bi bi-file-earmark-spreadsheet me-1"></i>Download Excel Report
                </a>
                <a class="btn btn-outline-secondary" href="{{ url_for('reports_attendance') }}">
                    <i class="bi bi-bar-chart-line me-1"></i>Attendance Analytics
                </a>
            </div>
        </div>

        <!-- Filter Toolbar -->
        <div class="card shadow-sm border-0 mb-4">
            <div class="card-body py-3">
                <form method="GET" action="{{ url_for('admin_attendance') }}" class="row g-3 align-items-end">
                    <div class="col-md-4 col-lg-4">
                        <label class="form-label small fw-bold text-muted mb-1"><i class="bi bi-person me-1"></i>Select Employee</label>
                        <select name="user_id" class="form-select form-select-sm" onchange="this.form.submit()">
                            <option value="all" {% if selected_user_id == 'all' %}selected{% endif %}>-- All Employees (Monthly Summary Matrix) --</option>
                            {% for emp in employees_list %}
                                {% set label_name = emp.emp_name or emp.full_name or emp.username %}
                                <option value="{{ emp.user_id }}" {% if selected_user_id == emp.user_id|string %}selected{% endif %}>{{ label_name }} ({{ emp.department or 'General' }})</option>
                            {% endfor %}
                        </select>
                    </div>
                    <div class="col-6 col-md-3 col-lg-2">
                        <label class="form-label small fw-bold text-muted mb-1"><i class="bi bi-calendar-month me-1"></i>Month</label>
                        <select name="month" class="form-select form-select-sm" onchange="this.form.submit()">
                            {% for m in range(1, 13) %}
                                <option value="{{ m }}" {% if month == m %}selected{% endif %}>{{ m | month_name_filter }}</option>
                            {% endfor %}
                        </select>
                    </div>
                    <div class="col-6 col-md-3 col-lg-2">
                        <label class="form-label small fw-bold text-muted mb-1"><i class="bi bi-calendar-event me-1"></i>Year</label>
                        <select name="year" class="form-select form-select-sm" onchange="this.form.submit()">
                            {% set start_yr = today_year - 5 %}
                            {% set end_yr = (year + 5) if (year + 5) > (today_year + 10) else (today_year + 10) %}
                            {% for y in range(start_yr, end_yr + 1) %}
                                <option value="{{ y }}" {% if year == y %}selected{% endif %}>{{ y }}</option>
                            {% endfor %}
                        </select>
                    </div>
                    <div class="col-md-2 col-lg-2 d-flex gap-2">
                        <button type="submit" class="btn btn-primary btn-sm w-100"><i class="bi bi-filter me-1"></i>Apply</button>
                        {% if selected_user_id != 'all' or month != today_month or year != today_year %}
                            <a href="{{ url_for('admin_attendance') }}" class="btn btn-outline-secondary btn-sm" title="Reset Filters"><i class="bi bi-arrow-counterclockwise"></i></a>
                        {% endif %}
                    </div>
                </form>
            </div>
        </div>

        {% if single_cal_data %}
            <!-- Single Employee Detailed Calendar View -->
            <div class="alert alert-info d-flex justify-content-between align-items-center py-2 px-3 mb-4 shadow-sm">
                <div>
                    <i class="bi bi-person-bounding-box me-2 fs-5"></i>
                    Viewing Attendance Calendar for <strong>{{ single_cal_data.display_name }}</strong> ({{ single_cal_data.department }}) - <strong>{{ single_cal_data.month_name }} {{ single_cal_data.year }}</strong>
                </div>
                <a href="{{ url_for('admin_attendance', year=year, month=month, user_id='all') }}" class="btn btn-outline-info btn-sm bg-white text-dark">
                    <i class="bi bi-grid-3x3 me-1"></i>View All Employees Matrix
                </a>
            </div>

            <!-- 5 Summary Widgets for Selected Employee -->
            <div class="row g-3 mb-4">
                <div class="col-6 col-md-4 col-lg flex-fill">
                    <div class="card shadow-sm border-0 border-start border-4 border-success h-100">
                        <div class="card-body p-3 text-center">
                            <div class="text-muted small fw-bold mb-1"><i class="bi bi-check-circle me-1 text-success"></i>PRESENT DAYS</div>
                            <div class="display-6 fw-bold text-success">{{ single_cal_data.stats.present_count }}</div>
                        </div>
                    </div>
                </div>
                <div class="col-6 col-md-4 col-lg flex-fill">
                    <div class="card shadow-sm border-0 border-start border-4 border-danger h-100">
                        <div class="card-body p-3 text-center">
                            <div class="text-muted small fw-bold mb-1"><i class="bi bi-x-circle me-1 text-danger"></i>ABSENT DAYS</div>
                            <div class="display-6 fw-bold text-danger">{{ single_cal_data.stats.absent_count }}</div>
                        </div>
                    </div>
                </div>
                <div class="col-6 col-md-4 col-lg flex-fill">
                    <div class="card shadow-sm border-0 border-start border-4 border-warning h-100">
                        <div class="card-body p-3 text-center">
                            <div class="text-muted small fw-bold mb-1"><i class="bi bi-calendar-minus me-1 text-warning"></i>LEAVE DAYS</div>
                            <div class="display-6 fw-bold text-warning">{{ single_cal_data.stats.leave_count }}</div>
                        </div>
                    </div>
                </div>
                <div class="col-6 col-md-4 col-lg flex-fill">
                    <div class="card shadow-sm border-0 border-start border-4 border-orange h-100" style="border-left-color: #f97316 !important;">
                        <div class="card-body p-3 text-center">
                            <div class="text-muted small fw-bold mb-1" style="color: #f97316;"><i class="bi bi-alarm me-1"></i>LATE ARRIVALS</div>
                            <div class="display-6 fw-bold" style="color: #f97316;">{{ single_cal_data.stats.late_count }}</div>
                        </div>
                    </div>
                </div>
                <div class="col-6 col-md-4 col-lg flex-fill">
                    <div class="card shadow-sm border-0 border-start border-4 border-info h-100">
                        <div class="card-body p-3 text-center">
                            <div class="text-muted small fw-bold mb-1"><i class="bi bi-hourglass-split me-1 text-info"></i>HALF DAYS</div>
                            <div class="display-6 fw-bold text-info">{{ single_cal_data.stats.half_day_count }}</div>
                        </div>
                    </div>
                </div>
                <div class="col-6 col-md-4 col-lg flex-fill">
                    <div class="card shadow-sm border-0 border-start border-4 border-primary h-100">
                        <div class="card-body p-3 text-center">
                            <div class="text-muted small fw-bold mb-1"><i class="bi bi-graph-up me-1 text-primary"></i>ATTENDANCE %</div>
                            <div class="display-6 fw-bold text-primary">{{ single_cal_data.stats.attendance_rate }}%</div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Calendar Grid Container -->
            <div class="card shadow-sm border-0 mb-4">
                <div class="card-header bg-white py-3 border-0 d-flex justify-content-between align-items-center flex-wrap gap-2">
                    <h5 class="card-title mb-0 fw-bold"><i class="bi bi-grid-3x3-gap me-2 text-primary"></i>Month Grid View</h5>
                    <div class="d-flex gap-3 flex-wrap align-items-center text-muted small">
                        <span class="fw-bold me-1 text-dark">Color Legend:</span>
                        <span><span class="badge bg-success p-2 me-1">Green</span> Present</span>
                        <span><span class="badge bg-danger p-2 me-1">Red</span> Absent</span>
                        <span><span class="badge bg-warning text-dark p-2 me-1">Yellow</span> Leave</span>
                        <span><span class="badge bg-primary p-2 me-1">Blue</span> Holiday</span>
                        <span><span class="badge bg-secondary p-2 me-1">Gray</span> Weekend</span>
                    </div>
                </div>
                <div class="card-body p-3">
                    <div class="attendance-calendar-grid">
                        <div class="calendar-weekday-header">Mon</div>
                        <div class="calendar-weekday-header">Tue</div>
                        <div class="calendar-weekday-header">Wed</div>
                        <div class="calendar-weekday-header">Thu</div>
                        <div class="calendar-weekday-header">Fri</div>
                        <div class="calendar-weekday-header">Sat</div>
                        <div class="calendar-weekday-header text-danger">Sun</div>

                        {% for _ in range(single_cal_data.first_weekday) %}
                            <div class="calendar-day-cell empty"></div>
                        {% endfor %}

                        {% for d in single_cal_data.days %}
                            <div class="calendar-day-cell {% if d.is_today %}today-cell{% endif %} {% if d.is_weekend %}weekend-cell{% endif %} clickable-day-cell"
                                 onclick="openAttendanceModal(this)"
                                 data-date="{{ d.date_formatted }}"
                                 data-weekday="{{ d.weekday_name }}"
                                 data-status="{{ d.status }}"
                                 data-badge="{{ d.badge_class }}"
                                 data-punchin="{{ d.punch_in_fmt }}"
                                 data-punchout="{{ d.punch_out_fmt }}"
                                 data-hours="{{ d.total_hours_fmt }}"
                                 data-late="{{ '1' if d.is_late else '0' }}"
                                 data-halfday="{{ '1' if d.is_half_day else '0' }}"
                                 data-notes="{{ d.notes }}">
                                <div class="day-header d-flex justify-content-between align-items-center mb-2">
                                    <span class="day-number {% if d.is_today %}badge bg-primary rounded-pill px-2 py-1{% else %}fw-bold{% endif %}">{{ d.day }}</span>
                                    <span class="badge {{ d.badge_class }} small-badge">{{ d.status }}</span>
                                </div>
                                <div class="day-body small">
                                    {% if d.status == 'Present' %}
                                        <div class="text-success fw-semibold"><i class="bi bi-clock me-1"></i>In: {{ d.punch_in_fmt }}</div>
                                        {% if d.is_late %}
                                            <span class="badge bg-warning text-dark border style-badge mt-1"><i class="bi bi-alarm me-1"></i>Late</span>
                                        {% endif %}
                                        {% if d.is_half_day %}
                                            <span class="badge bg-info text-dark border style-badge mt-1"><i class="bi bi-hourglass-split me-1"></i>Half Day</span>
                                        {% endif %}
                                        {% if d.total_hours %}
                                            <div class="badge bg-light text-dark border mt-1"><i class="bi bi-hourglass me-1"></i>{{ d.total_hours }} hrs</div>
                                        {% endif %}
                                    {% elif d.status == 'Leave' or d.status == 'Pending Leave' %}
                                        <div class="text-warning fw-semibold"><i class="bi bi-calendar-range me-1"></i>{{ d.leave_type or 'Leave' }}</div>
                                    {% elif d.status == 'Holiday' %}
                                        <div class="text-primary fw-semibold"><i class="bi bi-gift me-1"></i>{{ d.holiday_name }}</div>
                                    {% elif d.status == 'Weekend' %}
                                        <div class="text-muted italic"><i class="bi bi-cup-hot me-1"></i>Weekend</div>
                                    {% elif d.status == 'Absent' %}
                                        <div class="text-danger"><i class="bi bi-exclamation-octagon me-1"></i>No Log</div>
                                    {% else %}
                                        <div class="text-muted opacity-50">-</div>
                                    {% endif %}
                                </div>
                            </div>
                        {% endfor %}
                    </div>
                </div>
            </div>

            <!-- Date Detail Modal Popup for Admin -->
            <div class="modal fade" id="attendanceDayModal" tabindex="-1" aria-hidden="true">
                <div class="modal-dialog modal-dialog-centered">
                    <div class="modal-content shadow-lg border-0 rounded-4">
                        <div class="modal-header bg-light py-3 border-bottom">
                            <h5 class="modal-header-title mb-0 fw-bold">
                                <i class="bi bi-calendar-event me-2 text-primary"></i><span id="modalDateTitle">Date Details</span>
                            </h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                        </div>
                        <div class="modal-body p-4">
                            <div class="d-flex justify-content-between align-items-center mb-4 p-3 bg-light rounded border">
                                <div>
                                    <span class="text-muted small d-block">WEEKDAY</span>
                                    <h4 class="fw-bold mb-0 text-dark" id="modalWeekday">Monday</h4>
                                </div>
                                <span id="modalStatusBadge" class="badge fs-6 px-3 py-2">Present</span>
                            </div>

                            <div id="modalLateAlert" class="alert alert-warning py-2 mb-3 d-none">
                                <i class="bi bi-exclamation-triangle-fill me-2"></i><strong>Late Arrival:</strong> Punched in after 10:15 AM IST.
                            </div>
                            <div id="modalHalfDayAlert" class="alert alert-info py-2 mb-3 d-none">
                                <i class="bi bi-clock-history me-2"></i><strong>Half Day:</strong> Punched out before 3:00 PM IST.
                            </div>

                            <div class="row g-3 text-center mb-3">
                                <div class="col-6">
                                    <div class="p-3 border rounded bg-white shadow-sm">
                                        <i class="bi bi-box-arrow-in-right fs-4 text-success d-block mb-1"></i>
                                        <span class="text-muted small d-block">CHECK IN</span>
                                        <strong id="modalPunchIn" class="fs-6 text-dark">-</strong>
                                    </div>
                                </div>
                                <div class="col-6">
                                    <div class="p-3 border rounded bg-white shadow-sm">
                                        <i class="bi bi-box-arrow-right fs-4 text-danger d-block mb-1"></i>
                                        <span class="text-muted small d-block">CHECK OUT</span>
                                        <strong id="modalPunchOut" class="fs-6 text-dark">-</strong>
                                    </div>
                                </div>
                            </div>

                            <div class="p-3 border rounded bg-light mb-3 text-center">
                                <span class="text-muted small d-block mb-1">TOTAL LOGGED HOURS</span>
                                <h3 id="modalHours" class="fw-bold text-primary mb-0">0 Hours</h3>
                            </div>

                            <div id="modalNotesContainer" class="p-3 bg-white border rounded d-none">
                                <span class="text-muted small d-block fw-bold mb-1">NOTES / DETAILS</span>
                                <p id="modalNotesText" class="mb-0 small text-dark"></p>
                            </div>
                        </div>
                        <div class="modal-footer bg-light border-0 py-2">
                            <button type="button" class="btn btn-secondary btn-sm px-4" data-bs-dismiss="modal">Close</button>
                        </div>
                    </div>
                </div>
            </div>

            <script>
            function openAttendanceModal(el) {
                var date = el.getAttribute('data-date');
                var weekday = el.getAttribute('data-weekday');
                var status = el.getAttribute('data-status');
                var badgeClass = el.getAttribute('data-badge');
                var punchIn = el.getAttribute('data-punchin');
                var punchOut = el.getAttribute('data-punchout');
                var hours = el.getAttribute('data-hours');
                var isLate = el.getAttribute('data-late') === '1';
                var isHalfDay = el.getAttribute('data-halfday') === '1';
                var notes = el.getAttribute('data-notes');

                document.getElementById('modalDateTitle').innerText = date;
                document.getElementById('modalWeekday').innerText = weekday;
                
                var badgeEl = document.getElementById('modalStatusBadge');
                badgeEl.className = 'badge fs-6 px-3 py-2 ' + badgeClass;
                badgeEl.innerText = status;

                document.getElementById('modalPunchIn').innerText = punchIn;
                document.getElementById('modalPunchOut').innerText = punchOut;
                document.getElementById('modalHours').innerText = hours;

                var lateAlert = document.getElementById('modalLateAlert');
                if (isLate) {
                    lateAlert.classList.remove('d-none');
                } else {
                    lateAlert.classList.add('d-none');
                }

                var halfDayAlert = document.getElementById('modalHalfDayAlert');
                if (halfDayAlert) {
                    if (isHalfDay) {
                        halfDayAlert.classList.remove('d-none');
                    } else {
                        halfDayAlert.classList.add('d-none');
                    }
                }

                var notesContainer = document.getElementById('modalNotesContainer');
                var notesText = document.getElementById('modalNotesText');
                if (notes && notes.trim() !== '') {
                    notesText.innerText = notes;
                    notesContainer.classList.remove('d-none');
                } else {
                    notesContainer.classList.add('d-none');
                }

                var myModal = new bootstrap.Modal(document.getElementById('attendanceDayModal'));
                myModal.show();
            }
            </script>

        {% else %}
            <!-- All Employees Monthly Matrix Dashboard -->
            <div class="row g-3 mb-4">
                <div class="col-md-3">
                    <div class="card shadow-sm border-0 border-start border-4 border-primary h-100">
                        <div class="card-body p-3">
                            <div class="text-muted small fw-bold mb-1">ACTIVE EMPLOYEES</div>
                            <div class="display-6 fw-bold text-dark">{{ matrix_data.summary.total_employees }}</div>
                        </div>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="card shadow-sm border-0 border-start border-4 border-success h-100">
                        <div class="card-body p-3">
                            <div class="text-muted small fw-bold mb-1">TOTAL PRESENT LOGS</div>
                            <div class="display-6 fw-bold text-success">{{ matrix_data.summary.total_present }}</div>
                        </div>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="card shadow-sm border-0 border-start border-4 border-danger h-100">
                        <div class="card-body p-3">
                            <div class="text-muted small fw-bold mb-1">TOTAL ABSENT DAYS</div>
                            <div class="display-6 fw-bold text-danger">{{ matrix_data.summary.total_absent }}</div>
                        </div>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="card shadow-sm border-0 border-start border-4 border-info h-100">
                        <div class="card-body p-3">
                            <div class="text-muted small fw-bold mb-1">AVG ATTENDANCE RATE</div>
                            <div class="display-6 fw-bold text-info">{{ matrix_data.summary.avg_attendance_rate }}%</div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Monthly Attendance Matrix Table Card -->
            <div class="card shadow-sm border-0 mb-4">
                <div class="card-header bg-white py-3 border-0 d-flex justify-content-between align-items-center flex-wrap gap-2">
                    <div>
                        <h5 class="card-title mb-0 fw-bold"><i class="bi bi-table me-2 text-primary"></i>Monthly Attendance Summary Matrix ({{ matrix_data.month_name }} {{ matrix_data.year }})</h5>
                        <div class="text-muted small">Click any employee name to open their individual calendar.</div>
                    </div>
                    <div class="d-flex gap-2 flex-wrap small">
                        <span class="badge bg-success p-2">P = Present</span>
                        <span class="badge bg-danger p-2">A = Absent</span>
                        <span class="badge bg-warning text-dark p-2">L = Leave</span>
                        <span class="badge bg-info text-dark p-2">H = Holiday</span>
                        <span class="badge bg-secondary p-2">W = Weekend</span>
                    </div>
                </div>
                <div class="card-body p-0">
                    <div class="table-responsive">
                        <table class="table table-bordered table-hover align-middle mb-0 attendance-matrix-table">
                            <thead class="table-light text-center small">
                                <tr>
                                    <th class="text-start sticky-col" style="min-width: 180px;">Employee</th>
                                    <th style="min-width: 100px;">Dept</th>
                                    {% for day_num in matrix_data.day_numbers %}
                                        <th style="min-width: 32px; padding: 4px;">{{ day_num }}</th>
                                    {% endfor %}
                                    <th class="bg-success text-white" style="min-width: 45px;">P</th>
                                    <th class="bg-danger text-white" style="min-width: 45px;">A</th>
                                    <th class="bg-warning text-dark" style="min-width: 45px;">L</th>
                                    <th class="bg-primary text-white" style="min-width: 60px;">Hours</th>
                                </tr>
                            </thead>
                            <tbody class="small">
                                {% for emp in matrix_data.employees %}
                                    <tr>
                                        <td class="fw-bold sticky-col bg-white">
                                            <a href="{{ url_for('admin_attendance', year=year, month=month, user_id=emp.user_id) }}" class="text-primary text-decoration-none" title="Click to view full calendar">
                                                {{ emp.name }}
                                            </a>
                                        </td>
                                        <td class="text-muted text-center">{{ emp.department }}</td>
                                        {% for d in emp.days %}
                                            <td class="text-center p-1" title="{{ d.date }}: {{ d.status_label }}">
                                                {% if d.status_code == 'P' %}
                                                    <span class="badge bg-success w-100 py-1">P</span>
                                                {% elif d.status_code == 'A' %}
                                                    <span class="badge bg-danger w-100 py-1">A</span>
                                                {% elif d.status_code == 'L' or d.status_code == 'PL' %}
                                                    <span class="badge bg-warning text-dark w-100 py-1">L</span>
                                                {% elif d.status_code == 'H' %}
                                                    <span class="badge bg-info text-dark w-100 py-1">H</span>
                                                {% elif d.status_code == 'W' %}
                                                    <span class="badge bg-secondary opacity-50 w-100 py-1">W</span>
                                                {% else %}
                                                    <span class="text-muted opacity-25">-</span>
                                                {% endif %}
                                            </td>
                                        {% endfor %}
                                        <td class="text-center fw-bold text-success bg-light">{{ emp.stats.present_count }}</td>
                                        <td class="text-center fw-bold text-danger bg-light">{{ emp.stats.absent_count }}</td>
                                        <td class="text-center fw-bold text-warning bg-light">{{ emp.stats.leave_count }}</td>
                                        <td class="text-center fw-bold text-primary bg-light">{{ emp.stats.total_hours }}</td>
                                    </tr>
                                {% endfor %}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        {% endif %}
        {% endblock %}
        """,
        employees_list=employees_list,
        single_cal_data=single_cal_data,
        matrix_data=matrix_data,
        selected_user_id=selected_user_id,
        year=year,
        month=month,
        today_year=today.year,
        today_month=today.month,
    )


@app.route("/api/attendance/calendar-events")
@login_required
def api_attendance_calendar_events():
    """API Endpoint returning JSON attendance calendar data for dynamic client-side rendering."""
    today = datetime.datetime.now(tz=IST).date()
    year = request.args.get("year", type=int, default=today.year)
    month = request.args.get("month", type=int, default=today.month)
    target_user_id = request.args.get("user_id", type=int, default=current_user.id)

    # Permission check: Non-admin/non-HR can only request their own user_id
    if current_user.role not in ("admin", "hr") and target_user_id != current_user.id:
        return jsonify({"error": "Unauthorized"}), 403

    cal_data = get_monthly_attendance_calendar_data(year, month, target_user_id)
    return jsonify(cal_data)


@app.route("/admin/hr")
@login_required
def admin_hr():
    if current_user.role not in ("admin", "hr"):
        flash("Access denied.", "danger")
        return redirect(url_for("dashboard"))
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT u.id, u.username, u.full_name, u.email, u.role, u.force_password_change, e.id as emp_id, e.employee_code, e.department
            FROM users u
            LEFT JOIN employees e ON e.user_id = u.id
            WHERE u.role = 'hr'
            ORDER BY u.username
            """
        ).fetchall()
        users = [dict(row) for row in rows]

    return render_template_string(
        """
        {% extends "base.html" %}
        {% block title %}HR Management{% endblock %}
        {% block page_content %}
        <div class="container-fluid py-4">
            <div class="d-flex flex-wrap justify-content-between align-items-center gap-3 mb-4">
                <div>
                    <h1 class="h3 mb-1"><i class="bi bi-person-badge me-2 text-primary"></i>HR Management</h1>
                    <p class="text-muted mb-0">Overview HR staff accounts, permissions, and profiles.</p>
                </div>
                <div class="d-flex gap-2 flex-wrap">
                    <a class="btn btn-outline-secondary" href="{{ url_for('dashboard') }}"><i class="bi bi-arrow-left me-1"></i>Dashboard</a>
                    <a class="btn btn-primary" href="{{ url_for('add_hr') }}"><i class="bi bi-person-plus me-1"></i>Add HR</a>
                </div>
            </div>

            {% with messages = get_flashed_messages(with_categories=true) %}
                {% if messages %}
                    {% for category, message in messages %}
                        <div class="alert alert-{{ category }} alert-dismissible fade show" role="alert">
                            {{ message }}
                            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
                        </div>
                    {% endfor %}
                {% endif %}
            {% endwith %}

            <div class="card shadow-sm border-0">
                <div class="card-header bg-white py-3 border-0 d-flex justify-content-between align-items-center">
                    <h5 class="card-title mb-0 fw-bold"><i class="bi bi-person-badge-fill me-2 text-primary"></i>HR Staff Accounts</h5>
                    <span class="badge bg-light text-dark border">Total HR: {{ users|length }}</span>
                </div>
                <div class="card-body p-0">
                    <div class="table-responsive">
                        <table class="table table-hover align-middle mb-0">
                            <thead class="table-light">
                                <tr>
                                    <th class="ps-4">Username / Name</th>
                                    <th>Employee ID</th>
                                    <th>Email</th>
                                    <th>Role</th>
                                    <th>Status</th>
                                    <th class="text-end pe-4">Actions</th>
                                </tr>
                            </thead>
                            <tbody>
                            {% for u in users %}
                                <tr>
                                    <td class="ps-4 fw-bold">
                                        <i class="bi bi-person-circle me-2 text-secondary"></i>
                                        @{{ u.username }}
                                        {% if u.full_name %}<br><small class="text-muted ms-4">{{ u.full_name }}</small>{% endif %}
                                    </td>
                                    <td><span class="badge bg-secondary bg-opacity-10 text-dark border">{{ u.employee_code or 'N/A' }}</span></td>
                                    <td>{{ u.email or 'N/A' }}</td>
                                    <td><span class="badge bg-info text-dark fs-6"><i class="bi bi-person-badge me-1"></i>HR</span></td>
                                    <td>
                                        {% if u.force_password_change %}
                                            <span class="badge bg-warning text-dark"><i class="bi bi-exclamation-triangle me-1"></i>Pending Password Change</span>
                                        {% else %}
                                            <span class="badge bg-success"><i class="bi bi-check-circle me-1"></i>Active</span>
                                        {% endif %}
                                    </td>
                                    <td class="text-end pe-4">
                                        {% if u.emp_id %}
                                            <a class="btn btn-sm btn-outline-primary me-1" href="{{ url_for('view_employee', emp_id=u.emp_id) }}"><i class="bi bi-eye me-1"></i>View Profile</a>
                                        {% endif %}
                                    </td>
                                </tr>
                            {% else %}
                                <tr>
                                    <td colspan="6" class="text-center py-4 text-muted">No HR accounts found.</td>
                                </tr>
                            {% endfor %}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </div>
        {% endblock %}
        """,
        users=users,
    )


@app.route("/admin/admins")
@app.route("/admin/users")
@login_required
def admin_users():
    if current_user.role != "admin":
        flash("Admin access required.", "danger")
        return redirect(url_for("dashboard"))
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT u.id, u.username, u.full_name, u.email, u.role, u.force_password_change, e.id as emp_id, e.employee_code, e.department
            FROM users u
            LEFT JOIN employees e ON e.user_id = u.id
            WHERE u.role = 'admin'
            ORDER BY u.username
            """
        ).fetchall()
        users = [dict(row) for row in rows]

    return render_template_string(
        """
        {% extends "base.html" %}
        {% block title %}Admin Management{% endblock %}
        {% block page_content %}
        <div class="container-fluid py-4">
            <div class="d-flex flex-wrap justify-content-between align-items-center gap-3 mb-4">
                <div>
                    <h1 class="h3 mb-1"><i class="bi bi-shield-check me-2 text-primary"></i>Admin Management</h1>
                    <p class="text-muted mb-0">Overview system administrator accounts and root privileges.</p>
                </div>
                <div class="d-flex gap-2 flex-wrap">
                    <a class="btn btn-outline-secondary" href="{{ url_for('dashboard') }}"><i class="bi bi-arrow-left me-1"></i>Dashboard</a>
                    <a class="btn btn-primary" href="{{ url_for('add_admin') }}"><i class="bi bi-person-plus me-1"></i>Add Admin</a>
                </div>
            </div>

            {% with messages = get_flashed_messages(with_categories=true) %}
                {% if messages %}
                    {% for category, message in messages %}
                        <div class="alert alert-{{ category }} alert-dismissible fade show" role="alert">
                            {{ message }}
                            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
                        </div>
                    {% endfor %}
                {% endif %}
            {% endwith %}

            <div class="card shadow-sm border-0">
                <div class="card-header bg-white py-3 border-0 d-flex justify-content-between align-items-center">
                    <h5 class="card-title mb-0 fw-bold"><i class="bi bi-shield-lock-fill me-2 text-primary"></i>Administrator Accounts</h5>
                    <span class="badge bg-light text-dark border">Total Admins: {{ users|length }}</span>
                </div>
                <div class="card-body p-0">
                    <div class="table-responsive">
                        <table class="table table-hover align-middle mb-0">
                            <thead class="table-light">
                                <tr>
                                    <th class="ps-4">Username / Name</th>
                                    <th>Employee ID</th>
                                    <th>Email</th>
                                    <th>Role</th>
                                    <th>Status</th>
                                    <th class="text-end pe-4">Actions</th>
                                </tr>
                            </thead>
                            <tbody>
                            {% for u in users %}
                                <tr>
                                    <td class="ps-4 fw-bold">
                                        <i class="bi bi-person-circle me-2 text-secondary"></i>
                                        @{{ u.username }}
                                        {% if u.full_name %}<br><small class="text-muted ms-4">{{ u.full_name }}</small>{% endif %}
                                    </td>
                                    <td><span class="badge bg-secondary bg-opacity-10 text-dark border">{{ u.employee_code or 'N/A' }}</span></td>
                                    <td>{{ u.email or 'N/A' }}</td>
                                    <td><span class="badge bg-primary fs-6"><i class="bi bi-shield-check me-1"></i>Admin</span></td>
                                    <td>
                                        {% if u.force_password_change %}
                                            <span class="badge bg-warning text-dark"><i class="bi bi-exclamation-triangle me-1"></i>Pending Password Change</span>
                                        {% else %}
                                            <span class="badge bg-success"><i class="bi bi-check-circle me-1"></i>Active</span>
                                        {% endif %}
                                    </td>
                                    <td class="text-end pe-4">
                                        {% if u.id == current_user.id %}
                                            <span class="badge bg-light text-muted border py-2 px-3"><i class="bi bi-lock-fill me-1"></i>Current Session</span>
                                        {% else %}
                                            <form method="post" action="{{ url_for('delete_user', user_id=u.id) }}" class="d-inline" onsubmit="return confirm('Are you sure you want to permanently delete admin account @{{ u.username }}? This action cannot be undone.');">
                                                <button class="btn btn-sm btn-outline-danger" type="submit"><i class="bi bi-trash me-1"></i>Delete Admin</button>
                                            </form>
                                        {% endif %}
                                    </td>
                                </tr>
                            {% else %}
                                <tr>
                                    <td colspan="6" class="text-center py-4 text-muted">No admin accounts found.</td>
                                </tr>
                            {% endfor %}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </div>
        {% endblock %}
        """,
        users=users,
    )


@app.route("/admin/users/<int:user_id>/delete", methods=["POST"])
@login_required
def delete_user(user_id):
    if current_user.role != "admin":
        flash("Admin access required.", "danger")
        return redirect(url_for("dashboard"))

    if user_id == current_user.id:
        flash("You cannot delete your own active admin account.", "danger")
        return redirect(url_for("admin_users"))

    with get_db() as conn:
        u = conn.execute(
            "SELECT id, username FROM users WHERE id = ?", (user_id,)
        ).fetchone()
        if not u:
            flash("User account not found.", "warning")
            return redirect(url_for("admin_users"))

        username = u["username"]
        conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
        conn.commit()

    flash(f"User account '@{username}' deleted successfully.", "success")
    return redirect(url_for("admin_users"))


@app.route("/admin/employees")
@login_required
def admin_employees():
    if current_user.role not in ("admin", "hr"):
        flash("Access denied.", "danger")
        return redirect(url_for("dashboard"))
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT e.id, e.name, e.employee_code, e.department, e.salary, e.date_of_joining, e.date_of_birth, u.role
            FROM employees e
            LEFT JOIN users u ON e.user_id = u.id
            WHERE u.role IS NULL OR u.role NOT IN ('admin', 'hr')
            ORDER BY e.name
            """
        ).fetchall()
    return render_template_string(
        """
        {% extends "base.html" %}
        {% block title %}Employee Management{% endblock %}
        {% block page_content %}
        <div class="container-fluid py-4">
            <div class="d-flex flex-wrap justify-content-between align-items-center gap-3 mb-4">
                <div>
                    <h1 class="h3 mb-1"><i class="bi bi-people me-2 text-primary"></i>Employee Management</h1>
                    <p class="text-muted mb-0">Overview employee records, roles, joining dates, base salaries, and profiles.</p>
                </div>
                <div class="d-flex gap-2 flex-wrap">
                    <a class="btn btn-outline-secondary" href="{{ url_for('dashboard') }}"><i class="bi bi-arrow-left me-1"></i>Dashboard</a>
                    <a class="btn btn-primary" href="{{ url_for('add_employee') }}"><i class="bi bi-person-plus me-1"></i>Add Employee</a>
                </div>
            </div>

            {% with messages = get_flashed_messages(with_categories=true) %}
                {% if messages %}
                    {% for category, message in messages %}
                        <div class="alert alert-{{ category }} alert-dismissible fade show" role="alert">
                            {{ message }}
                            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
                        </div>
                    {% endfor %}
                {% endif %}
            {% endwith %}

            <div class="card shadow-sm border-0">
                <div class="card-body p-0">
                    <div class="table-responsive">
                        <table class="table table-hover align-middle mb-0">
                            <thead class="table-light">
                                <tr>
                                    <th class="ps-4">Employee ID</th>
                                    <th>Name</th>
                                    <th>Role</th>
                                    <th>Department</th>
                                    <th>Joining Date</th>
                                    <th>Salary</th>
                                    <th class="text-end pe-4">Actions</th>
                                </tr>
                            </thead>
                            <tbody>
                            {% for r in rows %}
                                <tr>
                                    <td class="ps-4"><span class="badge bg-secondary bg-opacity-10 text-dark border">{{ r.employee_code or ('EMP-%04d'|format(r.id)) }}</span></td>
                                    <td class="fw-bold">{{ r.name }}</td>
                                    <td>
                                        {% if r.role == 'admin' %}
                                            <span class="badge bg-primary">Admin</span>
                                        {% elif r.role == 'hr' %}
                                            <span class="badge bg-info text-dark">HR</span>
                                        {% elif r.role in ('permanent employee', 'permanent') %}
                                            <span class="badge bg-success">Permanent Employee</span>
                                        {% else %}
                                            <span class="badge bg-secondary">Temporary Employee</span>
                                        {% endif %}
                                    </td>
                                    <td><span class="badge bg-light text-dark border">{{ r.department or 'N/A' }}</span></td>
                                    <td>{{ r.date_of_joining or 'N/A' }}</td>
                                    <td>{{ r.salary | inr if r.salary else 'N/A' }}</td>
                                    <td class="text-end pe-4">
                                        <div class="d-inline-flex gap-1">
                                            <a class="btn btn-sm btn-primary" href="{{ url_for('view_employee', emp_id=r.id) }}"><i class="bi bi-eye me-1"></i>View</a>
                                            <a class="btn btn-sm btn-secondary" href="{{ url_for('edit_employee', emp_id=r.id) }}"><i class="bi bi-pencil me-1"></i>Edit</a>
                                            <form method="post" action="{{ url_for('delete_employee', emp_id=r.id) }}" style="display:inline-block;" onsubmit="return confirm('Are you sure you want to permanently delete employee {{ r.name }} and all associated user records? This action cannot be undone.');">
                                                <button class="btn btn-sm btn-danger" type="submit"><i class="bi bi-trash me-1"></i>Delete</button>
                                            </form>
                                        </div>
                                    </td>
                                </tr>
                            {% else %}
                                <tr>
                                    <td colspan="6" class="text-center text-muted py-4">No employees found.</td>
                                </tr>
                            {% endfor %}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </div>
        {% endblock %}
        """,
        rows=rows,
    )


@app.route("/admin/employees/add", methods=["GET", "POST"])
@login_required
def add_employee():
    if current_user.role not in ("admin", "hr"):
        flash("Access denied.", "danger")
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        employee_code = request.form.get("employee_code", "").strip()
        name = request.form.get("name", "").strip()
        employment_type = request.form.get("employment_type", "permanent employee").strip().lower()

        user_role = "temporary employee" if employment_type in ("temporary employee", "temporary") else "permanent employee"

        address = request.form.get("address", "").strip()
        education = request.form.get("education", "").strip()
        experience = request.form.get("experience", "").strip()
        contact_number = request.form.get("contact_number", "").strip()
        emergency_contact = request.form.get("emergency_contact", "").strip()
        departments = request.form.getlist("department")
        department = ",".join(departments)
        salary = request.form.get("salary") or None
        pan_file = request.files.get("pan")
        aadhaar_file = request.files.get("aadhaar")
        other_file = request.files.get("other")
        pan_path = save_uploaded_file(pan_file)
        aadhaar_path = save_uploaded_file(aadhaar_file)
        other_path = save_uploaded_file(other_file)
        date_of_joining = request.form.get("date_of_joining", "").strip() or None
        date_of_birth = request.form.get("date_of_birth", "").strip() or None

        # Integrated Login Account Creation Fields
        create_account = request.form.get("create_account") == "1"
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip()
        custom_password = request.form.get("password", "").strip()

        with get_db() as conn:
            valid, err_msg = validate_employee_code(conn, employee_code)
            if not valid:
                flash(err_msg, "danger")
                return redirect(url_for("add_employee"))

            new_user_id = None
            temp_password = None

            if create_account or username:
                if not username or not email:
                    flash("Username and Email are required to create a user login account.", "danger")
                    return redirect(url_for("add_employee"))

                existing_user = conn.execute(
                    "SELECT id FROM users WHERE username = ?",
                    (username,),
                ).fetchone()
                if existing_user:
                    flash("Username already exists. Please choose a different username.", "danger")
                    return redirect(url_for("add_employee"))

                temp_password = custom_password if custom_password else secrets.token_urlsafe(12)
                cursor = conn.execute(
                    "INSERT INTO users (username, password_hash, role, full_name, email, force_password_change) VALUES (?, ?, ?, ?, ?, ?)",
                    (
                        username,
                        generate_password_hash(temp_password),
                        user_role,
                        name,
                        email,
                        1 if not custom_password else 0,
                    ),
                )
                new_user_id = cursor.lastrowid

            if new_user_id:
                conn.execute(
                    "INSERT INTO employees (user_id, name, employee_code, address, education, experience, contact_number, emergency_contact, department, salary, pan_path, aadhaar_path, other_docs_path, date_of_joining, date_of_birth) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        new_user_id,
                        name,
                        employee_code,
                        address,
                        education,
                        experience,
                        contact_number,
                        emergency_contact,
                        department,
                        salary,
                        pan_path,
                        aadhaar_path,
                        other_path,
                        date_of_joining,
                        date_of_birth,
                    ),
                )
            else:
                conn.execute(
                    "INSERT INTO employees (name, employee_code, address, education, experience, contact_number, emergency_contact, department, salary, pan_path, aadhaar_path, other_docs_path, date_of_joining, date_of_birth) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        name,
                        employee_code,
                        address,
                        education,
                        experience,
                        contact_number,
                        emergency_contact,
                        department,
                        salary,
                        pan_path,
                        aadhaar_path,
                        other_path,
                        date_of_joining,
                        date_of_birth,
                    ),
                )

            conn.commit()
            sync_all_employee_roles(conn)

            if new_user_id:
                create_notification(
                    new_user_id,
                    "Welcome to HRMS",
                    f"Hello {name}, your account (@{username}) has been created.",
                    url_for("dashboard"),
                )
                notify_admins(
                    "New Employee Account Created",
                    f"Employee created for {name} (@{username}) with type {user_role}.",
                    url_for("admin_employees"),
                )
                send_welcome_email(email, name, username, temp_password)
                flash(f"Employee added successfully. Temporary password: {temp_password}", "success")
            else:
                flash("Employee added successfully.", "success")

        return redirect(url_for("admin_employees"))

    return render_template_string(
        """
        {% extends "base.html" %}
        {% block title %}Add Employee{% endblock %}
        {% block page_content %}
        <div class="container-fluid py-4">
            <div class="d-flex flex-wrap justify-content-between align-items-center gap-3 mb-4">
                <div>
                    <h1 class="h3 mb-1"><i class="bi bi-person-plus me-2 text-primary"></i>Add Employee</h1>
                    <p class="text-muted mb-0">Add a new employee profile to the system.</p>
                </div>
                <div>
                    <a class="btn btn-outline-secondary" href="{{ url_for('admin_employees') }}"><i class="bi bi-arrow-left me-1"></i>Back to Employees</a>
                </div>
            </div>

            {% with messages = get_flashed_messages(with_categories=true) %}
                {% if messages %}
                    {% for category, message in messages %}
                        <div class="alert alert-{{ category }} alert-dismissible fade show" role="alert">
                            {{ message }}
                            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                        </div>
                    {% endfor %}
                {% endif %}
            {% endwith %}

            <div class="card shadow-sm border-0 mx-auto" style="max-width: 800px;">
                <div class="card-body p-4">
                    <form method="post" enctype="multipart/form-data">
                        <h5 class="fw-bold mb-3"><i class="bi bi-person-badge me-2 text-primary"></i>Employee Details</h5>
                        <div class="row g-3 mb-3">
                            <div class="col-md-6">
                                <label class="form-label fw-bold">Employee ID <span class="text-danger">*</span></label>
                                <input class="form-control" name="employee_code" required placeholder="e.g. EMP001">
                            </div>
                            <div class="col-md-6">
                                <label class="form-label fw-bold">Name <span class="text-danger">*</span></label>
                                <input class="form-control" name="name" required placeholder="Full Name">
                            </div>
                        </div>
                        <div class="row g-3 mb-3">
                            <div class="col-md-6">
                                <label class="form-label fw-bold">Employee Type <span class="text-danger">*</span></label>
                                <select class="form-select" name="employment_type">
                                    <option value="permanent employee" selected>Permanent Employee</option>
                                    <option value="temporary employee">Temporary Employee</option>
                                </select>
                            </div>
                            <div class="col-md-6">
                                <label class="form-label fw-bold">Base Salary (INR)</label>
                                <input class="form-control" name="salary" type="number" step="0.01" placeholder="e.g. 50000">
                            </div>
                        </div>
                        <div class="row g-3 mb-3">
                            <div class="col-md-6">
                                <label class="form-label fw-bold">Date of Joining</label>
                                <input class="form-control" type="date" name="date_of_joining">
                            </div>
                            <div class="col-md-6">
                                <label class="form-label fw-bold">Date of Birth</label>
                                <input class="form-control" type="date" name="date_of_birth">
                            </div>
                        </div>
                        <div class="row g-3 mb-3">
                            <div class="col-md-6">
                                <label class="form-label fw-bold">Contact Number</label>
                                <input class="form-control" name="contact_number" placeholder="Phone number">
                            </div>
                            <div class="col-md-6">
                                <label class="form-label fw-bold">Emergency Contact Number</label>
                                <input class="form-control" name="emergency_contact" placeholder="Emergency contact">
                            </div>
                        </div>
                        <div class="row g-3 mb-3">
                            <div class="col-md-6">
                                <label class="form-label fw-bold">Education</label>
                                <input class="form-control" name="education" placeholder="Highest qualification">
                            </div>
                            <div class="col-md-6">
                                <label class="form-label fw-bold">Experience</label>
                                <input class="form-control" name="experience" placeholder="Years or summary of experience">
                            </div>
                        </div>
                        <div class="mb-3">
                            <label class="form-label fw-bold">Address</label>
                            <textarea class="form-control" name="address" rows="2" placeholder="Full residential address"></textarea>
                        </div>
                        <div class="mb-3">
                            <label class="form-label fw-bold d-block">Department</label>
                            <div class="d-flex flex-wrap gap-3">
                                <label class="form-check form-check-inline mb-0"><input class="form-check-input" type="checkbox" name="department" value="Google"> Google</label>
                                <label class="form-check form-check-inline mb-0"><input class="form-check-input" type="checkbox" name="department" value="Social"> Social</label>
                                <label class="form-check form-check-inline mb-0"><input class="form-check-input" type="checkbox" name="department" value="Website"> Website</label>
                            </div>
                        </div>

                        <hr class="my-4">
                        <h5 class="fw-bold mb-3"><i class="bi bi-file-earmark-arrow-up me-2 text-primary"></i>Employee Documents</h5>
                        <div class="mb-3">
                            <label class="form-label fw-semibold">PAN Card (upload)</label>
                            <input class="form-control" type="file" name="pan">
                        </div>
                        <div class="mb-3">
                            <label class="form-label fw-semibold">Aadhaar Card (upload)</label>
                            <input class="form-control" type="file" name="aadhaar">
                        </div>
                        <div class="mb-4">
                            <label class="form-label fw-semibold">Other Documents (upload)</label>
                            <input class="form-control" type="file" name="other">
                        </div>

                        <hr class="my-4">
                        <div class="bg-light p-3 rounded border mb-4">
                            <div class="form-check form-switch mb-3">
                                <input class="form-check-input" type="checkbox" name="create_account" value="1" id="createAccountSwitch" onchange="document.getElementById('userAccountFields').style.display = this.checked ? 'block' : 'none';">
                                <label class="form-check-label fw-bold text-primary" for="createAccountSwitch"><i class="bi bi-person-lock me-1"></i>Create User Login Account for this Employee</label>
                            </div>
                            <div id="userAccountFields" style="display: none;">
                                <p class="small text-muted mb-3">System login credentials will allow this employee to access their dashboard and leave requests.</p>
                                <div class="row g-3">
                                    <div class="col-md-6">
                                        <label class="form-label fw-semibold">Username</label>
                                        <input class="form-control" name="username" placeholder="e.g. johndoe">
                                    </div>
                                    <div class="col-md-6">
                                        <label class="form-label fw-semibold">Account Email</label>
                                        <input class="form-control" name="email" type="email" placeholder="e.g. john@example.com">
                                    </div>
                                    <div class="col-md-12">
                                        <label class="form-label fw-semibold">Password</label>
                                        <input class="form-control" name="password" type="password" placeholder="Leave blank to auto-generate temporary password">
                                    </div>
                                </div>
                            </div>
                        </div>

                        <div class="d-flex justify-content-end gap-2">
                            <a class="btn btn-outline-secondary" href="{{ url_for('admin_employees') }}">Cancel</a>
                            <button class="btn btn-primary" type="submit"><i class="bi bi-plus-lg me-1"></i>Add Employee</button>
                        </div>
                    </form>
                </div>
            </div>
        </div>
        {% endblock %}
        """,
    )


@app.route("/admin/hr/add", methods=["GET", "POST"])
@login_required
def add_hr():
    if current_user.role not in ("admin", "hr"):
        flash("Access denied.", "danger")
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip()
        custom_password = request.form.get("password", "").strip()
        employee_code = request.form.get("employee_code", "").strip()

        if not name or not username or not email:
            flash("Name, Username, and Email are required.", "danger")
            return redirect(url_for("add_hr"))

        with get_db() as conn:
            existing_user = conn.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone()
            if existing_user:
                flash("Username already exists. Please choose a different username.", "danger")
                return redirect(url_for("add_hr"))

            if employee_code:
                valid, err_msg = validate_employee_code(conn, employee_code)
                if not valid:
                    flash(err_msg, "danger")
                    return redirect(url_for("add_hr"))
            else:
                employee_code = f"HR-{secrets.token_hex(2).upper()}"

            temp_password = custom_password if custom_password else secrets.token_urlsafe(12)
            cursor = conn.execute(
                "INSERT INTO users (username, password_hash, role, full_name, email, force_password_change) VALUES (?, ?, 'hr', ?, ?, ?)",
                (
                    username,
                    generate_password_hash(temp_password),
                    name,
                    email,
                    1 if not custom_password else 0,
                ),
            )
            new_user_id = cursor.lastrowid

            conn.execute(
                "INSERT INTO employees (user_id, name, employee_code) VALUES (?, ?, ?)",
                (new_user_id, name, employee_code),
            )
            conn.commit()
            sync_all_employee_roles(conn)

            create_notification(new_user_id, "Welcome to HRMS", f"Hello {name}, your HR account (@{username}) has been created.", url_for("dashboard"))
            notify_admins("New HR Account Created", f"HR Account created for {name} (@{username}).", url_for("admin_hr"))
            send_welcome_email(email, name, username, temp_password)
            flash(f"HR account created successfully. Temporary password: {temp_password}", "success")

        return redirect(url_for("admin_hr"))

    return render_template_string(
        """
        {% extends "base.html" %}
        {% block title %}Add HR Account{% endblock %}
        {% block page_content %}
        <div class="container-fluid py-4">
            <div class="d-flex flex-wrap justify-content-between align-items-center gap-3 mb-4">
                <div>
                    <h1 class="h3 mb-1"><i class="bi bi-person-badge me-2 text-primary"></i>Add HR</h1>
                    <p class="text-muted mb-0">Create a new HR staff account with HR dashboard privileges.</p>
                </div>
                <div>
                    <a class="btn btn-outline-secondary" href="{{ url_for('admin_hr') }}"><i class="bi bi-arrow-left me-1"></i>Back to HR</a>
                </div>
            </div>

            {% with messages = get_flashed_messages(with_categories=true) %}
                {% if messages %}
                    {% for category, message in messages %}
                        <div class="alert alert-{{ category }} alert-dismissible fade show" role="alert">
                            {{ message }}
                            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                        </div>
                    {% endfor %}
                {% endif %}
            {% endwith %}

            <div class="card shadow-sm border-0 mx-auto" style="max-width: 650px;">
                <div class="card-body p-4">
                    <form method="post">
                        <div class="mb-3">
                            <label class="form-label fw-bold">Full Name <span class="text-danger">*</span></label>
                            <input class="form-control" name="name" required placeholder="e.g. Jane Doe">
                        </div>
                        <div class="row g-3 mb-3">
                            <div class="col-md-6">
                                <label class="form-label fw-bold">Username <span class="text-danger">*</span></label>
                                <input class="form-control" name="username" required placeholder="e.g. janedoe">
                            </div>
                            <div class="col-md-6">
                                <label class="form-label fw-bold">Email Address <span class="text-danger">*</span></label>
                                <input class="form-control" name="email" type="email" required placeholder="e.g. jane@example.com">
                            </div>
                        </div>
                        <div class="row g-3 mb-3">
                            <div class="col-md-6">
                                <label class="form-label fw-bold">Password</label>
                                <input class="form-control" name="password" type="password" placeholder="Leave blank for temp password">
                            </div>
                            <div class="col-md-6">
                                <label class="form-label fw-bold">Employee ID (Optional)</label>
                                <input class="form-control" name="employee_code" placeholder="e.g. HR001">
                            </div>
                        </div>
                        <div class="d-flex justify-content-end gap-2 mt-4">
                            <a class="btn btn-outline-secondary" href="{{ url_for('admin_hr') }}">Cancel</a>
                            <button class="btn btn-primary" type="submit"><i class="bi bi-check-circle me-1"></i>Add HR</button>
                        </div>
                    </form>
                </div>
            </div>
        </div>
        {% endblock %}
        """,
    )


@app.route("/admin/admins/add", methods=["GET", "POST"])
@login_required
def add_admin():
    if current_user.role != "admin":
        flash("Admin access required.", "danger")
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip()
        custom_password = request.form.get("password", "").strip()
        employee_code = request.form.get("employee_code", "").strip()

        if not name or not username or not email:
            flash("Name, Username, and Email are required.", "danger")
            return redirect(url_for("add_admin"))

        with get_db() as conn:
            existing_user = conn.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone()
            if existing_user:
                flash("Username already exists. Please choose a different username.", "danger")
                return redirect(url_for("add_admin"))

            if employee_code:
                valid, err_msg = validate_employee_code(conn, employee_code)
                if not valid:
                    flash(err_msg, "danger")
                    return redirect(url_for("add_admin"))
            else:
                employee_code = f"ADM-{secrets.token_hex(2).upper()}"

            temp_password = custom_password if custom_password else secrets.token_urlsafe(12)
            cursor = conn.execute(
                "INSERT INTO users (username, password_hash, role, full_name, email, force_password_change) VALUES (?, ?, 'admin', ?, ?, ?)",
                (
                    username,
                    generate_password_hash(temp_password),
                    name,
                    email,
                    1 if not custom_password else 0,
                ),
            )
            new_user_id = cursor.lastrowid

            conn.execute(
                "INSERT INTO employees (user_id, name, employee_code) VALUES (?, ?, ?)",
                (new_user_id, name, employee_code),
            )
            conn.commit()
            sync_all_employee_roles(conn)

            create_notification(new_user_id, "Welcome to HRMS", f"Hello {name}, your Admin account (@{username}) has been created.", url_for("dashboard"))
            notify_admins("New Admin Account Created", f"Admin Account created for {name} (@{username}).", url_for("admin_users"))
            send_welcome_email(email, name, username, temp_password)
            flash(f"Admin account created successfully. Temporary password: {temp_password}", "success")

        return redirect(url_for("admin_users"))

    return render_template_string(
        """
        {% extends "base.html" %}
        {% block title %}Add Admin Account{% endblock %}
        {% block page_content %}
        <div class="container-fluid py-4">
            <div class="d-flex flex-wrap justify-content-between align-items-center gap-3 mb-4">
                <div>
                    <h1 class="h3 mb-1"><i class="bi bi-shield-check me-2 text-primary"></i>Add Admin</h1>
                    <p class="text-muted mb-0">Create a new system administrator account with root privileges.</p>
                </div>
                <div>
                    <a class="btn btn-outline-secondary" href="{{ url_for('admin_users') }}"><i class="bi bi-arrow-left me-1"></i>Back to Admin</a>
                </div>
            </div>

            {% with messages = get_flashed_messages(with_categories=true) %}
                {% if messages %}
                    {% for category, message in messages %}
                        <div class="alert alert-{{ category }} alert-dismissible fade show" role="alert">
                            {{ message }}
                            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                        </div>
                    {% endfor %}
                {% endif %}
            {% endwith %}

            <div class="card shadow-sm border-0 mx-auto" style="max-width: 650px;">
                <div class="card-body p-4">
                    <form method="post">
                        <div class="mb-3">
                            <label class="form-label fw-bold">Full Name <span class="text-danger">*</span></label>
                            <input class="form-control" name="name" required placeholder="e.g. John Administrator">
                        </div>
                        <div class="row g-3 mb-3">
                            <div class="col-md-6">
                                <label class="form-label fw-bold">Username <span class="text-danger">*</span></label>
                                <input class="form-control" name="username" required placeholder="e.g. adminjohn">
                            </div>
                            <div class="col-md-6">
                                <label class="form-label fw-bold">Email Address <span class="text-danger">*</span></label>
                                <input class="form-control" name="email" type="email" required placeholder="e.g. admin@example.com">
                            </div>
                        </div>
                        <div class="row g-3 mb-3">
                            <div class="col-md-6">
                                <label class="form-label fw-bold">Password</label>
                                <input class="form-control" name="password" type="password" placeholder="Leave blank for temp password">
                            </div>
                            <div class="col-md-6">
                                <label class="form-label fw-bold">Employee ID (Optional)</label>
                                <input class="form-control" name="employee_code" placeholder="e.g. ADM001">
                            </div>
                        </div>
                        <div class="d-flex justify-content-end gap-2 mt-4">
                            <a class="btn btn-outline-secondary" href="{{ url_for('admin_users') }}">Cancel</a>
                            <button class="btn btn-primary" type="submit"><i class="bi bi-shield-check me-1"></i>Add Admin</button>
                        </div>
                    </form>
                </div>
            </div>
        </div>
        {% endblock %}
        """,
    )


@app.route("/admin/employees/<int:emp_id>")
@login_required
def view_employee(emp_id):
    if current_user.role not in ("admin", "hr"):
        flash("Access denied.", "danger")
        return redirect(url_for("dashboard"))
    with get_db() as conn:
        r = conn.execute("SELECT * FROM employees WHERE id = ?", (emp_id,)).fetchone()
        if not r:
            flash("Employee not found.", "warning")
            return redirect(url_for("admin_employees"))

        user_id = dict(r).get("user_id") or None
        if not user_id and r["name"]:
            u = conn.execute(
                "SELECT id FROM users WHERE full_name = ? OR username = ?",
                (r["name"], r["name"]),
            ).fetchone()
            if u:
                user_id = u["id"]

        emp_user = conn.execute("SELECT role FROM users WHERE id = ?", (user_id,)).fetchone() if user_id else None
        emp_role = emp_user["role"] if emp_user else "temporary employee"
        perf = calculate_employee_performance(conn, user_id)
        payroll = calculate_employee_payroll(conn, emp_id)

    return render_template_string(
        """
        {% extends "base.html" %}
        {% block title %}View Employee - {{ r.name }}{% endblock %}
        {% block page_content %}
        <div class="container-fluid py-4">
            {% with messages = get_flashed_messages(with_categories=true) %}
                {% if messages %}
                    {% for category, message in messages %}
                        <div class="alert alert-{{ category }} alert-dismissible fade show" role="alert">
                            {{ message }}
                            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                        </div>
                    {% endfor %}
                {% endif %}
            {% endwith %}

            <div class="d-flex flex-wrap justify-content-between align-items-center gap-3 mb-4">
                <div>
                    <h1 class="h3 mb-1"><i class="bi bi-person-badge me-2 text-primary"></i>{{ r.name }}</h1>
                    <p class="text-muted mb-0">Employee details, documents, payroll overview, and performance metrics.</p>
                </div>
                <div class="d-flex gap-2">
                    <a class="btn btn-outline-secondary" href="{{ url_for('admin_employees') }}"><i class="bi bi-arrow-left me-1"></i>Back to Employees</a>
                    <a class="btn btn-primary" href="{{ url_for('edit_employee', emp_id=r.id) }}"><i class="bi bi-pencil me-1"></i>Edit Profile</a>
                </div>
            </div>

            <!-- Profile Details Card -->
            <div class="card shadow-sm border-0 mb-4">
                <div class="card-header bg-transparent py-3 border-bottom">
                    <h5 class="mb-0 fw-bold"><i class="bi bi-info-circle me-2 text-primary"></i>Personal Information</h5>
                </div>
                <div class="card-body">
                    <div class="row g-3">
                        <div class="col-md-6">
                            <p class="mb-1 text-muted small">Employee Role</p>
                            <p class="fw-semibold mb-0">
                                {% if emp_role == 'admin' %}
                                    <span class="badge bg-primary fs-6">Admin</span>
                                {% elif emp_role == 'hr' %}
                                    <span class="badge bg-info text-dark fs-6">HR</span>
                                {% elif emp_role in ('permanent employee', 'permanent') %}
                                    <span class="badge bg-success fs-6">Permanent Employee</span>
                                {% else %}
                                    <span class="badge bg-secondary fs-6">Temporary Employee</span>
                                {% endif %}
                            </p>
                        </div>
                        <div class="col-md-6">
                            <p class="mb-1 text-muted small">Employee ID</p>
                            <p class="fw-semibold mb-0"><span class="badge bg-secondary bg-opacity-10 text-dark border">{{ r.employee_code or ('EMP-%04d'|format(r.id)) }}</span></p>
                        </div>
                        <div class="col-md-6"><p class="mb-1 text-muted small">Department</p><p class="fw-semibold mb-0"><span class="badge bg-light text-dark border">{{ r.department or 'N/A' }}</span></p></div>
                        <div class="col-md-6"><p class="mb-1 text-muted small">Date of Joining</p><p class="fw-semibold mb-0">{{ r.date_of_joining or 'N/A' }}</p></div>
                        <div class="col-md-6"><p class="mb-1 text-muted small">Date of Birth</p><p class="fw-semibold mb-0">{{ r.date_of_birth or 'N/A' }}</p></div>
                        <div class="col-md-6"><p class="mb-1 text-muted small">Base Salary</p><p class="fw-semibold mb-0">{{ r.salary | inr if r.salary else 'N/A' }}</p></div>
                        <div class="col-md-6"><p class="mb-1 text-muted small">Education</p><p class="fw-semibold mb-0">{{ r.education or 'N/A' }}</p></div>
                        <div class="col-md-6"><p class="mb-1 text-muted small">Experience</p><p class="fw-semibold mb-0">{{ r.experience or 'N/A' }}</p></div>
                        <div class="col-md-6"><p class="mb-1 text-muted small">Contact Number</p><p class="fw-semibold mb-0">{{ r.contact_number or 'N/A' }}</p></div>
                        <div class="col-md-6"><p class="mb-1 text-muted small">Emergency Contact</p><p class="fw-semibold mb-0">{{ r.emergency_contact or 'N/A' }}</p></div>
                        <div class="col-12"><p class="mb-1 text-muted small">Address</p><p class="fw-semibold mb-0">{{ r.address or 'N/A' }}</p></div>
                    </div>

                    <hr class="my-4">

                    <h6 class="fw-bold mb-3"><i class="bi bi-file-earmark-text me-2 text-primary"></i>Uploaded Documents</h6>
                    <div class="row g-3">
                        <div class="col-md-4">
                            <div class="p-3 border rounded text-center">
                                <i class="bi bi-card-text fs-3 text-primary d-block mb-1"></i>
                                <span class="text-muted small d-block mb-2">PAN Card</span>
                                {% if r.pan_path %}<a class="btn btn-sm btn-outline-primary" href="/{{ r.pan_path }}"><i class="bi bi-download me-1"></i>Download</a>{% else %}<span class="badge bg-light text-muted border">Not Uploaded</span>{% endif %}
                            </div>
                        </div>
                        <div class="col-md-4">
                            <div class="p-3 border rounded text-center">
                                <i class="bi bi-person-bounding-box fs-3 text-info d-block mb-1"></i>
                                <span class="text-muted small d-block mb-2">Aadhaar Card</span>
                                {% if r.aadhaar_path %}<a class="btn btn-sm btn-outline-primary" href="/{{ r.aadhaar_path }}"><i class="bi bi-download me-1"></i>Download</a>{% else %}<span class="badge bg-light text-muted border">Not Uploaded</span>{% endif %}
                            </div>
                        </div>
                        <div class="col-md-4">
                            <div class="p-3 border rounded text-center">
                                <i class="bi bi-folder2-open fs-3 text-secondary d-block mb-1"></i>
                                <span class="text-muted small d-block mb-2">Other Documents</span>
                                {% if r.other_docs_path %}<a class="btn btn-sm btn-outline-primary" href="/{{ r.other_docs_path }}"><i class="bi bi-download me-1"></i>Download</a>{% else %}<span class="badge bg-light text-muted border">Not Uploaded</span>{% endif %}
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Payroll Section -->
            {% if payroll %}
            <div class="card shadow-sm border-0 mb-4">
                <div class="card-header bg-transparent py-3 border-bottom d-flex flex-wrap justify-content-between align-items-center gap-2">
                    <h5 class="mb-0 fw-bold"><i class="bi bi-wallet2 me-2 text-success"></i>Payroll Section</h5>
                    <span class="badge bg-success px-3 py-1 fs-6">{{ payroll.payroll_month }}</span>
                </div>
                <div class="card-body">
                    <div class="row g-3 mb-3">
                        <div class="col-md-4">
                            <div class="p-3 border rounded text-center h-100">
                                <span class="text-muted small d-block mb-1">Current Base Salary</span>
                                <strong class="fs-5">{{ payroll.base_salary | inr }}</strong>
                                {% if current_user.role == 'admin' %}
                                    <form method="POST" action="{{ url_for('update_employee_base_salary', emp_id=r.id) }}" class="mt-2 d-flex gap-1 justify-content-center">
                                        <input type="number" step="0.01" name="salary" class="form-control form-control-sm" style="max-width: 110px;" value="{{ payroll.base_salary }}" required>
                                        <button type="submit" class="btn btn-sm btn-outline-primary" title="Update Base Salary"><i class="bi bi-check-lg"></i></button>
                                    </form>
                                {% endif %}
                            </div>
                        </div>
                        <div class="col-md-4">
                            <div class="p-3 border rounded text-center h-100">
                                <span class="text-muted small d-block mb-1">Current Month Final Salary</span>
                                <strong class="fs-4 text-success">{{ payroll.final_salary | inr }}</strong>
                                {% if payroll.leave_deduction > 0 %}
                                    <div class="text-danger small mt-1">(Deduction: -{{ payroll.leave_deduction | inr }})</div>
                                {% else %}
                                    <div class="text-muted small mt-1">(No Deductions)</div>
                                {% endif %}
                            </div>
                        </div>
                        <div class="col-md-4">
                            <div class="p-3 border rounded text-center h-100">
                                <span class="text-muted small d-block mb-1">Payroll Details</span>
                                <div class="fw-semibold small mb-1">Working Days: {{ payroll.working_days }}</div>
                                <div class="text-muted small">Status: <span class="badge bg-info text-dark">{{ payroll.payroll_status }}</span></div>
                            </div>
                        </div>
                    </div>
                    <div class="row g-2">
                        <div class="col-4 col-md-4">
                            <div class="p-2 border rounded text-center">
                                <span class="text-muted small d-block">Attendance %</span>
                                <strong class="text-success">{{ payroll.attendance_pct }}%</strong>
                            </div>
                        </div>
                        <div class="col-4 col-md-4">
                            <div class="p-2 border rounded text-center">
                                <span class="text-muted small d-block">Approved Leave Days</span>
                                <strong class="text-info">{{ payroll.approved_leave_days }}</strong>
                            </div>
                        </div>
                        <div class="col-4 col-md-4">
                            <div class="p-2 border rounded text-center">
                                <span class="text-muted small d-block">Performance %</span>
                                <strong class="text-primary">{{ payroll.performance_score }}%</strong>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            {% endif %}

            <!-- Performance Section -->
            <div class="card shadow-sm border-0 mb-4">
                <div class="card-header bg-transparent py-3 border-bottom d-flex flex-wrap justify-content-between align-items-center gap-2">
                    <h5 class="mb-0 fw-bold"><i class="bi bi-graph-up-arrow me-2 text-primary"></i>Performance Section</h5>
                    <span class="badge {{ perf.badge_class }} fs-6 px-3 py-1">{{ perf.performance_label }}</span>
                </div>
                <div class="card-body">
                    <div class="row align-items-center g-3 mb-3">
                        <div class="col-md-4 text-center border-end">
                            <div class="text-muted small fw-semibold">Performance Score</div>
                            <div class="display-6 fw-bold text-primary my-1">{{ perf.performance_score }}%</div>
                            <div class="progress mb-2" style="height: 10px;">
                                <div class="progress-bar {{ perf.bar_class }}" role="progressbar" style="width: {{ perf.performance_score }}%;" aria-valuenow="{{ perf.performance_score }}" aria-valuemin="0" aria-valuemax="100"></div>
                            </div>
                            <div class="text-muted small" style="font-size: 0.75rem;">
                                <i class="bi bi-clock me-1"></i>Last Updated: {{ perf.last_updated }}
                            </div>
                        </div>
                        <div class="col-md-8">
                            <div class="row g-2">
                                <div class="col-6">
                                    <div class="p-2 border rounded text-center">
                                        <span class="text-muted small d-block">Attendance %</span>
                                        <strong class="text-success">{{ perf.attendance_pct }}%</strong>
                                    </div>
                                </div>
                                <div class="col-6">
                                    <div class="p-2 border rounded text-center">
                                        <span class="text-muted small d-block">Task Completion %</span>
                                        <strong class="text-primary">{{ perf.task_completion_pct }}%</strong>
                                    </div>
                                </div>
                                <div class="col-6">
                                    <div class="p-2 border rounded text-center">
                                        <span class="text-muted small d-block">Approved Leaves</span>
                                        <strong class="text-info">{{ perf.approved_leaves }}</strong>
                                    </div>
                                </div>
                                <div class="col-6">
                                    <div class="p-2 border rounded text-center">
                                        <span class="text-muted small d-block">Overdue Tasks</span>
                                        <strong class="{% if perf.overdue_tasks > 0 %}text-danger{% else %}text-secondary{% endif %}">{{ perf.overdue_tasks }}</strong>
                                    </div>
                                </div>
                                <div class="col-6">
                                    <div class="p-2 border rounded text-center">
                                        <span class="text-muted small d-block">Completed Tasks</span>
                                        <strong class="text-success">{{ perf.completed_tasks }}</strong>
                                    </div>
                                </div>
                                <div class="col-6">
                                    <div class="p-2 border rounded text-center">
                                        <span class="text-muted small d-block">Pending Tasks</span>
                                        <strong class="text-warning">{{ perf.pending_tasks }}</strong>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        {% endblock %}
        """,
        r=r,
        emp_role=emp_role,
        perf=perf,
        payroll=payroll,
    )


@app.route("/admin/employees/<int:emp_id>/update-salary", methods=["POST"])
@login_required
def update_employee_base_salary(emp_id):
    if current_user.role not in ("admin", "hr"):
        flash("Access denied to edit Base Salary.", "danger")
        return redirect(url_for("dashboard"))

    new_salary = request.form.get("salary")
    try:
        sal_val = float(new_salary) if new_salary is not None else 0.0
    except (ValueError, TypeError):
        flash("Invalid salary amount.", "danger")
        return redirect(request.referrer or url_for("settings_payroll"))

    with get_db() as conn:
        emp = conn.execute(
            "SELECT id, name FROM employees WHERE id = ?", (emp_id,)
        ).fetchone()
        if not emp:
            flash("Employee not found.", "danger")
            return redirect(url_for("settings_payroll"))

        conn.execute(
            "UPDATE employees SET salary = ? WHERE id = ?", (sal_val, emp_id)
        )
        conn.commit()

    flash(
        f"Base Salary for {emp['name']} updated successfully to {format_inr(sal_val)}.",
        "success",
    )
    return redirect(request.referrer or url_for("settings_payroll"))


@app.route("/admin/employees/<int:emp_id>/edit", methods=["GET", "POST"])
@login_required
def edit_employee(emp_id):
    if current_user.role not in ("admin", "hr"):
        flash("Access denied.", "danger")
        return redirect(url_for("dashboard"))
    with get_db() as conn:
        r = conn.execute("SELECT * FROM employees WHERE id = ?", (emp_id,)).fetchone()
        if not r:
            flash("Employee not found.", "warning")
            return redirect(url_for("admin_employees"))
        if current_user.role == "hr" and r["user_id"]:
            target_user = conn.execute("SELECT role FROM users WHERE id = ?", (r["user_id"],)).fetchone()
            if target_user and target_user["role"] == "admin":
                flash("Access denied. HR cannot edit Admin accounts.", "danger")
                return redirect(url_for("admin_employees"))
    if request.method == "POST":
        employee_code = request.form.get("employee_code", "").strip()
        name = request.form.get("name", "").strip()
        employment_type = request.form.get("employment_type", "").strip().lower()
        address = request.form.get("address", "").strip()
        education = request.form.get("education", "").strip()
        experience = request.form.get("experience", "").strip()
        contact_number = request.form.get("contact_number", "").strip()
        emergency_contact = request.form.get("emergency_contact", "").strip()
        departments = request.form.getlist("department")
        department = ",".join(departments)
        salary = request.form.get("salary") or None
        pan_file = request.files.get("pan")
        aadhaar_file = request.files.get("aadhaar")
        other_file = request.files.get("other")
        pan_path = r["pan_path"]
        aadhaar_path = r["aadhaar_path"]
        other_path = r["other_docs_path"]
        date_of_joining = request.form.get("date_of_joining", "").strip() or None
        date_of_birth = request.form.get("date_of_birth", "").strip() or None
        if pan_file and pan_file.filename:
            pan_path = save_uploaded_file(pan_file)
        if aadhaar_file and aadhaar_file.filename:
            aadhaar_path = save_uploaded_file(aadhaar_file)
        if other_file and other_file.filename:
            other_path = save_uploaded_file(other_file)
        with get_db() as conn:
            valid, err_msg = validate_employee_code(conn, employee_code, current_emp_id=emp_id)
            if not valid:
                flash(err_msg, "danger")
                return redirect(url_for("edit_employee", emp_id=emp_id))

            if employment_type in ("permanent employee", "permanent"):
                target_role = "permanent employee"
            elif employment_type in ("temporary employee", "temporary"):
                target_role = "temporary employee"
            else:
                target_role = None

            if target_role and r["user_id"]:
                conn.execute(
                    "UPDATE users SET role = ? WHERE id = ?",
                    (target_role, r["user_id"]),
                )

            conn.execute(
                """
                    UPDATE employees SET name=?, employee_code=?, address=?, education=?, experience=?, contact_number=?, emergency_contact=?, department=?, salary=?, pan_path=?, aadhaar_path=?, other_docs_path=?, date_of_joining=?, date_of_birth=? WHERE id=?
                    """,
                (
                    name,
                    employee_code,
                    address,
                    education,
                    experience,
                    contact_number,
                    emergency_contact,
                    department,
                    salary,
                    pan_path,
                    aadhaar_path,
                    other_path,
                    date_of_joining,
                    date_of_birth,
                    emp_id,
                ),
            )
            conn.commit()
            sync_all_employee_roles(conn)
        if r["user_id"]:
            create_notification(
                r["user_id"],
                "Employee Profile Updated",
                "Your employee records and profile documents were updated by administration.",
                url_for("dashboard"),
            )
        flash("Employee updated.", "success")
        return redirect(url_for("view_employee", emp_id=emp_id))

    current_emp_type = "temporary employee"
    with get_db() as conn:
        if r["user_id"]:
            user_row = conn.execute("SELECT role FROM users WHERE id = ?", (r["user_id"],)).fetchone()
            if user_row:
                current_emp_type = user_row["role"]
        else:
            current_emp_type = compute_employee_role(r["date_of_joining"])

    current_depts = (r["department"] or "").split(",") if r["department"] else []
    return render_template_string(
        """
        {% extends "base.html" %}
        {% block title %}Edit Employee - {{ r.name }}{% endblock %}
        {% block page_content %}
        <div class="container-fluid py-4">
            <div class="d-flex flex-wrap justify-content-between align-items-center gap-3 mb-4">
                <div>
                    <h1 class="h3 mb-1"><i class="bi bi-pencil-square me-2 text-primary"></i>Edit Employee</h1>
                    <p class="text-muted mb-0">Update employee records and uploaded documents for {{ r.name }}.</p>
                </div>
                <div>
                    <a class="btn btn-outline-secondary" href="{{ url_for('view_employee', emp_id=r.id) }}"><i class="bi bi-arrow-left me-1"></i>Back to View Profile</a>
                </div>
            </div>

            {% with messages = get_flashed_messages(with_categories=true) %}
                {% if messages %}
                    {% for category, message in messages %}
                        <div class="alert alert-{{ category }} alert-dismissible fade show" role="alert">
                            {{ message }}
                            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                        </div>
                    {% endfor %}
                {% endif %}
            {% endwith %}

            <div class="card shadow-sm border-0 mx-auto" style="max-width: 800px;">
                <div class="card-body p-4">
                    <form method="post" enctype="multipart/form-data">
                        <div class="row g-3 mb-3">
                            <div class="col-md-6">
                                <label class="form-label fw-bold">Employee ID <span class="text-danger">*</span></label>
                                <input class="form-control" name="employee_code" value="{{ r.employee_code or ('EMP-%04d'|format(r.id)) }}" required placeholder="e.g. EMP001">
                            </div>
                            <div class="col-md-6">
                                <label class="form-label fw-bold">Name <span class="text-danger">*</span></label>
                                <input class="form-control" name="name" value="{{ r.name }}" required>
                            </div>
                        </div>
                        <div class="row g-3 mb-3">
                            <div class="col-md-6">
                                <label class="form-label fw-bold">Employment Type <span class="text-danger">*</span></label>
                                <select class="form-select" name="employment_type">
                                    <option value="permanent employee" {% if current_emp_type in ['permanent employee', 'permanent'] %}selected{% endif %}>Permanent Employee</option>
                                    <option value="temporary employee" {% if current_emp_type not in ['permanent employee', 'permanent'] %}selected{% endif %}>Temporary Employee</option>
                                </select>
                            </div>
                            <div class="col-md-6">
                                <label class="form-label fw-bold">Base Salary (INR)</label>
                                <input class="form-control" name="salary" type="number" step="0.01" value="{{ r.salary or '' }}" placeholder="e.g. 50000">
                            </div>
                        </div>
                        <div class="mb-3">
                            <label class="form-label fw-bold">Address</label>
                            <textarea class="form-control" name="address" rows="3">{{ r.address or '' }}</textarea>
                        </div>
                        <div class="row g-3 mb-3">
                            <div class="col-md-6">
                                <label class="form-label fw-bold">Education</label>
                                <input class="form-control" name="education" value="{{ r.education or '' }}">
                            </div>
                            <div class="col-md-6">
                                <label class="form-label fw-bold">Experience</label>
                                <input class="form-control" name="experience" value="{{ r.experience or '' }}">
                            </div>
                        </div>
                        <div class="row g-3 mb-3">
                            <div class="col-md-6">
                                <label class="form-label fw-bold">Date of Joining</label>
                                <input class="form-control" type="date" name="date_of_joining" value="{{ r.date_of_joining or '' }}">
                            </div>
                            <div class="col-md-6">
                                <label class="form-label fw-bold">Date of Birth</label>
                                <input class="form-control" type="date" name="date_of_birth" value="{{ r.date_of_birth or '' }}">
                            </div>
                        </div>
                        <div class="row g-3 mb-3">
                            <div class="col-md-6">
                                <label class="form-label fw-bold">Contact Number</label>
                                <input class="form-control" name="contact_number" value="{{ r.contact_number or '' }}">
                            </div>
                            <div class="col-md-6">
                                <label class="form-label fw-bold">Emergency Contact Number</label>
                                <input class="form-control" name="emergency_contact" value="{{ r.emergency_contact or '' }}">
                            </div>
                        </div>
                        <div class="mb-3">
                            <label class="form-label fw-bold d-block">Department</label>
                            <div class="d-flex flex-wrap gap-3">
                                {% for dep in ['Google','Social','Website'] %}
                                    <label class="form-check form-check-inline mb-0"><input class="form-check-input" type="checkbox" name="department" value="{{ dep }}" {% if dep in current_depts %}checked{% endif %}> {{ dep }}</label>
                                {% endfor %}
                            </div>
                        </div>
                        <div class="mb-3">
                            <label class="form-label fw-bold">Salary (INR)</label>
                            <input class="form-control" name="salary" type="number" step="0.01" value="{{ r.salary or '' }}">
                        </div>
                        <hr class="my-4">
                        <h5 class="fw-bold mb-3"><i class="bi bi-file-earmark-arrow-up me-2 text-primary"></i>Employee Documents</h5>
                        <div class="mb-3">
                            <label class="form-label fw-semibold">PAN Card (upload)</label>
                            <input class="form-control" type="file" name="pan">
                            {% if r.pan_path %}<div class="form-text text-muted">Current file: {{ r.pan_path }}</div>{% endif %}
                        </div>
                        <div class="mb-3">
                            <label class="form-label fw-semibold">Aadhaar Card (upload)</label>
                            <input class="form-control" type="file" name="aadhaar">
                            {% if r.aadhaar_path %}<div class="form-text text-muted">Current file: {{ r.aadhaar_path }}</div>{% endif %}
                        </div>
                        <div class="mb-4">
                            <label class="form-label fw-semibold">Other Documents (upload)</label>
                            <input class="form-control" type="file" name="other">
                            {% if r.other_docs_path %}<div class="form-text text-muted">Current file: {{ r.other_docs_path }}</div>{% endif %}
                        </div>
                        <div class="d-flex justify-content-end gap-2">
                            <a class="btn btn-outline-secondary" href="{{ url_for('view_employee', emp_id=r.id) }}">Cancel</a>
                            <button class="btn btn-primary" type="submit"><i class="bi bi-check-lg me-1"></i>Save Changes</button>
                        </div>
                    </form>
                </div>
            </div>
        </div>
        {% endblock %}
        """,
        r=r,
        current_depts=current_depts,
    )


@app.route("/admin/employees/<int:emp_id>/delete", methods=["POST"])
@login_required
def delete_employee(emp_id):
    if current_user.role not in ("admin", "hr"):
        flash("Access denied.", "danger")
        return redirect(url_for("dashboard"))

    with get_db() as conn:
        r = conn.execute("SELECT * FROM employees WHERE id = ?", (emp_id,)).fetchone()
        if not r:
            flash("Employee not found.", "warning")
            return redirect(url_for("admin_employees"))
        if current_user.role == "hr" and r["user_id"]:
            target_user = conn.execute("SELECT role FROM users WHERE id = ?", (r["user_id"],)).fetchone()
            if target_user and target_user["role"] == "admin":
                flash("Access denied. HR cannot delete Admin accounts.", "danger")
                return redirect(url_for("admin_employees"))

        linked_user_id = r["user_id"]
        employee_name = r["name"]

        # Prevent active admin self-deletion
        if linked_user_id and linked_user_id == current_user.id:
            flash("You cannot delete your own active admin account.", "danger")
            return redirect(url_for("admin_employees"))

        # Remove physical upload files
        for p in (r["pan_path"], r["aadhaar_path"], r["other_docs_path"]):
            try:
                if p and os.path.exists(p):
                    os.remove(p)
            except Exception:  # noqa: BLE001, S110  # Best-effort file removal without interrupting DB deletion
                pass

        if linked_user_id:
            # Delete dependent records linked by user_id
            conn.execute("DELETE FROM attendance WHERE user_id = ?", (linked_user_id,))
            conn.execute(
                "DELETE FROM leave_requests WHERE user_id = ?", (linked_user_id,)
            )
            conn.execute(
                "DELETE FROM performance_reviews WHERE employee_user_id = ?",
                (linked_user_id,),
            )
            conn.execute("DELETE FROM time_logs WHERE user_id = ?", (linked_user_id,))
            conn.execute("DELETE FROM users WHERE id = ?", (linked_user_id,))

        # Update tasks assigned to this employee to 'Unassigned'
        conn.execute(
            "UPDATE tasks SET assigned_to = ? WHERE assigned_to = ?",
            ("Unassigned", employee_name),
        )

        # Delete employee record
        conn.execute("DELETE FROM employees WHERE id = ?", (emp_id,))
        conn.commit()

    flash(
        f"Employee '{employee_name}' and all associated user records deleted successfully.",
        "success",
    )
    return redirect(url_for("admin_employees"))


@app.route("/admin/clients")
@login_required
def admin_clients():
    if current_user.role != "admin":
        flash("Admin access required.", "danger")
        return redirect(url_for("dashboard"))
    with get_db() as conn:
        clients = conn.execute(
            "SELECT * FROM clients ORDER BY lower(name), id"
        ).fetchall()
    return render_template_string(
        """
        {% extends "base.html" %}
        {% block title %}Client Management{% endblock %}
        {% block page_content %}
        <div class="page-header d-flex flex-wrap justify-content-between align-items-center gap-3 mb-4">
            <div>
                <h1>Client Management</h1>
                <p>Overview client directory, services, location, and contact information.</p>
            </div>
            <div>
                <a class="btn btn-primary" href="{{ url_for('add_client') }}"><i class="bi bi-plus-lg me-1"></i>Add New Client</a>
            </div>
        </div>

        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="alert alert-{{ category }} alert-dismissible fade show" role="alert">
                        {{ message }}
                        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
                    </div>
                {% endfor %}
            {% endif %}
        {% endwith %}

        <div class="card shadow-sm">
            <div class="card-header bg-white py-3 border-0 d-flex justify-content-between align-items-center">
                <h5 class="card-title mb-0 fw-bold"><i class="bi bi-building me-2 text-primary"></i>Client Directory</h5>
                <span class="badge bg-light text-dark border">Total Clients: {{ clients|length }}</span>
            </div>
            <div class="card-body p-0">
                <div class="table-responsive">
                    <table class="table table-hover align-middle mb-0">
                        <thead class="table-light">
                            <tr>
                                <th>Client Name</th>
                                <th>City</th>
                                <th>Services</th>
                                <th>Contact Number</th>
                                <th>Email</th>
                                <th class="text-end">Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            {% for client in clients %}
                            <tr>
                                <td>
                                    <strong class="text-dark">{{ client.name }}</strong>
                                    {% if client.gst_number %}<small class="d-block text-muted">GST: {{ client.gst_number }}</small>{% endif %}
                                </td>
                                <td>{{ client.city or '-' }}</td>
                                <td>
                                    {% if client.services %}
                                        <span class="badge bg-primary-subtle text-primary border border-primary-subtle">{{ client.services }}</span>
                                    {% else %}
                                        <span class="text-muted">-</span>
                                    {% endif %}
                                </td>
                                <td>{{ client.contact_number or '-' }}</td>
                                <td>{{ client.email or '-' }}</td>
                                <td class="text-end">
                                    <a class="btn btn-sm btn-outline-primary me-1" href="{{ url_for('edit_client', client_id=client.id) }}"><i class="bi bi-pencil me-1"></i>Edit</a>
                                    <form method="post" action="{{ url_for('delete_client', client_id=client.id) }}" class="d-inline" onsubmit="return confirm('Are you sure you want to delete this client?');">
                                        <button class="btn btn-sm btn-outline-danger" type="submit"><i class="bi bi-trash me-1"></i>Delete</button>
                                    </form>
                                </td>
                            </tr>
                            {% else %}
                            <tr>
                                <td colspan="6" class="text-center py-4 text-muted">
                                    <i class="bi bi-building-exclamation fs-3 d-block mb-2"></i>No clients found.
                                </td>
                            </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
        {% endblock %}
    """,
        clients=clients,
    )


def render_client_form(client=None):
    return render_template_string(
        """
        {% extends "base.html" %}
        {% block title %}{{ 'Edit Client' if client else 'Add Client' }}{% endblock %}
        {% block page_content %}
        <div class="page-header d-flex flex-wrap justify-content-between align-items-center gap-3 mb-4">
            <div>
                <h1>{{ 'Edit Client' if client else 'Add New Client' }}</h1>
                <p>{{ 'Update existing client profile details.' if client else 'Add a new client organization profile.' }}</p>
            </div>
            <div>
                <a class="btn btn-outline-secondary" href="{{ url_for('admin_clients') }}"><i class="bi bi-arrow-left me-1"></i>Back to Clients</a>
            </div>
        </div>

        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="alert alert-{{ category }} alert-dismissible fade show" role="alert">
                        {{ message }}
                        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
                    </div>
                {% endfor %}
            {% endif %}
        {% endwith %}

        <div class="row justify-content-center">
            <div class="col-lg-9">
                <div class="card shadow-sm">
                    <div class="card-header bg-white py-3 border-0">
                        <h5 class="card-title mb-0 fw-bold"><i class="bi bi-building-add me-2 text-primary"></i>Client Details</h5>
                    </div>
                    <div class="card-body">
                        <form method="post">
                            <div class="row g-3">
                                <div class="col-md-6">
                                    <label class="form-label fw-semibold">Client Name <span class="text-danger">*</span></label>
                                    <input class="form-control" name="name" value="{{ client.name if client else '' }}" required placeholder="e.g. Acme Corporation">
                                </div>
                                <div class="col-md-6">
                                    <label class="form-label fw-semibold">City</label>
                                    <input class="form-control" name="city" value="{{ client.city if client else '' }}" placeholder="e.g. Mumbai">
                                </div>
                                <div class="col-12">
                                    <label class="form-label fw-semibold">Client Address</label>
                                    <textarea class="form-control" name="address" rows="3" placeholder="Full business address">{{ client.address if client else '' }}</textarea>
                                </div>
                                <div class="col-md-6">
                                    <label class="form-label fw-semibold">Services</label>
                                    <input class="form-control" name="services" value="{{ client.services if client else '' }}" placeholder="e.g. SEO, Social Media, Web Dev">
                                </div>
                                <div class="col-md-6">
                                    <label class="form-label fw-semibold">GST Number</label>
                                    <input class="form-control" name="gst_number" value="{{ client.gst_number if client else '' }}" placeholder="e.g. 27AAAAA0000A1Z5">
                                </div>
                                <div class="col-md-6">
                                    <label class="form-label fw-semibold">Contact Number</label>
                                    <input class="form-control" name="contact_number" value="{{ client.contact_number if client else '' }}" placeholder="e.g. +91 9876543210">
                                </div>
                                <div class="col-md-6">
                                    <label class="form-label fw-semibold">Email Address</label>
                                    <input class="form-control" type="email" name="email" value="{{ client.email if client else '' }}" placeholder="contact@acme.com">
                                </div>
                            </div>
                            <div class="mt-4 d-flex gap-2">
                                <button class="btn btn-primary" type="submit"><i class="bi bi-check-circle me-1"></i>Save Client</button>
                                <a class="btn btn-outline-secondary" href="{{ url_for('admin_clients') }}">Cancel</a>
                            </div>
                        </form>
                    </div>
                </div>
            </div>
        </div>
        {% endblock %}
    """,
        client=client,
    )


@app.route("/admin/clients/add", methods=["GET", "POST"])
@login_required
def add_client():
    if current_user.role != "admin":
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        values = [
            request.form.get(key, "").strip()
            for key in (
                "name",
                "address",
                "city",
                "services",
                "gst_number",
                "contact_number",
                "email",
            )
        ]
        if not values[0]:
            flash("Client Name is required.", "danger")
            return render_client_form()
        with get_db() as conn:
            conn.execute(
                "INSERT INTO clients (name, address, city, services, gst_number, contact_number, email) VALUES (?, ?, ?, ?, ?, ?, ?)",
                values,
            )
        return redirect(url_for("admin_clients"))
    return render_client_form()


@app.route("/admin/clients/<int:client_id>", methods=["GET", "POST"])
@app.route("/admin/clients/<int:client_id>/edit", methods=["GET", "POST"])
@login_required
def edit_client(client_id):
    if current_user.role != "admin":
        return redirect(url_for("dashboard"))
    with get_db() as conn:
        client = conn.execute(
            "SELECT * FROM clients WHERE id = ?", (client_id,)
        ).fetchone()
        if client is None:
            flash("Client not found.", "warning")
            return redirect(url_for("admin_clients"))
        if request.method == "POST":
            values = [
                request.form.get(key, "").strip()
                for key in (
                    "name",
                    "address",
                    "city",
                    "services",
                    "gst_number",
                    "contact_number",
                    "email",
                )
            ]
            if not values[0]:
                flash("Client Name is required.", "danger")
                return render_client_form(client)
            conn.execute(
                "UPDATE clients SET name=?, address=?, city=?, services=?, gst_number=?, contact_number=?, email=? WHERE id=?",
                (*values, client_id),
            )
            return redirect(url_for("admin_clients"))
    return render_client_form(client)


@app.route("/admin/clients/<int:client_id>/delete", methods=["POST"])
@login_required
def delete_client(client_id):
    if current_user.role != "admin":
        return redirect(url_for("dashboard"))
    with get_db() as conn:
        conn.execute("DELETE FROM clients WHERE id = ?", (client_id,))
    return redirect(url_for("admin_clients"))


@app.route("/admin/projects")
@login_required
def admin_projects():
    if current_user.role != "admin":
        flash("Admin access required.", "danger")
        return redirect(url_for("dashboard"))

    search = (request.args.get("search") or "").strip()
    service_filter = (request.args.get("service_filter") or "All").strip()
    page = request.args.get("page", 1, type=int)
    page = max(page, 1)

    per_page = 10
    query = """
        SELECT projects.id, clients.name AS client_name, projects.assigned_to, projects.services,
               clients.email AS client_email, clients.contact_number AS whatsapp_number
        FROM projects LEFT JOIN clients ON clients.id = projects.client_id
        WHERE 1 = 1
    """
    params = []

    if search:
        search_term = f"%{search.lower()}%"
        query += """
            AND (
                lower(coalesce(clients.name, '')) LIKE ? OR
                lower(coalesce(projects.assigned_to, '')) LIKE ? OR
                lower(coalesce(clients.email, '')) LIKE ? OR
                lower(coalesce(clients.contact_number, '')) LIKE ?
            )
        """
        params.extend([search_term, search_term, search_term, search_term])

    if service_filter != "All":
        query += " AND lower(services) LIKE ?"
        params.append(f"%{service_filter.lower()}%")

    query += " ORDER BY lower(coalesce(clients.name, '')) ASC, projects.id ASC"

    with get_db() as conn:
        all_projects = conn.execute(query, params).fetchall()

    total_projects = len(all_projects)
    total_pages = max(1, (total_projects + per_page - 1) // per_page)
    page = min(page, total_pages)

    start = (page - 1) * per_page
    projects = all_projects[start : start + per_page]

    return render_template_string(
        """
        {% extends "base.html" %}
        {% block title %}Project Management{% endblock %}
        {% block page_content %}
        <div class="page-header d-flex flex-wrap justify-content-between align-items-center gap-3 mb-4">
            <div>
                <h1>Project Management</h1>
                <p>Track client projects, service allocations, assigned employees, and deliverables.</p>
            </div>
            <div>
                <a class="btn btn-primary" href="{{ url_for('add_project') }}"><i class="bi bi-plus-lg me-1"></i>Add Project</a>
            </div>
        </div>

        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="alert alert-{{ category }} alert-dismissible fade show" role="alert">
                        {{ message }}
                        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
                    </div>
                {% endfor %}
            {% endif %}
        {% endwith %}

        <div class="card shadow-sm">
            <div class="card-body">
                <div class="d-flex justify-content-between align-items-center mb-3 flex-wrap gap-2">
                    <div class="fw-semibold text-muted">Total Projects: {{ total_projects }}</div>
                    <form class="row g-2 align-items-end" method="get">
                        <div class="col">
                            <label class="form-label small mb-1" for="search">Search</label>
                            <input class="form-control" id="search" name="search" type="text" value="{{ search }}" placeholder="Client, employee, email, WhatsApp">
                        </div>
                        <div class="col">
                            <label class="form-label small mb-1" for="service_filter">Services</label>
                            <select class="form-select" id="service_filter" name="service_filter">
                                <option value="All" {% if service_filter == 'All' %}selected{% endif %}>All Services</option>
                                <option value="Social Media" {% if service_filter == 'Social Media' %}selected{% endif %}>Social Media</option>
                                <option value="SEO" {% if service_filter == 'SEO' %}selected{% endif %}>SEO</option>
                                <option value="Meta Ads" {% if service_filter == 'Meta Ads' %}selected{% endif %}>Meta Ads</option>
                                <option value="Google Ads" {% if service_filter == 'Google Ads' %}selected{% endif %}>Google Ads</option>
                                <option value="Website Development" {% if service_filter == 'Website Development' %}selected{% endif %}>Website Development</option>
                            </select>
                        </div>
                        <div class="col-auto">
                            <button class="btn btn-primary" type="submit"><i class="bi bi-funnel me-1"></i>Filter</button>
                        </div>
                        <div class="col-auto">
                            <a class="btn btn-outline-secondary" href="{{ url_for('admin_projects') }}">Reset</a>
                        </div>
                    </form>
                </div>
                <div class="table-responsive">
                    <table class="table table-hover align-middle">
                        <thead class="table-light">
                            <tr>
                                <th>Client Name</th>
                                <th>Assigned Employee</th>
                                <th>Services</th>
                                <th>Client Email</th>
                                <th>Client WhatsApp Number</th>
                                <th class="text-end">Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                        {% if projects %}
                            {% for project in projects %}
                                <tr>
                                    <td><strong class="text-dark">{{ project.client_name or 'No Client Assigned' }}</strong></td>
                                    <td>{{ project.assigned_to or '-' }}</td>
                                    <td>
                                        {% if project.services %}
                                            <span class="badge bg-primary-subtle text-primary border border-primary-subtle">{{ project.services }}</span>
                                        {% else %}
                                            <span class="text-muted">-</span>
                                        {% endif %}
                                    </td>
                                    <td>{{ project.client_email or '-' }}</td>
                                    <td>{{ project.whatsapp_number or '-' }}</td>
                                    <td class="text-end">
                                        <a class="btn btn-sm btn-outline-info me-1" href="{{ url_for('view_project', project_id=project.id) }}"><i class="bi bi-eye me-1"></i>View</a>
                                        <a class="btn btn-sm btn-outline-primary me-1" href="{{ url_for('edit_project', project_id=project.id) }}"><i class="bi bi-pencil me-1"></i>Edit</a>
                                        <a class="btn btn-sm btn-outline-danger" href="{{ url_for('delete_project', project_id=project.id) }}" onclick="return confirm('Are you sure you want to delete this project?');"><i class="bi bi-trash me-1"></i>Delete</a>
                                    </td>
                                </tr>
                            {% endfor %}
                        {% else %}
                            <tr>
                                <td colspan="6" class="text-center py-4 text-muted">
                                    <i class="bi bi-kanban fs-3 d-block mb-2"></i>
                                    {% if search or service_filter != 'All' %}
                                        No matching projects found.
                                    {% else %}
                                        No projects found.
                                    {% endif %}
                                </td>
                            </tr>
                        {% endif %}
                        </tbody>
                    </table>
                </div>
                {% if total_pages > 1 %}
                <nav aria-label="Project pagination" class="mt-3">
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
        {% endblock %}
        """,
        projects=projects,
        total_projects=total_projects,
        search=search,
        service_filter=service_filter,
        page=page,
        total_pages=total_pages,
    )


def render_project_form(project=None, clients=None, employees=None):
    return render_template_string(
        """
        {% extends "base.html" %}
        {% block title %}{{ 'Edit Project' if project else 'Add Project' }}{% endblock %}
        {% block page_content %}
        <div class="page-header d-flex flex-wrap justify-content-between align-items-center gap-3 mb-4">
            <div>
                <h1>{{ 'Edit Project' if project else 'Add New Project' }}</h1>
                <p>{{ 'Update project assignment and deliverables.' if project else 'Create a new client project record.' }}</p>
            </div>
            <div>
                <a class="btn btn-outline-secondary" href="{{ url_for('admin_projects') }}"><i class="bi bi-arrow-left me-1"></i>Back to Projects</a>
            </div>
        </div>

        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="alert alert-{{ category }} alert-dismissible fade show" role="alert">
                        {{ message }}
                        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
                    </div>
                {% endfor %}
            {% endif %}
        {% endwith %}

        <div class="row justify-content-center">
            <div class="col-lg-9">
                <div class="card shadow-sm">
                    <div class="card-header bg-white py-3 border-0">
                        <h5 class="card-title mb-0 fw-bold"><i class="bi bi-kanban me-2 text-primary"></i>Project Form</h5>
                    </div>
                    <div class="card-body">
                        <form method="post">
                            <div class="mb-3">
                                <label class="form-label fw-semibold">Client <span class="text-danger">*</span></label>
                                <select class="form-select" name="client_id" required>
                                    <option value="">Select client</option>
                                    {% for client in clients %}
                                        <option value="{{ client.id }}" {% if project and client.id == project.client_id %}selected{% endif %}>{{ client.name }}</option>
                                    {% endfor %}
                                </select>
                            </div>
                            <div class="mb-3">
                                <label class="form-label fw-semibold">Services <span class="text-danger">*</span></label>
                                <div class="d-flex flex-wrap gap-3 p-3 bg-light rounded border">
                                    {% for service in ['Social Media', 'SEO', 'Meta Ads', 'Google Ads', 'Website Development'] %}
                                        <label class="form-check form-check-inline mb-0">
                                            <input class="form-check-input" type="checkbox" name="services" value="{{ service }}" {% if project and service in current_services %}checked{% endif %}>
                                            <span class="form-check-label">{{ service }}</span>
                                        </label>
                                    {% endfor %}
                                </div>
                            </div>
                            <div class="mb-3">
                                <label class="form-label fw-semibold">Assigned Employee <span class="text-danger">*</span></label>
                                <select class="form-select" name="assigned_to" required>
                                    <option value="">Select employee</option>
                                    {% for employee in employees %}
                                        <option value="{{ employee.name }}" {% if project and employee.name == project.assigned_to %}selected{% endif %}>{{ employee.name }}</option>
                                    {% endfor %}
                                </select>
                            </div>
                            <div class="mb-3">
                                <label class="form-label fw-semibold">Delivery Details <span class="text-danger">*</span></label>
                                <textarea class="form-control" name="delivery_details" rows="3" required placeholder="Describe milestones, deliverables, or links...">{{ project.delivery_details if project else '' }}</textarea>
                            </div>
                            <div class="mt-4 d-flex gap-2">
                                <button class="btn btn-primary" type="submit"><i class="bi bi-check-circle me-1"></i>{{ 'Save Changes' if project else 'Save Project' }}</button>
                                <a class="btn btn-outline-secondary" href="{{ url_for('admin_projects') }}">Cancel</a>
                            </div>
                        </form>
                    </div>
                </div>
            </div>
        </div>
        {% endblock %}
    """,
        project=project,
        clients=clients,
        employees=employees,
        current_services=(project["services"] or "").split(",") if project else [],
    )


@app.route("/admin/projects/add", methods=["GET", "POST"])
@login_required
def add_project():
    if current_user.role != "admin":
        flash("Admin access required.", "danger")
        return redirect(url_for("dashboard"))
    with get_db() as conn:
        clients = conn.execute(
            "SELECT id, name FROM clients ORDER BY lower(name), id"
        ).fetchall()
        employees = conn.execute(
            "SELECT id, name FROM employees ORDER BY name"
        ).fetchall()
        if request.method == "GET":
            return render_project_form(None, clients, employees)
        if request.method == "POST":
            client_id = request.form.get("client_id", type=int)
            services = request.form.getlist("services")
            assigned_to = request.form.get("assigned_to", "").strip()
            delivery_details = request.form.get("delivery_details", "").strip()
            if not client_id or not services or not assigned_to or not delivery_details:
                flash("All fields are required.", "danger")
                return render_project_form(None, clients, employees)
            conn.execute(
                "INSERT INTO projects (client_id, services, assigned_to, delivery_details) VALUES (?, ?, ?, ?)",
                (client_id, ",".join(services), assigned_to, delivery_details),
            )
            conn.commit()
    flash("Project created successfully.", "success")
    return redirect(url_for("admin_projects"))


@app.route("/admin/projects/<int:project_id>/edit", methods=["GET", "POST"])
@login_required
def edit_project(project_id):
    if current_user.role != "admin":
        flash("Admin access required.", "danger")
        return redirect(url_for("dashboard"))
    with get_db() as conn:
        project = conn.execute(
            "SELECT * FROM projects WHERE id = ?", (project_id,)
        ).fetchone()
        if project is None:
            flash("Project not found.", "warning")
            return redirect(url_for("admin_projects"))
        clients = conn.execute(
            "SELECT id, name FROM clients ORDER BY lower(name), id"
        ).fetchall()
        employees = conn.execute(
            "SELECT id, name FROM employees ORDER BY name"
        ).fetchall()
        if request.method == "POST":
            client_id = request.form.get("client_id", type=int)
            services = request.form.getlist("services")
            assigned_to = request.form.get("assigned_to", "").strip()
            delivery_details = request.form.get("delivery_details", "").strip()
            if not client_id or not services or not assigned_to or not delivery_details:
                flash("All fields are required.", "danger")
                return render_project_form(project, clients, employees)
            conn.execute(
                "UPDATE projects SET client_id=?, services=?, assigned_to=?, delivery_details=? WHERE id=?",
                (
                    client_id,
                    ",".join(services),
                    assigned_to,
                    delivery_details,
                    project_id,
                ),
            )
            conn.commit()
            flash("Project updated successfully.", "success")
            return redirect(url_for("admin_projects"))
    return render_project_form(project, clients, employees)


@app.route("/admin/projects/add/legacy", methods=["GET", "POST"])
@login_required
def legacy_add_project():
    if current_user.role != "admin":
        flash("Admin access required.", "danger")
        return redirect(url_for("dashboard"))

    with get_db() as conn:
        employees = conn.execute(
            "SELECT id, name FROM employees ORDER BY name"
        ).fetchall()
        clients = conn.execute(
            "SELECT id, name FROM clients ORDER BY lower(name), id"
        ).fetchall()

    if request.method == "POST":
        client_id = request.form.get("client_id", type=int)
        services = request.form.getlist("services")
        assigned_to = request.form.get("assigned_to", "").strip()
        delivery_details = request.form.get("delivery_details", "").strip()

        required_fields = [
            ("Client", client_id),
            ("Services", services),
            ("Assigned To", assigned_to),
            ("Delivery Details", delivery_details),
        ]
        if any(not value for _, value in required_fields):
            flash("All fields are required.", "danger")
            return redirect(url_for("legacy_add_project"))


        services_text = ",".join(services)
        with get_db() as conn:
            conn.execute(
                """
                INSERT INTO projects (
                    client_id,
                    services,
                    assigned_to,
                    delivery_details
                ) VALUES (?, ?, ?, ?)
                """,
                (
                    client_id,
                    services_text,
                    assigned_to,
                    delivery_details,
                ),
            )
            conn.commit()

        notify_user_by_name_or_username(
            assigned_to,
            "Assigned to New Project",
            "You have been assigned to project for client.",
            url_for("dashboard"),
        )
        flash("Project created successfully.", "success")
        return redirect(url_for("admin_projects"))

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
                                <label class="form-label">Client</label>
                                <select class="form-select" name="client_id" required><option value="">Select client</option>{% for client in clients %}<option value="{{ client.id }}">{{ client.name }}</option>{% endfor %}</select>
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
        clients=clients,
    )


@app.route("/admin/projects/<int:project_id>")
@login_required
def view_project(project_id):
    if current_user.role != "admin":
        flash("Admin access required.", "danger")
        return redirect(url_for("dashboard"))
    with get_db() as conn:
        project = conn.execute(
            "SELECT projects.*, clients.name AS linked_client_name, clients.address AS linked_client_address, clients.city AS linked_client_city, clients.email AS linked_client_email, clients.contact_number AS linked_client_contact FROM projects LEFT JOIN clients ON clients.id = projects.client_id WHERE projects.id = ?",
            (project_id,),
        ).fetchone()
    if project is None:
        flash("Project not found.", "warning")
        return redirect(url_for("admin_projects"))
    return render_template_string(
        """
        {% extends "base.html" %}
        {% block title %}View Project{% endblock %}
        {% block page_content %}
        <div class="page-header d-flex flex-wrap justify-content-between align-items-center gap-3 mb-4">
            <div>
                <h1>Project Overview</h1>
                <p>Detailed project information and linked client contact record.</p>
            </div>
            <div>
                <a class="btn btn-outline-secondary" href="{{ url_for('admin_projects') }}"><i class="bi bi-arrow-left me-1"></i>Back to Projects</a>
                <a class="btn btn-primary ms-2" href="{{ url_for('edit_project', project_id=project.id) }}"><i class="bi bi-pencil me-1"></i>Edit Project</a>
            </div>
        </div>

        <div class="row justify-content-center">
            <div class="col-lg-8">
                <div class="card shadow-sm">
                    <div class="card-header bg-white py-3 border-0">
                        <h5 class="card-title mb-0 fw-bold"><i class="bi bi-kanban me-2 text-primary"></i>Project Summary</h5>
                    </div>
                    <div class="card-body">
                        <div class="row g-3">
                            <div class="col-md-6">
                                <label class="form-label text-muted small mb-0">Linked Client</label>
                                <div class="fw-bold text-dark fs-6">{{ project.linked_client_name or 'No Client Assigned' }}</div>
                            </div>
                            <div class="col-md-6">
                                <label class="form-label text-muted small mb-0">Assigned Employee</label>
                                <div class="fw-bold text-dark fs-6">{{ project.assigned_to or 'Unassigned' }}</div>
                            </div>
                            <div class="col-12">
                                <label class="form-label text-muted small mb-0">Services Provided</label>
                                <div>
                                    {% if project.services %}
                                        <span class="badge bg-primary-subtle text-primary border border-primary-subtle fs-7">{{ project.services }}</span>
                                    {% else %}
                                        <span class="text-muted">None specified</span>
                                    {% endif %}
                                </div>
                            </div>
                            <div class="col-12">
                                <label class="form-label text-muted small mb-0">Deliverables / Details</label>
                                <div class="p-3 bg-light rounded border text-dark">{{ project.delivery_details or 'No delivery details specified.' }}</div>
                            </div>
                            {% if project.linked_client_name %}
                            <div class="col-12"><hr class="my-2"></div>
                            <div class="col-md-6">
                                <label class="form-label text-muted small mb-0">Client Email</label>
                                <div>{{ project.linked_client_email or '-' }}</div>
                            </div>
                            <div class="col-md-6">
                                <label class="form-label text-muted small mb-0">Client Contact</label>
                                <div>{{ project.linked_client_contact or '-' }}</div>
                            </div>
                            <div class="col-12">
                                <label class="form-label text-muted small mb-0">Client Address</label>
                                <div>{{ project.linked_client_address or '' }}{% if project.linked_client_city %}, {{ project.linked_client_city }}{% endif %}</div>
                            </div>
                            {% endif %}
                        </div>
                    </div>
                </div>
            </div>
        </div>
        {% endblock %}
        """,
        project=project,
    )


@app.route("/admin/projects/<int:project_id>/edit/legacy", methods=["GET", "POST"])
@login_required
def legacy_edit_project(project_id):
    if current_user.role != "admin":
        flash("Admin access required.", "danger")
        return redirect(url_for("dashboard"))

    with get_db() as conn:
        project = conn.execute(
            "SELECT * FROM projects WHERE id = ?",
            (project_id,),
        ).fetchone()
        employees = conn.execute(
            "SELECT id, name FROM employees ORDER BY name"
        ).fetchall()
        clients = conn.execute(
            "SELECT id, name FROM clients ORDER BY lower(name), id"
        ).fetchall()

    if project is None:
        flash("Project not found.", "warning")
        return redirect(url_for("admin_projects"))

    current_services = []
    if project["services"]:
        current_services = [
            item.strip() for item in str(project["services"]).split(",") if item.strip()
        ]

    if request.method == "POST":
        client_id = request.form.get("client_id", type=int)
        client_name = (request.form.get("client_name") or "").strip()
        services = request.form.getlist("services")
        assigned_to = (request.form.get("assigned_to") or "").strip()
        delivery_details = (request.form.get("delivery_details") or "").strip()
        whatsapp_number = (request.form.get("whatsapp_number") or "").strip()
        client_email = (request.form.get("client_email") or "").strip()
        client_website = (request.form.get("client_website") or "").strip()
        client_address = (request.form.get("client_address") or "").strip()
        client_gst_number = (request.form.get("client_gst_number") or "").strip()

        required_fields = [
            ("Client", client_id),
            ("Services", services),
            ("Assigned To", assigned_to),
            ("Delivery Details", delivery_details),
        ]
        if any(not value for _, value in required_fields):
            flash("All fields are required.", "danger")
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

        services_text = ",".join(services)
        with get_db() as conn:
            conn.execute(
                """
                UPDATE projects
                SET client_id = ?,
                    services = ?,
                    assigned_to = ?,
                    delivery_details = ?,
                    client_name = client_name
                WHERE id = ?
                """,
                (
                    client_id,
                    services_text,
                    assigned_to,
                    delivery_details,
                    project_id,
                ),
            )
            conn.commit()

        flash("Project updated successfully.", "success")
        return redirect(url_for("admin_projects"))

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
                                <label class="form-label">Client</label>
                                <select class="form-select" name="client_id" required><option value="">Select client</option>{% for client in clients %}<option value="{{ client.id }}" {% if client.id == project.client_id %}selected{% endif %}>{{ client.name }}</option>{% endfor %}</select>
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
                            {% if false %}<div class="mb-3">
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
                            </div>{% endif %}
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
        clients=clients,
        current_services=current_services,
    )


@app.route("/admin/projects/<int:project_id>/delete", methods=["GET", "POST"])
@login_required
def delete_project(project_id):
    if current_user.role != "admin":
        flash("Admin access required.", "danger")
        return redirect(url_for("dashboard"))

    with get_db() as conn:
        project = conn.execute(
            "SELECT id, client_name, assigned_to FROM projects WHERE id = ?",
            (project_id,),
        ).fetchone()

    if project is None:
        flash("Project not found.", "warning")
        return redirect(url_for("admin_projects"))

    if request.method == "POST":
        with get_db() as conn:
            conn.execute("DELETE FROM projects WHERE id = ?", (project_id,))
            conn.commit()
        flash("Project deleted successfully.", "success")
        return redirect(url_for("admin_projects"))

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


@app.route("/admin/attendance/download")
@login_required
def download_attendance():
    if current_user.role != "admin":
        flash("Admin access required.", "danger")
        return redirect(url_for("dashboard"))
    with get_db() as conn:
        rows = conn.execute(
            "SELECT username, date, punch_in_time, punch_out_time, total_hours FROM attendance ORDER BY date DESC, username"
        ).fetchall()
    # Generate Excel file using openpyxl
    try:
        from openpyxl import Workbook  # type: ignore[import-untyped]
    except Exception:  # noqa: BLE001  # Catch import error or missing openpyxl dependency
        flash("openpyxl is not installed on the server.", "danger")
        return redirect(url_for("admin_attendance"))

    wb = Workbook()
    ws = wb.active
    assert ws is not None
    ws.title = "Attendance"
    headers = ["Username", "Date", "Punch In", "Punch Out", "Total Hours"]
    ws.append(headers)
    for r in rows:
        ws.append(
            [
                r["username"],
                r["date"],
                format_attendance_timestamp(r["punch_in_time"]),
                format_attendance_timestamp(r["punch_out_time"]),
                r["total_hours"],
            ]
        )

    bio = io.BytesIO()
    wb.save(bio)
    bio.seek(0)
    payload = bio.getvalue()
    headers = {
        "Content-Disposition": 'attachment; filename="attendance_report.xlsx"',
        "Content-Type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "Content-Length": str(len(payload)),
    }
    return Response(payload, headers=headers)


# Helper to retrieve employee display name
def get_employee_name_for_user(conn, user_id, fallback_name):
    emp = conn.execute(
        "SELECT name FROM employees WHERE user_id = ?", (user_id,)
    ).fetchone()
    if emp and emp["name"]:
        return str(emp["name"])
    usr = conn.execute(
        "SELECT full_name FROM users WHERE id = ?", (user_id,)
    ).fetchone()
    if usr and usr["full_name"]:
        return str(usr["full_name"])
    return str(fallback_name)


# Leave Management Module Routes


@app.route("/leave/apply", methods=["GET", "POST"])
@login_required
def apply_leave():
    if request.method == "POST":
        # Accept form data or JSON body
        if request.is_json and request.json:
            data = request.json
            leave_type = str(data.get("leave_type", "")).strip()
            start_date_str = str(data.get("start_date", "")).strip()
            end_date_str = str(data.get("end_date", "")).strip()
            reason = str(data.get("reason", "")).strip()
        else:
            leave_type = (request.form.get("leave_type") or "").strip()
            start_date_str = (request.form.get("start_date") or "").strip()
            end_date_str = (request.form.get("end_date") or "").strip()
            reason = (request.form.get("reason") or "").strip()

        if not leave_type or not start_date_str or not end_date_str or not reason:
            msg = "All fields (leave_type, start_date, end_date, reason) are required."
            flash(msg, "danger")
            if request.is_json:
                return jsonify({"status": "error", "message": msg}), 400
            return redirect(url_for("apply_leave"))

        try:
            start_date = datetime.datetime.strptime(start_date_str, "%Y-%m-%d").date()  # noqa: DTZ007  # Date string parsing
            end_date = datetime.datetime.strptime(end_date_str, "%Y-%m-%d").date()  # noqa: DTZ007  # Date string parsing
        except ValueError:
            msg = "Invalid date format. Use YYYY-MM-DD."
            flash(msg, "danger")
            if request.is_json:
                return jsonify({"status": "error", "message": msg}), 400
            return redirect(url_for("apply_leave"))

        if end_date < start_date:
            msg = "End date cannot be before start date."
            flash(msg, "danger")
            if request.is_json:
                return jsonify({"status": "error", "message": msg}), 400
            return redirect(url_for("apply_leave"))

        with get_db() as conn:
            # Calculate total_days excluding configured holidays
            holiday_rows = conn.execute(
                "SELECT date FROM holidays WHERE date >= ? AND date <= ?",
                (start_date_str, end_date_str),
            ).fetchall()
            holiday_dates = {h["date"] for h in holiday_rows}

            leave_days_count = 0.0
            curr_d = start_date
            while curr_d <= end_date:
                if curr_d.weekday() != 6 and curr_d.isoformat() not in holiday_dates:
                    leave_days_count += 1.0
                curr_d += datetime.timedelta(days=1)
            total_days = leave_days_count

            # Check duplicate pending request
            duplicate = conn.execute(
                """
                SELECT id FROM leave_requests
                WHERE user_id = ? AND leave_type = ? AND start_date = ? AND end_date = ? AND status = 'Pending'
                """,
                (current_user.id, leave_type, start_date_str, end_date_str),
            ).fetchone()
            if duplicate:
                msg = "An identical pending leave request already exists."
                flash(msg, "danger")
                if request.is_json:
                    return jsonify({"status": "error", "message": msg}), 400
                return redirect(url_for("apply_leave"))

            # Check overlapping pending or approved leave requests
            overlap = conn.execute(
                """
                SELECT id, leave_type, start_date, end_date FROM leave_requests
                WHERE user_id = ? AND status IN ('Pending', 'Approved')
                  AND start_date <= ? AND end_date >= ?
                """,
                (current_user.id, end_date_str, start_date_str),
            ).fetchone()
            if overlap:
                msg = "Your requested leave dates overlap with an existing pending or approved leave request."
                flash(msg, "danger")
                if request.is_json:
                    return jsonify({"status": "error", "message": msg}), 400
                return redirect(url_for("apply_leave"))

            employee_name = get_employee_name_for_user(
                conn, current_user.id, current_user.username
            )
            emp = conn.execute("SELECT id FROM employees WHERE user_id = ?", (current_user.id,)).fetchone()
            emp_id = f"EMP-{emp['id']}" if emp and emp["id"] else "N/A"
            applied_date = datetime.datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S")

            cursor = conn.execute(
                """
                INSERT INTO leave_requests (
                    user_id, employee_name, leave_type, start_date, end_date,
                    total_days, reason, status, applied_date
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 'Pending', ?)
                """,
                (
                    current_user.id,
                    employee_name,
                    leave_type,
                    start_date_str,
                    end_date_str,
                    total_days,
                    reason,
                    applied_date,
                ),
            )
            conn.commit()
            leave_id = cursor.lastrowid

        notify_admins(
            f"New Leave Request ({leave_type})",
            f"{employee_name} applied for {total_days} day(s) of {leave_type}.",
            url_for("pending_leave_requests"),
        )
        try:
            send_leave_submission_email_to_admin({
                "employee_name": employee_name,
                "employee_id": emp_id,
                "leave_type": leave_type,
                "start_date": start_date_str,
                "end_date": end_date_str,
                "total_days": total_days,
                "reason": reason,
                "applied_date": applied_date,
            })
        except Exception as e:  # noqa: BLE001
            print("Failed to trigger admin leave submission email:", e)

        msg = "Leave request submitted successfully."
        flash(msg, "success")
        if request.is_json:
            return jsonify({"status": "success", "message": msg, "leave_id": leave_id})
        return redirect(url_for("my_leave_requests"))

    valid_leave_types = [
        "Casual Leave",
        "Sick Leave",
        "Earned Leave",
        "Unpaid Leave",
        "Maternity Leave",
        "Paternity Leave",
    ]
    with get_db() as conn:
        leave_balance = get_user_paid_leave_balance(conn, current_user.id)

    if request.is_json or request.headers.get("Accept") == "application/json":
        return jsonify(
            {
                "status": "success",
                "action": "apply_leave",
                "leave_types": valid_leave_types,
                "leave_balance": leave_balance,
                "message": "Submit a POST request with leave_type, start_date, end_date, and reason to apply for leave.",
            }
        )
    return render_template_string(
        """
        {% extends "base.html" %}
        {% block title %}Apply for Leave{% endblock %}
        {% block page_content %}
        <div class="page-header d-flex flex-wrap justify-content-between align-items-center gap-3 mb-4">
            <div>
                <h1>Apply for Leave</h1>
                <p>Submit a new leave application for review and authorization.</p>
            </div>
            <div class="d-flex gap-2">
                <a class="btn btn-outline-secondary" href="{{ url_for('my_leave_requests') }}"><i class="bi bi-clock-history me-1"></i>My Requests</a>
                {% if current_user.role in ['admin', 'hr'] %}
                    <a class="btn btn-outline-secondary" href="{{ url_for('admin_leave_entitlements') }}"><i class="bi bi-person-workspace me-1"></i>Leave Entitlements</a>
                    <a class="btn btn-outline-secondary" href="{{ url_for('pending_leave_requests') }}"><i class="bi bi-hourglass-split me-1"></i>Pending Queue</a>
                    <a class="btn btn-outline-secondary" href="{{ url_for('view_all_leave_requests') }}"><i class="bi bi-list-task me-1"></i>All Requests</a>
                {% endif %}
            </div>
        </div>

        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="alert alert-{{ category }} alert-dismissible fade show" role="alert">
                        {{ message }}
                        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
                    </div>
                {% endfor %}
            {% endif %}
        {% endwith %}

        <div class="row g-3 mb-4 mx-auto" style="max-width: 680px;">
            <div class="col-md-4">
                <div class="card shadow-sm border-0 border-start border-primary border-4 text-center py-2">
                    <div class="card-body py-2">
                        <div class="text-muted small fw-semibold">Paid Entitlement</div>
                        <div class="fs-4 fw-bold text-primary">{{ leave_balance.entitlement }} <span class="fs-6 text-muted">days</span></div>
                    </div>
                </div>
            </div>
            <div class="col-md-4">
                <div class="card shadow-sm border-0 border-start border-warning border-4 text-center py-2">
                    <div class="card-body py-2">
                        <div class="text-muted small fw-semibold">Approved Used</div>
                        <div class="fs-4 fw-bold text-warning">{{ leave_balance.used }} <span class="fs-6 text-muted">days</span></div>
                    </div>
                </div>
            </div>
            <div class="col-md-4">
                <div class="card shadow-sm border-0 border-start border-success border-4 text-center py-2">
                    <div class="card-body py-2">
                        <div class="text-muted small fw-semibold">Remaining Balance</div>
                        <div class="fs-4 fw-bold text-success">{{ leave_balance.remaining }} <span class="fs-6 text-muted">days</span></div>
                    </div>
                </div>
            </div>
        </div>

        <div class="card shadow-sm mx-auto" style="max-width: 680px;">
            <div class="card-body">
                <form method="post">
                    <div class="mb-3">
                        <label class="form-label fw-semibold">Leave Type</label>
                        <select class="form-select" name="leave_type" required>
                            <option value="">Select Leave Type</option>
                            <option value="Casual Leave">Casual Leave</option>
                            <option value="Sick Leave">Sick Leave</option>
                            <option value="Earned Leave">Earned Leave</option>
                            <option value="Unpaid Leave">Unpaid Leave</option>
                            <option value="Maternity Leave">Maternity Leave</option>
                            <option value="Paternity Leave">Paternity Leave</option>
                        </select>
                    </div>
                    <div class="row g-3 mb-3">
                        <div class="col-md-6">
                            <label class="form-label fw-semibold">Start Date</label>
                            <input class="form-control" type="date" name="start_date" required>
                        </div>
                        <div class="col-md-6">
                            <label class="form-label fw-semibold">End Date</label>
                            <input class="form-control" type="date" name="end_date" required>
                        </div>
                    </div>
                    <div class="mb-4">
                        <label class="form-label fw-semibold">Reason for Leave</label>
                        <textarea class="form-control" name="reason" rows="3" placeholder="Provide details regarding your leave request..." required></textarea>
                    </div>
                    <div class="d-flex justify-content-end gap-2">
                        <a class="btn btn-outline-secondary" href="{{ url_for('my_leave_requests') }}">Cancel</a>
                        <button class="btn btn-primary" type="submit"><i class="bi bi-send me-1"></i>Submit Application</button>
                    </div>
                </form>
            </div>
        </div>
        {% endblock %}
        """,
        leave_balance=leave_balance,
    )


@app.route("/leave/my-requests", methods=["GET"])
@login_required
def my_leave_requests():
    from_date = (request.args.get("from_date") or request.args.get("start_date") or "").strip()
    to_date = (request.args.get("to_date") or request.args.get("end_date") or "").strip()

    valid_date_range = True
    if from_date and to_date and from_date > to_date:
        flash("From Date cannot be after To Date.", "warning")
        valid_date_range = False

    query = """
        SELECT id, user_id, employee_name, leave_type, start_date, end_date,
               total_days, reason, status, applied_date, approved_by, approval_date,
               comments, rejection_reason
        FROM leave_requests
        WHERE user_id = ?
    """
    params = [current_user.id]

    if valid_date_range:
        if from_date and to_date:
            query += " AND start_date <= ? AND end_date >= ?"
            params.extend([to_date, from_date])
        elif from_date:
            query += " AND end_date >= ?"
            params.append(from_date)
        elif to_date:
            query += " AND start_date <= ?"
            params.append(to_date)

    query += " ORDER BY applied_date DESC, id DESC"

    with get_db() as conn:
        rows = conn.execute(query, params).fetchall()
        requests_list = [dict(row) for row in rows]
        leave_balance = get_user_paid_leave_balance(conn, current_user.id)

    if request.is_json or request.headers.get("Accept") == "application/json":
        return jsonify({"status": "success", "from_date": from_date, "to_date": to_date, "leave_requests": requests_list, "leave_balance": leave_balance})

    return render_template_string(
        """
        {% extends "base.html" %}
        {% block title %}My Leave Requests{% endblock %}
        {% block page_content %}
        <div class="page-header d-flex flex-wrap justify-content-between align-items-center gap-3 mb-4">
            <div>
                <h1>My Leave Requests</h1>
                <p>Track the status of your submitted leave applications.</p>
            </div>
            <div class="d-flex gap-2">
                <a class="btn btn-primary" href="{{ url_for('apply_leave') }}"><i class="bi bi-plus-lg me-1"></i>Apply Leave</a>
                {% if current_user.role in ['admin', 'hr'] %}
                    <a class="btn btn-outline-secondary" href="{{ url_for('admin_leave_entitlements') }}"><i class="bi bi-person-workspace me-1"></i>Leave Entitlements</a>
                    <a class="btn btn-outline-secondary" href="{{ url_for('pending_leave_requests') }}"><i class="bi bi-hourglass-split me-1"></i>Pending Queue</a>
                    <a class="btn btn-outline-secondary" href="{{ url_for('view_all_leave_requests') }}"><i class="bi bi-list-task me-1"></i>All Leave History</a>
                {% endif %}
            </div>
        </div>

        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="alert alert-{{ category }} alert-dismissible fade show" role="alert">
                        {{ message }}
                        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
                    </div>
                {% endfor %}
            {% endif %}
        {% endwith %}

        <div class="row g-3 mb-4">
            <div class="col-md-4">
                <div class="card shadow-sm border-0 border-start border-primary border-4 text-center py-2">
                    <div class="card-body py-2">
                        <div class="text-muted small fw-semibold">Paid Entitlement</div>
                        <div class="fs-4 fw-bold text-primary">{{ leave_balance.entitlement }} <span class="fs-6 text-muted">days</span></div>
                    </div>
                </div>
            </div>
            <div class="col-md-4">
                <div class="card shadow-sm border-0 border-start border-warning border-4 text-center py-2">
                    <div class="card-body py-2">
                        <div class="text-muted small fw-semibold">Approved Used</div>
                        <div class="fs-4 fw-bold text-warning">{{ leave_balance.used }} <span class="fs-6 text-muted">days</span></div>
                    </div>
                </div>
            </div>
            <div class="col-md-4">
                <div class="card shadow-sm border-0 border-start border-success border-4 text-center py-2">
                    <div class="card-body py-2">
                        <div class="text-muted small fw-semibold">Remaining Balance</div>
                        <div class="fs-4 fw-bold text-success">{{ leave_balance.remaining }} <span class="fs-6 text-muted">days</span></div>
                    </div>
                </div>
            </div>
        </div>

        <div class="card shadow-sm mb-4">
            <div class="card-body py-3">
                <form method="get" class="row g-3 align-items-end">
                    <div class="col-md-4 col-sm-6">
                        <label class="form-label small fw-semibold text-muted mb-1">From Date</label>
                        <input type="date" class="form-control form-control-sm" name="from_date" value="{{ from_date or '' }}">
                    </div>
                    <div class="col-md-4 col-sm-6">
                        <label class="form-label small fw-semibold text-muted mb-1">To Date</label>
                        <input type="date" class="form-control form-control-sm" name="to_date" value="{{ to_date or '' }}">
                    </div>
                    <div class="col-md-4 col-sm-12 d-flex gap-2">
                        <button type="submit" class="btn btn-primary btn-sm px-3 flex-fill"><i class="bi bi-funnel me-1"></i>Apply Filter</button>
                        {% if from_date or to_date %}
                            <a class="btn btn-outline-secondary btn-sm px-3" href="{{ url_for('my_leave_requests') }}"><i class="bi bi-x-circle me-1"></i>Clear</a>
                        {% endif %}
                    </div>
                </form>
            </div>
        </div>

        <div class="card shadow-sm">
            <div class="card-body p-0">
                <div class="table-responsive">
                    <table class="table table-hover align-middle mb-0">
                        <thead class="table-light">
                            <tr>
                                <th>Leave Type</th>
                                <th>Duration</th>
                                <th>Days</th>
                                <th>Reason</th>
                                <th>Status</th>
                                <th>Applied On</th>
                                <th>Remarks / Reason</th>
                                <th class="text-end">Action</th>
                            </tr>
                        </thead>
                        <tbody>
                            {% for req in requests %}
                                <tr>
                                    <td class="fw-semibold">{{ req.leave_type }}</td>
                                    <td><i class="bi bi-calendar-event me-1 text-muted"></i>{{ req.start_date }} <span class="text-muted">to</span> {{ req.end_date }}</td>
                                    <td><span class="badge bg-light text-dark border">{{ req.total_days }} day{% if req.total_days != 1 %}s{% endif %}</span></td>
                                    <td style="max-width: 220px;" class="text-truncate" title="{{ req.reason }}">{{ req.reason }}</td>
                                    <td>
                                        <span class="badge bg-{% if req.status == 'Approved' %}success{% elif req.status == 'Rejected' %}danger{% elif req.status == 'Cancelled' %}secondary{% else %}warning text-dark{% endif %}">
                                            {{ req.status }}
                                        </span>
                                    </td>
                                    <td class="text-muted small">{{ req.applied_date }}</td>
                                    <td class="small">
                                        {% if req.status == 'Rejected' and req.rejection_reason %}
                                            <span class="text-danger"><i class="bi bi-exclamation-circle me-1"></i>{{ req.rejection_reason }}</span>
                                        {% elif req.comments %}
                                            <span class="text-muted"><i class="bi bi-chat-left-text me-1"></i>{{ req.comments }}</span>
                                        {% else %}
                                            <span class="text-muted">-</span>
                                        {% endif %}
                                    </td>
                                    <td class="text-end">
                                        {% if req.status == 'Pending' %}
                                            <form method="post" action="{{ url_for('cancel_leave', leave_id=req.id) }}" style="display:inline;">
                                                <button class="btn btn-sm btn-outline-danger" onclick="return confirm('Are you sure you want to cancel this pending leave request?')">
                                                    <i class="bi bi-x-circle me-1"></i>Cancel
                                                </button>
                                            </form>
                                        {% else %}
                                            <span class="text-muted small">-</span>
                                        {% endif %}
                                    </td>
                                </tr>
                            {% else %}
                                <tr>
                                    <td colspan="8" class="text-center py-4 text-muted">
                                        <i class="bi bi-calendar-x display-6 d-block mb-2"></i>
                                        No leave requests found. <a href="{{ url_for('apply_leave') }}">Apply for leave</a>
                                    </td>
                                </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
        {% endblock %}
        """,
        requests=requests_list,
        leave_balance=leave_balance,
    )


@app.route("/leave/cancel/<int:leave_id>", methods=["POST"])
@login_required
def cancel_leave(leave_id):
    with get_db() as conn:
        req = conn.execute(
            "SELECT * FROM leave_requests WHERE id = ? AND user_id = ?",
            (leave_id, current_user.id),
        ).fetchone()

        if req is None:
            msg = "Leave request not found or access denied."
            flash(msg, "danger")
            if request.is_json:
                return jsonify({"status": "error", "message": msg}), 404
            return redirect(url_for("my_leave_requests"))

        if req["status"] != "Pending":
            msg = "Only pending leave requests can be cancelled."
            flash(msg, "warning")
            if request.is_json:
                return jsonify({"status": "error", "message": msg}), 400
            return redirect(url_for("my_leave_requests"))

        conn.execute(
            "UPDATE leave_requests SET status = 'Cancelled' WHERE id = ?",
            (leave_id,),
        )
        conn.commit()

    msg = "Leave request cancelled successfully."
    flash(msg, "success")
    if request.is_json:
        return jsonify({"status": "success", "message": msg})
    return redirect(url_for("my_leave_requests"))


@app.route("/admin/leave/entitlements", methods=["GET", "POST"])
@login_required
def admin_leave_entitlements():
    if current_user.role not in ("admin", "hr"):
        flash("Access denied.", "danger")
        if request.is_json or request.headers.get("Accept") == "application/json":
            return jsonify({"status": "error", "message": "Access denied."}), 403
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        if request.is_json and request.json:
            data = request.json
            target_user_id = data.get("user_id")
            entitlement_val = data.get("entitlement")
        else:
            target_user_id = request.form.get("user_id")
            entitlement_val = request.form.get("entitlement")

        try:
            if target_user_id is None or entitlement_val is None:
                raise ValueError("Missing user_id or entitlement value.")
            target_user_id = int(target_user_id)
            entitlement_val = float(entitlement_val)
            if entitlement_val < 0:
                raise ValueError("Entitlement cannot be negative.")
        except (TypeError, ValueError):
            msg = "Invalid employee or entitlement value provided."
            flash(msg, "danger")
            if request.is_json:
                return jsonify({"status": "error", "message": msg}), 400
            return redirect(url_for("admin_leave_entitlements"))

        with get_db() as conn:
            target_user = conn.execute("SELECT id, username, full_name FROM users WHERE id = ?", (target_user_id,)).fetchone()
            if not target_user:
                msg = "User account not found."
                flash(msg, "danger")
                if request.is_json:
                    return jsonify({"status": "error", "message": msg}), 404
                return redirect(url_for("admin_leave_entitlements"))

            set_user_paid_leave_entitlement(conn, target_user_id, entitlement_val)
            user_name = target_user["full_name"] or target_user["username"]

        msg = f"Paid leave entitlement for '{user_name}' updated to {entitlement_val} days."
        flash(msg, "success")
        create_notification(
            target_user_id,
            "Paid Leave Entitlement Updated",
            f"Your annual paid leave entitlement has been set to {entitlement_val} days.",
            url_for("my_leave_requests"),
        )
        if request.is_json:
            return jsonify({"status": "success", "message": msg, "user_id": target_user_id, "entitlement": entitlement_val})
        return redirect(url_for("admin_leave_entitlements"))

    with get_db() as conn:
        users = conn.execute(
            """
            SELECT u.id, u.username, u.full_name, u.email, u.role
            FROM users u
            ORDER BY u.full_name ASC, u.username ASC
            """
        ).fetchall()

        entitlements_list = []
        for u in users:
            bal = get_user_paid_leave_balance(conn, u["id"])
            entitlements_list.append({
                "user_id": u["id"],
                "username": u["username"],
                "full_name": u["full_name"],
                "email": u["email"],
                "role": u["role"],
                "entitlement": bal["entitlement"],
                "used": bal["used"],
                "remaining": bal["remaining"],
            })

    if request.is_json or request.headers.get("Accept") == "application/json":
        return jsonify({"status": "success", "entitlements": entitlements_list})

    return render_template_string(
        """
        {% extends "base.html" %}
        {% block title %}Paid Leave Entitlements{% endblock %}
        {% block page_content %}
        <div class="page-header d-flex flex-wrap justify-content-between align-items-center gap-3 mb-4">
            <div>
                <h1>Paid Leave Entitlements</h1>
                <p>Manage individual employee paid leave entitlements and view real-time balances.</p>
            </div>
            <div class="d-flex gap-2">
                <a class="btn btn-outline-secondary" href="{{ url_for('pending_leave_requests') }}"><i class="bi bi-hourglass-split me-1"></i>Pending Queue</a>
                <a class="btn btn-outline-secondary" href="{{ url_for('view_all_leave_requests') }}"><i class="bi bi-list-task me-1"></i>All Requests</a>
            </div>
        </div>

        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="alert alert-{{ category }} alert-dismissible fade show" role="alert">
                        {{ message }}
                        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
                    </div>
                {% endfor %}
            {% endif %}
        {% endwith %}

        <div class="card shadow-sm">
            <div class="card-header bg-white py-3 border-0 d-flex justify-content-between align-items-center">
                <h5 class="card-title mb-0 fw-bold"><i class="bi bi-person-workspace me-2 text-primary"></i>Employee Leave Balances</h5>
                <span class="badge bg-light text-dark border">Total Users: {{ entitlements|length }}</span>
            </div>
            <div class="card-body p-0">
                <div class="table-responsive">
                    <table class="table table-hover align-middle mb-0">
                        <thead class="table-light">
                            <tr>
                                <th>Employee / User</th>
                                <th>Role</th>
                                <th>Paid Leave Entitlement</th>
                                <th>Approved Used</th>
                                <th>Remaining Balance</th>
                                <th class="text-end">Action</th>
                            </tr>
                        </thead>
                        <tbody>
                            {% for item in entitlements %}
                                <tr>
                                    <td class="fw-bold">
                                        <i class="bi bi-person-circle me-2 text-secondary"></i>
                                        {{ item.full_name or item.username }}
                                        {% if item.full_name %}<br><small class="text-muted ms-4">@{{ item.username }}</small>{% endif %}
                                    </td>
                                    <td>
                                        <span class="badge bg-{% if item.role == 'admin' %}primary{% elif item.role == 'hr' %}info text-dark{% else %}secondary{% endif %}">
                                            {{ 'HR' if item.role == 'hr' else (item.role|title) }}
                                        </span>
                                    </td>
                                    <td>
                                        <span class="fw-bold text-dark fs-6">{{ item.entitlement }} days</span>
                                    </td>
                                    <td>
                                        <span class="badge bg-warning text-dark fs-6">{{ item.used }} days</span>
                                    </td>
                                    <td>
                                        <span class="badge bg-{% if item.remaining > 3 %}success{% elif item.remaining > 0 %}warning text-dark{% else %}danger{% endif %} fs-6">
                                            {{ item.remaining }} days remaining
                                        </span>
                                    </td>
                                    <td class="text-end">
                                        <button type="button" class="btn btn-sm btn-outline-primary" data-bs-toggle="modal" data-bs-target="#editModal{{ item.user_id }}">
                                            <i class="bi bi-pencil-square me-1"></i>Set Entitlement
                                        </button>

                                        <div class="modal fade text-start" id="editModal{{ item.user_id }}" tabindex="-1" aria-hidden="true">
                                            <div class="modal-dialog modal-dialog-centered">
                                                <div class="modal-content">
                                                    <form method="post" action="{{ url_for('admin_leave_entitlements') }}">
                                                        <input type="hidden" name="user_id" value="{{ item.user_id }}">
                                                        <div class="modal-header">
                                                            <h5 class="modal-header-title fw-bold">Set Paid Leave Entitlement</h5>
                                                            <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                                                        </div>
                                                        <div class="modal-body">
                                                            <p class="mb-3">Updating paid leave entitlement for <strong>{{ item.full_name or item.username }}</strong> (@{{ item.username }}):</p>
                                                            <div class="mb-3">
                                                                <label class="form-label fw-semibold">Annual Paid Leave Entitlement (Days)</label>
                                                                <input type="number" step="0.5" min="0" class="form-control" name="entitlement" value="{{ item.entitlement }}" required>
                                                            </div>
                                                            <div class="alert alert-info py-2 small mb-0">
                                                                <i class="bi bi-info-circle me-1"></i>Current Approved Paid Used: <strong>{{ item.used }} days</strong>. New balance will be <strong>Entitlement - {{ item.used }}</strong>.
                                                            </div>
                                                        </div>
                                                        <div class="modal-footer">
                                                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                                                            <button type="submit" class="btn btn-primary"><i class="bi bi-check-circle me-1"></i>Save Entitlement</button>
                                                        </div>
                                                    </form>
                                                </div>
                                            </div>
                                        </div>
                                    </td>
                                </tr>
                            {% else %}
                                <tr>
                                    <td colspan="6" class="text-center py-4 text-muted">No employees found.</td>
                                </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
        {% endblock %}
        """,
        entitlements=entitlements_list,
    )


@app.route("/admin/leave/all", methods=["GET"])
@login_required
def view_all_leave_requests():
    if current_user.role not in ("admin", "hr"):
        flash("Access denied.", "danger")
        if request.is_json or request.headers.get("Accept") == "application/json":
            return (
                jsonify({"status": "error", "message": "Access denied."}),
                403,
            )
        return redirect(url_for("dashboard"))

    status_filter = (request.args.get("status") or "All").strip()
    from_date = (request.args.get("from_date") or request.args.get("start_date") or "").strip()
    to_date = (request.args.get("to_date") or request.args.get("end_date") or "").strip()

    valid_date_range = True
    if from_date and to_date and from_date > to_date:
        flash("From Date cannot be after To Date.", "warning")
        valid_date_range = False

    query = """
        SELECT id, user_id, employee_name, leave_type, start_date, end_date,
               total_days, reason, status, applied_date, approved_by, approval_date,
               comments, rejection_reason
        FROM leave_requests
        WHERE 1 = 1
    """
    params = []
    if status_filter != "All":
        query += " AND status = ?"
        params.append(status_filter)

    if valid_date_range:
        if from_date and to_date:
            query += " AND start_date <= ? AND end_date >= ?"
            params.extend([to_date, from_date])
        elif from_date:
            query += " AND end_date >= ?"
            params.append(from_date)
        elif to_date:
            query += " AND start_date <= ?"
            params.append(to_date)

    query += " ORDER BY applied_date DESC, id DESC"

    with get_db() as conn:
        rows = conn.execute(query, params).fetchall()
        requests_list = [dict(row) for row in rows]

    if request.is_json or request.headers.get("Accept") == "application/json":
        return jsonify(
            {
                "status": "success",
                "status_filter": status_filter,
                "from_date": from_date,
                "to_date": to_date,
                "leave_requests": requests_list,
            }
        )

    return render_template_string(
        """
        {% extends "base.html" %}
        {% block title %}All Leave Requests{% endblock %}
        {% block page_content %}
        <div class="page-header d-flex flex-wrap justify-content-between align-items-center gap-3 mb-4">
            <div>
                <h1>All Leave Requests</h1>
                <p>Master audit log of all leave applications across the company.</p>
            </div>
            <div class="d-flex gap-2">
                <a class="btn btn-outline-secondary" href="{{ url_for('pending_leave_requests') }}"><i class="bi bi-hourglass-split me-1"></i>Pending Queue</a>
                <a class="btn btn-primary" href="{{ url_for('apply_leave') }}"><i class="bi bi-plus-lg me-1"></i>Apply Leave</a>
            </div>
        </div>

        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="alert alert-{{ category }} alert-dismissible fade show" role="alert">
                        {{ message }}
                        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
                    </div>
                {% endfor %}
            {% endif %}
        {% endwith %}

        <div class="card shadow-sm mb-4">
            <div class="card-body py-3">
                <form method="get" class="row g-3 align-items-end">
                    <div class="col-md-3 col-sm-6">
                        <label class="form-label small fw-semibold text-muted mb-1">Status Filter</label>
                        <select class="form-select form-select-sm" name="status">
                            <option value="All" {% if status_filter == 'All' %}selected{% endif %}>All Statuses</option>
                            <option value="Pending" {% if status_filter == 'Pending' %}selected{% endif %}>Pending</option>
                            <option value="Approved" {% if status_filter == 'Approved' %}selected{% endif %}>Approved</option>
                            <option value="Rejected" {% if status_filter == 'Rejected' %}selected{% endif %}>Rejected</option>
                            <option value="Cancelled" {% if status_filter == 'Cancelled' %}selected{% endif %}>Cancelled</option>
                        </select>
                    </div>
                    <div class="col-md-3 col-sm-6">
                        <label class="form-label small fw-semibold text-muted mb-1">From Date</label>
                        <input type="date" class="form-control form-control-sm" name="from_date" value="{{ from_date or '' }}">
                    </div>
                    <div class="col-md-3 col-sm-6">
                        <label class="form-label small fw-semibold text-muted mb-1">To Date</label>
                        <input type="date" class="form-control form-control-sm" name="to_date" value="{{ to_date or '' }}">
                    </div>
                    <div class="col-md-3 col-sm-6 d-flex gap-2">
                        <button type="submit" class="btn btn-primary btn-sm px-3 flex-fill"><i class="bi bi-funnel me-1"></i>Apply</button>
                        {% if status_filter != 'All' or from_date or to_date %}
                            <a class="btn btn-outline-secondary btn-sm px-3" href="{{ url_for('view_all_leave_requests') }}"><i class="bi bi-x-circle me-1"></i>Clear</a>
                        {% endif %}
                    </div>
                </form>
            </div>
        </div>

        <div class="card shadow-sm">
            <div class="card-body p-0">
                <div class="table-responsive">
                    <table class="table table-hover align-middle mb-0">
                        <thead class="table-light">
                            <tr>
                                <th>Employee</th>
                                <th>Leave Type</th>
                                <th>Dates</th>
                                <th>Days</th>
                                <th>Reason</th>
                                <th>Status</th>
                                <th>Applied On</th>
                                <th>Processed By</th>
                                <th>Remarks / Reason</th>
                            </tr>
                        </thead>
                        <tbody>
                            {% for req in requests %}
                                <tr>
                                    <td class="fw-bold">{{ req.employee_name }}</td>
                                    <td>{{ req.leave_type }}</td>
                                    <td>{{ req.start_date }} <span class="text-muted">to</span> {{ req.end_date }}</td>
                                    <td><span class="badge bg-light text-dark border">{{ req.total_days }} day{% if req.total_days != 1 %}s{% endif %}</span></td>
                                    <td style="max-width: 200px;" class="text-truncate" title="{{ req.reason }}">{{ req.reason }}</td>
                                    <td>
                                        <span class="badge bg-{% if req.status == 'Approved' %}success{% elif req.status == 'Rejected' %}danger{% elif req.status == 'Cancelled' %}secondary{% else %}warning text-dark{% endif %}">
                                            {{ req.status }}
                                        </span>
                                    </td>
                                    <td class="text-muted small">{{ req.applied_date }}</td>
                                    <td class="small">
                                        {% if req.approved_by %}
                                            <span class="fw-semibold">{{ req.approved_by }}</span>
                                            {% if req.approval_date %}<br><small class="text-muted">{{ req.approval_date }}</small>{% endif %}
                                        {% else %}
                                            <span class="text-muted">-</span>
                                        {% endif %}
                                    </td>
                                    <td class="small">
                                        {% if req.status == 'Rejected' and req.rejection_reason %}
                                            <span class="text-danger"><i class="bi bi-exclamation-circle me-1"></i>{{ req.rejection_reason }}</span>
                                        {% elif req.comments %}
                                            <span class="text-muted"><i class="bi bi-chat-left-text me-1"></i>{{ req.comments }}</span>
                                        {% else %}
                                            <span class="text-muted">-</span>
                                        {% endif %}
                                    </td>
                                </tr>
                            {% else %}
                                <tr>
                                    <td colspan="9" class="text-center py-4 text-muted">
                                        <i class="bi bi-inbox display-6 d-block mb-2"></i>
                                        No leave requests found matching criteria.
                                    </td>
                                </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
        {% endblock %}
        """,
        requests=requests_list,
        status_filter=status_filter,
        from_date=from_date,
        to_date=to_date,
    )


@app.route("/admin/leave/pending", methods=["GET"])
@login_required
def pending_leave_requests():
    if current_user.role not in ("admin", "hr"):
        flash("Access denied.", "danger")
        if request.is_json or request.headers.get("Accept") == "application/json":
            return (
                jsonify({"status": "error", "message": "Access denied."}),
                403,
            )
        return redirect(url_for("dashboard"))

    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT id, user_id, employee_name, leave_type, start_date, end_date,
                   total_days, reason, status, applied_date, approved_by, approval_date,
                   comments, rejection_reason
            FROM leave_requests
            WHERE status = 'Pending'
            ORDER BY applied_date ASC, id ASC
            """
        ).fetchall()
        requests_list = [dict(row) for row in rows]

    if request.is_json or request.headers.get("Accept") == "application/json":
        return jsonify({"status": "success", "pending_requests": requests_list})

    return render_template_string(
        """
        {% extends "base.html" %}
        {% block title %}Pending Leave Requests{% endblock %}
        {% block page_content %}
        <div class="page-header d-flex flex-wrap justify-content-between align-items-center gap-3 mb-4">
            <div>
                <h1>Pending Leave Requests</h1>
                <p>Review and process employee leave applications queued for authorization.</p>
            </div>
            <div class="d-flex gap-2">
                <a class="btn btn-outline-secondary active" href="{{ url_for('pending_leave_requests') }}"><i class="bi bi-hourglass-split me-1"></i>Pending Queue</a>
                <a class="btn btn-outline-secondary" href="{{ url_for('view_all_leave_requests') }}"><i class="bi bi-list-task me-1"></i>All Leave History</a>
            </div>
        </div>

        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="alert alert-{{ category }} alert-dismissible fade show" role="alert">
                        {{ message }}
                        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
                    </div>
                {% endfor %}
            {% endif %}
        {% endwith %}

        <div class="card shadow-sm">
            <div class="card-body p-0">
                <div class="table-responsive">
                    <table class="table table-hover align-middle mb-0">
                        <thead class="table-light">
                            <tr>
                                <th>Employee</th>
                                <th>Type</th>
                                <th>Dates</th>
                                <th>Days</th>
                                <th>Reason</th>
                                <th>Applied On</th>
                                <th class="text-end">Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            {% for req in requests %}
                                <tr>
                                    <td class="fw-bold"><i class="bi bi-person me-1 text-primary"></i>{{ req.employee_name }}</td>
                                    <td><span class="badge bg-light text-dark border">{{ req.leave_type }}</span></td>
                                    <td>{{ req.start_date }} <span class="text-muted">to</span> {{ req.end_date }}</td>
                                    <td><span class="badge bg-info text-dark">{{ req.total_days }} day{% if req.total_days != 1 %}s{% endif %}</span></td>
                                    <td style="max-width: 250px;">{{ req.reason }}</td>
                                    <td class="text-muted small">{{ req.applied_date }}</td>
                                    <td class="text-end">
                                        <div class="d-inline-flex gap-2">
                                            <button type="button" class="btn btn-sm btn-success" data-bs-toggle="modal" data-bs-target="#approveModal{{ req.id }}">
                                                <i class="bi bi-check-circle me-1"></i>Approve
                                            </button>
                                            <button type="button" class="btn btn-sm btn-danger" data-bs-toggle="modal" data-bs-target="#rejectModal{{ req.id }}">
                                                <i class="bi bi-x-circle me-1"></i>Reject
                                            </button>
                                        </div>

                                        <!-- Approve Modal -->
                                        <div class="modal fade text-start" id="approveModal{{ req.id }}" tabindex="-1" aria-hidden="true">
                                            <div class="modal-dialog">
                                                <div class="modal-content">
                                                    <form method="post" action="{{ url_for('approve_leave', leave_id=req.id) }}">
                                                        <div class="modal-header">
                                                            <h5 class="modal-title">Approve Leave Request</h5>
                                                            <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                                                        </div>
                                                        <div class="modal-body">
                                                            <p>Approve leave for <strong>{{ req.employee_name }}</strong> ({{ req.start_date }} to {{ req.end_date }})?</p>
                                                            <div class="mb-3">
                                                                <label class="form-label">Approval Comments (Optional)</label>
                                                                <textarea class="form-control" name="comments" rows="2" placeholder="Optional comments for employee..."></textarea>
                                                            </div>
                                                        </div>
                                                        <div class="modal-footer">
                                                            <button type="button" class="btn btn-outline-secondary" data-bs-dismiss="modal">Cancel</button>
                                                            <button type="submit" class="btn btn-success">Confirm Approval</button>
                                                        </div>
                                                    </form>
                                                </div>
                                            </div>
                                        </div>

                                        <!-- Reject Modal -->
                                        <div class="modal fade text-start" id="rejectModal{{ req.id }}" tabindex="-1" aria-hidden="true">
                                            <div class="modal-dialog">
                                                <div class="modal-content">
                                                    <form method="post" action="{{ url_for('reject_leave', leave_id=req.id) }}">
                                                        <div class="modal-header">
                                                            <h5 class="modal-title text-danger">Reject Leave Request</h5>
                                                            <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                                                        </div>
                                                        <div class="modal-body">
                                                            <p>Reject leave request for <strong>{{ req.employee_name }}</strong>?</p>
                                                            <div class="mb-3">
                                                                <label class="form-label">Rejection Reason <span class="text-danger">*</span></label>
                                                                <textarea class="form-control" name="rejection_reason" rows="2" placeholder="Specify reason for rejection..." required></textarea>
                                                            </div>
                                                            <div class="mb-3">
                                                                <label class="form-label">Additional Comments (Optional)</label>
                                                                <textarea class="form-control" name="comments" rows="2" placeholder="Optional comments..."></textarea>
                                                            </div>
                                                        </div>
                                                        <div class="modal-footer">
                                                            <button type="button" class="btn btn-outline-secondary" data-bs-dismiss="modal">Cancel</button>
                                                            <button type="submit" class="btn btn-danger">Confirm Rejection</button>
                                                        </div>
                                                    </form>
                                                </div>
                                            </div>
                                        </div>
                                    </td>
                                </tr>
                            {% else %}
                                <tr>
                                    <td colspan="7" class="text-center py-4 text-muted">
                                        <i class="bi bi-check-all display-6 d-block mb-2 text-success"></i>
                                        No pending leave requests to process.
                                    </td>
                                </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
        <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>
        {% endblock %}
        """,
        requests=requests_list,
    )


@app.route("/admin/leave/<int:leave_id>/approve", methods=["POST"])
@login_required
def approve_leave(leave_id):
    if current_user.role not in ("admin", "hr"):
        flash("Access denied.", "danger")
        if request.is_json:
            return (
                jsonify({"status": "error", "message": "Access denied."}),
                403,
            )
        return redirect(url_for("dashboard"))

    if request.is_json and request.json:
        comments = str(request.json.get("comments", "")).strip()
    else:
        comments = (request.form.get("comments") or "").strip()

    with get_db() as conn:
        req = conn.execute(
            "SELECT * FROM leave_requests WHERE id = ?",
            (leave_id,),
        ).fetchone()

        if req is None:
            msg = "Leave request not found."
            flash(msg, "danger")
            if request.is_json:
                return jsonify({"status": "error", "message": msg}), 404
            return redirect(url_for("pending_leave_requests"))

        if req["status"] != "Pending":
            msg = f"Cannot approve leave request with status '{req['status']}'."
            flash(msg, "warning")
            if request.is_json:
                return jsonify({"status": "error", "message": msg}), 400
            return redirect(url_for("pending_leave_requests"))

        approval_date = datetime.datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S")
        conn.execute(
            """
            UPDATE leave_requests
            SET status = 'Approved',
                approved_by = ?,
                approval_date = ?,
                comments = ?
            WHERE id = ?
            """,
            (current_user.username, approval_date, comments, leave_id),
        )
        conn.commit()

    create_notification(
        req["user_id"],
        "Leave Request Approved",
        f"Your {req['leave_type']} request ({req['start_date']} to {req['end_date']}) has been approved.",
        url_for("my_leave_requests"),
    )
    try:
        send_leave_approval_email_to_employee(
            req["user_id"],
            dict(req),
            comments=comments,
        )
    except Exception as e:  # noqa: BLE001
        print("Failed to trigger leave approval email:", e)

    msg = "Leave request approved successfully."
    flash(msg, "success")
    if request.is_json:
        return jsonify({"status": "success", "message": msg, "leave_id": leave_id})
    return redirect(url_for("pending_leave_requests"))


@app.route("/admin/leave/<int:leave_id>/reject", methods=["POST"])
@login_required
def reject_leave(leave_id):
    if current_user.role not in ("admin", "hr"):
        flash("Access denied.", "danger")
        if request.is_json:
            return (
                jsonify({"status": "error", "message": "Access denied."}),
                403,
            )
        return redirect(url_for("dashboard"))

    if request.is_json and request.json:
        data = request.json
        rejection_reason = str(data.get("rejection_reason", "")).strip()
        comments = str(data.get("comments", "")).strip()
    else:
        rejection_reason = (request.form.get("rejection_reason") or "").strip()
        comments = (request.form.get("comments") or "").strip()

    if not rejection_reason:
        msg = "Rejection reason is required."
        flash(msg, "danger")
        if request.is_json:
            return jsonify({"status": "error", "message": msg}), 400
        return redirect(url_for("pending_leave_requests"))

    with get_db() as conn:
        req = conn.execute(
            "SELECT * FROM leave_requests WHERE id = ?",
            (leave_id,),
        ).fetchone()

        if req is None:
            msg = "Leave request not found."
            flash(msg, "danger")
            if request.is_json:
                return jsonify({"status": "error", "message": msg}), 404
            return redirect(url_for("pending_leave_requests"))

        if req["status"] != "Pending":
            msg = f"Cannot reject leave request with status '{req['status']}'."
            flash(msg, "warning")
            if request.is_json:
                return jsonify({"status": "error", "message": msg}), 400
            return redirect(url_for("pending_leave_requests"))

        approval_date = datetime.datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S")
        conn.execute(
            """
            UPDATE leave_requests
            SET status = 'Rejected',
                approved_by = ?,
                approval_date = ?,
                rejection_reason = ?,
                comments = ?
            WHERE id = ?
            """,
            (
                current_user.username,
                approval_date,
                rejection_reason,
                comments,
                leave_id,
            ),
        )
        conn.commit()

    create_notification(
        req["user_id"],
        "Leave Request Rejected",
        f"Your {req['leave_type']} request ({req['start_date']} to {req['end_date']}) was rejected.",
        url_for("my_leave_requests"),
    )
    try:
        send_leave_rejection_email_to_employee(
            req["user_id"],
            dict(req),
            rejection_reason=rejection_reason,
            comments=comments,
        )
    except Exception as e:  # noqa: BLE001
        print("Failed to trigger leave rejection email:", e)

    msg = "Leave request rejected successfully."
    flash(msg, "success")
    if request.is_json:
        return jsonify({"status": "success", "message": msg, "leave_id": leave_id})
    return redirect(url_for("pending_leave_requests"))


# Performance Management Module Routes


@app.route("/performance")
@login_required
def performance_dashboard():
    if current_user.role not in ("admin", "hr"):
        flash("Access denied.", "danger")
        return redirect(url_for("dashboard"))

    with get_db() as conn:
        total_reviews = conn.execute(
            "SELECT COUNT(*) FROM performance_reviews"
        ).fetchone()[0]
        avg_company_rating = (
            conn.execute(
                "SELECT AVG(overall_rating) FROM performance_reviews"
            ).fetchone()[0]
            or 0.0
        )

        users_rows = conn.execute(
            """
            SELECT u.id, u.username, u.role, u.full_name, u.email,
                   COUNT(r.id) AS review_count,
                   AVG(r.overall_rating) AS avg_rating,
                   MAX(r.created_at) AS latest_review_date
            FROM users u
            LEFT JOIN performance_reviews r ON r.employee_user_id = u.id
            GROUP BY u.id
            ORDER BY CASE WHEN AVG(r.overall_rating) IS NULL THEN 1 ELSE 0 END, AVG(r.overall_rating) DESC, u.username ASC
            """
        ).fetchall()
        employees_perf = [dict(row) for row in users_rows]

        # Rating distribution metrics for visual chart
        dist_high = sum(
            1 for e in employees_perf if e["avg_rating"] and e["avg_rating"] >= 4.5
        )
        dist_good = sum(
            1
            for e in employees_perf
            if e["avg_rating"] and 3.5 <= e["avg_rating"] < 4.5
        )
        dist_needs_work = sum(
            1 for e in employees_perf if e["avg_rating"] and e["avg_rating"] < 3.5
        )
        dist_unrated = sum(1 for e in employees_perf if not e["avg_rating"])

    return render_template_string(
                """
                {% extends "base.html" %}
                {% block title %}Performance Dashboard{% endblock %}
                {% block page_content %}
                <div class="page-header d-flex flex-wrap justify-content-between align-items-center gap-3 mb-4">
                    <div>
                        <h1>Performance Dashboard</h1>
                        <p>Company-wide performance management, skill analytics, and evaluations.</p>
                    </div>
                </div>

                {% with messages = get_flashed_messages(with_categories=true) %}
                    {% if messages %}
                        {% for category, message in messages %}
                            <div class="alert alert-{{ category }} alert-dismissible fade show" role="alert">
                                {{ message }}
                                <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
                            </div>
                        {% endfor %}
                    {% endif %}
                {% endwith %}

                <div class="row g-3 mb-4">
                    <div class="col-md-6 col-lg-3">
                        <div class="card shadow-sm h-100 border-0 border-start border-primary border-4">
                            <div class="card-body d-flex align-items-center">
                                <div class="rounded-circle bg-primary bg-opacity-10 p-3 me-3 text-primary">
                                    <i class="bi bi-graph-up-arrow fs-3"></i>
                                </div>
                                <div>
                                    <div class="text-muted small fw-semibold">Company Avg Rating</div>
                                    <div class="fs-4 fw-bold text-dark">{{ '%.2f'|format(avg_company_rating) }} <span class="fs-6 text-warning">★</span></div>
                                    <div class="progress mt-1" style="height: 4px; width: 100px;">
                                        <div class="progress-bar bg-primary" style="width: {{ (avg_company_rating / 5.0) * 100 }}%;"></div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>

                    <div class="col-md-6 col-lg-3">
                        <div class="card shadow-sm h-100 border-0 border-start border-success border-4">
                            <div class="card-body d-flex align-items-center">
                                <div class="rounded-circle bg-success bg-opacity-10 p-3 me-3 text-success">
                                    <i class="bi bi-journal-check fs-3"></i>
                                </div>
                                <div>
                                    <div class="text-muted small fw-semibold">Total Reviews Logged</div>
                                    <div class="fs-4 fw-bold text-dark">{{ total_reviews }}</div>
                                    <span class="text-muted small">Reviews recorded</span>
                                </div>
                            </div>
                        </div>
                    </div>

                    <div class="col-md-6 col-lg-3">
                        <div class="card shadow-sm h-100 border-0 border-start border-info border-4">
                            <div class="card-body d-flex align-items-center">
                                <div class="rounded-circle bg-info bg-opacity-10 p-3 me-3 text-info">
                                    <i class="bi bi-people fs-3"></i>
                                </div>
                                <div>
                                    <div class="text-muted small fw-semibold">Evaluated Employees</div>
                                    <div class="fs-4 fw-bold text-dark">{{ employees|selectattr('avg_rating')|list|length }} / {{ employees|length }}</div>
                                    <span class="text-muted small">Active team members</span>
                                </div>
                            </div>
                        </div>
                    </div>

                    <div class="col-md-6 col-lg-3">
                        <div class="card shadow-sm h-100 border-0 border-start border-warning border-4">
                            <div class="card-body d-flex align-items-center">
                                <div class="rounded-circle bg-warning bg-opacity-10 p-3 me-3 text-warning">
                                    <i class="bi bi-trophy fs-3"></i>
                                </div>
                                <div>
                                    <div class="text-muted small fw-semibold">Top Performers (4.5+)</div>
                                    <div class="fs-4 fw-bold text-dark">{{ dist_high }}</div>
                                    <span class="text-muted small">High rating tier</span>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                <div class="row g-4 mb-4">
                    <div class="col-lg-8">
                        <div class="card shadow-sm h-100">
                            <div class="card-header bg-white py-3 border-0 d-flex justify-content-between align-items-center">
                                <h5 class="card-title mb-0 fw-bold"><i class="bi bi-bar-chart-line-fill me-2 text-primary"></i>Performance Tier Distribution</h5>
                            </div>
                            <div class="card-body">
                                <div style="height: 220px; position: relative;">
                                    <canvas id="performanceDistChart"></canvas>
                                </div>
                            </div>
                        </div>
                    </div>

                    <div class="col-lg-4">
                        <div class="card shadow-sm h-100">
                            <div class="card-header bg-white py-3 border-0">
                                <h5 class="card-title mb-0 fw-bold"><i class="bi bi-pie-chart-fill me-2 text-primary"></i>Evaluation Coverage</h5>
                            </div>
                            <div class="card-body text-center d-flex flex-column justify-content-center">
                                <div style="height: 180px; position: relative;" class="mx-auto">
                                    <canvas id="coverageDoughnutChart"></canvas>
                                </div>
                                <div class="mt-2 text-muted small">
                                    <span class="badge bg-success me-1">Evaluated</span>
                                    <span class="badge bg-secondary">Pending Initial Review</span>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                <div class="card shadow-sm">
                    <div class="card-header bg-white py-3 border-0 d-flex justify-content-between align-items-center">
                        <h5 class="card-title mb-0 fw-bold"><i class="bi bi-award me-2 text-primary"></i>Employee Performance Directory</h5>
                    </div>
                    <div class="card-body p-0">
                        <div class="table-responsive">
                            <table class="table table-hover align-middle mb-0">
                                <thead class="table-light">
                                    <tr>
                                        <th>Employee</th>
                                        <th>Role</th>
                                        <th>Reviews Count</th>
                                        <th>Overall Rating</th>
                                        <th>Last Reviewed</th>
                                        <th class="text-end">Actions</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {% for emp in employees %}
                                        <tr>
                                            <td class="fw-bold">
                                                <i class="bi bi-person-circle me-2 text-primary"></i>
                                                {{ emp.full_name or emp.username }}
                                                {% if emp.full_name %}<br><small class="text-muted ms-4">@{{ emp.username }}</small>{% endif %}
                                            </td>
                                            <td><span class="badge bg-light text-dark border">{{ emp.role }}</span></td>
                                            <td><span class="badge bg-light text-dark border">{{ emp.review_count }} review{% if emp.review_count != 1 %}s{% endif %}</span></td>
                                            <td>
                                                {% if emp.avg_rating %}
                                                    <span class="badge bg-{% if emp.avg_rating >= 4.5 %}success{% elif emp.avg_rating >= 3.5 %}primary{% else %}warning text-dark{% endif %} fs-6">
                                                        {{ '%.1f'|format(emp.avg_rating) }} ★
                                                    </span>
                                                {% else %}
                                                    <span class="text-muted small">Not Evaluated</span>
                                                {% endif %}
                                            </td>
                                            <td class="text-muted small">{{ emp.latest_review_date or '-' }}</td>
                                            <td class="text-end">
                                                <div class="d-inline-flex gap-2">
                                                    <a class="btn btn-sm btn-outline-primary" href="{{ url_for('employee_performance_profile', user_id=emp.id) }}">
                                                        <i class="bi bi-eye me-1"></i>Profile
                                                    </a>
                                                    <a class="btn btn-sm btn-primary" href="{{ url_for('add_performance_review', user_id=emp.id) }}">
                                                        <i class="bi bi-plus-lg me-1"></i>Review
                                                    </a>
                                                </div>
                                            </td>
                                        </tr>
                                    {% else %}
                                        <tr>
                                            <td colspan="6" class="text-center py-4 text-muted">No employees found.</td>
                                        </tr>
                                    {% endfor %}
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>

                <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
                <script>
                    document.addEventListener('DOMContentLoaded', function() {
                        // Bar Chart for Rating Tier Distribution
                        const ctxDist = document.getElementById('performanceDistChart').getContext('2d');
                        new Chart(ctxDist, {
                            type: 'bar',
                            data: {
                                labels: ['High (4.5 - 5.0)', 'Good (3.5 - 4.4)', 'Needs Work (<3.5)', 'Unrated'],
                                datasets: [{
                                    label: 'Number of Employees',
                                    data: [{{ dist_high }}, {{ dist_good }}, {{ dist_needs_work }}, {{ dist_unrated }}],
                                    backgroundColor: ['#22c55e', '#4f46e5', '#f59e0b', '#cbd5e1'],
                                    borderRadius: 6
                                }]
                            },
                            options: {
                                responsive: true,
                                maintainAspectRatio: false,
                                plugins: { legend: { display: false } },
                                scales: {
                                    y: { beginAtZero: true, ticks: { stepSize: 1 } }
                                }
                            }
                        });

                        // Doughnut Chart for Coverage
                        const ctxCov = document.getElementById('coverageDoughnutChart').getContext('2d');
                        new Chart(ctxCov, {
                            type: 'doughnut',
                            data: {
                                labels: ['Evaluated', 'Pending Review'],
                                datasets: [{
                                    data: [{{ employees|selectattr('avg_rating')|list|length }}, {{ dist_unrated }}],
                                    backgroundColor: ['#22c55e', '#94a3b8'],
                                    borderWidth: 0
                                }]
                            },
                            options: {
                                responsive: true,
                                maintainAspectRatio: false,
                                plugins: { legend: { display: false } }
                            }
                        });
                    });
                </script>
                {% endblock %}
                """,
                employees=employees_perf,
                avg_company_rating=avg_company_rating,
                total_reviews=total_reviews,
                dist_high=dist_high,
                dist_good=dist_good,
                dist_needs_work=dist_needs_work,
                dist_unrated=dist_unrated,
            )


@app.route("/performance/profile/<int:user_id>")
@login_required
def employee_performance_profile(user_id):
    if current_user.role not in ("admin", "hr") and current_user.id != user_id:
        flash("Access denied.", "danger")
        return redirect(url_for("dashboard"))

    from_date = (request.args.get("from_date") or request.args.get("start_date") or "").strip()
    to_date = (request.args.get("to_date") or request.args.get("end_date") or "").strip()

    valid_date_range = True
    if from_date and to_date and from_date > to_date:
        flash("From Date cannot be after To Date.", "warning")
        valid_date_range = False

    rev_sql = """
        SELECT id, employee_user_id, employee_name, reviewer_username, review_period,
               overall_rating, technical_skills_score, communication_score,
               productivity_score, teamwork_score, strengths, areas_for_improvement,
               comments, created_at
        FROM performance_reviews
        WHERE employee_user_id = ?
    """
    rev_params = [user_id]

    if valid_date_range:
        if from_date and to_date:
            rev_sql += " AND created_at >= ? AND created_at <= ?"
            rev_params.extend([from_date, to_date + " 23:59:59"])
        elif from_date:
            rev_sql += " AND created_at >= ?"
            rev_params.append(from_date)
        elif to_date:
            rev_sql += " AND created_at <= ?"
            rev_params.append(to_date + " 23:59:59")

    rev_sql += " ORDER BY created_at DESC, id DESC"

    with get_db() as conn:
        emp_user = conn.execute(
            "SELECT id, username, role, full_name, email, profile_pic, last_active_at FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()

        if emp_user is None:
            flash("Employee user not found.", "danger")
            return redirect(url_for("performance_dashboard"))

        reviews_rows = conn.execute(rev_sql, rev_params).fetchall()
        reviews = [dict(row) for row in reviews_rows]

        if reviews:
            avg_overall = sum(r["overall_rating"] for r in reviews) / len(reviews)
            avg_tech = sum(r["technical_skills_score"] for r in reviews) / len(reviews)
            avg_comm = sum(r["communication_score"] for r in reviews) / len(reviews)
            avg_prod = sum(r["productivity_score"] for r in reviews) / len(reviews)
            avg_team = sum(r["teamwork_score"] for r in reviews) / len(reviews)
        else:
            avg_overall = avg_tech = avg_comm = avg_prod = avg_team = 0.0

        perf = calculate_employee_performance(conn, user_id)
        emp_user_online = is_user_online(emp_user["last_active_at"])

    return render_template_string(
        """
        {% extends "base.html" %}
        {% block title %}Performance Profile - {{ emp.full_name or emp.username }}{% endblock %}
        {% block page_content %}
        <style>.status-indicator { position: absolute; border-radius: 50%; } .online { background-color: #22c55e; } .offline { background-color: #94a3b8; }</style>
        <div class="page-header d-flex flex-wrap justify-content-between align-items-center gap-3 mb-4">
            <div>
                <h1>Performance Profile</h1>
                <p>Employee skill evaluations and review history for <strong>{{ emp.full_name or emp.username }}</strong>.</p>
            </div>
            <div class="d-flex gap-2">
                <a class="btn btn-outline-secondary" href="{{ url_for('performance_dashboard') }}"><i class="bi bi-arrow-left me-1"></i>Back to Dashboard</a>
                {% if current_user.role in ['admin', 'hr'] %}
                    <a class="btn btn-primary" href="{{ url_for('add_performance_review', user_id=emp.id) }}"><i class="bi bi-plus-lg me-1"></i>Add Review</a>
                {% endif %}
            </div>
        </div>

        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="alert alert-{{ category }} alert-dismissible fade show" role="alert">
                        {{ message }}
                        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
                    </div>
                {% endfor %}
            {% endif %}
        {% endwith %}

        <div class="card shadow-sm mb-4">
            <div class="card-body py-3">
                <form method="get" class="row g-3 align-items-end">
                    <div class="col-md-4 col-sm-6">
                        <label class="form-label small fw-semibold text-muted mb-1">From Date</label>
                        <input type="date" class="form-control form-control-sm" name="from_date" value="{{ from_date or '' }}">
                    </div>
                    <div class="col-md-4 col-sm-6">
                        <label class="form-label small fw-semibold text-muted mb-1">To Date</label>
                        <input type="date" class="form-control form-control-sm" name="to_date" value="{{ to_date or '' }}">
                    </div>
                    <div class="col-md-4 col-sm-12 d-flex gap-2">
                        <button type="submit" class="btn btn-primary btn-sm px-3 flex-fill"><i class="bi bi-funnel me-1"></i>Filter Reviews</button>
                        {% if from_date or to_date %}
                            <a class="btn btn-outline-secondary btn-sm px-3" href="{{ url_for('employee_performance_profile', user_id=emp.id) }}"><i class="bi bi-x-circle me-1"></i>Clear</a>
                        {% endif %}
                    </div>
                </form>
            </div>
        </div>

        <div class="card shadow-sm mb-4 border-0 border-start border-primary border-4">
            <div class="card-header bg-white py-3 border-0 d-flex flex-wrap justify-content-between align-items-center gap-2">
                <h5 class="card-title fw-bold mb-0 text-dark">
                    <i class="bi bi-cpu-fill me-2 text-primary"></i>Automated HRMS Performance Score
                </h5>
                <span class="badge {{ perf.badge_class }} fs-6 px-3 py-2 fw-semibold">
                    {{ perf.performance_label }}
                </span>
            </div>
            <div class="card-body">
                <div class="row align-items-center g-4">
                    <div class="col-md-4 text-center border-end-md">
                        <div class="text-muted small fw-semibold text-uppercase">Performance Score</div>
                        <div class="display-4 fw-bold text-primary my-2">{{ perf.performance_score }}%</div>
                        <div class="progress mb-2 mx-auto" style="height: 12px; max-width: 85%;">
                            <div class="progress-bar {{ perf.bar_class }}" role="progressbar" style="width: {{ perf.performance_score }}%;" aria-valuenow="{{ perf.performance_score }}" aria-valuemin="0" aria-valuemax="100"></div>
                        </div>
                        <div class="text-muted small">
                            <i class="bi bi-clock-history me-1"></i>Last Updated: {{ perf.last_updated }}
                        </div>
                    </div>
                    
                    <div class="col-md-8">
                        <div class="row g-3">
                            <div class="col-6 col-md-3">
                                <div class="p-3 bg-light rounded text-center h-100 border">
                                    <div class="text-muted small fw-semibold">Attendance %</div>
                                    <div class="fs-5 fw-bold text-success mt-1">{{ perf.attendance_pct }}%</div>
                                </div>
                            </div>
                            <div class="col-6 col-md-3">
                                <div class="p-3 bg-light rounded text-center h-100 border">
                                    <div class="text-muted small fw-semibold">Task Completion %</div>
                                    <div class="fs-5 fw-bold text-primary mt-1">{{ perf.task_completion_pct }}%</div>
                                </div>
                            </div>
                            <div class="col-6 col-md-3">
                                <div class="p-3 bg-light rounded text-center h-100 border">
                                    <div class="text-muted small fw-semibold">Approved Leaves</div>
                                    <div class="fs-5 fw-bold text-info mt-1">{{ perf.approved_leaves }}</div>
                                </div>
                            </div>
                            <div class="col-6 col-md-3">
                                <div class="p-3 bg-light rounded text-center h-100 border">
                                    <div class="text-muted small fw-semibold">Overdue Tasks</div>
                                    <div class="fs-5 fw-bold {% if perf.overdue_tasks > 0 %}text-danger{% else %}text-secondary{% endif %} mt-1">{{ perf.overdue_tasks }}</div>
                                </div>
                            </div>
                            <div class="col-6 col-md-4">
                                <div class="p-2 border rounded d-flex justify-content-between align-items-center bg-white">
                                    <span class="small text-muted fw-semibold">Completed Tasks:</span>
                                    <span class="fw-bold text-success">{{ perf.completed_tasks }}</span>
                                </div>
                            </div>
                            <div class="col-6 col-md-4">
                                <div class="p-2 border rounded d-flex justify-content-between align-items-center bg-white">
                                    <span class="small text-muted fw-semibold">Pending Tasks:</span>
                                    <span class="fw-bold text-warning text-dark">{{ perf.pending_tasks }}</span>
                                </div>
                            </div>
                            <div class="col-6 col-md-4">
                                <div class="p-2 border rounded d-flex justify-content-between align-items-center bg-white">
                                    <span class="small text-muted fw-semibold">Total Assigned Tasks:</span>
                                    <span class="fw-bold text-primary">{{ perf.total_tasks }}</span>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <div class="card shadow-sm mb-4">
            <div class="card-body py-4">
                <div class="d-flex flex-wrap align-items-center justify-content-between gap-3">
                    <div class="d-flex align-items-center gap-3">
                        <div class="user-avatar fs-3 flex-shrink-0" style="width:72px; height:72px; background: #e0e7ff; color: #4338ca; display: flex; align-items: center; justify-content: center; border-radius: 50%; position: relative;">
                            {% if emp.profile_pic %}
                                <img src="{{ url_for('static', filename=emp.profile_pic) }}" alt="Avatar" style="width: 100%; height: 100%; object-fit: cover; border-radius: 50%;">
                            {% else %}
                                {{ (emp.full_name or emp.username)[:2]|upper }}
                            {% endif %}
                            <span class="status-indicator {% if emp_user_online %}online{% else %}offline{% endif %}" style="width: 14px; height: 14px; border: 2px solid #fff; bottom: 2px; right: 2px;" title="{% if emp_user_online %}Online{% else %}Offline{% endif %}"></span>
                        </div>
                        <div>
                            <h4 class="h5 mb-1 fw-bold">{{ emp.full_name or emp.username }}</h4>
                            <p class="text-muted small mb-0">@{{ emp.username }} • <span class="badge bg-light text-dark border">{{ emp.role }}</span></p>
                        </div>
                    </div>
                    <div class="text-start text-md-end border-start-md ps-md-4">
                        <div class="text-muted small fw-semibold">Overall Review Average</div>
                        <div class="display-6 fw-bold text-primary my-1">{{ '%.1f'|format(avg_overall) }} <span class="fs-4 text-warning">★</span></div>
                        <div class="text-muted small">Based on {{ reviews|length }} review{% if reviews|length != 1 %}s{% endif %}</div>
                    </div>
                </div>
            </div>
        </div>

        <div class="card shadow-sm">
            <div class="card-header bg-white py-3 border-0">
                <h5 class="card-title mb-0 fw-bold"><i class="bi bi-clock-history me-2 text-primary"></i>Manager Evaluation History</h5>
            </div>
            <div class="card-body p-0">
                <div class="table-responsive">
                    <table class="table table-hover align-middle mb-0">
                        <thead class="table-light">
                            <tr>
                                <th>Review Period</th>
                                <th>Overall Rating</th>
                                <th>Category Scores</th>
                                <th>Strengths & Improvement Areas</th>
                                <th>Evaluated By</th>
                                <th>Date</th>
                            </tr>
                        </thead>
                        <tbody>
                            {% for r in reviews %}
                            <tr>
                                <td><span class="fw-bold">{{ r.review_period }}</span></td>
                                <td>
                                    <span class="badge bg-primary fs-6 px-2 py-1">{{ r.overall_rating }}.0 ★</span>
                                </td>
                                <td>
                                    <div class="small">
                                        <div>Technical: <strong>{{ r.technical_skills_score }}/5</strong></div>
                                        <div>Communication: <strong>{{ r.communication_score }}/5</strong></div>
                                        <div>Productivity: <strong>{{ r.productivity_score }}/5</strong></div>
                                        <div>Teamwork: <strong>{{ r.teamwork_score }}/5</strong></div>
                                    </div>
                                </td>
                                <td>
                                    {% if r.strengths %}<div class="small text-success"><strong>Strengths:</strong> {{ r.strengths }}</div>{% endif %}
                                    {% if r.areas_for_improvement %}<div class="small text-danger mt-1"><strong>Improvement:</strong> {{ r.areas_for_improvement }}</div>{% endif %}
                                    {% if r.comments %}<div class="small text-muted mt-1"><em>"{{ r.comments }}"</em></div>{% endif %}
                                </td>
                                <td><span class="badge bg-light text-dark border">@{{ r.reviewer_username }}</span></td>
                                <td class="small text-muted">{{ r.created_at }}</td>
                            </tr>
                            {% else %}
                            <tr>
                                <td colspan="6" class="text-center py-4 text-muted">No manager evaluation reviews recorded yet.</td>
                            </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
        {% endblock %}
        """,
        emp=emp_user,
        perf=perf,
        reviews=reviews,
        avg_overall=avg_overall,
        avg_tech=avg_tech,
        avg_comm=avg_comm,
        avg_prod=avg_prod,
        avg_team=avg_team,
        emp_user_online=emp_user_online,
    )


@app.route("/performance/review/add/<int:user_id>", methods=["GET", "POST"])
@login_required
def add_performance_review(user_id):
    if current_user.role not in ("admin", "hr"):
        flash("Access denied to add performance reviews.", "danger")
        return redirect(url_for("dashboard"))

    with get_db() as conn:
        emp_user = conn.execute(
            "SELECT id, username, role, full_name, email FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()

        if emp_user is None:
            flash("Employee user not found.", "danger")
            return redirect(url_for("performance_dashboard"))

    if request.method == "POST":
        review_period = (request.form.get("review_period") or "").strip()
        strengths = (request.form.get("strengths") or "").strip()
        areas_for_improvement = (
            request.form.get("areas_for_improvement") or ""
        ).strip()
        comments = (request.form.get("comments") or "").strip()

        try:
            overall_rating = float(request.form.get("overall_rating") or 0.0)
            technical_skills_score = float(
                request.form.get("technical_skills_score") or 0.0
            )
            communication_score = float(request.form.get("communication_score") or 0.0)
            productivity_score = float(request.form.get("productivity_score") or 0.0)
            teamwork_score = float(request.form.get("teamwork_score") or 0.0)
        except ValueError:
            flash("Scores must be valid numbers.", "danger")
            return redirect(url_for("add_performance_review", user_id=user_id))

        if not review_period:
            flash("Review period is required (e.g. Q1 2026).", "danger")
            return redirect(url_for("add_performance_review", user_id=user_id))

        if not (1.0 <= overall_rating <= 5.0):
            flash("Overall rating must be between 1.0 and 5.0.", "danger")
            return redirect(url_for("add_performance_review", user_id=user_id))

        employee_name = str(emp_user["full_name"] or emp_user["username"])
        created_at = datetime.datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S")

        with get_db() as conn:
            conn.execute(
                """
                INSERT INTO performance_reviews (
                    employee_user_id, employee_name, reviewer_username, review_period,
                    overall_rating, technical_skills_score, communication_score,
                    productivity_score, teamwork_score, strengths, areas_for_improvement,
                    comments, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    employee_name,
                    current_user.username,
                    review_period,
                    overall_rating,
                    technical_skills_score,
                    communication_score,
                    productivity_score,
                    teamwork_score,
                    strengths,
                    areas_for_improvement,
                    comments,
                    created_at,
                ),
            )
            conn.commit()

        create_notification(
            user_id,
            "New Performance Review Published",
            f"You received a review for {review_period} with score {overall_rating:.1f} ★.",
            url_for("employee_performance_profile", user_id=user_id),
        )
        flash("Performance review submitted successfully.", "success")
        return redirect(url_for("employee_performance_profile", user_id=user_id))

    return render_template_string(
        """
        {% extends "base.html" %}
        {% block title %}Add Performance Review{% endblock %}
        {% block page_content %}
        <div class="page-header d-flex flex-wrap justify-content-between align-items-center gap-3 mb-4">
            <div>
                <h1>Add Performance Review</h1>
                <p>Evaluate manager review metrics for <strong>{{ emp.full_name or emp.username }}</strong>.</p>
            </div>
            <a class="btn btn-outline-secondary" href="{{ url_for('employee_performance_profile', user_id=emp.id) }}"><i class="bi bi-arrow-left me-1"></i>Cancel</a>
        </div>

        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="alert alert-{{ category }} alert-dismissible fade show" role="alert">
                        {{ message }}
                        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
                    </div>
                {% endfor %}
            {% endif %}
        {% endwith %}

        <div class="card shadow-sm mx-auto" style="max-width: 760px;">
            <div class="card-body">
                <form method="post">
                    <div class="mb-3">
                        <label class="form-label fw-semibold">Review Period <span class="text-danger">*</span></label>
                        <input class="form-control" name="review_period" placeholder="e.g. Q1 2026, Annual Review 2026" required>
                    </div>
                    
                    <div class="mb-4 p-3 bg-light rounded border">
                        <label class="form-label fw-bold text-primary mb-2"><i class="bi bi-star-fill me-1 text-warning"></i>Overall Rating (1.0 to 5.0) <span class="text-danger">*</span></label>
                        <input class="form-control form-control-lg" type="number" step="0.1" min="1.0" max="5.0" name="overall_rating" placeholder="e.g. 4.5" required>
                    </div>

                    <h5 class="h6 fw-bold mb-3">Skills Score Breakdown (1.0 to 5.0)</h5>
                    <div class="row g-3 mb-4">
                        <div class="col-md-6">
                            <label class="form-label fw-semibold">Technical Skills Score</label>
                            <input class="form-control" type="number" step="0.1" min="1.0" max="5.0" name="technical_skills_score" value="4.0" required>
                        </div>
                        <div class="col-md-6">
                            <label class="form-label fw-semibold">Communication Score</label>
                            <input class="form-control" type="number" step="0.1" min="1.0" max="5.0" name="communication_score" value="4.0" required>
                        </div>
                        <div class="col-md-6">
                            <label class="form-label fw-semibold">Productivity Score</label>
                            <input class="form-control" type="number" step="0.1" min="1.0" max="5.0" name="productivity_score" value="4.0" required>
                        </div>
                        <div class="col-md-6">
                            <label class="form-label fw-semibold">Teamwork Score</label>
                            <input class="form-control" type="number" step="0.1" min="1.0" max="5.0" name="teamwork_score" value="4.0" required>
                        </div>
                    </div>

                    <div class="mb-3">
                        <label class="form-label fw-semibold">Key Strengths</label>
                        <textarea class="form-control" name="strengths" rows="2" placeholder="Highlight key achievements and strong skill sets..."></textarea>
                    </div>

                    <div class="mb-3">
                        <label class="form-label fw-semibold">Areas for Improvement</label>
                        <textarea class="form-control" name="areas_for_improvement" rows="2" placeholder="Constructive feedback and areas to develop..."></textarea>
                    </div>

                    <div class="mb-4">
                        <label class="form-label fw-semibold">Additional Comments</label>
                        <textarea class="form-control" name="comments" rows="2" placeholder="General manager notes or goal benchmarks..."></textarea>
                    </div>

                    <div class="d-flex justify-content-end gap-2">
                        <a class="btn btn-outline-secondary" href="{{ url_for('employee_performance_profile', user_id=emp.id) }}">Cancel</a>
                        <button class="btn btn-primary" type="submit"><i class="bi bi-check-circle me-1"></i>Save Performance Review</button>
                    </div>
                </form>
            </div>
        </div>
        {% endblock %}
        """,
        emp=emp_user,
    )


# Reports Module Routes


@app.route("/reports")
@login_required
def reports_dashboard():
    if current_user.role != "admin":
        flash("Access denied. Admin privileges required.", "danger")
        return redirect(url_for("dashboard"))

    with get_db() as conn:
        total_employees = conn.execute("SELECT COUNT(*) FROM employees").fetchone()[0]
        total_attendance = conn.execute("SELECT COUNT(*) FROM attendance").fetchone()[0]
        total_leaves = conn.execute("SELECT COUNT(*) FROM leave_requests").fetchone()[0]
        avg_rating = conn.execute(
            "SELECT COALESCE(AVG(overall_rating), 0) FROM performance_reviews"
        ).fetchone()[0]
        total_projects = conn.execute("SELECT COUNT(*) FROM projects").fetchone()[0]
        total_tasks = conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]

    return render_template_string(
        """
        {% extends "base.html" %}
        {% block title %}HRMS Reports & Analytics{% endblock %}
        {% block page_content %}
        <div class="page-header d-flex flex-wrap justify-content-between align-items-center gap-3 mb-4">
            <div>
                <h1>Reports & Analytics Directory</h1>
                <p>Access operational summaries, performance metrics, and organizational analytics.</p>
            </div>
            <button type="button" class="btn btn-outline-secondary btn-export" onclick="window.print()"><i class="bi bi-printer me-1"></i>Print / PDF</button>
        </div>

        <div class="row g-4 mb-4">
            <div class="col-md-6 col-lg-4">
                <div class="card shadow-sm h-100 border-0 border-start border-primary border-4">
                    <div class="card-body">
                        <div class="d-flex align-items-center mb-3">
                            <div class="rounded-circle bg-primary bg-opacity-10 p-3 me-3 text-primary">
                                <i class="bi bi-people fs-3"></i>
                            </div>
                            <div>
                                <h5 class="card-title fw-bold mb-0">Employee Reports</h5>
                                <span class="text-muted small">Headcount & Department Analytics</span>
                            </div>
                        </div>
                        <div class="display-6 fw-bold text-dark mb-2">{{ total_employees }}</div>
                        <p class="text-muted small mb-3">Total registered employees across departments.</p>
                        <a class="btn btn-outline-primary btn-sm w-100" href="{{ url_for('reports_employees') }}">
                            <i class="bi bi-arrow-right-circle me-1"></i>View Employee Report
                        </a>
                    </div>
                </div>
            </div>

            <div class="col-md-6 col-lg-4">
                <div class="card shadow-sm h-100 border-0 border-start border-info border-4">
                    <div class="card-body">
                        <div class="d-flex align-items-center mb-3">
                            <div class="rounded-circle bg-info bg-opacity-10 p-3 me-3 text-info">
                                <i class="bi bi-calendar-check fs-3"></i>
                            </div>
                            <div>
                                <h5 class="card-title fw-bold mb-0">Attendance Reports</h5>
                                <span class="text-muted small">Logs & Work Hours Trends</span>
                            </div>
                        </div>
                        <div class="display-6 fw-bold text-dark mb-2">{{ total_attendance }}</div>
                        <p class="text-muted small mb-3">Total attendance records logged in system.</p>
                        <a class="btn btn-outline-info btn-sm w-100" href="{{ url_for('reports_attendance') }}">
                            <i class="bi bi-arrow-right-circle me-1"></i>View Attendance Report
                        </a>
                    </div>
                </div>
            </div>

            <div class="col-md-6 col-lg-4">
                <div class="card shadow-sm h-100 border-0 border-start border-warning border-4">
                    <div class="card-body">
                        <div class="d-flex align-items-center mb-3">
                            <div class="rounded-circle bg-warning bg-opacity-10 p-3 me-3 text-warning">
                                <i class="bi bi-calendar-minus fs-3"></i>
                            </div>
                            <div>
                                <h5 class="card-title fw-bold mb-0">Leave Reports</h5>
                                <span class="text-muted small">Approval & Utilization Analytics</span>
                            </div>
                        </div>
                        <div class="display-6 fw-bold text-dark mb-2">{{ total_leaves }}</div>
                        <p class="text-muted small mb-3">Total submitted leave requests.</p>
                        <a class="btn btn-outline-warning btn-sm text-dark w-100" href="{{ url_for('reports_leave') }}">
                            <i class="bi bi-arrow-right-circle me-1"></i>View Leave Report
                        </a>
                    </div>
                </div>
            </div>

            <div class="col-md-6 col-lg-6">
                <div class="card shadow-sm h-100 border-0 border-start border-success border-4">
                    <div class="card-body">
                        <div class="d-flex align-items-center mb-3">
                            <div class="rounded-circle bg-success bg-opacity-10 p-3 me-3 text-success">
                                <i class="bi bi-graph-up-arrow fs-3"></i>
                            </div>
                            <div>
                                <h5 class="card-title fw-bold mb-0">Performance Reports</h5>
                                <span class="text-muted small">Ratings & Competency Matrix</span>
                            </div>
                        </div>
                        <div class="display-6 fw-bold text-dark mb-2">{{ '%.1f'|format(avg_rating) }} <span class="fs-4 text-warning">★</span></div>
                        <p class="text-muted small mb-3">Company-wide performance average rating.</p>
                        <a class="btn btn-outline-success btn-sm w-100" href="{{ url_for('reports_performance') }}">
                            <i class="bi bi-arrow-right-circle me-1"></i>View Performance Report
                        </a>
                    </div>
                </div>
            </div>

            <div class="col-md-6 col-lg-6">
                <div class="card shadow-sm h-100 border-0 border-start border-secondary border-4">
                    <div class="card-body">
                        <div class="d-flex align-items-center mb-3">
                            <div class="rounded-circle bg-secondary bg-opacity-10 p-3 me-3 text-secondary">
                                <i class="bi bi-kanban fs-3"></i>
                            </div>
                            <div>
                                <h5 class="card-title fw-bold mb-0">Project & Task Reports</h5>
                                <span class="text-muted small">Workload & Delivery Completion</span>
                            </div>
                        </div>
                        <div class="display-6 fw-bold text-dark mb-2">{{ total_projects }} <span class="fs-6 text-muted">projects / {{ total_tasks }} tasks</span></div>
                        <p class="text-muted small mb-3">Active projects and assigned task statistics.</p>
                        <a class="btn btn-outline-secondary btn-sm w-100" href="{{ url_for('reports_projects') }}">
                            <i class="bi bi-arrow-right-circle me-1"></i>View Project Report
                        </a>
                    </div>
                </div>
            </div>
        </div>
        {% endblock %}
        """,
        total_employees=total_employees,
        total_attendance=total_attendance,
        total_leaves=total_leaves,
        avg_rating=avg_rating,
        total_projects=total_projects,
        total_tasks=total_tasks,
    )


@app.route("/reports/employees")
@login_required
def reports_employees():
    if current_user.role != "admin":
        flash("Access denied. Admin privileges required.", "danger")
        return redirect(url_for("dashboard"))

    selected_dept = request.args.get("dept", "").strip()

    with get_db() as conn:
        emp_rows = conn.execute(
            "SELECT id, user_id, name, department, salary FROM employees"
        ).fetchall()
        user_count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]

    total_emp = len(emp_rows)
    linked_user_count = sum(1 for e in emp_rows if e["user_id"] is not None)
    unlinked_count = total_emp - linked_user_count
    salaries = [e["salary"] for e in emp_rows if e["salary"] is not None]
    avg_salary = sum(salaries) / len(salaries) if salaries else 0.0

    dept_counts = {}
    dept_salaries = {}
    for e in emp_rows:
        depts = [
            d.strip() for d in (e["department"] or "Unassigned").split(",") if d.strip()
        ]
        if not depts:
            depts = ["Unassigned"]
        for d in depts:
            dept_counts[d] = dept_counts.get(d, 0) + 1
            if d not in dept_salaries:
                dept_salaries[d] = []
            if e["salary"]:
                dept_salaries[d].append(e["salary"])

    all_dept_labels = sorted(dept_counts.keys())
    dept_labels = all_dept_labels
    dept_values = [dept_counts[d] for d in dept_labels]

    dept_summary = []
    for d in all_dept_labels:
        if selected_dept and selected_dept != d:
            continue
        s_list = dept_salaries.get(d, [])
        d_avg_sal = sum(s_list) / len(s_list) if s_list else 0.0
        dept_summary.append(
            {"department": d, "count": dept_counts[d], "avg_salary": d_avg_sal}
        )

    return render_template_string(
        """
        {% extends "base.html" %}
        {% block title %}Employee Analytics Report{% endblock %}
        {% block page_content %}
        <div class="page-header d-flex flex-wrap justify-content-between align-items-center gap-3 mb-4">
            <div>
                <h1>Employee Analytics Report</h1>
                <p>Headcount breakdown, department distribution, and active user account metrics.</p>
            </div>
            <div class="d-flex gap-2">
                <button type="button" class="btn btn-outline-secondary btn-export" onclick="window.print()"><i class="bi bi-printer me-1"></i>Print / PDF</button>
                <button type="button" class="btn btn-outline-success btn-export" onclick="exportTableToCSV('empReportTable', 'employee_analytics_report.csv')"><i class="bi bi-file-earmark-spreadsheet me-1"></i>Export CSV</button>
                <a class="btn btn-outline-primary" href="{{ url_for('reports_dashboard') }}"><i class="bi bi-arrow-left me-1"></i>Back to Hub</a>
            </div>
        </div>

        <div class="card shadow-sm border-0 mb-4 report-filter-bar">
            <div class="card-body py-3">
                <form method="GET" action="{{ url_for('reports_employees') }}" class="row g-3 align-items-center">
                    <div class="col-md-4">
                        <label class="form-label small text-muted mb-1 fw-bold">Filter by Department</label>
                        <select name="dept" class="form-select form-select-sm" onchange="this.form.submit()">
                            <option value="">All Departments</option>
                            {% for d in all_dept_labels %}
                                <option value="{{ d }}" {% if selected_dept == d %}selected{% endif %}>{{ d }}</option>
                            {% endfor %}
                        </select>
                    </div>
                    {% if selected_dept %}
                        <div class="col-md-2 mt-4">
                            <a href="{{ url_for('reports_employees') }}" class="btn btn-sm btn-link text-decoration-none"><i class="bi bi-x-circle me-1"></i>Clear Filter</a>
                        </div>
                    {% endif %}
                </form>
            </div>
        </div>

        <div class="row g-4 mb-4">
            <div class="col-md-3">
                <div class="card shadow-sm border-0 border-start border-primary border-4 h-100">
                    <div class="card-body">
                        <div class="text-muted small fw-semibold">Total Employees</div>
                        <div class="display-6 fw-bold text-dark my-1">{{ total_emp }}</div>
                        <span class="text-muted small">Registered HR profiles</span>
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card shadow-sm border-0 border-start border-success border-4 h-100">
                    <div class="card-body">
                        <div class="text-muted small fw-semibold">Active Login Users</div>
                        <div class="display-6 fw-bold text-dark my-1">{{ user_count }}</div>
                        <span class="text-muted small">Authentication accounts</span>
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card shadow-sm border-0 border-start border-info border-4 h-100">
                    <div class="card-body">
                        <div class="text-muted small fw-semibold">Departments</div>
                        <div class="display-6 fw-bold text-dark my-1">{{ all_dept_labels|length }}</div>
                        <span class="text-muted small">Active department teams</span>
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card shadow-sm border-0 border-start border-warning border-4 h-100">
                    <div class="card-body">
                        <div class="text-muted small fw-semibold">Average Salary</div>
                        <div class="display-6 fw-bold text-dark my-1">{{ avg_salary|inr }}</div>
                        <span class="text-muted small">Average compensation</span>
                    </div>
                </div>
            </div>
        </div>

        <div class="row g-4 mb-4">
            <div class="col-lg-8">
                <div class="card shadow-sm h-100">
                    <div class="card-header bg-white py-3 border-0">
                        <h5 class="card-title mb-0 fw-bold"><i class="bi bi-bar-chart-fill me-2 text-primary"></i>Department Headcount Distribution</h5>
                    </div>
                    <div class="card-body">
                        <div style="height: 250px; position: relative;">
                            <canvas id="deptChart"></canvas>
                        </div>
                    </div>
                </div>
            </div>

            <div class="col-lg-4">
                <div class="card shadow-sm h-100">
                    <div class="card-header bg-white py-3 border-0">
                        <h5 class="card-title mb-0 fw-bold"><i class="bi bi-pie-chart-fill me-2 text-primary"></i>User Account Link Status</h5>
                    </div>
                    <div class="card-body text-center d-flex flex-column justify-content-center">
                        <div style="height: 200px; position: relative;" class="mx-auto">
                            <canvas id="accountChart"></canvas>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <div class="card shadow-sm">
            <div class="card-header bg-white py-3 border-0 d-flex justify-content-between align-items-center">
                <h5 class="card-title mb-0 fw-bold"><i class="bi bi-table me-2 text-primary"></i>Department Analytics Breakdown</h5>
                <button type="button" class="btn btn-sm btn-outline-success" onclick="exportTableToCSV('empReportTable', 'department_breakdown.csv')"><i class="bi bi-download me-1"></i>CSV</button>
            </div>
            <div class="card-body p-0">
                <div class="table-responsive">
                    <table class="table table-hover align-middle mb-0" id="empReportTable">
                        <thead class="table-light">
                            <tr>
                                <th>Department</th>
                                <th>Employee Headcount</th>
                                <th>Average Salary</th>
                            </tr>
                        </thead>
                        <tbody>
                            {% for d in dept_summary %}
                                <tr>
                                    <td class="fw-bold"><i class="bi bi-building me-2 text-primary"></i>{{ d.department }}</td>
                                    <td><span class="badge bg-primary fs-6">{{ d.count }}</span></td>
                                    <td>{{ d.avg_salary | inr }}</td>
                                </tr>
                            {% else %}
                                <tr><td colspan="3" class="text-center py-4 text-muted">No department records matching filter.</td></tr>
                            {% endfor %}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>

        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <script>
            function exportTableToCSV(tableId, filename) {
                var table = document.getElementById(tableId);
                if (!table) return;
                var rows = table.querySelectorAll("tr");
                var csv = [];
                for (var i = 0; i < rows.length; i++) {
                    var row = [], cols = rows[i].querySelectorAll("td, th");
                    for (var j = 0; j < cols.length; j++) {
                        var text = cols[j].innerText.replace(/(\\r\\n|\\n|\\r)/gm, " ").replace(/"/g, '""').trim();
                        row.push('"' + text + '"');
                    }
                    csv.push(row.join(","));
                }
                var csvFile = new Blob([csv.join("\\n")], {type: "text/csv"});
                var downloadLink = document.createElement("a");
                downloadLink.download = filename;
                downloadLink.href = window.URL.createObjectURL(csvFile);
                downloadLink.style.display = "none";
                document.body.appendChild(downloadLink);
                downloadLink.click();
                document.body.removeChild(downloadLink);
            }

            document.addEventListener('DOMContentLoaded', function() {
                const ctxDept = document.getElementById('deptChart').getContext('2d');
                new Chart(ctxDept, {
                    type: 'bar',
                    data: {
                        labels: {{ dept_labels|tojson }},
                        datasets: [{
                            label: 'Headcount',
                            data: {{ dept_values|tojson }},
                            backgroundColor: '#4f46e5',
                            borderRadius: 6
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: { legend: { display: false } },
                        scales: { y: { beginAtZero: true, ticks: { stepSize: 1 } } }
                    }
                });

                const ctxAcc = document.getElementById('accountChart').getContext('2d');
                new Chart(ctxAcc, {
                    type: 'doughnut',
                    data: {
                        labels: ['Linked Account', 'Unlinked Profile'],
                        datasets: [{
                            data: [{{ linked_user_count }}, {{ unlinked_count }}],
                            backgroundColor: ['#22c55e', '#cbd5e1']
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false
                    }
                });
            });
        </script>
        {% endblock %}
        """,
        total_emp=total_emp,
        user_count=user_count,
        avg_salary=avg_salary,
        linked_user_count=linked_user_count,
        unlinked_count=unlinked_count,
        dept_labels=dept_labels,
        dept_values=dept_values,
        all_dept_labels=all_dept_labels,
        selected_dept=selected_dept,
        dept_summary=dept_summary,
    )


@app.route("/reports/attendance")
@login_required
def reports_attendance():
    if current_user.role != "admin":
        flash("Access denied. Admin privileges required.", "danger")
        return redirect(url_for("dashboard"))

    start_date = (request.args.get("start_date") or request.args.get("from_date") or "").strip()
    end_date = (request.args.get("end_date") or request.args.get("to_date") or "").strip()

    valid_date_range = True
    if start_date and end_date and start_date > end_date:
        flash("From Date cannot be after To Date.", "warning")
        valid_date_range = False

    query_where = []
    params = []
    if valid_date_range:
        if start_date:
            query_where.append("date >= ?")
            params.append(start_date)
        if end_date:
            query_where.append("date <= ?")
            params.append(end_date)

    where_clause = (" WHERE " + " AND ".join(query_where)) if query_where else ""

    with get_db() as conn:
        total_logs = conn.execute(
            "SELECT COUNT(*) FROM attendance" + where_clause, params
        ).fetchone()[0]
        total_hours = conn.execute(
            "SELECT COALESCE(SUM(total_hours), 0) FROM attendance" + where_clause,
            params,
        ).fetchone()[0]
        avg_hours = conn.execute(
            "SELECT COALESCE(AVG(total_hours), 0) FROM attendance WHERE total_hours IS NOT NULL"
            + ((" AND " + " AND ".join(query_where)) if query_where else ""),
            params,
        ).fetchone()[0]

        trend_rows = conn.execute(
            "SELECT date, COUNT(*) AS count, COALESCE(SUM(total_hours), 0) AS total_hrs FROM attendance"
            + where_clause
            + " GROUP BY date ORDER BY date ASC LIMIT 15",
            params,
        ).fetchall()

        top_employee_rows = conn.execute(
            "SELECT username, COALESCE(SUM(total_hours), 0) AS total_hrs, COUNT(*) AS log_count FROM attendance"
            + where_clause
            + " GROUP BY username ORDER BY total_hrs DESC LIMIT 8",
            params,
        ).fetchall()

    trend_dates = [r["date"] for r in trend_rows]
    trend_hours = [round(r["total_hrs"], 2) for r in trend_rows]

    emp_names = [r["username"] for r in top_employee_rows]
    emp_hours = [round(r["total_hrs"], 2) for r in top_employee_rows]

    return render_template_string(
        """
        {% extends "base.html" %}
        {% block title %}Attendance Analytics Report{% endblock %}
        {% block page_content %}
        <div class="page-header d-flex flex-wrap justify-content-between align-items-center gap-3 mb-4">
            <div>
                <h1>Attendance Analytics Report</h1>
                <p>System work hours trends, punch log statistics, and top contributor rankings.</p>
            </div>
            <div class="d-flex gap-2">
                <button type="button" class="btn btn-outline-secondary btn-export" onclick="window.print()"><i class="bi bi-printer me-1"></i>Print / PDF</button>
                <button type="button" class="btn btn-outline-success btn-export" onclick="exportTableToCSV('attendanceReportTable', 'attendance_analytics_report.csv')"><i class="bi bi-file-earmark-spreadsheet me-1"></i>Export CSV</button>
                <a class="btn btn-outline-primary" href="{{ url_for('reports_dashboard') }}"><i class="bi bi-arrow-left me-1"></i>Back to Hub</a>
            </div>
        </div>

        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="alert alert-{{ category }} alert-dismissible fade show" role="alert">
                        {{ message }}
                        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
                    </div>
                {% endfor %}
            {% endif %}
        {% endwith %}

        <div class="card shadow-sm border-0 mb-4 report-filter-bar">
            <div class="card-body py-3">
                <form method="GET" action="{{ url_for('reports_attendance') }}" class="row g-3 align-items-end">
                    <div class="col-md-4">
                        <label class="form-label small text-muted mb-1 fw-bold">Start Date</label>
                        <input type="date" name="start_date" class="form-control form-control-sm" value="{{ start_date }}">
                    </div>
                    <div class="col-md-4">
                        <label class="form-label small text-muted mb-1 fw-bold">End Date</label>
                        <input type="date" name="end_date" class="form-control form-control-sm" value="{{ end_date }}">
                    </div>
                    <div class="col-md-4 d-flex gap-2">
                        <button type="submit" class="btn btn-primary btn-sm"><i class="bi bi-funnel me-1"></i>Filter</button>
                        {% if start_date or end_date %}
                            <a href="{{ url_for('reports_attendance') }}" class="btn btn-outline-secondary btn-sm"><i class="bi bi-x-circle me-1"></i>Reset</a>
                        {% endif %}
                    </div>
                </form>
            </div>
        </div>

        <div class="row g-4 mb-4">
            <div class="col-md-4">
                <div class="card shadow-sm border-0 border-start border-info border-4 h-100">
                    <div class="card-body">
                        <div class="text-muted small fw-semibold">Total Attendance Logs</div>
                        <div class="display-6 fw-bold text-dark my-1">{{ total_logs }}</div>
                        <span class="text-muted small">Recorded punch sessions</span>
                    </div>
                </div>
            </div>
            <div class="col-md-4">
                <div class="card shadow-sm border-0 border-start border-success border-4 h-100">
                    <div class="card-body">
                        <div class="text-muted small fw-semibold">Total Hours Logged</div>
                        <div class="display-6 fw-bold text-dark my-1">{{ '%.1f'|format(total_hours) }} hrs</div>
                        <span class="text-muted small">Cumulative work time</span>
                    </div>
                </div>
            </div>
            <div class="col-md-4">
                <div class="card shadow-sm border-0 border-start border-primary border-4 h-100">
                    <div class="card-body">
                        <div class="text-muted small fw-semibold">Average Session Duration</div>
                        <div class="display-6 fw-bold text-dark my-1">{{ '%.1f'|format(avg_hours) }} hrs</div>
                        <span class="text-muted small">Average shift length</span>
                    </div>
                </div>
            </div>
        </div>

        <div class="row g-4 mb-4">
            <div class="col-lg-7">
                <div class="card shadow-sm h-100">
                    <div class="card-header bg-white py-3 border-0">
                        <h5 class="card-title mb-0 fw-bold"><i class="bi bi-graph-up me-2 text-primary"></i>Daily Work Hours Trend</h5>
                    </div>
                    <div class="card-body">
                        <div style="height: 250px; position: relative;">
                            <canvas id="attendanceTrendChart"></canvas>
                        </div>
                    </div>
                </div>
            </div>

            <div class="col-lg-5">
                <div class="card shadow-sm h-100">
                    <div class="card-header bg-white py-3 border-0 d-flex justify-content-between align-items-center">
                        <h5 class="card-title mb-0 fw-bold"><i class="bi bi-trophy-fill me-2 text-primary"></i>Top Contributor Hours</h5>
                        <button type="button" class="btn btn-sm btn-outline-success" onclick="exportTableToCSV('attendanceReportTable', 'top_attendance_contributors.csv')"><i class="bi bi-download me-1"></i>CSV</button>
                    </div>
                    <div class="card-body">
                        <div style="height: 250px; position: relative;">
                            <canvas id="topHoursChart"></canvas>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <div class="card shadow-sm">
            <div class="card-header bg-white py-3 border-0 d-flex justify-content-between align-items-center">
                <h5 class="card-title mb-0 fw-bold"><i class="bi bi-table me-2 text-primary"></i>Employee Attendance Hours Directory</h5>
                <button type="button" class="btn btn-sm btn-outline-success" onclick="exportTableToCSV('attendanceReportTable', 'attendance_hours_summary.csv')"><i class="bi bi-download me-1"></i>CSV</button>
            </div>
            <div class="card-body p-0">
                <div class="table-responsive">
                    <table class="table table-hover align-middle mb-0" id="attendanceReportTable">
                        <thead class="table-light">
                            <tr>
                                <th>Employee / Username</th>
                                <th>Total Logged Hours</th>
                                <th>Total Punch Sessions</th>
                            </tr>
                        </thead>
                        <tbody>
                            {% for r in top_employee_rows %}
                                <tr>
                                    <td class="fw-bold"><i class="bi bi-person-circle me-2 text-primary"></i>{{ r.username }}</td>
                                    <td><span class="badge bg-success fs-6">{{ '%.2f'|format(r.total_hrs) }} hrs</span></td>
                                    <td><span class="badge bg-light text-dark border">{{ r.log_count }} sessions</span></td>
                                </tr>
                            {% else %}
                                <tr><td colspan="3" class="text-center py-4 text-muted">No attendance logs matching filter dates.</td></tr>
                            {% endfor %}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>

        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <script>
            function exportTableToCSV(tableId, filename) {
                var table = document.getElementById(tableId);
                if (!table) return;
                var rows = table.querySelectorAll("tr");
                var csv = [];
                for (var i = 0; i < rows.length; i++) {
                    var row = [], cols = rows[i].querySelectorAll("td, th");
                    for (var j = 0; j < cols.length; j++) {
                        var text = cols[j].innerText.replace(/(\\r\\n|\\n|\\r)/gm, " ").replace(/"/g, '""').trim();
                        row.push('"' + text + '"');
                    }
                    csv.push(row.join(","));
                }
                var csvFile = new Blob([csv.join("\\n")], {type: "text/csv"});
                var downloadLink = document.createElement("a");
                downloadLink.download = filename;
                downloadLink.href = window.URL.createObjectURL(csvFile);
                downloadLink.style.display = "none";
                document.body.appendChild(downloadLink);
                downloadLink.click();
                document.body.removeChild(downloadLink);
            }

            document.addEventListener('DOMContentLoaded', function() {
                const ctxTrend = document.getElementById('attendanceTrendChart').getContext('2d');
                new Chart(ctxTrend, {
                    type: 'line',
                    data: {
                        labels: {{ trend_dates|tojson }},
                        datasets: [{
                            label: 'Total Hours',
                            data: {{ trend_hours|tojson }},
                            borderColor: '#0284c7',
                            backgroundColor: 'rgba(2, 132, 199, 0.1)',
                            fill: true,
                            tension: 0.3
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        scales: { y: { beginAtZero: true } }
                    }
                });

                const ctxTop = document.getElementById('topHoursChart').getContext('2d');
                new Chart(ctxTop, {
                    type: 'bar',
                    data: {
                        labels: {{ emp_names|tojson }},
                        datasets: [{
                            label: 'Hours',
                            data: {{ emp_hours|tojson }},
                            backgroundColor: '#22c55e',
                            borderRadius: 6
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: { legend: { display: false } },
                        scales: { y: { beginAtZero: true } }
                    }
                });
            });
        </script>
        {% endblock %}
        """,
        total_logs=total_logs,
        total_hours=total_hours,
        avg_hours=avg_hours,
        trend_dates=trend_dates,
        trend_hours=trend_hours,
        emp_names=emp_names,
        emp_hours=emp_hours,
        start_date=start_date,
        end_date=end_date,
        top_employee_rows=top_employee_rows,
    )


@app.route("/reports/leave")
@login_required
def reports_leave():
    if current_user.role != "admin":
        flash("Access denied. Admin privileges required.", "danger")
        return redirect(url_for("dashboard"))

    selected_status = request.args.get("status", "").strip()
    selected_type = request.args.get("leave_type", "").strip()
    from_date = (request.args.get("from_date") or request.args.get("start_date") or "").strip()
    to_date = (request.args.get("to_date") or request.args.get("end_date") or "").strip()

    valid_date_range = True
    if from_date and to_date and from_date > to_date:
        flash("From Date cannot be after To Date.", "warning")
        valid_date_range = False

    query_where = []
    params = []
    if selected_status:
        query_where.append("status = ?")
        params.append(selected_status)
    if selected_type:
        query_where.append("leave_type = ?")
        params.append(selected_type)

    if valid_date_range:
        if from_date and to_date:
            query_where.append("start_date <= ? AND end_date >= ?")
            params.extend([to_date, from_date])
        elif from_date:
            query_where.append("end_date >= ?")
            params.append(from_date)
        elif to_date:
            query_where.append("start_date <= ?")
            params.append(to_date)

    where_clause = (" WHERE " + " AND ".join(query_where)) if query_where else ""

    with get_db() as conn:
        total_leaves = conn.execute("SELECT COUNT(*) FROM leave_requests").fetchone()[0]
        approved_count = conn.execute(
            "SELECT COUNT(*) FROM leave_requests WHERE status = 'Approved'"
        ).fetchone()[0]
        pending_count = conn.execute(
            "SELECT COUNT(*) FROM leave_requests WHERE status = 'Pending'"
        ).fetchone()[0]
        rejected_count = conn.execute(
            "SELECT COUNT(*) FROM leave_requests WHERE status = 'Rejected'"
        ).fetchone()[0]

        type_rows = conn.execute(
            "SELECT leave_type, COUNT(*) AS count, COALESCE(SUM(total_days), 0) AS total_days FROM leave_requests GROUP BY leave_type ORDER BY count DESC"
        ).fetchall()

        all_types = [r["leave_type"] for r in type_rows]

        recent_leaves = conn.execute(
            "SELECT * FROM leave_requests"
            + where_clause
            + " ORDER BY applied_date DESC LIMIT 15",
            params,
        ).fetchall()

    type_labels = [r["leave_type"] for r in type_rows]
    type_counts = [r["count"] for r in type_rows]

    return render_template_string(
        """
        {% extends "base.html" %}
        {% block title %}Leave Analytics Report{% endblock %}
        {% block page_content %}
        <div class="page-header d-flex flex-wrap justify-content-between align-items-center gap-3 mb-4">
            <div>
                <h1>Leave Analytics Report</h1>
                <p>Approval status breakdown, leave type distribution, and recent application log.</p>
            </div>
            <div class="d-flex gap-2">
                <button type="button" class="btn btn-outline-secondary btn-export" onclick="window.print()"><i class="bi bi-printer me-1"></i>Print / PDF</button>
                <button type="button" class="btn btn-outline-success btn-export" onclick="exportTableToCSV('leaveReportTable', 'leave_analytics_report.csv')"><i class="bi bi-file-earmark-spreadsheet me-1"></i>Export CSV</button>
                <a class="btn btn-outline-primary" href="{{ url_for('reports_dashboard') }}"><i class="bi bi-arrow-left me-1"></i>Back to Hub</a>
            </div>
        </div>

        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="alert alert-{{ category }} alert-dismissible fade show" role="alert">
                        {{ message }}
                        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
                    </div>
                {% endfor %}
            {% endif %}
        {% endwith %}

        <div class="card shadow-sm border-0 mb-4 report-filter-bar">
            <div class="card-body py-3">
                <form method="GET" action="{{ url_for('reports_leave') }}" class="row g-3 align-items-end">
                    <div class="col-md-3 col-sm-6">
                        <label class="form-label small text-muted mb-1 fw-bold">Filter by Status</label>
                        <select name="status" class="form-select form-select-sm">
                            <option value="">All Statuses</option>
                            <option value="Approved" {% if selected_status == 'Approved' %}selected{% endif %}>Approved</option>
                            <option value="Pending" {% if selected_status == 'Pending' %}selected{% endif %}>Pending</option>
                            <option value="Rejected" {% if selected_status == 'Rejected' %}selected{% endif %}>Rejected</option>
                        </select>
                    </div>
                    <div class="col-md-3 col-sm-6">
                        <label class="form-label small text-muted mb-1 fw-bold">Filter by Leave Type</label>
                        <select name="leave_type" class="form-select form-select-sm">
                            <option value="">All Leave Types</option>
                            {% for t in all_types %}
                                <option value="{{ t }}" {% if selected_type == t %}selected{% endif %}>{{ t }}</option>
                            {% endfor %}
                        </select>
                    </div>
                    <div class="col-md-2 col-sm-6">
                        <label class="form-label small text-muted mb-1 fw-bold">From Date</label>
                        <input type="date" name="from_date" class="form-control form-control-sm" value="{{ from_date or '' }}">
                    </div>
                    <div class="col-md-2 col-sm-6">
                        <label class="form-label small text-muted mb-1 fw-bold">To Date</label>
                        <input type="date" name="to_date" class="form-control form-control-sm" value="{{ to_date or '' }}">
                    </div>
                    <div class="col-md-2 col-sm-12 d-flex gap-2">
                        <button type="submit" class="btn btn-primary btn-sm flex-fill"><i class="bi bi-funnel me-1"></i>Apply</button>
                        {% if selected_status or selected_type or from_date or to_date %}
                            <a href="{{ url_for('reports_leave') }}" class="btn btn-outline-secondary btn-sm"><i class="bi bi-x-circle me-1"></i>Clear</a>
                        {% endif %}
                    </div>
                </form>
            </div>
        </div>

        <div class="row g-4 mb-4">
            <div class="col-md-3">
                <div class="card shadow-sm border-0 border-start border-primary border-4 h-100">
                    <div class="card-body">
                        <div class="text-muted small fw-semibold">Total Requests</div>
                        <div class="display-6 fw-bold text-dark my-1">{{ total_leaves }}</div>
                        <span class="text-muted small">Submitted leave forms</span>
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card shadow-sm border-0 border-start border-success border-4 h-100">
                    <div class="card-body">
                        <div class="text-muted small fw-semibold">Approved Leaves</div>
                        <div class="display-6 fw-bold text-success my-1">{{ approved_count }}</div>
                        <span class="text-muted small">Authorized absences</span>
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card shadow-sm border-0 border-start border-warning border-4 h-100">
                    <div class="card-body">
                        <div class="text-muted small fw-semibold">Pending Approvals</div>
                        <div class="display-6 fw-bold text-warning my-1">{{ pending_count }}</div>
                        <span class="text-muted small">Awaiting review</span>
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card shadow-sm border-0 border-start border-danger border-4 h-100">
                    <div class="card-body">
                        <div class="text-muted small fw-semibold">Rejected Requests</div>
                        <div class="display-6 fw-bold text-danger my-1">{{ rejected_count }}</div>
                        <span class="text-muted small">Declined applications</span>
                    </div>
                </div>
            </div>
        </div>

        <div class="row g-4 mb-4">
            <div class="col-lg-5">
                <div class="card shadow-sm h-100">
                    <div class="card-header bg-white py-3 border-0">
                        <h5 class="card-title mb-0 fw-bold"><i class="bi bi-pie-chart-fill me-2 text-primary"></i>Approval Status Breakdown</h5>
                    </div>
                    <div class="card-body text-center d-flex flex-column justify-content-center">
                        <div style="height: 220px; position: relative;" class="mx-auto">
                            <canvas id="leaveStatusChart"></canvas>
                        </div>
                    </div>
                </div>
            </div>

            <div class="col-lg-7">
                <div class="card shadow-sm h-100">
                    <div class="card-header bg-white py-3 border-0">
                        <h5 class="card-title mb-0 fw-bold"><i class="bi bi-bar-chart-fill me-2 text-primary"></i>Leave Type Distribution</h5>
                    </div>
                    <div class="card-body">
                        <div style="height: 220px; position: relative;">
                            <canvas id="leaveTypeChart"></canvas>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <div class="card shadow-sm">
            <div class="card-header bg-white py-3 border-0 d-flex justify-content-between align-items-center">
                <h5 class="card-title mb-0 fw-bold"><i class="bi bi-list-task me-2 text-primary"></i>Leave Applications Summary Directory</h5>
                <button type="button" class="btn btn-sm btn-outline-success" onclick="exportTableToCSV('leaveReportTable', 'leave_applications_summary.csv')"><i class="bi bi-download me-1"></i>CSV</button>
            </div>
            <div class="card-body p-0">
                <div class="table-responsive">
                    <table class="table table-hover align-middle mb-0" id="leaveReportTable">
                        <thead class="table-light">
                            <tr>
                                <th>Employee</th>
                                <th>Leave Type</th>
                                <th>Dates</th>
                                <th>Days</th>
                                <th>Status</th>
                            </tr>
                        </thead>
                        <tbody>
                            {% for l in recent_leaves %}
                                <tr>
                                    <td class="fw-bold">{{ l.employee_name }}</td>
                                    <td><span class="badge bg-light text-dark border">{{ l.leave_type }}</span></td>
                                    <td class="small">{{ l.start_date }} to {{ l.end_date }}</td>
                                    <td>{{ l.total_days }}</td>
                                    <td>
                                        {% if l.status == 'Approved' %}
                                            <span class="badge bg-success">Approved</span>
                                        {% elif l.status == 'Pending' %}
                                            <span class="badge bg-warning text-dark">Pending</span>
                                        {% else %}
                                            <span class="badge bg-danger">Rejected</span>
                                        {% endif %}
                                    </td>
                                </tr>
                            {% else %}
                                <tr><td colspan="5" class="text-center py-4 text-muted">No leave request logs matching filters.</td></tr>
                            {% endfor %}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>

        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <script>
            function exportTableToCSV(tableId, filename) {
                var table = document.getElementById(tableId);
                if (!table) return;
                var rows = table.querySelectorAll("tr");
                var csv = [];
                for (var i = 0; i < rows.length; i++) {
                    var row = [], cols = rows[i].querySelectorAll("td, th");
                    for (var j = 0; j < cols.length; j++) {
                        var text = cols[j].innerText.replace(/(\\r\\n|\\n|\\r)/gm, " ").replace(/"/g, '""').trim();
                        row.push('"' + text + '"');
                    }
                    csv.push(row.join(","));
                }
                var csvFile = new Blob([csv.join("\\n")], {type: "text/csv"});
                var downloadLink = document.createElement("a");
                downloadLink.download = filename;
                downloadLink.href = window.URL.createObjectURL(csvFile);
                downloadLink.style.display = "none";
                document.body.appendChild(downloadLink);
                downloadLink.click();
                document.body.removeChild(downloadLink);
            }

            document.addEventListener('DOMContentLoaded', function() {
                const ctxStatus = document.getElementById('leaveStatusChart').getContext('2d');
                new Chart(ctxStatus, {
                    type: 'doughnut',
                    data: {
                        labels: ['Approved', 'Pending', 'Rejected'],
                        datasets: [{
                            data: [{{ approved_count }}, {{ pending_count }}, {{ rejected_count }}],
                            backgroundColor: ['#22c55e', '#f59e0b', '#ef4444']
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false
                    }
                });

                const ctxType = document.getElementById('leaveTypeChart').getContext('2d');
                new Chart(ctxType, {
                    type: 'bar',
                    data: {
                        labels: {{ type_labels|tojson }},
                        datasets: [{
                            label: 'Requests Count',
                            data: {{ type_counts|tojson }},
                            backgroundColor: '#4f46e5',
                            borderRadius: 6
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: { legend: { display: false } },
                        scales: { y: { beginAtZero: true, ticks: { stepSize: 1 } } }
                    }
                });
            });
        </script>
        {% endblock %}
        """,
        total_leaves=total_leaves,
        approved_count=approved_count,
        pending_count=pending_count,
        rejected_count=rejected_count,
        type_labels=type_labels,
        type_counts=type_counts,
        all_types=all_types,
        selected_status=selected_status,
        selected_type=selected_type,
        recent_leaves=recent_leaves,
    )


@app.route("/reports/performance")
@login_required
def reports_performance():
    if current_user.role != "admin":
        flash("Access denied. Admin privileges required.", "danger")
        return redirect(url_for("dashboard"))

    min_rating = request.args.get("min_rating", "").strip()
    min_val = float(min_rating) if min_rating else 0.0
    from_date = (request.args.get("from_date") or request.args.get("start_date") or "").strip()
    to_date = (request.args.get("to_date") or request.args.get("end_date") or "").strip()

    valid_date_range = True
    if from_date and to_date and from_date > to_date:
        flash("From Date cannot be after To Date.", "warning")
        valid_date_range = False

    where_clauses = []
    params = []
    if valid_date_range:
        if from_date and to_date:
            where_clauses.append("created_at >= ? AND created_at <= ?")
            params.extend([from_date, to_date + " 23:59:59"])
        elif from_date:
            where_clauses.append("created_at >= ?")
            params.append(from_date)
        elif to_date:
            where_clauses.append("created_at <= ?")
            params.append(to_date + " 23:59:59")

    where_sql = (" WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

    with get_db() as conn:
        total_evaluations = conn.execute(
            "SELECT COUNT(*) FROM performance_reviews" + where_sql, params
        ).fetchone()[0]
        avg_rating = conn.execute(
            "SELECT COALESCE(AVG(overall_rating), 0) FROM performance_reviews" + where_sql, params
        ).fetchone()[0]
        
        hp_sql = "SELECT COUNT(DISTINCT employee_user_id) FROM performance_reviews WHERE overall_rating >= 4.5"
        if where_clauses:
            hp_sql += " AND " + " AND ".join(where_clauses)
        high_performers = conn.execute(hp_sql, params).fetchone()[0]

        avg_tech = conn.execute(
            "SELECT COALESCE(AVG(technical_skills_score), 0) FROM performance_reviews" + where_sql, params
        ).fetchone()[0]
        avg_comm = conn.execute(
            "SELECT COALESCE(AVG(communication_score), 0) FROM performance_reviews" + where_sql, params
        ).fetchone()[0]
        avg_prod = conn.execute(
            "SELECT COALESCE(AVG(productivity_score), 0) FROM performance_reviews" + where_sql, params
        ).fetchone()[0]
        avg_team = conn.execute(
            "SELECT COALESCE(AVG(teamwork_score), 0) FROM performance_reviews" + where_sql, params
        ).fetchone()[0]

        top_sql = """
            SELECT employee_name, AVG(overall_rating) AS avg_score, COUNT(*) AS review_count, MAX(created_at) AS last_review
            FROM performance_reviews
        """
        top_params = []
        if where_clauses:
            top_sql += " WHERE " + " AND ".join(where_clauses)
            top_params.extend(params)
        top_sql += " GROUP BY employee_name HAVING avg_score >= ? ORDER BY avg_score DESC LIMIT 10"
        top_params.append(min_val)

        top_performers = conn.execute(top_sql, top_params).fetchall()

    return render_template_string(
        """
        {% extends "base.html" %}
        {% block title %}Performance Analytics Report{% endblock %}
        {% block page_content %}
        <div class="page-header d-flex flex-wrap justify-content-between align-items-center gap-3 mb-4">
            <div>
                <h1>Performance Analytics Report</h1>
                <p>Company-wide skill averages, rating metrics, and top performer directory.</p>
            </div>
            <div class="d-flex gap-2">
                <button type="button" class="btn btn-outline-secondary btn-export" onclick="window.print()"><i class="bi bi-printer me-1"></i>Print / PDF</button>
                <button type="button" class="btn btn-outline-success btn-export" onclick="exportTableToCSV('perfReportTable', 'performance_analytics_report.csv')"><i class="bi bi-file-earmark-spreadsheet me-1"></i>Export CSV</button>
                <a class="btn btn-outline-primary" href="{{ url_for('reports_dashboard') }}"><i class="bi bi-arrow-left me-1"></i>Back to Hub</a>
            </div>
        </div>

        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="alert alert-{{ category }} alert-dismissible fade show" role="alert">
                        {{ message }}
                        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
                    </div>
                {% endfor %}
            {% endif %}
        {% endwith %}

        <div class="card shadow-sm border-0 mb-4 report-filter-bar">
            <div class="card-body py-3">
                <form method="GET" action="{{ url_for('reports_performance') }}" class="row g-3 align-items-end">
                    <div class="col-md-4 col-sm-6">
                        <label class="form-label small text-muted mb-1 fw-bold">Filter Leaderboard by Rating</label>
                        <select name="min_rating" class="form-select form-select-sm">
                            <option value="">All Ratings</option>
                            <option value="4.5" {% if min_rating == '4.5' %}selected{% endif %}>4.5+ (High Performers)</option>
                            <option value="4.0" {% if min_rating == '4.0' %}selected{% endif %}>4.0+ (Good Performers)</option>
                            <option value="3.5" {% if min_rating == '3.5' %}selected{% endif %}>3.5+ (Average)</option>
                        </select>
                    </div>
                    <div class="col-md-3 col-sm-6">
                        <label class="form-label small text-muted mb-1 fw-bold">From Date</label>
                        <input type="date" name="from_date" class="form-control form-control-sm" value="{{ from_date or '' }}">
                    </div>
                    <div class="col-md-3 col-sm-6">
                        <label class="form-label small text-muted mb-1 fw-bold">To Date</label>
                        <input type="date" name="to_date" class="form-control form-control-sm" value="{{ to_date or '' }}">
                    </div>
                    <div class="col-md-2 col-sm-6 d-flex gap-2">
                        <button type="submit" class="btn btn-primary btn-sm flex-fill"><i class="bi bi-funnel me-1"></i>Apply</button>
                        {% if min_rating or from_date or to_date %}
                            <a href="{{ url_for('reports_performance') }}" class="btn btn-outline-secondary btn-sm"><i class="bi bi-x-circle me-1"></i>Clear</a>
                        {% endif %}
                    </div>
                </form>
            </div>
        </div>

        <div class="row g-4 mb-4">
            <div class="col-md-4">
                <div class="card shadow-sm border-0 border-start border-success border-4 h-100">
                    <div class="card-body">
                        <div class="text-muted small fw-semibold">Company Average Rating</div>
                        <div class="display-6 fw-bold text-success my-1">{{ '%.1f'|format(avg_rating) }} <span class="fs-4 text-warning">★</span></div>
                        <span class="text-muted small">Overall score mean</span>
                    </div>
                </div>
            </div>
            <div class="col-md-4">
                <div class="card shadow-sm border-0 border-start border-primary border-4 h-100">
                    <div class="card-body">
                        <div class="text-muted small fw-semibold">Total Evaluations Logged</div>
                        <div class="display-6 fw-bold text-dark my-1">{{ total_evaluations }}</div>
                        <span class="text-muted small">Completed review forms</span>
                    </div>
                </div>
            </div>
            <div class="col-md-4">
                <div class="card shadow-sm border-0 border-start border-warning border-4 h-100">
                    <div class="card-body">
                        <div class="text-muted small fw-semibold">High Performers (4.5+)</div>
                        <div class="display-6 fw-bold text-dark my-1">{{ high_performers }}</div>
                        <span class="text-muted small">Top rating tier count</span>
                    </div>
                </div>
            </div>
        </div>

        <div class="row g-4 mb-4">
            <div class="col-lg-6">
                <div class="card shadow-sm h-100">
                    <div class="card-header bg-white py-3 border-0">
                        <h5 class="card-title mb-0 fw-bold"><i class="bi bi-radar me-2 text-primary"></i>Company Skill Competency Radar</h5>
                    </div>
                    <div class="card-body">
                        <div style="height: 240px; position: relative;">
                            <canvas id="companyRadarChart"></canvas>
                        </div>
                    </div>
                </div>
            </div>

            <div class="col-lg-6">
                <div class="card shadow-sm h-100">
                    <div class="card-header bg-white py-3 border-0">
                        <h5 class="card-title mb-0 fw-bold"><i class="bi bi-award me-2 text-primary"></i>Skill Scores Summary</h5>
                    </div>
                    <div class="card-body d-flex flex-column justify-content-center gap-3">
                        <div>
                            <div class="d-flex justify-content-between mb-1"><span class="fw-semibold small">Technical Skills</span><span class="fw-bold small">{{ '%.1f'|format(avg_tech) }} / 5.0</span></div>
                            <div class="progress" style="height: 8px;"><div class="progress-bar bg-primary" style="width: {{ (avg_tech / 5.0) * 100 }}%;"></div></div>
                        </div>
                        <div>
                            <div class="d-flex justify-content-between mb-1"><span class="fw-semibold small">Communication</span><span class="fw-bold small">{{ '%.1f'|format(avg_comm) }} / 5.0</span></div>
                            <div class="progress" style="height: 8px;"><div class="progress-bar bg-info" style="width: {{ (avg_comm / 5.0) * 100 }}%;"></div></div>
                        </div>
                        <div>
                            <div class="d-flex justify-content-between mb-1"><span class="fw-semibold small">Productivity</span><span class="fw-bold small">{{ '%.1f'|format(avg_prod) }} / 5.0</span></div>
                            <div class="progress" style="height: 8px;"><div class="progress-bar bg-success" style="width: {{ (avg_prod / 5.0) * 100 }}%;"></div></div>
                        </div>
                        <div>
                            <div class="d-flex justify-content-between mb-1"><span class="fw-semibold small">Teamwork</span><span class="fw-bold small">{{ '%.1f'|format(avg_team) }} / 5.0</span></div>
                            <div class="progress" style="height: 8px;"><div class="progress-bar bg-warning" style="width: {{ (avg_team / 5.0) * 100 }}%;"></div></div>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <div class="card shadow-sm">
            <div class="card-header bg-white py-3 border-0 d-flex justify-content-between align-items-center">
                <h5 class="card-title mb-0 fw-bold"><i class="bi bi-trophy me-2 text-primary"></i>Top Performer Leaderboard</h5>
                <button type="button" class="btn btn-sm btn-outline-success" onclick="exportTableToCSV('perfReportTable', 'top_performers_leaderboard.csv')"><i class="bi bi-download me-1"></i>CSV</button>
            </div>
            <div class="card-body p-0">
                <div class="table-responsive">
                    <table class="table table-hover align-middle mb-0" id="perfReportTable">
                        <thead class="table-light">
                            <tr>
                                <th>Employee</th>
                                <th>Average Score</th>
                                <th>Total Evaluations</th>
                                <th>Last Review Date</th>
                            </tr>
                        </thead>
                        <tbody>
                            {% for p in top_performers %}
                                <tr>
                                    <td class="fw-bold"><i class="bi bi-person-circle me-2 text-primary"></i>{{ p.employee_name }}</td>
                                    <td><span class="badge bg-success fs-6">{{ '%.1f'|format(p.avg_score) }} ★</span></td>
                                    <td><span class="badge bg-light text-dark border">{{ p.review_count }} review{% if p.review_count != 1 %}s{% endif %}</span></td>
                                    <td class="text-muted small">{{ p.last_review }}</td>
                                </tr>
                            {% else %}
                                <tr><td colspan="4" class="text-center py-4 text-muted">No performance review records matching filter.</td></tr>
                            {% endfor %}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>

        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <script>
            function exportTableToCSV(tableId, filename) {
                var table = document.getElementById(tableId);
                if (!table) return;
                var rows = table.querySelectorAll("tr");
                var csv = [];
                for (var i = 0; i < rows.length; i++) {
                    var row = [], cols = rows[i].querySelectorAll("td, th");
                    for (var j = 0; j < cols.length; j++) {
                        var text = cols[j].innerText.replace(/(\\r\\n|\\n|\\r)/gm, " ").replace(/"/g, '""').trim();
                        row.push('"' + text + '"');
                    }
                    csv.push(row.join(","));
                }
                var csvFile = new Blob([csv.join("\\n")], {type: "text/csv"});
                var downloadLink = document.createElement("a");
                downloadLink.download = filename;
                downloadLink.href = window.URL.createObjectURL(csvFile);
                downloadLink.style.display = "none";
                document.body.appendChild(downloadLink);
                downloadLink.click();
                document.body.removeChild(downloadLink);
            }

            document.addEventListener('DOMContentLoaded', function() {
                const ctxRadar = document.getElementById('companyRadarChart').getContext('2d');
                new Chart(ctxRadar, {
                    type: 'radar',
                    data: {
                        labels: ['Technical', 'Communication', 'Productivity', 'Teamwork'],
                        datasets: [{
                            label: 'Company Average',
                            data: [{{ avg_tech }}, {{ avg_comm }}, {{ avg_prod }}, {{ avg_team }}],
                            backgroundColor: 'rgba(34, 197, 94, 0.2)',
                            borderColor: '#22c55e',
                            pointBackgroundColor: '#22c55e'
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        scales: { r: { suggestedMin: 0, suggestedMax: 5 } }
                    }
                });
            });
        </script>
        {% endblock %}
        """,
        total_evaluations=total_evaluations,
        avg_rating=avg_rating,
        high_performers=high_performers,
        avg_tech=avg_tech,
        avg_comm=avg_comm,
        avg_prod=avg_prod,
        avg_team=avg_team,
        top_performers=top_performers,
        min_rating=min_rating,
    )


@app.route("/reports/projects")
@login_required
def reports_projects():
    if current_user.role != "admin":
        flash("Access denied. Admin privileges required.", "danger")
        return redirect(url_for("dashboard"))

    selected_status = request.args.get("status", "").strip()

    task_where = []
    task_params = []
    if selected_status:
        task_where.append("status = ?")
        task_params.append(selected_status)

    where_clause = (" WHERE " + " AND ".join(task_where)) if task_where else ""

    with get_db() as conn:
        total_projects = conn.execute("SELECT COUNT(*) FROM projects").fetchone()[0]
        total_tasks = conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
        completed_tasks = conn.execute(
            "SELECT COUNT(*) FROM tasks WHERE status = 'Completed'"
        ).fetchone()[0]
        completion_rate = (
            (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0.0
        )
        total_logged_hours = conn.execute(
            "SELECT COALESCE(SUM(hours_worked), 0) FROM time_logs"
        ).fetchone()[0]

        status_rows = conn.execute(
            "SELECT status, COUNT(*) AS count FROM tasks GROUP BY status"
        ).fetchall()
        status_dict = {r["status"]: r["count"] for r in status_rows}

        workload_rows = conn.execute(
            (
                """
            SELECT assigned_to, COUNT(*) AS total_tasks,
                   SUM(CASE WHEN status = 'Completed' THEN 1 ELSE 0 END) AS completed_tasks,
                   SUM(CASE WHEN status = 'Pending' THEN 1 ELSE 0 END) AS pending_tasks
            FROM tasks
            """
                + where_clause
                + """
            AND assigned_to IS NOT NULL AND assigned_to != ''
            GROUP BY assigned_to
            ORDER BY total_tasks DESC
            LIMIT 10
            """
                if where_clause
                else """
            SELECT assigned_to, COUNT(*) AS total_tasks,
                   SUM(CASE WHEN status = 'Completed' THEN 1 ELSE 0 END) AS completed_tasks,
                   SUM(CASE WHEN status = 'Pending' THEN 1 ELSE 0 END) AS pending_tasks
            FROM tasks
            WHERE assigned_to IS NOT NULL AND assigned_to != ''
            GROUP BY assigned_to
            ORDER BY total_tasks DESC
            LIMIT 10
            """
            ),
            task_params,
        ).fetchall()

    workload_names = [r["assigned_to"] for r in workload_rows]
    workload_tasks = [r["total_tasks"] for r in workload_rows]

    return render_template_string(
        """
        {% extends "base.html" %}
        {% block title %}Project & Task Analytics Report{% endblock %}
        {% block page_content %}
        <div class="page-header d-flex flex-wrap justify-content-between align-items-center gap-3 mb-4">
            <div>
                <h1>Project & Task Analytics Report</h1>
                <p>Task completion statistics, project delivery summary, and employee workload overview.</p>
            </div>
            <div class="d-flex gap-2">
                <button type="button" class="btn btn-outline-secondary btn-export" onclick="window.print()"><i class="bi bi-printer me-1"></i>Print / PDF</button>
                <button type="button" class="btn btn-outline-success btn-export" onclick="exportTableToCSV('projReportTable', 'project_task_analytics.csv')"><i class="bi bi-file-earmark-spreadsheet me-1"></i>Export CSV</button>
                <a class="btn btn-outline-primary" href="{{ url_for('reports_dashboard') }}"><i class="bi bi-arrow-left me-1"></i>Back to Hub</a>
            </div>
        </div>

        <div class="card shadow-sm border-0 mb-4 report-filter-bar">
            <div class="card-body py-3">
                <form method="GET" action="{{ url_for('reports_projects') }}" class="row g-3 align-items-center">
                    <div class="col-md-4">
                        <label class="form-label small text-muted mb-1 fw-bold">Filter Workload by Task Status</label>
                        <select name="status" class="form-select form-select-sm" onchange="this.form.submit()">
                            <option value="">All Task Statuses</option>
                            <option value="Completed" {% if selected_status == 'Completed' %}selected{% endif %}>Completed</option>
                            <option value="In Progress" {% if selected_status == 'In Progress' %}selected{% endif %}>In Progress</option>
                            <option value="Pending" {% if selected_status == 'Pending' %}selected{% endif %}>Pending</option>
                            <option value="Blocked" {% if selected_status == 'Blocked' %}selected{% endif %}>Blocked</option>
                        </select>
                    </div>
                    {% if selected_status %}
                        <div class="col-md-2 mt-4">
                            <a href="{{ url_for('reports_projects') }}" class="btn btn-sm btn-link text-decoration-none"><i class="bi bi-x-circle me-1"></i>Clear Filter</a>
                        </div>
                    {% endif %}
                </form>
            </div>
        </div>

        <div class="row g-4 mb-4">
            <div class="col-md-3">
                <div class="card shadow-sm border-0 border-start border-primary border-4 h-100">
                    <div class="card-body">
                        <div class="text-muted small fw-semibold">Active Projects</div>
                        <div class="display-6 fw-bold text-dark my-1">{{ total_projects }}</div>
                        <span class="text-muted small">Registered client projects</span>
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card shadow-sm border-0 border-start border-info border-4 h-100">
                    <div class="card-body">
                        <div class="text-muted small fw-semibold">Total Assigned Tasks</div>
                        <div class="display-6 fw-bold text-dark my-1">{{ total_tasks }}</div>
                        <span class="text-muted small">System task items</span>
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card shadow-sm border-0 border-start border-success border-4 h-100">
                    <div class="card-body">
                        <div class="text-muted small fw-semibold">Task Completion Rate</div>
                        <div class="display-6 fw-bold text-success my-1">{{ '%.0f'|format(completion_rate) }}%</div>
                        <span class="text-muted small">{{ completed_tasks }} of {{ total_tasks }} completed</span>
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card shadow-sm border-0 border-start border-warning border-4 h-100">
                    <div class="card-body">
                        <div class="text-muted small fw-semibold">Task Hours Logged</div>
                        <div class="display-6 fw-bold text-dark my-1">{{ '%.1f'|format(total_logged_hours) }} hrs</div>
                        <span class="text-muted small">Time log records</span>
                    </div>
                </div>
            </div>
        </div>

        <div class="row g-4 mb-4">
            <div class="col-lg-5">
                <div class="card shadow-sm h-100">
                    <div class="card-header bg-white py-3 border-0">
                        <h5 class="card-title mb-0 fw-bold"><i class="bi bi-pie-chart-fill me-2 text-primary"></i>Task Status Distribution</h5>
                    </div>
                    <div class="card-body text-center d-flex flex-column justify-content-center">
                        <div style="height: 220px; position: relative;" class="mx-auto">
                            <canvas id="taskStatusChart"></canvas>
                        </div>
                    </div>
                </div>
            </div>

            <div class="col-lg-7">
                <div class="card shadow-sm h-100">
                    <div class="card-header bg-white py-3 border-0">
                        <h5 class="card-title mb-0 fw-bold"><i class="bi bi-bar-chart-fill me-2 text-primary"></i>Employee Task Workload Overview</h5>
                    </div>
                    <div class="card-body">
                        <div style="height: 220px; position: relative;">
                            <canvas id="workloadChart"></canvas>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <div class="card shadow-sm">
            <div class="card-header bg-white py-3 border-0 d-flex justify-content-between align-items-center">
                <h5 class="card-title mb-0 fw-bold"><i class="bi bi-person-workspace me-2 text-primary"></i>Employee Workload Summary Directory</h5>
                <button type="button" class="btn btn-sm btn-outline-success" onclick="exportTableToCSV('projReportTable', 'employee_workload_summary.csv')"><i class="bi bi-download me-1"></i>CSV</button>
            </div>
            <div class="card-body p-0">
                <div class="table-responsive">
                    <table class="table table-hover align-middle mb-0" id="projReportTable">
                        <thead class="table-light">
                            <tr>
                                <th>Assigned Employee</th>
                                <th>Total Assigned Tasks</th>
                                <th>Completed Tasks</th>
                                <th>Pending Tasks</th>
                            </tr>
                        </thead>
                        <tbody>
                            {% for w in workload_rows %}
                                <tr>
                                    <td class="fw-bold">{{ w.assigned_to }}</td>
                                    <td><span class="badge bg-primary fs-6">{{ w.total_tasks }}</span></td>
                                    <td><span class="badge bg-success fs-6">{{ w.completed_tasks }}</span></td>
                                    <td><span class="badge bg-warning text-dark fs-6">{{ w.pending_tasks }}</span></td>
                                </tr>
                            {% else %}
                                <tr><td colspan="4" class="text-center py-4 text-muted">No task assignment workload data available matching filter.</td></tr>
                            {% endfor %}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>

        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <script>
            function exportTableToCSV(tableId, filename) {
                var table = document.getElementById(tableId);
                if (!table) return;
                var rows = table.querySelectorAll("tr");
                var csv = [];
                for (var i = 0; i < rows.length; i++) {
                    var row = [], cols = rows[i].querySelectorAll("td, th");
                    for (var j = 0; j < cols.length; j++) {
                        var text = cols[j].innerText.replace(/(\\r\\n|\\n|\\r)/gm, " ").replace(/"/g, '""').trim();
                        row.push('"' + text + '"');
                    }
                    csv.push(row.join(","));
                }
                var csvFile = new Blob([csv.join("\\n")], {type: "text/csv"});
                var downloadLink = document.createElement("a");
                downloadLink.download = filename;
                downloadLink.href = window.URL.createObjectURL(csvFile);
                downloadLink.style.display = "none";
                document.body.appendChild(downloadLink);
                downloadLink.click();
                document.body.removeChild(downloadLink);
            }

            document.addEventListener('DOMContentLoaded', function() {
                const ctxStatus = document.getElementById('taskStatusChart').getContext('2d');
                new Chart(ctxStatus, {
                    type: 'doughnut',
                    data: {
                        labels: ['Completed', 'In Progress', 'Pending', 'Blocked'],
                        datasets: [{
                            data: [
                                {{ status_dict.get('Completed', 0) }},
                                {{ status_dict.get('In Progress', 0) }},
                                {{ status_dict.get('Pending', 0) }},
                                {{ status_dict.get('Blocked', 0) }}
                            ],
                            backgroundColor: ['#22c55e', '#0284c7', '#f59e0b', '#ef4444']
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false
                    }
                });

                const ctxWorkload = document.getElementById('workloadChart').getContext('2d');
                new Chart(ctxWorkload, {
                    type: 'bar',
                    data: {
                        labels: {{ workload_names|tojson }},
                        datasets: [{
                            label: 'Assigned Tasks',
                            data: {{ workload_tasks|tojson }},
                            backgroundColor: '#4f46e5',
                            borderRadius: 6
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: { legend: { display: false } },
                        scales: { y: { beginAtZero: true, ticks: { stepSize: 1 } } }
                    }
                });
            });
        </script>
        {% endblock %}
        """,
        total_projects=total_projects,
        total_tasks=total_tasks,
        completed_tasks=completed_tasks,
        completion_rate=completion_rate,
        total_logged_hours=total_logged_hours,
        status_dict=status_dict,
        workload_rows=workload_rows,
        workload_names=workload_names,
        workload_tasks=workload_tasks,
        selected_status=selected_status,
    )


# Notification API & View Routes


@app.route("/api/notifications")
@login_required
def api_get_notifications():
    unread_only = request.args.get("unread_only", "1") == "1"
    with get_db() as conn:
        query = """
            SELECT id, title, message, link, is_read, created_at
            FROM notifications
            WHERE user_id = ?
        """
        params = [current_user.id]
        if unread_only:
            query += " AND is_read = 0"

        query += " ORDER BY id DESC LIMIT 15"
        rows = conn.execute(query, params).fetchall()

        unread_count = conn.execute(
            "SELECT COUNT(*) FROM notifications WHERE user_id = ? AND is_read = 0",
            (current_user.id,),
        ).fetchone()[0]

    notifs = [dict(r) for r in rows]
    return jsonify({"unread_count": unread_count, "notifications": notifs})


@app.route("/api/notifications/<int:notif_id>/read", methods=["POST"])
@login_required
def api_mark_notification_read(notif_id):
    with get_db() as conn:
        conn.execute(
            "UPDATE notifications SET is_read = 1 WHERE id = ? AND user_id = ?",
            (notif_id, current_user.id),
        )
        conn.commit()
    return jsonify({"status": "success"})


@app.route("/api/notifications/read-all", methods=["POST"])
@login_required
def api_mark_all_notifications_read():
    with get_db() as conn:
        conn.execute(
            "UPDATE notifications SET is_read = 1 WHERE user_id = ?", (current_user.id,)
        )
        conn.commit()
    return jsonify({"status": "success"})


@app.route("/notifications")
@login_required
def user_notifications():
    from_date = (request.args.get("from_date") or request.args.get("start_date") or "").strip()
    to_date = (request.args.get("to_date") or request.args.get("end_date") or "").strip()

    valid_date_range = True
    if from_date and to_date and from_date > to_date:
        flash("From Date cannot be after To Date.", "warning")
        valid_date_range = False

    sql = """
        SELECT id, title, message, link, is_read, created_at
        FROM notifications
        WHERE user_id = ?
    """
    params = [current_user.id]

    if valid_date_range:
        if from_date and to_date:
            sql += " AND created_at >= ? AND created_at <= ?"
            params.extend([from_date, to_date + " 23:59:59"])
        elif from_date:
            sql += " AND created_at >= ?"
            params.append(from_date)
        elif to_date:
            sql += " AND created_at <= ?"
            params.append(to_date + " 23:59:59")

    sql += " ORDER BY id DESC"

    with get_db() as conn:
        notifications = conn.execute(sql, params).fetchall()

    return render_template_string(
        """
        {% extends "base.html" %}
        {% block title %}Notifications Inbox{% endblock %}
        {% block page_content %}
        <div class="page-header d-flex flex-wrap justify-content-between align-items-center gap-3 mb-4">
            <div>
                <h1>Notifications Inbox</h1>
                <p>System announcements, task alerts, and leave status updates.</p>
            </div>
            <button type="button" class="btn btn-outline-primary btn-sm" onclick="markAllNotificationsReadPage()">
                <i class="bi bi-check-all me-1"></i>Mark All as Read
            </button>
        </div>

        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="alert alert-{{ category }} alert-dismissible fade show" role="alert">
                        {{ message }}
                        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
                    </div>
                {% endfor %}
            {% endif %}
        {% endwith %}

        <div class="card shadow-sm mb-4">
            <div class="card-body py-3">
                <form method="get" class="row g-3 align-items-end">
                    <div class="col-md-4 col-sm-6">
                        <label class="form-label small fw-semibold text-muted mb-1">From Date</label>
                        <input type="date" class="form-control form-control-sm" name="from_date" value="{{ from_date or '' }}">
                    </div>
                    <div class="col-md-4 col-sm-6">
                        <label class="form-label small fw-semibold text-muted mb-1">To Date</label>
                        <input type="date" class="form-control form-control-sm" name="to_date" value="{{ to_date or '' }}">
                    </div>
                    <div class="col-md-4 col-sm-12 d-flex gap-2">
                        <button type="submit" class="btn btn-primary btn-sm px-3 flex-fill"><i class="bi bi-funnel me-1"></i>Filter Inbox</button>
                        {% if from_date or to_date %}
                            <a class="btn btn-outline-secondary btn-sm px-3" href="{{ url_for('user_notifications') }}"><i class="bi bi-x-circle me-1"></i>Clear</a>
                        {% endif %}
                    </div>
                </form>
            </div>
        </div>

        <div class="card shadow-sm border-0">
            <div class="card-body p-0">
                <div class="list-group list-group-flush" id="notifInboxList">
                    {% for n in notifications %}
                        <div class="list-group-item p-3 border-bottom d-flex align-items-start gap-3 {% if not n.is_read %}bg-primary bg-opacity-10{% endif %}">
                            <div class="rounded-circle p-2 {% if not n.is_read %}bg-primary text-white{% else %}bg-secondary bg-opacity-10 text-secondary{% endif %}">
                                <i class="bi bi-bell-fill fs-5"></i>
                            </div>
                            <div class="flex-grow-1">
                                <div class="d-flex justify-content-between align-items-center mb-1">
                                    <h6 class="mb-0 fw-bold">{{ n.title }}</h6>
                                    <small class="text-muted">{{ n.created_at }}</small>
                                </div>
                                <p class="mb-1 text-secondary small">{{ n.message }}</p>
                                {% if n.link %}
                                    <a href="{{ n.link }}" class="btn btn-sm btn-link p-0 text-primary small text-decoration-none fw-semibold">View details <i class="bi bi-arrow-right"></i></a>
                                {% endif %}
                            </div>
                        </div>
                    {% else %}
                        <div class="text-center py-5 text-muted">
                            <i class="bi bi-bell-slash fs-1 d-block mb-2 text-secondary opacity-50"></i>
                            You have no notifications in your inbox.
                        </div>
                    {% endfor %}
                </div>
            </div>
        </div>

        <script>
            function markAllNotificationsReadPage() {
                fetch('/api/notifications/read-all', { method: 'POST' })
                    .then(res => res.json())
                    .then(data => {
                        if (data.status === 'success') {
                            window.location.reload();
                        }
                    });
            }
        </script>
        {% endblock %}
        """,
        notifications=notifications,
    )


# Settings Module Routes


@app.route("/settings")
@login_required
def settings_overview():
    return redirect(url_for("settings_profile"))


@app.route("/settings/profile", methods=["GET", "POST"])
@login_required
def settings_profile():
    if request.method == "POST":
        action = request.form.get("action", "update_profile")
        if action == "remove_picture":
            with get_db() as conn:
                user_rec = conn.execute("SELECT profile_pic FROM users WHERE id = ?", (current_user.id,)).fetchone()
                if user_rec and user_rec["profile_pic"]:
                    old_file_path = os.path.join(app.root_path, "static", user_rec["profile_pic"])
                    if os.path.exists(old_file_path):
                        try:
                            os.remove(old_file_path)
                        except OSError as e:
                            app.logger.debug("Failed to remove old profile picture: %s", e)
                conn.execute("UPDATE users SET profile_pic = NULL WHERE id = ?", (current_user.id,))
                conn.commit()
            flash("Profile picture removed.", "success")
            return redirect(url_for("settings_profile"))

        full_name = request.form.get("full_name", "").strip()
        email = request.form.get("email", "").strip()
        pic_file = request.files.get("profile_pic_file")
        rel_pic_path = None
        if pic_file and pic_file.filename:
            rel_pic_path, err_msg = process_and_save_profile_pic(pic_file, current_user.id)
            if err_msg:
                flash(err_msg, "danger")
                return redirect(url_for("settings_profile"))

        with get_db() as conn:
            if rel_pic_path:
                user_rec = conn.execute("SELECT profile_pic FROM users WHERE id = ?", (current_user.id,)).fetchone()
                if user_rec and user_rec["profile_pic"]:
                    old_file_path = os.path.join(app.root_path, "static", user_rec["profile_pic"])
                    if os.path.exists(old_file_path):
                        try:
                            os.remove(old_file_path)
                        except OSError as e:
                            app.logger.debug("Failed to remove old profile picture: %s", e)
                conn.execute(
                    "UPDATE users SET full_name = ?, email = ?, profile_pic = ? WHERE id = ?",
                    (full_name or None, email or None, rel_pic_path, current_user.id),
                )
            else:
                conn.execute(
                    "UPDATE users SET full_name = ?, email = ? WHERE id = ?",
                    (full_name or None, email or None, current_user.id),
                )
            conn.commit()

        notify_user_by_name_or_username(
            current_user.username,
            "Profile Updated",
            "Your account profile information was updated.",
            url_for("settings_profile"),
        )
        flash("Profile settings updated successfully.", "success")
        return redirect(url_for("settings_profile"))

    with get_db() as conn:
        u = conn.execute(
            "SELECT id, username, full_name, email, role, profile_pic, last_active_at FROM users WHERE id = ?",
            (current_user.id,),
        ).fetchone()

        emp_row = conn.execute(
            "SELECT id FROM employees WHERE user_id = ? OR name = ? OR name = ? ORDER BY id LIMIT 1",
            (current_user.id, u["full_name"] if u else None, current_user.username),
        ).fetchone()

        payroll = calculate_employee_payroll(conn, emp_row["id"]) if emp_row else None
        user_online = is_user_online(u["last_active_at"]) if u else False

    return render_template_string(
        """
        {% extends "base.html" %}
        {% block title %}Profile Settings - Settings{% endblock %}
        {% block page_content %}
        <div class="page-header d-flex justify-content-between align-items-center mb-4">
            <div>
                <h1><i class="bi bi-person-gear me-2 text-primary"></i>Profile Settings</h1>
                <p>Manage your account profile, personal info, contact details, and profile picture.</p>
            </div>
        </div>

        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="alert alert-{{ category }} alert-dismissible fade show" role="alert">
                        {{ message }}
                        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                    </div>
                {% endfor %}
            {% endif %}
        {% endwith %}

        <div class="row g-4 mb-4">
            <div class="col-md-4">
                <div class="card shadow-sm text-center p-4 h-100">
                    <div class="mb-3 position-relative d-inline-block mx-auto">
                        <div class="user-avatar rounded-circle shadow-sm overflow-hidden d-inline-flex align-items-center justify-content-center border" style="width: 120px; height: 120px; background: #e0e7ff; color: #4338ca; position: relative;">
                            {% if u.profile_pic %}
                                <img id="avatarPreviewImg" src="{{ url_for('static', filename=u.profile_pic) }}" alt="Profile Picture" style="width: 100%; height: 100%; object-fit: cover;">
                            {% else %}
                                <img id="avatarPreviewImg" src="" alt="Preview" style="width: 100%; height: 100%; object-fit: cover; display: none;">
                                <span id="avatarPlaceholder" class="fs-1 fw-bold">{{ (u.full_name or u.username)[:1]|upper }}</span>
                            {% endif %}
                            <span class="status-indicator {% if user_online %}online{% else %}offline{% endif %}" style="width: 16px; height: 16px; border: 3px solid #fff; bottom: 4px; right: 4px;" title="{% if user_online %}Online{% else %}Offline{% endif %}"></span>
                        </div>
                    </div>
                    <h5 class="fw-bold mb-1">{{ u.full_name or u.username }}</h5>
                    <p class="text-muted small mb-2">@{{ u.username }}</p>
                    <span class="badge bg-primary px-3 py-2 align-self-center text-uppercase">{{ u.role }}</span>
                    
                    {% if u.profile_pic %}
                    <form method="POST" action="{{ url_for('settings_profile') }}" class="mt-3">
                        <input type="hidden" name="action" value="remove_picture">
                        <button type="submit" class="btn btn-sm btn-outline-danger w-100" onclick="return confirm('Are you sure you want to remove your profile picture?');">
                            <i class="bi bi-trash me-1"></i>Remove Picture
                        </button>
                    </form>
                    {% endif %}
                </div>
            </div>

            <div class="col-md-8">
                <div class="card shadow-sm h-100">
                    <div class="card-header bg-white py-3 border-0">
                        <h5 class="card-title mb-0 fw-bold"><i class="bi bi-pencil-square me-2 text-primary"></i>Edit Personal Information</h5>
                    </div>
                    <div class="card-body">
                        <form method="POST" action="{{ url_for('settings_profile') }}" enctype="multipart/form-data">
                            <input type="hidden" name="action" value="update_profile">
                            <div class="mb-3">
                                <label class="form-label fw-semibold">Profile Picture</label>
                                <input type="file" class="form-control" name="profile_pic_file" id="profile_pic_file" accept=".jpg,.jpeg,.png,.webp" onchange="previewProfilePic(event)">
                                <div class="form-text">Supported formats: JPG, JPEG, PNG, WEBP. Maximum file size: 2 MB. Image will automatically be resized to 256x256 pixels.</div>
                            </div>
                            <div class="mb-3">
                                <label class="form-label fw-semibold">Username</label>
                                <input type="text" class="form-control bg-light" value="{{ u.username }}" readonly disabled>
                                <div class="form-text">Usernames are permanently linked to authentication.</div>
                            </div>
                            <div class="mb-3">
                                <label class="form-label fw-semibold">Full Name</label>
                                <input type="text" class="form-control" name="full_name" value="{{ u.full_name or '' }}" placeholder="Enter full name" required>
                            </div>
                            <div class="mb-3">
                                <label class="form-label fw-semibold">Email Address</label>
                                <input type="email" class="form-control" name="email" value="{{ u.email or '' }}" placeholder="Enter email address">
                            </div>
                            <button type="submit" class="btn btn-primary"><i class="bi bi-check-circle me-1"></i>Save Profile Changes</button>
                        </form>
                    </div>
                </div>
            </div>
        </div>

        <script>
        function previewProfilePic(event) {
            const input = event.target;
            if (input.files && input.files[0]) {
                const file = input.files[0];
                if (file.size > 2 * 1024 * 1024) {
                    alert('File size exceeds maximum limit of 2 MB. Please select a smaller file.');
                    input.value = '';
                    return;
                }
                const reader = new FileReader();
                reader.onload = function(e) {
                    const img = document.getElementById('avatarPreviewImg');
                    const placeholder = document.getElementById('avatarPlaceholder');
                    if (img) {
                        img.src = e.target.result;
                        img.style.display = 'block';
                    }
                    if (placeholder) {
                        placeholder.style.display = 'none';
                    }
                };
                reader.readAsDataURL(file);
            }
        }
        </script>

        {% if payroll %}
        <!-- Payroll Section -->
        <div class="card shadow-sm mb-4">
            <div class="card-header bg-white py-3 border-0 d-flex flex-wrap justify-content-between align-items-center">
                <h5 class="card-title mb-0 fw-bold"><i class="bi bi-wallet2 me-2 text-success"></i>Payroll Section</h5>
                <span class="badge bg-success px-3 py-1 fs-6">{{ payroll.payroll_month }}</span>
            </div>
            <div class="card-body">
                <div class="row g-3 mb-3">
                    <div class="col-md-4">
                        <div class="p-3 bg-light rounded border text-center h-100">
                            <span class="text-muted small d-block mb-1">Current Base Salary</span>
                            <strong class="fs-5 text-dark">{{ payroll.base_salary | inr }}</strong>
                        </div>
                    </div>
                    <div class="col-md-4">
                        <div class="p-3 bg-light rounded border text-center h-100">
                            <span class="text-muted small d-block mb-1">Current Month Final Salary</span>
                            <strong class="fs-4 text-success">{{ payroll.final_salary | inr }}</strong>
                            {% if payroll.leave_deduction > 0 %}
                                <div class="text-danger small mt-1">(Leave Deduction: -{{ payroll.leave_deduction | inr }})</div>
                            {% else %}
                                <div class="text-muted small mt-1">(No Deductions)</div>
                            {% endif %}
                        </div>
                    </div>
                    <div class="col-md-4">
                        <div class="p-3 bg-light rounded border text-center h-100">
                            <span class="text-muted small d-block mb-1">Payroll Month</span>
                            <strong class="fs-6 text-primary">{{ payroll.payroll_month }}</strong>
                            <div class="text-muted small mt-1">Status: <span class="badge bg-info text-dark">{{ payroll.payroll_status }}</span></div>
                        </div>
                    </div>
                </div>
                <div class="row g-2">
                    <div class="col-4 col-md-4">
                        <div class="p-2 bg-light rounded border text-center">
                            <span class="text-muted small d-block">Attendance %</span>
                            <strong class="text-success">{{ payroll.attendance_pct }}%</strong>
                        </div>
                    </div>
                    <div class="col-4 col-md-4">
                        <div class="p-2 bg-light rounded border text-center">
                            <span class="text-muted small d-block">Approved Leave Days</span>
                            <strong class="text-info">{{ payroll.approved_leave_days }}</strong>
                        </div>
                    </div>
                    <div class="col-4 col-md-4">
                        <div class="p-2 bg-light rounded border text-center">
                            <span class="text-muted small d-block">Performance %</span>
                            <strong class="text-primary">{{ payroll.performance_score }}%</strong>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        {% endif %}
        {% endblock %}
        """,
        u=u,
        payroll=payroll,
        user_online=user_online,
    )


@app.route("/settings/security", methods=["GET", "POST"])
@login_required
def settings_security():
    if request.method == "POST":
        action = request.form.get("action")
        if action == "change_password":
            curr_pw = request.form.get("current_password", "").strip()
            new_pw = request.form.get("new_password", "").strip()
            conf_pw = request.form.get("confirm_password", "").strip()

            if not check_password_hash(current_user.password_hash, curr_pw):
                flash("Current password is incorrect.", "danger")
                return redirect(url_for("settings_security"))
            if new_pw != conf_pw:
                flash("New passwords do not match.", "danger")
                return redirect(url_for("settings_security"))
            if len(new_pw) < 6:
                flash("New password must be at least 6 characters.", "danger")
                return redirect(url_for("settings_security"))

            with get_db() as conn:
                conn.execute(
                    "UPDATE users SET password_hash = ?, force_password_change = 0 WHERE id = ?",
                    (generate_password_hash(new_pw), current_user.id),
                )
                conn.commit()
            current_user.password_hash = generate_password_hash(new_pw)
            current_user.force_password_change = False
            create_notification(
                current_user.id,
                "Security Alert: Password Changed",
                "Your account password was changed successfully.",
                url_for("settings_security"),
            )
            flash("Password updated successfully.", "success")
            return redirect(url_for("settings_security"))

    return render_template_string(
        """
        {% extends "base.html" %}
        {% block title %}Security Settings - Settings{% endblock %}
        {% block page_content %}
        <div class="page-header d-flex justify-content-between align-items-center mb-4">
            <div>
                <h1><i class="bi bi-shield-lock me-2 text-primary"></i>Security Settings</h1>
                <p>Manage account security, update authentication passwords, and monitor sessions.</p>
            </div>
        </div>

        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="alert alert-{{ category }} alert-dismissible fade show" role="alert">
                        {{ message }}
                        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                    </div>
                {% endfor %}
            {% endif %}
        {% endwith %}

        <div class="row g-4">
            <div class="col-md-6">
                <div class="card shadow-sm h-100">
                    <div class="card-header bg-white py-3 border-0">
                        <h5 class="card-title mb-0 fw-bold"><i class="bi bi-key me-2 text-primary"></i>Change Account Password</h5>
                    </div>
                    <div class="card-body">
                        <form method="POST" action="{{ url_for('settings_security') }}">
                            <input type="hidden" name="action" value="change_password">
                            <div class="mb-3">
                                <label class="form-label fw-semibold">Current Password</label>
                                <input type="password" class="form-control" name="current_password" required>
                            </div>
                            <div class="mb-3">
                                <label class="form-label fw-semibold">New Password</label>
                                <input type="password" class="form-control" name="new_password" minlength="6" required>
                            </div>
                            <div class="mb-3">
                                <label class="form-label fw-semibold">Confirm New Password</label>
                                <input type="password" class="form-control" name="confirm_password" minlength="6" required>
                            </div>
                            <button type="submit" class="btn btn-primary"><i class="bi bi-shield-check me-1"></i>Update Password</button>
                        </form>
                    </div>
                </div>
            </div>

            <div class="col-md-6">
                <div class="card shadow-sm h-100">
                    <div class="card-header bg-white py-3 border-0">
                        <h5 class="card-title mb-0 fw-bold"><i class="bi bi-shield-check me-2 text-success"></i>Security & Session Overview</h5>
                    </div>
                    <div class="card-body">
                        <div class="d-flex align-items-center mb-3 p-3 bg-light rounded">
                            <i class="bi bi-person-badge fs-2 text-primary me-3"></i>
                            <div>
                                <h6 class="mb-0 fw-bold">Role Privilege</h6>
                                <span class="text-muted small">Account role level: <span class="badge bg-secondary text-uppercase">{{ current_user.role }}</span></span>
                            </div>
                        </div>
                        <div class="d-flex align-items-center mb-3 p-3 bg-light rounded">
                            <i class="bi bi-laptop fs-2 text-success me-3"></i>
                            <div>
                                <h6 class="mb-0 fw-bold">Active Web Session</h6>
                                <span class="text-muted small">Logged in as @{{ current_user.username }}</span>
                            </div>
                        </div>
                        <div class="d-flex align-items-center p-3 bg-light rounded">
                            <i class="bi bi-lock-fill fs-2 text-info me-3"></i>
                            <div>
                                <h6 class="mb-0 fw-bold">Two-Factor Authentication</h6>
                                <span class="text-muted small">Standard Session Encryption Active</span>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        {% endblock %}
        """
    )


@app.route("/settings/appearance", methods=["GET", "POST"])
@login_required
def settings_appearance():
    if request.method == "POST":
        theme = request.form.get("theme", "light").strip()
        with get_db() as conn:
            conn.execute(
                """
                INSERT INTO user_preferences (user_id, theme)
                VALUES (?, ?)
                ON CONFLICT(user_id) DO UPDATE SET theme = excluded.theme
            """,
                (current_user.id, theme),
            )
            conn.commit()
        flash("Appearance preferences saved.", "success")
        return redirect(url_for("settings_appearance"))

    with get_db() as conn:
        pref = conn.execute(
            "SELECT theme FROM user_preferences WHERE user_id = ?",
            (current_user.id,),
        ).fetchone()

    theme = pref["theme"] if pref else "light"

    return render_template_string(
        """
        {% extends "base.html" %}
        {% block title %}Appearance Settings - Settings{% endblock %}
        {% block page_content %}
        <div class="page-header d-flex justify-content-between align-items-center mb-4">
            <div>
                <h1><i class="bi bi-palette me-2 text-primary"></i>Appearance Settings</h1>
                <p>Customize UI color themes and display preferences.</p>
            </div>
        </div>

        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="alert alert-{{ category }} alert-dismissible fade show" role="alert">
                        {{ message }}
                        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                    </div>
                {% endfor %}
            {% endif %}
        {% endwith %}

        <div class="card shadow-sm">
            <div class="card-header bg-white py-3 border-0">
                <h5 class="card-title mb-0 fw-bold"><i class="bi bi-sliders me-2 text-primary"></i>Theme Customization</h5>
            </div>
            <div class="card-body">
                <form method="POST" action="{{ url_for('settings_appearance') }}">
                    <div class="mb-4">
                        <label class="form-label fw-bold">Interface Theme</label>
                        <div class="row g-3">
                            <div class="col-md-4">
                                <div class="form-check card p-3 border text-center h-100">
                                    <input class="form-check-input mx-auto mb-2" type="radio" name="theme" id="themeLight" value="light" {% if theme == 'light' %}checked{% endif %}>
                                    <label class="form-check-label fw-semibold cursor-pointer" for="themeLight">
                                        <i class="bi bi-sun fs-2 text-warning d-block mb-1"></i>
                                        Light Theme
                                    </label>
                                </div>
                            </div>
                            <div class="col-md-4">
                                <div class="form-check card p-3 border text-center h-100">
                                    <input class="form-check-input mx-auto mb-2" type="radio" name="theme" id="themeDark" value="dark" {% if theme == 'dark' %}checked{% endif %}>
                                    <label class="form-check-label fw-semibold cursor-pointer" for="themeDark">
                                        <i class="bi bi-moon-stars fs-2 text-primary d-block mb-1"></i>
                                        Dark Mode
                                    </label>
                                </div>
                            </div>
                            <div class="col-md-4">
                                <div class="form-check card p-3 border text-center h-100">
                                    <input class="form-check-input mx-auto mb-2" type="radio" name="theme" id="themeSystem" value="system" {% if theme == 'system' %}checked{% endif %}>
                                    <label class="form-check-label fw-semibold cursor-pointer" for="themeSystem">
                                        <i class="bi bi-display fs-2 text-secondary d-block mb-1"></i>
                                        System Theme
                                    </label>
                                </div>
                            </div>
                        </div>
                    </div>

                    <button type="submit" class="btn btn-primary"><i class="bi bi-check-circle me-1"></i>Save Appearance</button>
                </form>
            </div>
        </div>
        {% endblock %}
        """,
        theme=theme,
    )


@app.route("/settings/company", methods=["GET", "POST"])
@login_required
def settings_company():
    if current_user.role != "admin":
        flash("Admin access required for Company Settings.", "danger")
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        c_name = request.form.get("company_name", "").strip()
        c_email = request.form.get("company_email", "").strip()
        c_address = request.form.get("company_address", "").strip()
        w_hours = request.form.get("working_hours", "").strip()
        gst = request.form.get("gst_number", "").strip()

        with get_db() as conn:
            conn.execute(
                """
                UPDATE company_settings
                SET company_name = ?, company_email = ?, company_address = ?, working_hours = ?, gst_number = ?
                WHERE id = 1
            """,
                (c_name, c_email, c_address, w_hours, gst),
            )
            conn.commit()
        flash("Company settings updated successfully.", "success")
        return redirect(url_for("settings_company"))

    with get_db() as conn:
        cs = conn.execute(
            "SELECT company_name, company_email, company_address, working_hours, gst_number FROM company_settings WHERE id = 1"
        ).fetchone()

    return render_template_string(
        """
        {% extends "base.html" %}
        {% block title %}Company Settings - Settings{% endblock %}
        {% block page_content %}
        <div class="page-header d-flex justify-content-between align-items-center mb-4">
            <div>
                <h1><i class="bi bi-building-gear me-2 text-primary"></i>Company Settings</h1>
                <p>Configure enterprise organization details, working hours, and GST credentials.</p>
            </div>
        </div>

        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="alert alert-{{ category }} alert-dismissible fade show" role="alert">
                        {{ message }}
                        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                    </div>
                {% endfor %}
            {% endif %}
        {% endwith %}

        <div class="card shadow-sm">
            <div class="card-header bg-white py-3 border-0">
                <h5 class="card-title mb-0 fw-bold"><i class="bi bi-building me-2 text-primary"></i>Enterprise Profile & Operational Parameters</h5>
            </div>
            <div class="card-body">
                <form method="POST" action="{{ url_for('settings_company') }}">
                    <div class="row g-3">
                        <div class="col-md-6">
                            <label class="form-label fw-semibold">Company Legal Name</label>
                            <input type="text" class="form-control" name="company_name" value="{{ cs.company_name if cs else '' }}" required>
                        </div>
                        <div class="col-md-6">
                            <label class="form-label fw-semibold">Contact Email</label>
                            <input type="email" class="form-control" name="company_email" value="{{ cs.company_email if cs else '' }}" required>
                        </div>
                        <div class="col-12">
                            <label class="form-label fw-semibold">Corporate Address</label>
                            <textarea class="form-control" name="company_address" rows="2" required>{{ cs.company_address if cs else '' }}</textarea>
                        </div>
                        <div class="col-md-6">
                            <label class="form-label fw-semibold">Standard Working Hours</label>
                            <input type="text" class="form-control" name="working_hours" value="{{ cs.working_hours if cs else '' }}" required>
                        </div>
                        <div class="col-md-6">
                            <label class="form-label fw-semibold">GST / Tax Registration Number</label>
                            <input type="text" class="form-control" name="gst_number" value="{{ cs.gst_number if cs else '' }}" required>
                        </div>
                    </div>
                    <button type="submit" class="btn btn-primary mt-4"><i class="bi bi-check-circle me-1"></i>Save Company Settings</button>
                </form>
            </div>
        </div>
        {% endblock %}
        """,
        cs=cs,
    )


@app.route("/settings/holidays", methods=["GET", "POST"])
@login_required
def settings_holidays():
    ensure_holidays_table()
    if request.method == "POST":
        if current_user.role not in ("admin", "hr"):
            flash("Access denied to modify holidays.", "danger")
            return redirect(url_for("settings_holidays"))

        action = request.form.get("action")
        if action == "add":
            title = (request.form.get("title") or "").strip()
            h_date = (request.form.get("date") or "").strip()
            description = (request.form.get("description") or "").strip()
            holiday_type = request.form.get("holiday_type", "Public Holiday").strip()
            is_paid_val = 1 if request.form.get("is_paid", "1") in ("1", "Yes", "on") else 0

            if not title or not h_date:
                flash("Holiday Name and Date are required.", "danger")
                return redirect(url_for("settings_holidays"))

            with get_db() as conn:
                existing = conn.execute("SELECT id FROM holidays WHERE date = ?", (h_date,)).fetchone()
                if existing:
                    flash(f"A holiday already exists for date {h_date}.", "warning")
                    return redirect(url_for("settings_holidays"))

                conn.execute(
                    "INSERT INTO holidays (title, date, description, holiday_type, is_paid) VALUES (?, ?, ?, ?, ?)",
                    (title, h_date, description, holiday_type, is_paid_val),
                )
                conn.commit()
            flash("Holiday added successfully.", "success")
            return redirect(url_for("settings_holidays"))

        elif action == "edit":
            h_id = request.form.get("id")
            title = (request.form.get("title") or "").strip()
            h_date = (request.form.get("date") or "").strip()
            description = (request.form.get("description") or "").strip()
            holiday_type = request.form.get("holiday_type", "Public Holiday").strip()
            is_paid_val = 1 if request.form.get("is_paid", "1") in ("1", "Yes", "on") else 0

            if not h_id or not title or not h_date:
                flash("Valid ID, Name, and Date are required.", "danger")
                return redirect(url_for("settings_holidays"))

            with get_db() as conn:
                conn.execute(
                    "UPDATE holidays SET title = ?, date = ?, description = ?, holiday_type = ?, is_paid = ? WHERE id = ?",
                    (title, h_date, description, holiday_type, is_paid_val, h_id),
                )
                conn.commit()
            flash("Holiday updated successfully.", "success")
            return redirect(url_for("settings_holidays"))

        elif action == "delete":
            h_id = request.form.get("id")
            if h_id:
                with get_db() as conn:
                    conn.execute("DELETE FROM holidays WHERE id = ?", (h_id,))
                    conn.commit()
                flash("Holiday deleted successfully.", "success")
            return redirect(url_for("settings_holidays"))

    with get_db() as conn:
        holidays_rows = conn.execute(
            "SELECT * FROM holidays ORDER BY date DESC"
        ).fetchall()
        holidays_list = [dict(r) for r in holidays_rows]

    return render_template_string(
        """
        {% extends "base.html" %}
        {% block title %}Holiday Management - HRMS{% endblock %}
        {% block page_content %}
        <div class="page-header d-flex flex-wrap justify-content-between align-items-center mb-4 gap-3">
            <div>
                <h1><i class="bi bi-calendar-event me-2 text-primary"></i>Holiday Management</h1>
                <p class="text-muted mb-0">Configure Public & Company Holidays for attendance and payroll calculations.</p>
            </div>
            {% if current_user.role in ['admin', 'hr'] %}
            <div>
                <button type="button" class="btn btn-primary" data-bs-toggle="modal" data-bs-target="#addHolidayModal">
                    <i class="bi bi-plus-lg me-1"></i>Add Holiday
                </button>
            </div>
            {% endif %}
        </div>

        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="alert alert-{{ category }} alert-dismissible fade show" role="alert">
                        {{ message }}
                        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                    </div>
                {% endfor %}
            {% endif %}
        {% endwith %}

        <div class="card shadow-sm">
            <div class="card-header bg-white py-3 border-0 d-flex justify-content-between align-items-center">
                <h5 class="card-title mb-0 fw-bold"><i class="bi bi-list-stars me-2 text-primary"></i>Configured Holidays</h5>
                <span class="badge bg-light text-dark border">Total: {{ holidays_list|length }}</span>
            </div>
            <div class="card-body p-0">
                <div class="table-responsive">
                    <table class="table table-hover align-middle mb-0">
                        <thead class="table-light">
                            <tr>
                                <th>Holiday Name</th>
                                <th>Date</th>
                                <th>Holiday Type</th>
                                <th>Paid Holiday</th>
                                <th>Description</th>
                                {% if current_user.role in ['admin', 'hr'] %}<th class="text-end">Actions</th>{% endif %}
                            </tr>
                        </thead>
                        <tbody>
                            {% for h in holidays_list %}
                                <tr>
                                    <td class="fw-bold text-dark"><i class="bi bi-calendar2-check me-2 text-primary"></i>{{ h.title }}</td>
                                    <td class="text-nowrap">{{ h.date }}</td>
                                    <td>
                                        <span class="badge {% if h.holiday_type == 'Public Holiday' %}bg-primary{% else %}bg-info text-dark{% endif %}">
                                            {{ h.holiday_type or 'Public Holiday' }}
                                        </span>
                                    </td>
                                    <td>
                                        {% if h.is_paid == 1 or h.is_paid == '1' or h.is_paid == 'Yes' %}
                                            <span class="badge bg-success"><i class="bi bi-check-circle me-1"></i>Paid</span>
                                        {% else %}
                                            <span class="badge bg-secondary"><i class="bi bi-x-circle me-1"></i>Unpaid</span>
                                        {% endif %}
                                    </td>
                                    <td class="text-muted small">{{ h.description or '-' }}</td>
                                    {% if current_user.role in ['admin', 'hr'] %}
                                    <td class="text-end text-nowrap">
                                        <button type="button" class="btn btn-sm btn-outline-primary me-1" data-bs-toggle="modal" data-bs-target="#editHolidayModal{{ h.id }}">
                                            <i class="bi bi-pencil me-1"></i>Edit
                                        </button>
                                        <form method="POST" action="{{ url_for('settings_holidays') }}" class="d-inline" onsubmit="return confirm('Are you sure you want to delete this holiday?');">
                                            <input type="hidden" name="action" value="delete">
                                            <input type="hidden" name="id" value="{{ h.id }}">
                                            <button type="submit" class="btn btn-sm btn-outline-danger"><i class="bi bi-trash me-1"></i>Delete</button>
                                        </form>

                                        <!-- Edit Modal -->
                                        <div class="modal fade text-start" id="editHolidayModal{{ h.id }}" tabindex="-1" aria-hidden="true">
                                            <div class="modal-dialog modal-dialog-centered">
                                                <div class="modal-content">
                                                    <form method="POST" action="{{ url_for('settings_holidays') }}">
                                                        <input type="hidden" name="action" value="edit">
                                                        <input type="hidden" name="id" value="{{ h.id }}">
                                                        <div class="modal-header">
                                                            <h5 class="modal-title fw-bold"><i class="bi bi-pencil-square me-2 text-primary"></i>Edit Holiday</h5>
                                                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                                                        </div>
                                                        <div class="modal-body">
                                                            <div class="mb-3">
                                                                <label class="form-label fw-semibold">Holiday Name</label>
                                                                <input type="text" name="title" value="{{ h.title }}" class="form-control" required>
                                                            </div>
                                                            <div class="mb-3">
                                                                <label class="form-label fw-semibold">Holiday Date</label>
                                                                <input type="date" name="date" value="{{ h.date }}" class="form-control" required>
                                                            </div>
                                                            <div class="row g-3 mb-3">
                                                                <div class="col-md-6">
                                                                    <label class="form-label fw-semibold">Holiday Type</label>
                                                                    <select name="holiday_type" class="form-select">
                                                                        <option value="Public Holiday" {% if h.holiday_type == 'Public Holiday' %}selected{% endif %}>Public Holiday</option>
                                                                        <option value="Company Holiday" {% if h.holiday_type == 'Company Holiday' %}selected{% endif %}>Company Holiday</option>
                                                                    </select>
                                                                </div>
                                                                <div class="col-md-6">
                                                                    <label class="form-label fw-semibold">Paid Holiday</label>
                                                                    <select name="is_paid" class="form-select">
                                                                        <option value="1" {% if h.is_paid == 1 or h.is_paid == '1' or h.is_paid == 'Yes' %}selected{% endif %}>Yes (Paid)</option>
                                                                        <option value="0" {% if h.is_paid == 0 or h.is_paid == '0' or h.is_paid == 'No' %}selected{% endif %}>No (Unpaid)</option>
                                                                    </select>
                                                                </div>
                                                            </div>
                                                            <div class="mb-3">
                                                                <label class="form-label fw-semibold">Description (Optional)</label>
                                                                <textarea name="description" class="form-control" rows="2">{{ h.description or '' }}</textarea>
                                                            </div>
                                                        </div>
                                                        <div class="modal-footer">
                                                            <button type="button" class="btn btn-secondary btn-sm" data-bs-dismiss="modal">Cancel</button>
                                                            <button type="submit" class="btn btn-primary btn-sm"><i class="bi bi-check-lg me-1"></i>Save Changes</button>
                                                        </div>
                                                    </form>
                                                </div>
                                            </div>
                                        </div>
                                    </td>
                                    {% endif %}
                                </tr>
                            {% else %}
                                <tr>
                                    <td colspan="6" class="text-center py-4 text-muted">No holidays configured yet.</td>
                                </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>

        {% if current_user.role in ['admin', 'hr'] %}
        <!-- Add Holiday Modal -->
        <div class="modal fade" id="addHolidayModal" tabindex="-1" aria-hidden="true">
            <div class="modal-dialog modal-dialog-centered">
                <div class="modal-content">
                    <form method="POST" action="{{ url_for('settings_holidays') }}">
                        <input type="hidden" name="action" value="add">
                        <div class="modal-header">
                            <h5 class="modal-title fw-bold"><i class="bi bi-calendar-plus me-2 text-primary"></i>Add New Holiday</h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body">
                            <div class="mb-3">
                                <label class="form-label fw-semibold">Holiday Name</label>
                                <input type="text" name="title" class="form-control" placeholder="e.g. Independence Day" required>
                            </div>
                            <div class="mb-3">
                                <label class="form-label fw-semibold">Holiday Date</label>
                                <input type="date" name="date" class="form-control" required>
                            </div>
                            <div class="row g-3 mb-3">
                                <div class="col-md-6">
                                    <label class="form-label fw-semibold">Holiday Type</label>
                                    <select name="holiday_type" class="form-select">
                                        <option value="Public Holiday" selected>Public Holiday</option>
                                        <option value="Company Holiday">Company Holiday</option>
                                    </select>
                                </div>
                                <div class="col-md-6">
                                    <label class="form-label fw-semibold">Paid Holiday</label>
                                    <select name="is_paid" class="form-select">
                                        <option value="1" selected>Yes (Paid)</option>
                                        <option value="0">No (Unpaid)</option>
                                    </select>
                                </div>
                            </div>
                            <div class="mb-3">
                                <label class="form-label fw-semibold">Description (Optional)</label>
                                <textarea name="description" class="form-control" rows="2" placeholder="Short description of the holiday"></textarea>
                            </div>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary btn-sm" data-bs-dismiss="modal">Cancel</button>
                            <button type="submit" class="btn btn-primary btn-sm"><i class="bi bi-plus-lg me-1"></i>Add Holiday</button>
                        </div>
                    </form>
                </div>
            </div>
        </div>
        {% endif %}
        {% endblock %}
        """,
        holidays_list=holidays_list,
    )


@app.route("/settings/payroll", methods=["GET", "POST"])
@login_required
def settings_payroll():
    ensure_payroll_table()
    now = datetime.datetime.now(tz=IST)

    if request.method == "POST":
        action = request.form.get("action")
        if action == "update_base_salary":
            if current_user.role not in ("admin", "hr"):
                flash("Access denied to edit Base Salary.", "danger")
                return redirect(url_for("settings_payroll"))
            emp_id = request.form.get("emp_id")
            new_salary = request.form.get("salary")
            try:
                sal_val = float(new_salary) if new_salary is not None else 0.0
                if emp_id is None:
                    raise ValueError("Missing emp_id")
                emp_id_val = int(emp_id)
            except (ValueError, TypeError):
                flash("Invalid salary input.", "danger")
                return redirect(url_for("settings_payroll"))

            with get_db() as conn:
                conn.execute(
                    "UPDATE employees SET salary = ? WHERE id = ?",
                    (sal_val, emp_id_val),
                )
                conn.commit()
            flash("Base salary updated successfully.", "success")
            return redirect(url_for("settings_payroll"))

        elif action in ("finalize_payroll", "mark_paid"):
            if current_user.role not in ("admin", "hr"):
                flash("Access denied to update payroll status.", "danger")
                return redirect(url_for("settings_payroll"))
            emp_id = request.form.get("emp_id")
            month_year_val = request.form.get("month_year")
            new_status = "Paid" if action == "mark_paid" else "Finalized"
            if emp_id and month_year_val:
                try:
                    y, m = [int(x) for x in month_year_val.split("-")]
                except (ValueError, TypeError, AttributeError):
                    y, m = now.year, now.month

                with get_db() as conn:
                    p = calculate_employee_payroll(conn, int(emp_id), y, m)
                    if p:
                        created_now = datetime.datetime.now(tz=IST).strftime("%Y-%m-%d %H:%M:%S")
                        sb_json = json.dumps(p.get("salary_breakdown", {}))
                        conn.execute(
                            """
                            INSERT INTO payroll_records (
                                employee_id, user_id, month_year, base_salary, working_days,
                                present_days, attendance_pct, approved_leave_days, unpaid_leave_days,
                                performance_score, leave_deduction, adjustments, final_salary, status,
                                salary_breakdown, created_at
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            ON CONFLICT(employee_id, month_year) DO UPDATE SET
                                status = excluded.status
                            """,
                            (
                                p["emp_id"], p.get("user_id"), p["month_year"], p["base_salary"], p["working_days"],
                                p["present_days"], p["attendance_pct"], p["approved_leave_days"], p["unpaid_leave_days"],
                                p["performance_score"], p["leave_deduction"], p["adjustments"], p["final_salary"], new_status,
                                sb_json, created_now
                            ),
                        )
                        conn.commit()
                        flash(f"Payroll record for {p['name']} ({p['payroll_month']}) updated to {new_status}.", "success")
            return redirect(url_for("settings_payroll", month=month_year_val))

        else:
            if current_user.role != "admin":
                flash("Admin access required to save currency settings.", "danger")
                return redirect(url_for("settings_payroll"))
            currency = request.form.get("currency", "INR (₹)").strip()
            with get_db() as conn:
                conn.execute(
                    "UPDATE company_settings SET currency = ? WHERE id = 1",
                    (currency,),
                )
                conn.commit()
            flash("Payroll currency and settings updated.", "success")
            return redirect(url_for("settings_payroll"))

    month_arg = request.args.get("month")
    selected_emp_id = request.args.get("employee_id")
    selected_year_filter = request.args.get("year")

    try:
        if month_arg and "-" in month_arg:
            y_str, m_str = month_arg.split("-", 1)
            sel_year = int(y_str)
            sel_month = int(m_str)
        else:
            sel_year = now.year
            sel_month = now.month
    except (ValueError, TypeError):
        sel_year = now.year
        sel_month = now.month

    selected_month_str = f"{sel_year:04d}-{sel_month:02d}"

    with get_db() as conn:
        cs = conn.execute(
            "SELECT currency FROM company_settings WHERE id = 1"
        ).fetchone()

        all_employees = conn.execute("SELECT id, name, department FROM employees ORDER BY name").fetchall()
        employees_list = [dict(r) for r in all_employees]

        if current_user.role in ("admin", "hr"):
            if selected_emp_id:
                emp_rows = conn.execute(
                    "SELECT id FROM employees WHERE id = ? ORDER BY name", (int(selected_emp_id),)
                ).fetchall()
            else:
                emp_rows = conn.execute("SELECT id FROM employees ORDER BY name").fetchall()
        else:
            u_fn = None
            u_rec = conn.execute("SELECT full_name FROM users WHERE id = ?", (current_user.id,)).fetchone()
            if u_rec and u_rec["full_name"]:
                u_fn = u_rec["full_name"]
            emp_rows = conn.execute(
                "SELECT id FROM employees WHERE user_id = ? OR name = ? OR name = ? ORDER BY name",
                (current_user.id, u_fn, current_user.username),
            ).fetchall()
            if not emp_rows:
                emp_rows = conn.execute("SELECT id FROM employees ORDER BY name").fetchall()

        payroll_list = []
        for emp_r in emp_rows:
            p_data = calculate_employee_payroll(conn, emp_r["id"], sel_year, sel_month)
            if p_data:
                payroll_list.append(p_data)

        # Fetch Payroll History Records
        history_query = """
            SELECT pr.*, e.name as emp_name, e.department as emp_dept
            FROM payroll_records pr
            JOIN employees e ON pr.employee_id = e.id
        """
        history_params = []
        history_conditions = []

        if current_user.role not in ("admin", "hr"):
            emp_user_rec = conn.execute("SELECT id FROM employees WHERE user_id = ?", (current_user.id,)).fetchone()
            user_emp_id = emp_user_rec["id"] if emp_user_rec else None
            if user_emp_id:
                history_conditions.append("pr.employee_id = ?")
                history_params.append(user_emp_id)
        elif selected_emp_id:
            history_conditions.append("pr.employee_id = ?")
            history_params.append(int(selected_emp_id))

        if selected_year_filter:
            history_conditions.append("pr.month_year LIKE ?")
            history_params.append(f"{selected_year_filter}-%")

        if history_conditions:
            history_query += " WHERE " + " AND ".join(history_conditions)

        history_query += " ORDER BY pr.month_year DESC, pr.created_at DESC"

        history_rows = conn.execute(history_query, history_params).fetchall()
        payroll_history = []
        for hr in history_rows:
            h_dict = dict(hr)
            try:
                hy, hm = [int(x) for x in h_dict["month_year"].split("-")]
                h_dict["month_name"] = datetime.date(hy, hm, 1).strftime("%B %Y")
            except (ValueError, TypeError, AttributeError, KeyError):
                h_dict["month_name"] = h_dict["month_year"]
            payroll_history.append(h_dict)

    currency = cs["currency"] if cs else "INR (₹)"

    year_set = set(range(now.year - 5, now.year + 6))
    db_years = conn.execute("SELECT DISTINCT substr(month_year, 1, 4) AS y FROM payroll_records").fetchall()
    for y_row in db_years:
        if y_row["y"] and y_row["y"].isdigit():
            year_set.add(int(y_row["y"]))
    if selected_year_filter and selected_year_filter.isdigit():
        year_set.add(int(selected_year_filter))
    available_payroll_years = sorted(list(year_set), reverse=True)

    return render_template_string(
        """
        {% extends "base.html" %}
        {% block title %}Payroll - HRMS{% endblock %}
        {% block page_content %}
        <div class="page-header d-flex flex-wrap justify-content-between align-items-center mb-4 gap-3">
            <div>
                <h1><i class="bi bi-currency-rupee me-2 text-primary"></i>Payroll & Salary Management</h1>
                <p class="text-muted mb-0">Automated monthly salary calculation based on Attendance, approved Leaves, and Base Salary.</p>
            </div>
            <div class="d-flex align-items-center gap-2">
                <form method="GET" action="{{ url_for('settings_payroll') }}" class="d-flex align-items-center gap-2 flex-wrap">
                    {% if current_user.role in ['admin', 'hr'] %}
                    <select name="employee_id" class="form-select form-select-sm" style="max-width: 170px;" onchange="this.form.submit()">
                        <option value="">All Employees</option>
                        {% for emp in employees_list %}
                            <option value="{{ emp.id }}" {% if selected_emp_id and selected_emp_id|int == emp.id %}selected{% endif %}>{{ emp.name }}</option>
                        {% endfor %}
                    </select>
                    {% endif %}
                    <input type="month" name="month" value="{{ selected_month_str }}" class="form-control form-control-sm" onchange="this.form.submit()">
                </form>
            </div>
        </div>

        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="alert alert-{{ category }} alert-dismissible fade show" role="alert">
                        {{ message }}
                        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                    </div>
                {% endfor %}
            {% endif %}
        {% endwith %}

        {% if current_user.role == 'admin' %}
        <div class="card shadow-sm mb-4">
            <div class="card-header bg-white py-3 border-0">
                <h5 class="card-title mb-0 fw-bold"><i class="bi bi-cash-stack me-2 text-success"></i>Global Currency & Payroll Parameters</h5>
            </div>
            <div class="card-body">
                <form method="POST" action="{{ url_for('settings_payroll') }}">
                    <div class="mb-3">
                        <label class="form-label fw-bold">Primary HRMS Currency</label>
                        <select name="currency" class="form-select">
                            <option value="INR (₹)" {% if currency == 'INR (₹)' %}selected{% endif %}>Indian Rupee (INR - ₹)</option>
                            <option value="USD ($)" {% if currency == 'USD ($)' %}selected{% endif %}>US Dollar (USD - $)</option>
                        </select>
                        <div class="form-text text-muted">Selected currency symbol is applied across all employee profiles and financial views.</div>
                    </div>
                    <button type="submit" class="btn btn-primary btn-sm"><i class="bi bi-check-circle me-1"></i>Save Currency Settings</button>
                </form>
            </div>
        </div>
        {% endif %}

        <!-- Payroll Records Table -->
        <div class="card shadow-sm mb-4">
            <div class="card-header bg-white py-3 border-0 d-flex justify-content-between align-items-center flex-wrap gap-2">
                <h5 class="card-title mb-0 fw-bold"><i class="bi bi-wallet2 me-2 text-primary"></i>Current Month Payroll Breakdown</h5>
                <span class="badge bg-light text-dark border">Month: {{ selected_month_str }}</span>
            </div>
            <div class="card-body p-0">
                <div class="table-responsive">
                    <table class="table table-hover align-middle mb-0" style="font-size: 0.9rem;">
                        <thead class="table-light">
                            <tr>
                                <th>Employee</th>
                                <th>Payroll Month</th>
                                <th>Base Salary</th>
                                <th>Working Days</th>
                                <th>Present Days</th>
                                <th>Attendance %</th>
                                <th>Approved Leaves</th>
                                <th>Unpaid Leaves</th>
                                <th>Performance %</th>
                                <th>Leave Deduction</th>
                                <th>Final Salary</th>
                                <th>Status</th>
                                <th>Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            {% for item in payroll_list %}
                                <tr>
                                    <td class="fw-bold text-nowrap">
                                        <i class="bi bi-person-circle me-1 text-primary"></i>{{ item.name }}
                                        <div class="text-muted small fw-normal">{{ item.department }}</div>
                                    </td>
                                    <td class="text-nowrap">{{ item.payroll_month }}</td>
                                    <td>
                                        {% if current_user.role in ['admin', 'hr'] %}
                                            <form method="POST" action="{{ url_for('settings_payroll') }}" class="d-flex align-items-center gap-1" style="min-width: 130px;">
                                                <input type="hidden" name="action" value="update_base_salary">
                                                <input type="hidden" name="emp_id" value="{{ item.emp_id }}">
                                                <input type="number" step="0.01" name="salary" class="form-control form-control-sm" value="{{ item.base_salary }}" required style="width: 85px;">
                                                <button type="submit" class="btn btn-sm btn-outline-primary p-1" title="Save Base Salary"><i class="bi bi-check-lg"></i></button>
                                            </form>
                                        {% else %}
                                            <span class="fw-bold text-dark">{{ item.base_salary | inr }}</span>
                                        {% endif %}
                                    </td>
                                    <td class="text-center"><span class="badge bg-light text-dark border">{{ item.working_days }}</span></td>
                                    <td class="text-center"><span class="badge bg-success bg-opacity-10 text-success border border-success">{{ item.present_days }}</span></td>
                                    <td class="text-center"><span class="fw-semibold text-success">{{ item.attendance_pct }}%</span></td>
                                    <td class="text-center"><span class="fw-semibold text-info">{{ item.approved_leave_days }}</span></td>
                                    <td class="text-center"><span class="{% if item.unpaid_leave_days > 0 %}text-danger fw-bold{% else %}text-muted{% endif %}">{{ item.unpaid_leave_days }}</span></td>
                                    <td class="text-center"><span class="fw-semibold text-primary">{{ item.performance_score }}%</span></td>
                                    <td class="text-danger fw-semibold">{{ item.leave_deduction | inr }}</td>
                                    <td class="fw-bold text-success fs-6">{{ item.final_salary | inr }}</td>
                                    <td>
                                        {% if item.payroll_status == 'Paid' %}
                                            <span class="badge bg-success"><i class="bi bi-check-all me-1"></i>Paid</span>
                                        {% elif item.payroll_status == 'Finalized' %}
                                            <span class="badge bg-primary"><i class="bi bi-lock-fill me-1"></i>Finalized</span>
                                        {% else %}
                                            <span class="badge bg-info text-dark">{{ item.payroll_status }}</span>
                                        {% endif %}
                                    </td>
                                    <td class="text-nowrap">
                                        <button type="button" class="btn btn-sm btn-outline-secondary me-1" data-bs-toggle="modal" data-bs-target="#breakdownModal{{ item.emp_id }}">
                                            <i class="bi bi-calculator me-1"></i>Breakdown
                                        </button>
                                        {% if current_user.role in ['admin', 'hr'] %}
                                            <a href="{{ url_for('download_payslip', emp_id=item.emp_id, month=selected_month_str) }}" target="_blank" class="btn btn-sm btn-outline-primary me-1" title="Generate & Download PDF Payslip">
                                                <i class="bi bi-file-earmark-pdf me-1"></i>Payslip
                                            </a>
                                            <form method="POST" action="{{ url_for('email_payslip', emp_id=item.emp_id) }}" class="d-inline">
                                                <input type="hidden" name="month" value="{{ selected_month_str }}">
                                                <button type="submit" class="btn btn-sm btn-outline-success me-1" title="Email PDF Payslip to Employee" onclick="return confirm('Send PDF payslip to {{ item.name }} via email?');">
                                                    <i class="bi bi-envelope me-1"></i>Email
                                                </button>
                                            </form>
                                            {% if item.payroll_status != 'Paid' %}
                                                <form method="POST" action="{{ url_for('settings_payroll') }}" class="d-inline">
                                                    <input type="hidden" name="action" value="mark_paid">
                                                    <input type="hidden" name="emp_id" value="{{ item.emp_id }}">
                                                    <input type="hidden" name="month_year" value="{{ item.month_year }}">
                                                    <button type="submit" class="btn btn-sm btn-success" title="Mark as Paid"><i class="bi bi-check2-all me-1"></i>Mark Paid</button>
                                                </form>
                                            {% endif %}
                                        {% endif %}

                                        <!-- Breakdown Modal -->
                                        <div class="modal fade" id="breakdownModal{{ item.emp_id }}" tabindex="-1" aria-hidden="true">
                                            <div class="modal-dialog modal-dialog-centered">
                                                <div class="modal-content">
                                                    <div class="modal-header">
                                                        <h5 class="modal-title fw-bold"><i class="bi bi-file-earmark-spreadsheet me-2 text-primary"></i>Salary Breakdown - {{ item.name }}</h5>
                                                        <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                                                    </div>
                                                    <div class="modal-body">
                                                        <div class="list-group list-group-flush">
                                                            <div class="list-group-item d-flex justify-content-between align-items-center">
                                                                <span>Base Monthly Salary</span>
                                                                <strong class="text-dark">{{ item.base_salary | inr }}</strong>
                                                            </div>
                                                            <div class="list-group-item d-flex justify-content-between align-items-center">
                                                                <span>Total Working Days</span>
                                                                <span>{{ item.working_days }} Days</span>
                                                            </div>
                                                            <div class="list-group-item d-flex justify-content-between align-items-center">
                                                                <span>Calculated Per Day Salary</span>
                                                                <span>{{ item.per_day_salary | inr }} / day</span>
                                                            </div>
                                                            <div class="list-group-item d-flex justify-content-between align-items-center">
                                                                <span>Unpaid Leave Days</span>
                                                                <span class="text-danger fw-bold">{{ item.unpaid_leave_days }} Days</span>
                                                            </div>
                                                            <div class="list-group-item d-flex justify-content-between align-items-center">
                                                                <span>Leave Deduction</span>
                                                                <strong class="text-danger">- {{ item.leave_deduction | inr }}</strong>
                                                            </div>
                                                            <div class="list-group-item d-flex justify-content-between align-items-center bg-light">
                                                                <span class="fw-bold fs-6">Final Calculated Salary</span>
                                                                <strong class="text-success fs-5">{{ item.final_salary | inr }}</strong>
                                                            </div>
                                                        </div>
                                                        <div class="mt-3 text-muted small">
                                                            <i class="bi bi-info-circle me-1"></i>Performance Score ({{ item.performance_score }}%) is informational and does not deduct salary.
                                                        </div>
                                                    </div>
                                                    <div class="modal-footer">
                                                        <button type="button" class="btn btn-secondary btn-sm" data-bs-dismiss="modal">Close</button>
                                                    </div>
                                                </div>
                                            </div>
                                        </div>
                                    </td>
                                </tr>
                            {% else %}
                                <tr>
                                    <td colspan="13" class="text-center py-4 text-muted">No employee salary records found.</td>
                                </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>

        <!-- FEATURE 1: PAYROLL HISTORY & TIMELINE -->
        <div class="card shadow-sm">
            <div class="card-header bg-white py-3 border-0 d-flex flex-wrap justify-content-between align-items-center gap-2">
                <h5 class="card-title mb-0 fw-bold"><i class="bi bi-clock-history me-2 text-primary"></i>Payroll History & Timeline</h5>
                <form method="GET" action="{{ url_for('settings_payroll') }}" class="d-flex align-items-center gap-2 flex-wrap">
                    {% if selected_emp_id %}<input type="hidden" name="employee_id" value="{{ selected_emp_id }}">{% endif %}
                    <select name="year" class="form-select form-select-sm" style="width: 110px;" onchange="this.form.submit()">
                        <option value="">All Years</option>
                        {% for y in available_payroll_years %}
                            <option value="{{ y }}" {% if selected_year_filter == y|string %}selected{% endif %}>{{ y }}</option>
                        {% endfor %}
                    </select>
                </form>
            </div>
            <div class="card-body">
                {% if payroll_history %}
                    <div class="timeline position-relative ps-3">
                        {% for record in payroll_history %}
                            <div class="timeline-item mb-4 pb-3 border-bottom position-relative">
                                <div class="d-flex flex-wrap justify-content-between align-items-center gap-2 mb-2">
                                    <div>
                                        <span class="badge {% if record.status == 'Paid' %}bg-success{% elif record.status == 'Finalized' %}bg-primary{% else %}bg-info text-dark{% endif %} me-2">
                                            {% if record.status == 'Paid' %}<i class="bi bi-check-all me-1"></i>Paid{% elif record.status == 'Finalized' %}<i class="bi bi-lock-fill me-1"></i>Finalized{% else %}{{ record.status }}{% endif %}
                                        </span>
                                        <strong class="fs-6 text-dark me-2">{{ record.month_name }}</strong>
                                        <span class="text-muted small">({{ record.emp_name }} - {{ record.emp_dept or 'N/A' }})</span>
                                    </div>
                                    <div class="d-flex align-items-center gap-3">
                                        <span class="fw-bold text-success fs-6">{{ record.final_salary | inr }}</span>
                                        <button type="button" class="btn btn-sm btn-outline-primary" data-bs-toggle="modal" data-bs-target="#historyDetailModal{{ record.id }}">
                                            <i class="bi bi-eye me-1"></i>View Details
                                        </button>
                                    </div>
                                </div>
                                <div class="text-muted small">
                                    Generated: {{ record.created_at }} • Working Days: {{ record.working_days }} • Attendance: {{ record.attendance_pct }}%
                                </div>

                                <!-- History Detail Modal displaying all 15 required details -->
                                <div class="modal fade text-start" id="historyDetailModal{{ record.id }}" tabindex="-1" aria-hidden="true">
                                    <div class="modal-dialog modal-dialog-centered modal-lg">
                                        <div class="modal-content">
                                            <div class="modal-header">
                                                <h5 class="modal-title fw-bold"><i class="bi bi-receipt me-2 text-primary"></i>Historical Payroll Record - {{ record.month_name }}</h5>
                                                <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                                            </div>
                                            <div class="modal-body">
                                                <div class="row g-3 mb-3">
                                                    <div class="col-md-6">
                                                        <div class="p-3 bg-light rounded border">
                                                            <div class="text-muted small fw-semibold">Employee Name</div>
                                                            <div class="fw-bold text-dark fs-6">{{ record.emp_name }}</div>
                                                            <div class="text-muted small">Department: {{ record.emp_dept or 'N/A' }}</div>
                                                        </div>
                                                    </div>
                                                    <div class="col-md-6">
                                                        <div class="p-3 bg-light rounded border">
                                                            <div class="text-muted small fw-semibold">Payroll Status & Date</div>
                                                            <div>
                                                                <span class="badge {% if record.status == 'Paid' %}bg-success{% else %}bg-primary{% endif %} me-2">{{ record.status }}</span>
                                                                <span class="fw-bold text-dark">{{ record.month_name }}</span>
                                                            </div>
                                                            <div class="text-muted small mt-1">Generated Date: {{ record.created_at }}</div>
                                                        </div>
                                                    </div>
                                                </div>

                                                <div class="table-responsive">
                                                    <table class="table table-bordered align-middle">
                                                        <thead class="table-light">
                                                            <tr>
                                                                <th>Metric / Field</th>
                                                                <th>Historical Recorded Value</th>
                                                            </tr>
                                                        </thead>
                                                        <tbody>
                                                            <tr><td>Base Salary</td><td class="fw-bold">{{ record.base_salary | inr }}</td></tr>
                                                            <tr><td>Working Days</td><td>{{ record.working_days }} Days</td></tr>
                                                            <tr><td>Present Days</td><td class="text-success fw-semibold">{{ record.present_days }} Days</td></tr>
                                                            <tr><td>Attendance %</td><td class="text-success fw-bold">{{ record.attendance_pct }}%</td></tr>
                                                            <tr><td>Approved Leave Days</td><td class="text-info fw-semibold">{{ record.approved_leave_days }} Days</td></tr>
                                                            <tr><td>Unpaid Leave Days</td><td class="{% if record.unpaid_leave_days > 0 %}text-danger fw-bold{% else %}text-muted{% endif %}">{{ record.unpaid_leave_days }} Days</td></tr>
                                                            <tr><td>Performance Score %</td><td class="text-primary fw-semibold">{{ record.performance_score }}%</td></tr>
                                                            <tr><td>Leave Deduction</td><td class="text-danger fw-bold">- {{ record.leave_deduction | inr }}</td></tr>
                                                            <tr><td>Adjustments</td><td>{{ record.adjustments | inr }}</td></tr>
                                                            <tr class="table-success">
                                                                <td class="fw-bold">Final Salary Paid</td>
                                                                <td class="fw-bold text-success fs-5">{{ record.final_salary | inr }}</td>
                                                            </tr>
                                                        </tbody>
                                                    </table>
                                                </div>
                                            </div>
                                            <div class="modal-footer">
                                                <button type="button" class="btn btn-secondary btn-sm" data-bs-dismiss="modal">Close</button>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        {% endfor %}
                    </div>
                {% else %}
                    <div class="text-center py-4 text-muted">
                        <i class="bi bi-clock-history display-6 d-block mb-2 text-secondary"></i>
                        No historical payroll records found for the selected filters. Mark a month's payroll as Paid or Finalized to save it into history.
                    </div>
                {% endif %}
            </div>
        </div>
        {% endblock %}
        """,
        currency=currency,
        payroll_list=payroll_list,
        payroll_history=payroll_history,
        employees_list=employees_list,
        selected_month_str=selected_month_str,
        selected_emp_id=selected_emp_id,
        selected_year_filter=selected_year_filter,
        available_payroll_years=available_payroll_years,
    )


@app.route("/admin/payroll/<int:emp_id>/payslip")
@login_required
def download_payslip(emp_id):
    if current_user.role not in ("admin", "hr"):
        flash("Access denied. Admin or HR privileges required to generate payslips.", "danger")
        return redirect(url_for("dashboard"))

    month_arg = request.args.get("month", "").strip()
    now = datetime.datetime.now(tz=IST)
    if month_arg and "-" in month_arg:
        try:
            y, m = [int(x) for x in month_arg.split("-", 1)]
        except ValueError:
            y, m = now.year, now.month
    else:
        y, m = now.year, now.month

    month_year_str = f"{y:04d}-{m:02d}"

    with get_db() as conn:
        emp = conn.execute("SELECT * FROM employees WHERE id = ?", (emp_id,)).fetchone()
        if not emp:
            flash("Employee record not found.", "danger")
            return redirect(url_for("settings_payroll"))

        payroll_data = calculate_employee_payroll(conn, emp_id, y, m)
        if not payroll_data:
            flash("Unable to calculate payroll data for employee.", "danger")
            return redirect(url_for("settings_payroll"))

    try:
        pdf_bytes = generate_payslip_pdf(payroll_data)
        filename = f"Payslip_{emp_id}_{month_year_str}.pdf"
        return send_file(
            io.BytesIO(pdf_bytes),
            mimetype="application/pdf",
            as_attachment=True,
            download_name=filename
        )
    except Exception as e:  # noqa: BLE001
        print(f"ERROR generating PDF payslip: {e}")
        traceback.print_exc()
        flash(f"Failed to generate payslip PDF: {str(e)}", "danger")
        return redirect(url_for("settings_payroll"))


@app.route("/admin/payroll/<int:emp_id>/email-payslip", methods=["POST"])
@login_required
def email_payslip(emp_id):
    if current_user.role not in ("admin", "hr"):
        flash("Access denied. Admin or HR privileges required to email payslips.", "danger")
        return redirect(url_for("dashboard"))

    month_arg = request.form.get("month", "").strip() or request.args.get("month", "").strip()
    now = datetime.datetime.now(tz=IST)
    if month_arg and "-" in month_arg:
        try:
            y, m = [int(x) for x in month_arg.split("-", 1)]
        except ValueError:
            y, m = now.year, now.month
    else:
        y, m = now.year, now.month

    month_year_str = f"{y:04d}-{m:02d}"

    with get_db() as conn:
        emp = conn.execute("SELECT * FROM employees WHERE id = ?", (emp_id,)).fetchone()
        if not emp:
            flash("Employee record not found.", "danger")
            return redirect(url_for("settings_payroll"))

        user_id = emp["user_id"]
        to_email = None
        if user_id:
            u = conn.execute("SELECT email FROM users WHERE id = ?", (user_id,)).fetchone()
            if u and u["email"]:
                to_email = u["email"].strip()

        if not to_email:
            flash(f"Employee email address is not available for {emp['name']}.", "warning")
            return redirect(url_for("settings_payroll", month=month_year_str))

        payroll_data = calculate_employee_payroll(conn, emp_id, y, m)
        if not payroll_data:
            flash("Unable to calculate payroll data for employee.", "danger")
            return redirect(url_for("settings_payroll", month=month_year_str))

    try:
        pdf_bytes = generate_payslip_pdf(payroll_data)
        filename = f"Payslip_{emp_id}_{month_year_str}.pdf"

        subject = f"Payslip - {payroll_data['payroll_month']}"
        html_content = f"""
        <div style="font-family: Arial, sans-serif; padding: 20px; color: #333;">
            <h2 style="color: #4f46e5;">BIZZNEX HRMS Payslip</h2>
            <p>Dear <strong>{payroll_data['name']}</strong>,</p>
            <p>Please find attached your official salary payslip for <strong>{payroll_data['payroll_month']}</strong>.</p>
            <table style="width: 100%; max-width: 500px; border-collapse: collapse; margin: 20px 0;">
                <tr style="background-color: #f8fafc;"><td style="padding: 8px; border: 1px solid #cbd5e1;">Employee Name</td><td style="padding: 8px; border: 1px solid #cbd5e1;"><strong>{payroll_data['name']}</strong></td></tr>
                <tr><td style="padding: 8px; border: 1px solid #cbd5e1;">Pay Period</td><td style="padding: 8px; border: 1px solid #cbd5e1;">{payroll_data['payroll_month']}</td></tr>
                <tr style="background-color: #f8fafc;"><td style="padding: 8px; border: 1px solid #cbd5e1;">Net Payable</td><td style="padding: 8px; border: 1px solid #cbd5e1; color: #15803d;"><strong>INR {payroll_data['final_salary']:,.2f}</strong></td></tr>
            </table>
            <p>If you have any questions regarding your salary computation, please contact HR/Payroll department.</p>
            <br>
            <p>Best regards,<br><strong>Bizznex HR Operations</strong></p>
        </div>
        """

        success, msg = send_email_with_attachment(to_email, subject, html_content, pdf_bytes, filename)
        if success:
            flash(f"Payslip for {payroll_data['name']} ({payroll_data['payroll_month']}) successfully emailed to {to_email}.", "success")
        else:
            flash(f"Could not send email to {to_email}: {msg}. You can still download the PDF payslip directly.", "warning")
    except Exception as e:  # noqa: BLE001
        print(f"ERROR emailing payslip: {e}")
        traceback.print_exc()
        flash(f"An error occurred while preparing payslip email: {str(e)}. You can still download the PDF directly.", "warning")

    return redirect(url_for("settings_payroll", month=month_year_str))


@app.route("/settings/notifications", methods=["GET", "POST"])
@login_required
def settings_notifications():
    if request.method == "POST":
        email_notif = 1 if request.form.get("email_notifications") == "on" else 0
        in_app_notif = 1 if request.form.get("in_app_notifications") == "on" else 0
        with get_db() as conn:
            conn.execute(
                """
                INSERT INTO user_preferences (user_id, email_notifications, in_app_notifications)
                VALUES (?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET email_notifications = excluded.email_notifications, in_app_notifications = excluded.in_app_notifications
            """,
                (current_user.id, email_notif, in_app_notif),
            )
            conn.commit()
        flash("Notification preferences updated.", "success")
        return redirect(url_for("settings_notifications"))

    with get_db() as conn:
        pref = conn.execute(
            "SELECT email_notifications, in_app_notifications FROM user_preferences WHERE user_id = ?",
            (current_user.id,),
        ).fetchone()

    email_notif = pref["email_notifications"] if pref else 1
    in_app_notif = pref["in_app_notifications"] if pref else 1

    return render_template_string(
        """
        {% extends "base.html" %}
        {% block title %}Notification Settings - Settings{% endblock %}
        {% block page_content %}
        <div class="page-header d-flex justify-content-between align-items-center mb-4">
            <div>
                <h1><i class="bi bi-bell-gear me-2 text-primary"></i>Notification Settings</h1>
                <p>Configure notification delivery channels and automated system alerts.</p>
            </div>
        </div>

        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="alert alert-{{ category }} alert-dismissible fade show" role="alert">
                        {{ message }}
                        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                    </div>
                {% endfor %}
            {% endif %}
        {% endwith %}

        <div class="card shadow-sm">
            <div class="card-header bg-white py-3 border-0">
                <h5 class="card-title mb-0 fw-bold"><i class="bi bi-sliders me-2 text-primary"></i>Alert Delivery Channels</h5>
            </div>
            <div class="card-body">
                <form method="POST" action="{{ url_for('settings_notifications') }}">
                    <div class="form-check form-switch mb-3 p-3 bg-light rounded border d-flex justify-content-between align-items-center">
                        <label class="form-check-label fw-semibold cursor-pointer" for="inAppSwitch">
                            <i class="bi bi-bell-fill me-2 text-primary"></i>In-App Topbar Notifications
                            <span class="d-block text-muted small fw-normal">Receive real-time bell dropdown alerts for task, leave, and security events.</span>
                        </label>
                        <input class="form-check-input ms-3" type="checkbox" role="switch" id="inAppSwitch" name="in_app_notifications" {% if in_app_notif %}checked{% endif %}>
                    </div>

                    <div class="form-check form-switch mb-4 p-3 bg-light rounded border d-flex justify-content-between align-items-center">
                        <label class="form-check-label fw-semibold cursor-pointer" for="emailSwitch">
                            <i class="bi bi-envelope-check-fill me-2 text-success"></i>Email Digest & Alerts
                            <span class="d-block text-muted small fw-normal">Receive automated email alerts for assigned tasks and leave status updates.</span>
                        </label>
                        <input class="form-check-input ms-3" type="checkbox" role="switch" id="emailSwitch" name="email_notifications" {% if email_notif %}checked{% endif %}>
                    </div>

                    <button type="submit" class="btn btn-primary"><i class="bi bi-check-circle me-1"></i>Save Notification Preferences</button>
                </form>
            </div>
        </div>
        {% endblock %}
        """,
        email_notif=email_notif,
        in_app_notif=in_app_notif,
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")))
    app.run(debug=True)
