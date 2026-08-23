"""Robust parsing of vision model output into the QAAnalysis contract.

The model is prompted to return raw JSON, but responses can include markdown
fences or leading prose. This parser extracts the first valid JSON object and
validates it against the contract; unknown enum values degrade gracefully
instead of failing the whole analysis.
"""

import json
import re
from dataclasses import dataclass
from typing import Optional

from pydantic import ValidationError

from src.infrastructure.qa_visual.models import QAIssue, QAAnalysis

# Extracts the outermost {...} block, ignoring braces inside strings.
_JSON_OBJECT_RE = re.compile(r"\{.*\}", re.DOTALL)


@dataclass
class ParseResult:
    """Outcome of parsing the model content."""

    analysis: Optional[QAAnalysis] = None
    parse_error: bool = False
    raw_content: str = ""


def _extract_json_text(content: str) -> Optional[str]:
    """Extract candidate JSON text, handling fences and leading prose."""
    text = content.strip()
    if not text:
        return None
    if text.startswith("```"):
        # Strip markdown fence lines (with or without language tag).
        lines = [line for line in text.split("\n") if not line.strip().startswith("```")]
        text = "\n".join(lines).strip()
    if text.startswith("{"):
        return text
    match = _JSON_OBJECT_RE.search(text)
    return match.group(0) if match else None


def parse_qa_analysis(content: str) -> ParseResult:
    """Parse model output into a validated QAAnalysis.

    Returns ParseResult with parse_error=True and the raw content when the
    output cannot be parsed or does not satisfy the contract.
    """
    json_text = _extract_json_text(content)
    if json_text is None:
        return ParseResult(analysis=None, parse_error=True, raw_content=content)

    try:
        data = json.loads(json_text)
    except json.JSONDecodeError:
        return ParseResult(analysis=None, parse_error=True, raw_content=content)

    if not isinstance(data, dict):
        return ParseResult(analysis=None, parse_error=True, raw_content=content)

    try:
        analysis = QAAnalysis.model_validate(data)
    except ValidationError:
        # Retry with degraded tolerance: drop invalid issues instead of failing.
        analysis = _coerce_lenient(data)
        if analysis is None:
            return ParseResult(analysis=None, parse_error=True, raw_content=content)

    return ParseResult(analysis=analysis, parse_error=False)


def _coerce_lenient(data: dict) -> Optional[QAAnalysis]:
    """Best-effort coercion: unknown severities/categories fall back to defaults."""
    if "overall_score" not in data:
        return None
    valid_keys = {"severity", "category", "description", "element"}
    issues = []
    for issue in data.get("qa_issues") or []:
        if not isinstance(issue, dict):
            continue
        candidate = {k: v for k, v in issue.items() if k in valid_keys}
        try:
            issues.append(QAIssue.model_validate(candidate))
            continue
        except ValidationError:
            pass
        # Drop invalid enum values and retry with the remaining fields.
        cleaned = dict(candidate)
        for key in ("severity", "category"):
            if key in cleaned:
                try:
                    QAIssue.model_validate({key: cleaned[key], "description": ""})
                except ValidationError:
                    cleaned.pop(key, None)
        try:
            issues.append(QAIssue.model_validate(cleaned))
        except ValidationError:
            continue
    patched = dict(data)
    patched["qa_issues"] = [issue.model_dump() for issue in issues]
    try:
        return QAAnalysis.model_validate(patched)
    except ValidationError:
        return None
