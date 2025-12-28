from dataclasses import dataclass
from pathlib import Path
import os
from typing import Optional

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parent
ENV_PATH = PROJECT_ROOT / ".env"


class ConfigError(Exception):
    """Raised when required configuration is missing."""


@dataclass
class PortalCredentials:
    roll_number: str
    password: str


@dataclass
class EmailSettings:
    sender: str
    recipient: str
    smtp_user: str
    smtp_password: str


@dataclass
class AppConfig:
    base_url: str
    login_path: str
    result_path: str
    attendance_path: str
    attendance_table_id: str
    credentials: PortalCredentials
    email: EmailSettings
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    request_timeout: tuple[float, float] = (5.0, 20.0)


def _get_env(name: str, default: Optional[str] = None) -> str:
    value = os.getenv(name, default)
    if value is None or not value.strip():
        raise ConfigError(f"Missing required environment variable: {name}")
    return value.strip()


def load_config() -> AppConfig:
    if ENV_PATH.exists():
        load_dotenv(ENV_PATH, override=False)
    else:
        parent_env = PROJECT_ROOT.parent / ".env"
        if parent_env.exists():
            load_dotenv(parent_env, override=False)

    base_url = os.getenv("PORTAL_BASE_URL", "https://ecampus.psgtech.ac.in/studzone2")
    login_path = os.getenv("PORTAL_LOGIN_PATH", "") or "Default.aspx"
    result_path = os.getenv("PORTAL_RESULT_PATH", "") or "FrmEpsStudResult.aspx"
    attendance_path = os.getenv("PORTAL_ATTENDANCE_PATH", "") or "FrmAttendanceView.aspx"
    attendance_table_id = os.getenv("ATTENDANCE_TABLE_ID", "") or "DgAttendance"
    attendance_table_id = attendance_table_id.strip() or "DgAttendance"

    credentials = PortalCredentials(
        roll_number=_get_env("PORTAL_ROLL_NUMBER"),
        password=_get_env("PORTAL_PASSWORD"),
    )

    email = EmailSettings(
        sender=_get_env("EMAIL_SENDER"),
        recipient=_get_env("EMAIL_RECIPIENT"),
        smtp_user=_get_env("EMAIL_SMTP_USER"),
        smtp_password=_get_env("EMAIL_SMTP_PASSWORD"),
    )

    timeout_connect = float(os.getenv("REQUEST_TIMEOUT_CONNECT", "5"))
    timeout_read = float(os.getenv("REQUEST_TIMEOUT_READ", "20"))

    return AppConfig(
        base_url=base_url.rstrip("/"),
        login_path=login_path.lstrip("/"),
        result_path=result_path.lstrip("/"),
        attendance_path=attendance_path.lstrip("/"),
        attendance_table_id=attendance_table_id,
        credentials=credentials,
        email=email,
        request_timeout=(timeout_connect, timeout_read),
    )
