"""Config loading and secret redaction for the AI Council skill.

The API key is loaded from ~/.ai-council/config.env (or $AI_COUNCIL_CONFIG) and is
never written to stdout/stderr. redact() is applied to every error string that
leaves this process, so a key that leaks into an exception message from urllib or
a proxy error body does not end up in the model's context.
"""

import hashlib
import os
import re
import sys
from pathlib import Path

DEFAULT_CONFIG = Path.home() / ".ai-council" / "config.env"

REQUIRED = ("AI_COUNCIL_BASE_URL", "AI_COUNCIL_API_KEY")

_LINE = re.compile(r"""^\s*(?:export\s+)?([A-Z0-9_]+)\s*=\s*(.*?)\s*$""")


class ConfigError(Exception):
    pass


def config_path() -> Path:
    return Path(os.environ.get("AI_COUNCIL_CONFIG", DEFAULT_CONFIG)).expanduser()


def _unquote(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1]
    return value


def load() -> dict:
    """Return config from the file, with real environment variables taking priority."""
    data = {}
    path = config_path()
    if path.exists():
        mode = path.stat().st_mode & 0o077
        if mode:
            print(
                f"warning: {path} is readable by other users (chmod 600 recommended)",
                file=sys.stderr,
            )
        for raw in path.read_text(encoding="utf-8").splitlines():
            if not raw.strip() or raw.lstrip().startswith("#"):
                continue
            m = _LINE.match(raw)
            if m:
                data[m.group(1)] = _unquote(m.group(2))

    for key in (
        "AI_COUNCIL_BASE_URL",
        "AI_COUNCIL_API_KEY",
        "AI_COUNCIL_MODELS",
        "AI_COUNCIL_TIMEOUT",
    ):
        if os.environ.get(key):
            data[key] = os.environ[key]

    missing = [k for k in REQUIRED if not data.get(k)]
    if missing:
        raise ConfigError(
            "Missing "
            + ", ".join(missing)
            + f". Expected in {path} or the environment. "
            "Run scripts/init_config.sh in your own terminal to create it."
        )

    data["AI_COUNCIL_BASE_URL"] = data["AI_COUNCIL_BASE_URL"].rstrip("/")
    return data


def models(cfg: dict) -> list:
    raw = cfg.get("AI_COUNCIL_MODELS", "")
    return [m.strip() for m in raw.split(",") if m.strip()]


def fingerprint(secret: str) -> str:
    """Short, non-reversible identifier so a key can be talked about safely."""
    return hashlib.sha256(secret.encode("utf-8")).hexdigest()[:8]


_secrets = []


def register_secret(value: str) -> None:
    if value and len(value) >= 6:
        _secrets.append(value)


def redact(text) -> str:
    text = str(text)
    for secret in _secrets:
        text = text.replace(secret, "<redacted-api-key>")
    # catch bearer tokens the proxy may echo back in an error body
    text = re.sub(r"(?i)(bearer\s+)[A-Za-z0-9._\-]{6,}", r"\1<redacted>", text)
    text = re.sub(r"(?i)(sk-[A-Za-z0-9._\-]{6,})", "<redacted-api-key>", text)
    return text
