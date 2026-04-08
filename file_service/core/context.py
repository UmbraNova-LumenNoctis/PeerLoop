"""Shared runtime context for file service."""

import logging
import os
from threading import Lock

from imagekitio import ImageKit

from shared_schemas.vault_client import PATHS_FILE_SERVICE, load_vault_secrets

load_vault_secrets(PATHS_FILE_SERVICE)

SERVICE_NAME = "file-service"
logger = logging.getLogger("file-service")

NOTIFICATION_SERVICE_URL = os.getenv("NOTIFICATION_SERVICE_URL")
INTERNAL_SERVICE_TOKEN = os.getenv("INTERNAL_SERVICE_TOKEN")
INTERNAL_TLS_VERIFY = (os.getenv("INTERNAL_TLS_VERIFY") or "false").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}
NOTIFICATION_TIMEOUT_SECONDS = 5.0
TOKEN_VALIDATION_TIMEOUT_SECONDS = 5.0
MEDIA_FILES_TABLE = "media_files"

ALLOWED_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
    ".mp4",
    ".mov",
    ".webm",
    ".mkv",
    ".pdf",
    ".txt",
    ".doc",
    ".docx",
}

ALLOWED_MIME_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "video/mp4",
    "video/webm",
    "video/quicktime",
    "video/x-matroska",
    "application/pdf",
    "text/plain",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/zip",
}

ALLOWED_DETECTED_MIME_BY_EXTENSION = {
    ".jpg": {"image/jpeg"},
    ".jpeg": {"image/jpeg"},
    ".png": {"image/png"},
    ".webp": {"image/webp"},
    ".mp4": {"video/mp4"},
    ".mov": {"video/quicktime"},
    ".webm": {"video/webm"},
    ".mkv": {"video/x-matroska"},
    ".pdf": {"application/pdf"},
    ".txt": {"text/plain"},
    ".doc": {"application/msword", "application/octet-stream"},
    ".docx": {
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/zip",
        "application/octet-stream",
    },
}

IMAGEKIT_PRIVATE_KEY: str | None = None
IMAGEKIT_PUBLIC_KEY: str | None = None
IMAGEKIT_URL: str | None = None
SUPABASE_URL: str | None = None
SUPABASE_KEY: str | None = None
MAX_FILE_SIZE_MB = 25
MAX_FILE_SIZE = MAX_FILE_SIZE_MB * 1024 * 1024

runtime_config_lock = Lock()
imagekit: ImageKit | None = None
supabase = None
