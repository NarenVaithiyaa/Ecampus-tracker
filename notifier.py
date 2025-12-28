from __future__ import annotations

import logging
import smtplib
from datetime import datetime
from email.message import EmailMessage
from typing import Dict, Iterable, List, Optional

from config import AppConfig


class NotificationError(Exception):
    """Raised when email notification fails."""


def _format_change(change: Dict[str, object], record_label: str = "result") -> str:
    change_type = change.get("type", "unknown")
    key = change.get("key", "")
    if change_type == "new":
        record = change.get("new", {})
        lines = [f"New {record_label}: {key}"]
        for field, value in record.items():
            lines.append(f"  {field}: {value}")
        return "\n".join(lines)
    if change_type == "updated":
        field_changes: Dict[str, Dict[str, str]] = change.get("changes", {})  # type: ignore[arg-type]
        lines = [f"Updated {record_label}: {key}"]
        for field, values in field_changes.items():
            old_val = values.get("old", "")
            new_val = values.get("new", "")
            lines.append(f"  {field}: {old_val} -> {new_val}")
        return "\n".join(lines)
    return f"Change detected for {key}: {change}"


def _send_email(config: AppConfig, subject: str, body: str) -> None:
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = config.email.sender
    message["To"] = config.email.recipient
    message.set_content(body)

    logging.info("Sending email to %s with subject '%s'", config.email.recipient, subject)
    try:
        with smtplib.SMTP_SSL(config.smtp_host, 465, timeout=30) as smtp:
            smtp.login(config.email.smtp_user, config.email.smtp_password)
            smtp.send_message(message)
    except (smtplib.SMTPException, OSError) as exc:
        raise NotificationError(f"Failed to send notification: {exc}") from exc


def send_result_notification(config: AppConfig, changes: List[Dict[str, object]]) -> None:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    body_lines = [
        "Changes detected in your PSG Tech results.",
        f"Timestamp: {timestamp}",
        "",
    ]
    for change in changes:
        body_lines.append(_format_change(change, "result"))
        body_lines.append("")

    body = "\n".join(body_lines).strip() + "\n"

    _send_email(config, "PSG Tech Result Update", body)


def send_login_success_email(config: AppConfig) -> None:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    body = (
        "Login to the PSG Tech result portal succeeded.\n"
        f"Timestamp: {timestamp}\n"
    )
    _send_email(config, "PSG Tech Portal Login Successful", body)


def send_attendance_notification(config: AppConfig, changes: List[Dict[str, object]]) -> None:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    body_lines = [
        "Changes detected in your PSG Tech attendance.",
        f"Timestamp: {timestamp}",
        "",
    ]
    for change in changes:
        body_lines.append(_format_change(change, "attendance entry"))
        body_lines.append("")

    body = "\n".join(body_lines).strip() + "\n"

    _send_email(config, "PSG Tech Attendance Update", body)


def _format_snapshot_records(records: Iterable[Dict[str, object]], *, include_key: bool = False) -> str:
    lines: List[str] = []
    for index, record in enumerate(records, start=1):
        key = str(record.get("_key", index))
        label = f"{index}." if not include_key else f"{index}. ({key})"
        lines.append(label)
        for field, value in record.items():
            if field == "_key":
                continue
            value_str = str(value)
            lines.append(f"   {field}: {value_str}")
        lines.append("")
    return "\n".join(lines).strip()


def send_snapshot_email(
    config: AppConfig,
    *,
    results: Optional[List[Dict[str, object]]] = None,
    attendance: Optional[List[Dict[str, object]]] = None,
    results_error: Optional[str] = None,
    attendance_error: Optional[str] = None,
) -> None:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    body_lines = [
        "Current PSG Tech portal snapshot.",
        f"Timestamp: {timestamp}",
        "",
    ]

    body_lines.append("Results:")
    if results_error is not None:
        body_lines.append(f"  Failed to fetch results: {results_error}")
    elif results:
        body_lines.append(_format_snapshot_records(results))
    else:
        body_lines.append("  No result records were parsed.")
    body_lines.append("")

    body_lines.append("Attendance:")
    if attendance_error is not None:
        body_lines.append(f"  Failed to fetch attendance: {attendance_error}")
    elif attendance:
        body_lines.append(_format_snapshot_records(attendance, include_key=True))
    else:
        body_lines.append("  No attendance records were parsed.")

    body = "\n".join(body_lines).strip() + "\n"

    _send_email(config, "PSG Tech Portal Snapshot", body)


def send_portal_update_notification(
    config: AppConfig,
    *,
    attendance_changes: List[Dict[str, object]],
    result_changes: List[Dict[str, object]],
) -> None:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    body_lines = [
        "Attendance/results updated.",
        f"Timestamp: {timestamp}",
        "",
    ]

    if result_changes:
        body_lines.append("Result changes:")
        for change in result_changes:
            body_lines.append(_format_change(change, "result"))
            body_lines.append("")
    else:
        body_lines.append("Result changes: none detected during this run.")
        body_lines.append("")

    if attendance_changes:
        body_lines.append("Attendance changes:")
        for change in attendance_changes:
            body_lines.append(_format_change(change, "attendance entry"))
            body_lines.append("")
    else:
        body_lines.append("Attendance changes: none detected during this run.")

    body = "\n".join(body_lines).strip() + "\n"

    _send_email(config, "Attendance/results updated", body)
