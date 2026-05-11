import os
import requests
from flask import current_app

SMS_API_KEY = os.getenv("SMS_API_KEY")
SMS_SENDER_ID = os.getenv("SMS_SENDER_ID")
SMS_BASE_URL = os.getenv("SMS_BASE_URL", "https://sms.arkesel.com/api/v2/sms/send")


def _normalize_phone(phone):
    digits = "".join(ch for ch in str(phone) if ch.isdigit())
    if digits.startswith("0") and len(digits) >= 10:
        return "233" + digits[1:]
    return digits


def send_sms(to, message):
    """Send an SMS via Arkesel. Returns (success: bool, details).

    Expects `SMS_API_KEY` and `SMS_SENDER_ID` to be set in the environment.
    """
    if not SMS_API_KEY or not SMS_SENDER_ID:
        current_app.logger.warning("SMS not sent: missing SMS_API_KEY or SMS_SENDER_ID")
        return False, "missing_credentials"

    payload = {
        "key": SMS_API_KEY,
        "sender": SMS_SENDER_ID,
        "message": message,
        "recipients": [_normalize_phone(to)],
        # Compatibility fields for alternate Arkesel SMS payload variants.
        "to": _normalize_phone(to),
        "sender_id": SMS_SENDER_ID,
    }

    headers = {
        "Content-Type": "application/json",
        "api-key": SMS_API_KEY,
    }

    try:
        resp = requests.post(SMS_BASE_URL, json=payload, headers=headers, timeout=10)
        if resp.ok:
            try:
                details = resp.json()
            except Exception:
                details = resp.text

            current_app.logger.info("SMS sent successfully to %s: %s", _normalize_phone(to), details)
            return True, details
        else:
            return False, resp.text
    except Exception as exc:
        current_app.logger.exception("Error sending SMS: %s", exc)
        return False, str(exc)
