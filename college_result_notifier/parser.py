from __future__ import annotations

import re
from typing import Dict, List

from bs4 import BeautifulSoup


class ParseError(Exception):
    """Raised when result parsing fails."""


def _clean_text(value: str) -> str:
    return value.strip().replace("\xa0", " ")


def _normalize_header(value: str) -> str:
    normalized = re.sub(r"[^A-Za-z0-9]+", " ", value).strip().lower()
    if not normalized:
        return "column"
    parts = [part for part in normalized.split() if part]
    return "_".join(parts) if parts else "column"


def parse_results(html: str) -> List[Dict[str, str]]:
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table", {"id": "DgResult"})
    if table is None:
        raise ParseError("Result table DgResult not found.")

    rows = table.find_all("tr")
    if not rows:
        raise ParseError("Result table is empty.")

    header_cells = [
        _clean_text(cell.get_text())
        for cell in rows[0].find_all(["th", "td"])
    ]

    expected_columns = {
        "semester",
        "course code",
        "course title",
        "credits",
        "grade",
        "grade / remark",
        "grade/remark",
        "result",
    }
    normalized_headers = [col.lower() for col in header_cells]
    if not any(col in expected_columns for col in normalized_headers):
        raise ParseError("Unexpected table headers in result table.")

    results: List[Dict[str, str]] = []
    for row in rows[1:]:
        cells = row.find_all("td")
        if not cells:
            continue
        values = [_clean_text(cell.get_text()) for cell in cells]
        record = {}
        for header, value in zip(normalized_headers, values):
            match header:
                case "semester":
                    record["semester"] = value
                case "course code":
                    record["course_code"] = value
                case "course title":
                    record["course_title"] = value
                case "credits":
                    record["credits"] = value
                case "grade" | "grade / remark" | "grade/remark":
                    record["grade"] = value
                case "result":
                    record["result"] = value
        if record:
            results.append(record)

    if not results:
        raise ParseError("No result rows parsed from table.")

    return results


def parse_attendance(html: str, table_id: str) -> List[Dict[str, str]]:
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table", {"id": table_id})
    if table is None:
        raise ParseError(f"Attendance table {table_id} not found.")

    rows = table.find_all("tr")
    if len(rows) < 2:
        raise ParseError("Attendance table is empty.")

    header_cells = rows[0].find_all(["th", "td"])
    headers: List[str] = []
    normalized_headers: List[str] = []
    for index, cell in enumerate(header_cells):
        header_text = _clean_text(cell.get_text()) or f"Column {index + 1}"
        headers.append(header_text)
        normalized_value = _normalize_header(header_text)
        if normalized_value == "column":
            normalized_value = f"column_{index + 1}"
        normalized_headers.append(normalized_value)

    records: List[Dict[str, str]] = []
    for idx, row in enumerate(rows[1:], start=1):
        cells = row.find_all("td")
        if not cells:
            continue
        record: Dict[str, str] = {}
        for header_name, norm_name, cell in zip(headers, normalized_headers, cells):
            record[norm_name] = _clean_text(cell.get_text())
        key_field = normalized_headers[0] if normalized_headers else "row"
        key_value = record.get(key_field, f"row_{idx}")
        record.setdefault("_key", key_value or f"row_{idx}")
        records.append(record)

    if not records:
        raise ParseError("No attendance rows parsed from table.")

    return records
