from __future__ import annotations

import math
from typing import Any

from .errors import ModeError

VALID_MODES = ("standard", "strict")


def validate_mode(mode: str) -> str:
    if mode not in VALID_MODES:
        raise ModeError(
            f"Unsupported mode {mode!r}. Expected one of {', '.join(VALID_MODES)}.",
            code="unsupported-mode",
            category="api_error",
        )
    return mode
def is_special_float(value: Any) -> bool:
    return isinstance(value, float) and not math.isfinite(value)
