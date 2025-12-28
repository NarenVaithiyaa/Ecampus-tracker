from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import requests

from config import AppConfig, ConfigError, load_config
from login import LoginError, authenticate
from notifier import (
    NotificationError,
    send_login_success_email,
    send_portal_update_notification,
    send_snapshot_email,
)
from parser import ParseError, parse_attendance, parse_results
from scheduler import run_scheduler
from scraper import (
    AttendanceFetchError,
    ResultFetchError,
    fetch_attendance_page,
    fetch_results_page,
)


RESULT_STATE_FILE = Path(__file__).resolve().parent / "state.json"
ATTENDANCE_STATE_FILE = Path(__file__).resolve().parent / "attendance_state.json"
RESULT_CHECK_FIELDS = ("grade", "result")


def _load_state(path: Path) -> List[Dict[str, object]]:
    if not path.exists():
        return []
    try:
        with path.open("r", encoding="utf-8") as file:
            return json.load(file)
    except json.JSONDecodeError:
        logging.warning("State file %s corrupted. Reinitializing baseline state.", path.name)
        return []


def _save_state(path: Path, data: List[Dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        json.dump(data, file, indent=2)


def _index_results(results: List[Dict[str, object]]) -> Dict[str, Dict[str, object]]:
    indexed = {}
    for record in results:
        semester = str(record.get("semester", ""))
        course_code = str(record.get("course_code", ""))
        key = f"{semester} | {course_code}".strip()
        indexed[key] = record
    return indexed


def detect_result_changes(
    previous: List[Dict[str, object]], current: List[Dict[str, object]]
) -> List[Dict[str, object]]:
    old_map = _index_results(previous)
    new_map = _index_results(current)

    changes: List[Dict[str, object]] = []

    for key, new_record in new_map.items():
        if key not in old_map:
            changes.append({"type": "new", "key": key, "new": new_record})
            continue
        old_record = old_map[key]
        field_changes: Dict[str, Dict[str, object]] = {}
        for field in RESULT_CHECK_FIELDS:
            old_value = str(old_record.get(field, ""))
            new_value = str(new_record.get(field, ""))
            if old_value != new_value:
                field_changes[field] = {"old": old_value, "new": new_value}
        if field_changes:
            changes.append({
                "type": "updated",
                "key": key,
                "changes": field_changes,
            })

    return changes


def _record_key(record: Dict[str, object], index: int) -> str:
    key = str(record.get("_key", "")).strip()
    if key:
        return key
    return f"row_{index}"


def _sanitize_record(record: Dict[str, object]) -> Dict[str, str]:
    return {
        key: str(value)
        for key, value in record.items()
        if key != "_key"
    }


def detect_attendance_changes(
    previous: List[Dict[str, object]], current: List[Dict[str, object]]
) -> List[Dict[str, object]]:
    old_map = {
        _record_key(record, idx): record
        for idx, record in enumerate(previous)
    }
    new_map = {
        _record_key(record, idx): record
        for idx, record in enumerate(current)
    }

    changes: List[Dict[str, object]] = []

    for key, new_record in new_map.items():
        sanitized_new = _sanitize_record(new_record)
        if key not in old_map:
            changes.append({"type": "new", "key": key, "new": sanitized_new})
            continue
        old_record = old_map[key]
        sanitized_old = _sanitize_record(old_record)
        field_changes: Dict[str, Dict[str, str]] = {}
        all_fields = set(sanitized_new) | set(sanitized_old)
        for field in all_fields:
            old_value = sanitized_old.get(field, "")
            new_value = sanitized_new.get(field, "")
            if old_value != new_value:
                field_changes[field] = {"old": old_value, "new": new_value}
        if field_changes:
            changes.append({
                "type": "updated",
                "key": key,
                "changes": field_changes,
            })

    return changes


def _create_session() -> requests.Session:
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (compatible; ResultMonitor/1.0)",
    })
    return session


def check_attendance(
    session: requests.Session,
    config: AppConfig,
) -> Tuple[List[Dict[str, object]], Optional[List[Dict[str, object]]]]:
    print("attendance checking")
    try:
        html = fetch_attendance_page(session, config)
        attendance_records = parse_attendance(html, config.attendance_table_id)
    except (AttendanceFetchError, ParseError) as exc:
        logging.error("Attendance check failed: %s", exc)
        return [], None

    previous_attendance = _load_state(ATTENDANCE_STATE_FILE)
    if not previous_attendance:
        logging.info("Attendance baseline not found. Saving current attendance without notification.")
        _save_state(ATTENDANCE_STATE_FILE, attendance_records)
        return [], attendance_records

    attendance_changes = detect_attendance_changes(previous_attendance, attendance_records)
    if not attendance_changes:
        logging.info("No attendance changes detected.")
        return [], attendance_records

    logging.info("Attendance changes detected: %s", len(attendance_changes))
    return attendance_changes, attendance_records


