# AI_CONTEXT.md

# HRMS Project Context

## Project Overview

This is a production-style Human Resource Management System (HRMS) being developed as part of an internship.

The goal is to build a clean, modular, scalable application that could realistically be used by a small or medium-sized company.

This is NOT a demo project.

---

# Tech Stack

Backend
- Python
- Flask
- SQLAlchemy
- SQLite

Frontend
- Bootstrap 5
- HTML
- CSS
- JavaScript (only where necessary)

Authentication
- Flask-Login
- Werkzeug Password Hashing

---

# Current Modules

## Authentication

- Secure Login
- Role-based Access
- Password Hashing
- Forced Password Reset
- Session Management

---

## Employee Management

Stores

- Personal Information
- Department
- Salary
- Education
- Experience
- Emergency Contact
- Documents

---

## Attendance

Employees can

- Punch In
- Punch Out

Stores

- Date
- Time In
- Time Out
- Working Hours

---

## Project Management

Projects contain

- Client
- Assigned Employee
- Services
- Contact Details
- Delivery Information

---

## Task Management

Tasks belong to Projects.

Each task stores

- Employee
- Priority
- Status
- Deadline
- Description
- Assigned Date
- Recurring Type

Employees can

- Update Status
- Log Hours
- Add Work Notes

---

## Work Logs

Stores

- Hours Worked
- Date
- Notes

Running totals are calculated automatically.

---

# Planned Modules

Current Priority

1. Client Management
2. Performance Management

Future

- Leave Management
- Payroll
- Notifications
- Dashboard Improvements
- Branding
- Reports
- Analytics
- AI Features

---

# Database Philosophy

The database should remain normalized.

Avoid duplicate information.

Reuse existing relationships whenever possible.

Prefer extending existing tables instead of creating unnecessary ones.

---

# UI Philosophy

The UI should remain

- Clean
- Professional
- Modern
- Responsive

Use Bootstrap components whenever possible.

Do not redesign existing pages unless requested.

Maintain a consistent look across the application.

---

# Coding Rules

Always

- Reuse existing code
- Keep functions modular
- Keep routes organized
- Use meaningful variable names
- Avoid duplicate code
- Keep comments useful but concise

Never

- Break authentication
- Rename existing routes unnecessarily
- Remove existing functionality
- Rewrite working code without a reason

---

# AI Workflow

Before writing code

1. Read the existing implementation.
2. Understand the architecture.
3. Explain your implementation plan.
4. List every file that will be modified.

Only then begin coding.

---

# While Coding

Modify only files related to the requested feature.

Avoid unrelated refactoring.

Keep changes as small as possible.

---

# After Coding

Always provide

- Summary of changes
- Files modified
- Database changes
- Potential improvements
- Possible bugs
- Suggested next steps

---

# Code Quality

Prioritize

- Readability
- Maintainability
- Security
- Scalability

Write code as if another developer will maintain it.

---

# Communication Style

Be concise.

Do not produce unnecessary explanations.

When multiple approaches exist

- Compare them briefly
- Recommend one
- Explain why

If requirements are unclear

Ask questions before implementing.

---

# My Preferred Workflow

For every new feature

1. Analyze
2. Plan
3. Implement
4. Review
5. Improve

Never jump directly into large code changes.

---

# IMPORTANT

Treat this as a real software engineering project.

Act as a senior software engineer and code reviewer.

Optimize for long-term maintainability rather than the fastest possible implementation.