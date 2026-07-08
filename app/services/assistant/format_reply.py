"""Plain-text formatting for assistant replies shown in the UI.

Ported from myclinic-back management_assistant/format_reply.py — the same
OpenCode models can leak tool-call markup in plain-text replies, so we sanitize
before showing anything to the user.
"""

import re

_METADATA_LINE = re.compile(r"^\s*_?\s*Fonte\s*:.*$", re.IGNORECASE | re.MULTILINE)
# Only paired double markers are unwrapped. Single * / _ are intentionally left
# untouched: math, file names and emphasis used mid-word make them ambiguous.
_BOLD = re.compile(r"\*\*(.+?)\*\*")
_BOLD_UL = re.compile(r"__(.+?)__")
_HEADING = re.compile(r"^#{1,6}\s+", re.MULTILINE)
_DSML_ARTIFACT = re.compile(r"<\|[\|｜\s]*DSML[\|｜\s>]*.*", re.DOTALL | re.IGNORECASE)
_TOOL_INVOKE_ARTIFACT = re.compile(
    r"<\|[\|｜\s]*(?:DSML[\|｜\s>]*)?(?:tool_calls|invoke)\b.*",
    re.DOTALL | re.IGNORECASE,
)


def is_leaked_tool_markup(text: str) -> bool:
    """True when the model returned tool-call syntax instead of a user reply."""
    if not text:
        return False
    lowered = text.lower()
    if "dsml" in lowered and ("tool_calls" in lowered or "invoke" in lowered):
        return True
    if "<|tool_call" in lowered or "<tool_call" in lowered:
        return True
    return bool(_TOOL_INVOKE_ARTIFACT.search(text))


def sanitize_assistant_reply(text: str) -> str:
    """Strip markdown, tool markup and metadata footer; UI renders metadata separately."""
    if not text:
        return text

    if is_leaked_tool_markup(text):
        return ""

    cleaned = _DSML_ARTIFACT.sub("", text)
    cleaned = _TOOL_INVOKE_ARTIFACT.sub("", cleaned)
    cleaned = _METADATA_LINE.sub("", cleaned)
    cleaned = _HEADING.sub("", cleaned)
    for pattern in (_BOLD, _BOLD_UL):
        cleaned = pattern.sub(r"\1", cleaned)

    lines = [line.rstrip() for line in cleaned.splitlines()]
    normalized: list[str] = []
    blank_pending = False
    for line in lines:
        if not line.strip():
            if normalized and not blank_pending:
                blank_pending = True
            continue
        blank_pending = False
        normalized.append(line)

    return "\n\n".join(normalized).strip()
