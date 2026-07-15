from __future__ import annotations

import os
from pathlib import Path


DEFAULT_CREDENTIAL_FILE = Path(r"D:\hh\保险箱\重要凭据.txt")


def load_tushare_token(
    token_env: str = "TUSHARE_TOKEN",
    credential_file: Path = DEFAULT_CREDENTIAL_FILE,
) -> str | None:
    token = os.environ.get(token_env)
    if token:
        return token.strip()
    return _load_labeled_secret(credential_file, ("tushare", "token"))


def load_joinquant_credentials(
    username_env: str = "JQDATA_USERNAME",
    password_env: str = "JQDATA_PASSWORD",
    credential_file: Path = DEFAULT_CREDENTIAL_FILE,
) -> tuple[str | None, str | None]:
    username = os.environ.get(username_env)
    password = os.environ.get(password_env)
    if username and password:
        return username.strip(), password.strip()
    text = _read_secret_text(credential_file)
    if not text:
        return username, password
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    found_user = username
    found_password = password
    for index, line in enumerate(lines):
        lower = line.lower()
        value = _inline_value(line)
        if not found_user and _has_any(lower, ("joinquant", "jqdata", "聚宽")) and _has_any(lower, ("user", "account", "账号", "用户名")):
            found_user = value or _next_value(lines, index)
        if not found_password and _has_any(lower, ("joinquant", "jqdata", "聚宽")) and _has_any(lower, ("password", "密码")):
            found_password = value or _next_value(lines, index)
    return found_user, found_password


def _load_labeled_secret(path: Path, labels: tuple[str, ...]) -> str | None:
    text = _read_secret_text(path)
    if not text:
        return None
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    for index, line in enumerate(lines):
        lower = line.lower()
        if all(label.lower() in lower for label in labels):
            return _inline_value(line) or _next_value(lines, index)
    return None


def _read_secret_text(path: Path) -> str:
    if not path.exists():
        return ""
    raw = path.read_bytes()
    for encoding in ("utf-8-sig", "utf-8", "gbk", "utf-16"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="ignore")


def _inline_value(line: str) -> str | None:
    for separator in (":", "：", "="):
        if separator in line:
            value = line.split(separator, 1)[1].strip()
            return value or None
    return None


def _next_value(lines: list[str], index: int) -> str | None:
    if index + 1 >= len(lines):
        return None
    candidate = lines[index + 1].strip()
    if not candidate or any(separator in candidate for separator in (":", "：", "=")):
        return None
    return candidate


def _has_any(text: str, needles: tuple[str, ...]) -> bool:
    return any(needle.lower() in text for needle in needles)
