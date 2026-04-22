from __future__ import annotations

import hashlib
import hmac


def is_valid_hmac_sha1_signature(*, secret_key: str, body: bytes, provided_signature: str) -> bool:
    normalized_secret = str(secret_key or "").strip()
    normalized_signature = str(provided_signature or "").strip().lower()
    if not normalized_secret or not normalized_signature:
        return False
    expected_signature = hmac.new(
        normalized_secret.encode("utf-8"),
        body or b"",
        hashlib.sha1,
    ).hexdigest()
    return hmac.compare_digest(expected_signature, normalized_signature)
