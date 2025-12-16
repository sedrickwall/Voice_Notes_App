from __future__ import annotations
import re
from typing import List

ACTION_PATTERNS = [
    r"\bI need to\b",
    r"\bI should\b",
    r"\bI must\b",
    r"\bI'll\b",
    r"\bI will\b",
    r"\bWe need to\b",
    r"\bWe should\b",
    r"\bNext step\b",
    r"\bTodo\b",
    r"\bTo-do\b",
    r"\bAction item\b",
    r"\bFollow up\b",
    r"\bFollow-up\b",
    r"\bEmail\b",
    r"\bCall\b",
    r"\bText\b",
    r"\bSchedule\b",
    r"\bSend\b",
    r"\bSubmit\b",
    r"\bUpdate\b",
    r"\bCreate\b",
    r"\bFinish\b",
]

# Simple sentence splitter
_SENT_SPLIT = re.compile(r"(?<=[.!?])\s+|\n+")


def extract_action_items(transcript: str, max_items: int = 12) -> List[str]:
    sentences = [s.strip() for s in _SENT_SPLIT.split(transcript) if s.strip()]
    hits = []

    for s in sentences:
        s_norm = s.lower()
        if any(re.search(pat.lower(), s_norm) for pat in ACTION_PATTERNS):
            hits.append(s)

    # Deduplicate while preserving order
    deduped = []
    seen = set()
    for x in hits:
        key = re.sub(r"\s+", " ", x.lower())
        if key not in seen:
            deduped.append(x)
            seen.add(key)

    return deduped[:max_items]
