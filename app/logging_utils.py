from __future__ import annotations

import logging
import os
import re


TELEGRAM_BOT_URL_RE = re.compile(r"/bot[^/\s]+/")


class RedactingFilter(logging.Filter):
    def __init__(self, secrets: list[str]) -> None:
        super().__init__()
        self.secrets = [secret for secret in secrets if secret]

    def filter(self, record: logging.LogRecord) -> bool:
        message = record.getMessage()
        message = TELEGRAM_BOT_URL_RE.sub("/bot<redacted>/", message)
        for secret in self.secrets:
            message = message.replace(secret, "<redacted>")
        record.msg = message
        record.args = ()
        return True


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    redacting_filter = RedactingFilter(
        [
            os.getenv("TELEGRAM_BOT_TOKEN", ""),
            os.getenv("STRAVA_CLIENT_SECRET", ""),
            os.getenv("STRAVA_REFRESH_TOKEN", ""),
        ]
    )
    logging.getLogger().addFilter(redacting_filter)
    for handler in logging.getLogger().handlers:
        handler.addFilter(redacting_filter)
