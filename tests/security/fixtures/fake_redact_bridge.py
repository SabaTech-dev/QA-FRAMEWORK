#!/usr/bin/env python3
"""Deterministic stand-in for the Node redact bridge (tests only).

Speaks the exact bridge protocol: NDJSON on stdin
    {"id": 1, "text": "..."}
and replies one NDJSON line per request on stdout:
    {"id": 1, "redactedText": "...", "items": [{"label": ..., "original": ...,
     "placeholder": ...}]}
The fake replaces ONLY email addresses; it exists so unit tests never
download the 195MB SDK model.
"""

from __future__ import annotations

import json
import re
import sys

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")


def main() -> int:
    counters: dict[str, int] = {}
    originals: dict[str, str] = {}
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except json.JSONDecodeError:
            continue
        text = req.get("text", "")
        items: list[dict[str, str]] = []

        def sub(m: re.Match[str]) -> str:
            label = "email"
            counters[label] = counters.get(label, 0) + 1
            placeholder = f"[{label.upper()}_{counters[label]}]"
            originals[placeholder] = m.group(0)
            items.append(
                {
                    "label": label,
                    "original": m.group(0),
                    "placeholder": placeholder,
                }
            )
            return placeholder

        redacted = EMAIL_RE.sub(sub, text)
        sys.stdout.write(
            json.dumps({"id": req.get("id"), "redactedText": redacted, "items": items}) + "\n"
        )
        sys.stdout.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
