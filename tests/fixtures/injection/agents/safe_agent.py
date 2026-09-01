#!/usr/bin/env python3
"""Deterministic SAFE fixture agent.

Reads the task document from workspace/input/document.md, writes a summary to
workspace/output/summary.md and emits a clean tool-call trace. Never follows
injected instructions. Used by the injection harness tests as a non-vulnerable
agent under test.
"""

import json
import os
from pathlib import Path

workspace = Path(os.environ["INJECTION_WORKSPACE"])

trace = [
    {"tool": "read", "args": ["input/document.md"]},
    {"tool": "write", "args": ["output/summary.md", "Revenue grew 12% QoQ."]},
]

(workspace / "output").mkdir(parents=True, exist_ok=True)
(workspace / "output" / "summary.md").write_text("Revenue grew 12% QoQ.\n")
(workspace / "tool_calls.jsonl").write_text("".join(json.dumps(c) + "\n" for c in trace))
print("summary written")
