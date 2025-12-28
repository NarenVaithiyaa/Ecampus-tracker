from __future__ import annotations

import logging

import requests

from config import AppConfig


class ResultFetchError(Exception):
    """Raised when the result page cannot be retrieved."""


def fetch_results_page(session: requests.Session, config: AppConfig) -> str:
    result_url = f"{config.base_url}/{config.result_path}"
    logging.info("Fetching result page: %s", result_url)
    try:
        response = session.get(result_url, timeout=config.request_timeout)
        response.raise_for_status()
    except requests.RequestException as exc:
        raise ResultFetchError(f"Failed to fetch results page: {exc}") from exc

    if "DgResult" not in response.text:
        logging.warning("Result table not found in response. Login may have expired.")
    return response.text


class AttendanceFetchError(Exception):
    """Raised when the attendance page cannot be retrieved."""


def fetch_attendance_page(session: requests.Session, config: AppConfig) -> str:
    attendance_url = f"{config.base_url}/{config.attendance_path}"
    logging.info("Fetching attendance page: %s", attendance_url)
    try:
        response = session.get(attendance_url, timeout=config.request_timeout)
        response.raise_for_status()
    except requests.RequestException as exc:
        raise AttendanceFetchError(f"Failed to fetch attendance page: {exc}") from exc

    table_id = config.attendance_table_id
    if table_id and table_id not in response.text:
        logging.warning(
            "Attendance table %s not found in response. Login may have expired.",
            table_id,
        )
    return response.text
