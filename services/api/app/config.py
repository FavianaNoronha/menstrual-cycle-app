"""Settings from environment variables. Copy .env.example to .env for local runs."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    whatsapp_verify_token: str = ""
    whatsapp_app_secret: str = ""
    whatsapp_access_token: str = ""
    whatsapp_phone_number_id: str = ""
    graph_api_version: str = "v21.0"  # check Meta's docs for the current version
    sarvam_api_key: str = ""
    sarvam_stt_model: str = "saaras:v3"
    timezone: str = "Asia/Kolkata"
    database_path: str = ""  # empty = in-memory (dev only)
    store_key: str = ""  # Fernet key; required when database_path is set

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            whatsapp_verify_token=os.getenv("WHATSAPP_VERIFY_TOKEN", ""),
            whatsapp_app_secret=os.getenv("WHATSAPP_APP_SECRET", ""),
            whatsapp_access_token=os.getenv("WHATSAPP_ACCESS_TOKEN", ""),
            whatsapp_phone_number_id=os.getenv("WHATSAPP_PHONE_NUMBER_ID", ""),
            graph_api_version=os.getenv("GRAPH_API_VERSION", "v21.0"),
            sarvam_api_key=os.getenv("SARVAM_API_KEY", ""),
            sarvam_stt_model=os.getenv("SARVAM_STT_MODEL", "saaras:v3"),
            timezone=os.getenv("APP_TIMEZONE", "Asia/Kolkata"),
            database_path=os.getenv("DATABASE_PATH", ""),
            store_key=os.getenv("STORE_KEY", ""),
        )
