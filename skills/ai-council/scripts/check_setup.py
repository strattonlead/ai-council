#!/usr/bin/env python3
"""Verify that the AI Council is configured and the LiteLLM proxy answers.

Prints the base URL, the configured roster and a short key fingerprint.
It deliberately never prints the API key itself.

Exit codes: 0 ready, 1 not configured, 2 configured but unreachable.
"""

import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _config  # noqa: E402


def probe(base_url: str, key: str, timeout: float = 15.0):
    """Ask the proxy which models it serves. Returns (ok, detail)."""
    req = urllib.request.Request(
        f"{base_url}/v1/models",
        headers={"Authorization": f"Bearer {key}", "Accept": "application/json"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = json.loads(resp.read().decode("utf-8"))
        served = [m.get("id") for m in body.get("data", []) if m.get("id")]
        return True, served
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")[:400]
        return False, f"HTTP {exc.code}: {_config.redact(detail)}"
    except Exception as exc:  # noqa: BLE001
        return False, _config.redact(exc)


def main() -> int:
    try:
        cfg = _config.load()
    except _config.ConfigError as exc:
        print("NOT CONFIGURED")
        print(f"  {exc}")
        print("  See references/setup.md. Do not ask the user for the key in chat.")
        return 1

    key = cfg["AI_COUNCIL_API_KEY"]
    _config.register_secret(key)
    base = cfg["AI_COUNCIL_BASE_URL"]
    roster = _config.models(cfg)

    print(f"config file : {_config.config_path()}")
    print(f"base url    : {base}")
    print(f"api key     : set, fingerprint {_config.fingerprint(key)} (value never printed)")
    print(f"roster      : {', '.join(roster) if roster else '(none configured)'}")

    ok, detail = probe(base, key, float(cfg.get("AI_COUNCIL_TIMEOUT", 15)))
    if not ok:
        print(f"proxy       : UNREACHABLE — {detail}")
        return 2

    print(f"proxy       : reachable, {len(detail)} model(s) served")
    unknown = [m for m in roster if detail and m not in detail]
    if unknown:
        print(f"warning     : not served by the proxy: {', '.join(unknown)}")
    if not roster:
        print("hint        : set AI_COUNCIL_MODELS, or pass --models to council.py")
    print("\nREADY")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
