"""Robust JSON extraction from LLM responses.

Llama 3.3 via Groq often wraps JSON in preamble text, code fences, or
trailing commentary.  This module tries four strategies in order and
returns the first successfully-parsed Python object.
"""

from __future__ import annotations

import json
import re
from typing import Any


def extract_json(text: str) -> Any:
    """Extract a JSON object or array from *text* using four strategies.

    Returns the parsed Python object (dict or list).
    Raises ``ValueError`` if every strategy fails.
    """
    text = text.strip()

    # Strategy 1 — direct parse (ideal case)
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        pass

    # Strategy 2 — extract from ```json ... ``` code fences
    fence_match = re.search(
        r"```(?:json)?\s*\n?(.*?)```", text, re.DOTALL
    )
    if fence_match:
        try:
            return json.loads(fence_match.group(1).strip())
        except (json.JSONDecodeError, TypeError):
            pass

    # Strategy 3 — find outermost braces with depth tracking (object)
    obj = _extract_balanced(text, "{", "}")
    if obj is not None:
        try:
            return json.loads(obj)
        except (json.JSONDecodeError, TypeError):
            pass

    # Strategy 4 — find outermost brackets (array)
    arr = _extract_balanced(text, "[", "]")
    if arr is not None:
        try:
            return json.loads(arr)
        except (json.JSONDecodeError, TypeError):
            pass

    raise ValueError(
        f"Could not extract valid JSON from LLM response "
        f"(length={len(text)}). First 200 chars: {text[:200]!r}"
    )


def _extract_balanced(text: str, open_ch: str, close_ch: str) -> str | None:
    """Return the first balanced substring delimited by *open_ch* / *close_ch*.

    Uses depth tracking so nested braces / brackets are handled correctly.
    Returns ``None`` if no balanced region is found.
    """
    start = text.find(open_ch)
    if start == -1:
        return None

    depth = 0
    in_string = False
    escape_next = False

    for i in range(start, len(text)):
        ch = text[i]

        if escape_next:
            escape_next = False
            continue

        if ch == "\\":
            if in_string:
                escape_next = True
            continue

        if ch == '"':
            in_string = not in_string
            continue

        if in_string:
            continue

        if ch == open_ch:
            depth += 1
        elif ch == close_ch:
            depth -= 1
            if depth == 0:
                return text[start : i + 1]

    return None
