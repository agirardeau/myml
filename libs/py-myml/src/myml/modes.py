from __future__ import annotations

import math
import re
from typing import Any

from .errors import ModeError

VALID_MODES = ("default", "strict", "y11safety")

_Y11_BOOLEAN_WORDS = {"yes", "no", "on", "off", "y", "n"}
_Y11_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}(?:[tT ].*)?$")
_Y11_TIME_RE = re.compile(r"^\d{1,2}:\d{2}:\d{2}(?:\.\d+)?$")
_Y11_OCTAL_RE = re.compile(r"^0[0-9]+$")
_Y11_SEXAGESIMAL_RE = re.compile(r"^\d+:\d{2}(?::\d{2}(?:\.\d+)?)?$")


def validate_mode(mode: str) -> str:
    if mode not in VALID_MODES:
        raise ModeError(
            f"Unsupported mode {mode!r}. Expected one of {', '.join(VALID_MODES)}.",
            code="unsupported-mode",
            category="api_error",
        )
    return mode


def yaml11_ambiguity(text: str) -> tuple[str, str] | None:
    lowered = text.lower()
    if lowered in _Y11_BOOLEAN_WORDS:
        return ("yaml11-safety-ambiguous-boolean", "YAML 1.1-ambiguous boolean spelling")
    if _Y11_DATE_RE.match(text):
        return ("yaml11-safety-date-like", "YAML 1.1-ambiguous date/time form")
    if _Y11_TIME_RE.match(text):
        return ("yaml11-safety-date-like", "YAML 1.1-ambiguous time form")
    if _Y11_OCTAL_RE.match(text):
        return ("yaml11-safety-octal-like", "YAML 1.1-ambiguous octal-like form")
    if _Y11_SEXAGESIMAL_RE.match(text):
        return ("yaml11-safety-sexagesimal-like", "YAML 1.1-ambiguous sexagesimal-like form")
    return None


def is_special_float(value: Any) -> bool:
    return isinstance(value, float) and not math.isfinite(value)
