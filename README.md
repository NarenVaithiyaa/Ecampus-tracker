# College Result Notifier

Python utility that logs into the college e-campus portal, captures attendance and result data, watches for updates, and emails notifications.

## Features
- Authenticates against the ASP.NET WebForms campus portal
- Parses attendance and result pages to build structured snapshots
- Stores previous state locally to detect changes between runs
- Emails either ad-hoc snapshots or change alerts via SMTP
- Supports scheduled checks using APScheduler

## Prerequisites
- Python 3.11+
- Gmail account with an app password (or any SMTP provider credentials)

## Installation
```bash
python -m venv .venv
.\.venv\Scripts\activate
pip install -r college_result_notifier/requirements.txt
```

## Configuration
Create a `.env` file with the credentials and email settings:
```dotenv
PORTAL_USERNAME=your-student-id
PORTAL_PASSWORD=your-password
SMTP_USERNAME=your-smtp-user
SMTP_PASSWORD=your-app-password
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
TO_EMAIL=recipient@example.com
FROM_EMAIL=sender@example.com
```

## Usage
Run an immediate snapshot email:
```bash
python -m college_result_notifier.main --send-snapshot
```

Run the standard change-detection loop (sends combined "Attendance/results updated" emails when changes are detected):
```bash
python -m college_result_notifier.main
```

Launch the scheduler to poll periodically (default interval defined in `scheduler.py`):
```bash
python -m college_result_notifier.scheduler
```

## Troubleshooting
- Ensure the `.env` file is filled with valid portal and SMTP credentials
- Delete `college_result_notifier/state.json` and `college_result_notifier/attendance_state.json` if you need to reset stored baselines
- Run with `--send-snapshot` to validate connectivity and email delivery before enabling scheduled checks
