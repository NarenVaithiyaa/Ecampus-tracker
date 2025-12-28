from __future__ import annotations

import logging
from typing import Dict, Optional

import requests
from bs4 import BeautifulSoup

from config import AppConfig


class LoginError(Exception):
    """Raised when authentication fails."""


def _extract_hidden_fields(html: str) -> Dict[str, str]:
    soup = BeautifulSoup(html, "html.parser")
    hidden_fields = {}
    for field_name in ["__VIEWSTATE", "__EVENTVALIDATION", "__VIEWSTATEGENERATOR"]:
        element = soup.find("input", {"name": field_name})
        if element and element.has_attr("value"):
            hidden_fields[field_name] = element["value"]
        else:
            raise LoginError(f"Unable to locate hidden field: {field_name}")
    return hidden_fields


def _build_login_url(config: AppConfig, override_path: Optional[str] = None) -> str:
    path = override_path if override_path is not None else config.login_path
    path = path.strip().lstrip("/")
    if not path:
        return config.base_url
    return f"{config.base_url}/{path}"


def authenticate(session: requests.Session, config: AppConfig) -> None:
    base_login_url = _build_login_url(config, "")
    explicit_login_url = _build_login_url(config)

    urls = [base_login_url]
    if explicit_login_url not in urls:
        urls.append(explicit_login_url)

    logging.info("Login URL candidates: %s", urls)

    response: Optional[requests.Response] = None
    login_url: Optional[str] = None
    for attempt, url in enumerate(urls, start=1):
        logging.info("Attempting login GET (%s): %s", attempt, url)
        try:
            response = session.get(url, timeout=config.request_timeout)
            response.raise_for_status()
            login_url = response.url
            break
        except requests.HTTPError as exc:
            status_code = exc.response.status_code if exc.response else None
            if status_code == 404 and attempt < len(urls):
                logging.warning("Login URL returned 404, trying alternative URL")
                continue
            raise LoginError(f"Login page request failed: {exc}") from exc
        except requests.RequestException as exc:
            raise LoginError(f"Login page request failed: {exc}") from exc

    if response is None or login_url is None:
        raise LoginError("Login page could not be retrieved.")

    hidden_fields = _extract_hidden_fields(response.text)

    payload = {
        "__EVENTTARGET": "abcd3",
        "__EVENTARGUMENT": "",
        "__LASTFOCUS": "",
        "__VIEWSTATE": hidden_fields.get("__VIEWSTATE", ""),
        "__VIEWSTATEGENERATOR": hidden_fields.get("__VIEWSTATEGENERATOR", ""),
        "__EVENTVALIDATION": hidden_fields.get("__EVENTVALIDATION", ""),
        "rdolst": "S",
        "txtusercheck": config.credentials.roll_number,
        "txtpwdcheck": config.credentials.password,
        "abcd3": "Login",
    }

    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Referer": response.url,
        "User-Agent": "Mozilla/5.0 (compatible; ResultMonitor/1.0)",
    }

    try:
        post_response = session.post(
            login_url,
            data=payload,
            headers=headers,
            timeout=config.request_timeout,
            allow_redirects=True,
        )
        post_response.raise_for_status()
        logging.info("Login POST completed at %s", post_response.url)
    except requests.RequestException as exc:
        raise LoginError(f"Login request failed: {exc}") from exc

    if "Invalid" in post_response.text or "alert" in post_response.text.lower():
        raise LoginError("Portal rejected the provided credentials.")
