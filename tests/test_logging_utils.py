import logging

from app.logging_utils import RedactingFilter


def test_redacts_telegram_bot_token_from_http_url() -> None:
    record = logging.LogRecord(
        name="httpx",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg='HTTP Request: POST https://api.telegram.org/bot123:ABC/getUpdates "HTTP/1.1 200 OK"',
        args=(),
        exc_info=None,
    )

    RedactingFilter(["123:ABC"]).filter(record)

    message = record.getMessage()
    assert "123:ABC" not in message
    assert "/bot<redacted>/getUpdates" in message


def test_redacts_secret_from_formatted_log_args() -> None:
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="token=%s",
        args=("secret-value",),
        exc_info=None,
    )

    RedactingFilter(["secret-value"]).filter(record)

    assert record.getMessage() == "token=<redacted>"
