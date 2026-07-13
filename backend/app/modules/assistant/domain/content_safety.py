from __future__ import annotations

import re


MAX_QUESTION_LENGTH = 1200
MAX_ANSWER_LENGTH = 5000
MAX_COMMENT_LENGTH = 600

SECRET_PATTERNS = (
    re.compile(r"\bsk-[A-Za-z0-9_\-]{12,}\b"),
    re.compile(r"\bsk-proj-[A-Za-z0-9_\-]{12,}\b"),
    re.compile(r"(?i)\b(api[_-]?key|token|secret|password|senha)\s*[:=]\s*['\"]?[^'\"\s]{8,}"),
    re.compile(r"(?i)\b(bearer)\s+[A-Za-z0-9_\-\.]{12,}"),
)


def sanitize_text(value: object, *, limit: int) -> str:
    text = str(value or "").replace("\x00", " ").strip()
    for pattern in SECRET_PATTERNS:
        text = pattern.sub("[redigido]", text)
    text = re.sub(r"\s+\n", "\n", text)
    text = re.sub(r"\n{4,}", "\n\n\n", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    return text[:limit].strip()


def sanitize_question(value: object) -> str:
    return sanitize_text(value, limit=MAX_QUESTION_LENGTH)


def sanitize_answer(value: object) -> str:
    return sanitize_text(value, limit=MAX_ANSWER_LENGTH)


def sanitize_comment(value: object) -> str:
    return sanitize_text(value, limit=MAX_COMMENT_LENGTH)


def title_from_question(question: str) -> str:
    clean = sanitize_question(question)
    if not clean:
        return "Nova conversa"
    return clean[:80].rstrip(" .,!?:;") or "Nova conversa"