def check_results(
    session: requests.Session,
    config: AppConfig,
) -> Tuple[List[Dict[str, object]], Optional[List[Dict[str, object]]]]:
    print("result checking")
    try:
        html = fetch_results_page(session, config)
        results = parse_results(html)
    except (ResultFetchError, ParseError) as exc:
        logging.error("Result check failed: %s", exc)
        return [], None

    previous_results = _load_state(RESULT_STATE_FILE)
    if not previous_results:
        logging.info("Result baseline not found. Saving current results without notification.")
        _save_state(RESULT_STATE_FILE, results)
        return [], results

    changes = detect_result_changes(previous_results, results)
    if not changes:
        logging.info("No result changes detected.")
        return [], results

    logging.info("Result changes detected: %s", len(changes))
    return changes, results


def perform_check(config: AppConfig) -> None:
    logging.info("Starting portal check")
    session = _create_session()

    try:
        authenticate(session, config)
        logging.info("Authentication succeeded")
        try:
            send_login_success_email(config)
            logging.info("Login success email sent")
        except NotificationError as exc:
            logging.error("Login success email failed: %s", exc)
    except LoginError as exc:
        logging.error("Authentication failed: %s", exc)
        return

    attendance_changes, attendance_records = check_attendance(session, config)
    result_changes, result_records = check_results(session, config)

    if not attendance_changes and not result_changes:
        logging.info("No attendance or result changes detected during this run.")
        return

    try:
        send_portal_update_notification(
            config,
            attendance_changes=attendance_changes,
            result_changes=result_changes,
        )
        logging.info("Combined update notification sent successfully")
    except NotificationError as exc:
        logging.error("Combined update email failed: %s", exc)
        return

    if attendance_changes and attendance_records is not None:
        _save_state(ATTENDANCE_STATE_FILE, attendance_records)
        logging.info("Attendance state updated with latest data")
    if result_changes and result_records is not None:
        _save_state(RESULT_STATE_FILE, result_records)
        logging.info("Result state updated with latest data")


def send_snapshot(config: AppConfig) -> None:
    logging.info("Preparing portal snapshot email")
    session = _create_session()

    try:
        authenticate(session, config)
        logging.info("Authentication succeeded")
    except LoginError as exc:
        logging.error("Authentication failed: %s", exc)
        raise

    attendance_records: List[Dict[str, object]] | None = None
    results: List[Dict[str, object]] | None = None
    attendance_error: str | None = None
    results_error: str | None = None

    try:
        attendance_html = fetch_attendance_page(session, config)
        attendance_records = parse_attendance(attendance_html, config.attendance_table_id)
        logging.info("Attendance page fetched and parsed")
    except (AttendanceFetchError, ParseError) as exc:
        attendance_error = str(exc)
        logging.error("Attendance snapshot failed: %s", exc)

    try:
        result_html = fetch_results_page(session, config)
        results = parse_results(result_html)
        logging.info("Result page fetched and parsed")
    except (ResultFetchError, ParseError) as exc:
        results_error = str(exc)
        logging.error("Result snapshot failed: %s", exc)

    try:
        send_snapshot_email(
            config,
            results=results,
            attendance=attendance_records,
            results_error=results_error,
            attendance_error=attendance_error,
        )
        logging.info("Snapshot email sent successfully")
    except NotificationError as exc:
        logging.error("Snapshot email failed: %s", exc)
        raise


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="PSG Tech portal checker")
    parser.add_argument(
        "--send-snapshot",
        action="store_true",
        help="Fetch current results and attendance and email them immediately",
    )
    return parser.parse_args()


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
    )

    args = _parse_args()

    try:
        config = load_config()
    except ConfigError as exc:
        logging.error("Configuration error: %s", exc)
        return

    if args.send_snapshot:
        try:
            send_snapshot(config)
        except Exception as exc:  # noqa: BLE001
            logging.exception("Unhandled error during snapshot: %s", exc)
        return

    def job_wrapper() -> None:
        try:
            perform_check(config)
        except Exception as exc:  # noqa: BLE001
            logging.exception("Unhandled error during scheduled job: %s", exc)

    perform_check(config)
    run_scheduler(lambda: job_wrapper(), interval_minutes=15)


if __name__ == "__main__":
    main()
