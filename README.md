# College Result Notifier

A minimal Python service that logs into the PSG Tech eCampus portal, monitors both results and attendance, and emails you only when something new appears or existing data changes.

## Features
- ASP.NET WebForms login handled with hidden field extraction
- Immediate email confirmation after each successful login
- BeautifulSoup parsing of the `DgResult` table and configurable attendance table
- Local state snapshots stored in `state.json` and `attendance_state.json`
- Gmail SMTP email notifications with detailed diffs
- APScheduler background job every 15 minutes

## Prerequisites
- Python 3.11 or newer
- Gmail account with an app password (two-factor authentication recommended)
- Stable network connectivity to the PSG Tech portal

## Installation
1. Clone or copy the project to your machine.
2. Create and activate a virtual environment:
   ```bash
   python -m venv .venv
   .venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Configuration
1. Duplicate the sample below into a new `.env` file placed in the project root:
   ```ini
   PORTAL_ROLL_NUMBER=YOUR_ROLL_NUMBER
   PORTAL_PASSWORD=YOUR_PORTAL_PASSWORD

   EMAIL_SENDER=notify@example.com
   EMAIL_RECIPIENT=youraddress@example.com
   EMAIL_SMTP_USER=yourgmail@gmail.com
   EMAIL_SMTP_PASSWORD=YOUR_GMAIL_APP_PASSWORD
   ```
2. Optional overrides:
   ```ini
   PORTAL_BASE_URL=https://ecampus.psgtech.ac.in/studzone2
   PORTAL_LOGIN_PATH=Default.aspx
   PORTAL_RESULT_PATH=FrmEpsStudResult.aspx
   PORTAL_ATTENDANCE_PATH=FrmAttendanceView.aspx
   ATTENDANCE_TABLE_ID=DgAttendance
   REQUEST_TIMEOUT_CONNECT=5
   REQUEST_TIMEOUT_READ=20
   ```
3. Keep `.env` out of version control.

## Usage
- First run seeds the baseline without sending an email:
   ```bash
   python main.py
   ```
- Send a one-off email containing the current results and attendance data:
   ```bash
   python main.py --send-snapshot
   ```
- Run the scheduler loop (checks every 15 minutes by default):
   ```bash
   python scheduler.py
   ```
- Stop the service with Ctrl+C.

## Testing Checklist
1. **Login**
   - Run `python main.py` and confirm `Authentication succeeded` in the console.
   - Check your inbox for a "PSG Tech Portal Login Successful" confirmation.
   2. **Result Detection**
   - Temporarily edit `state.json` to simulate an older grade and rerun; watch for a detected change and an email.
   3. **Attendance Detection**
      - Adjust `attendance_state.json` (e.g., change a percentage) and rerun; expect an "Attendance Update" email.
   4. **Email Notification**
   - Confirm the Gmail SMTP app password is valid by forcing a change (as above) and checking your inbox.

## Troubleshooting
- `Portal rejected the provided credentials.` → Recheck roll number/password and make sure there is no CAPTCHA.
- `Result table DgResult not found.` → Portal layout may have changed; capture the HTML and inspect manually.
- `Email notification failed` → Verify SMTP credentials, app password, and that less secure app access is not blocking the login.
- Reset the baseline by deleting `state.json` if you want to reinitialize without historical data.
