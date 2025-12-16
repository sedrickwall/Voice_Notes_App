from __future__ import annotations
import re
from typing import Dict, List

_SENT_SPLIT = re.compile(r"(?<=[.!?])\s+|\n+")

KEYWORDS = [
    "goal", "plan", "strategy", "important", "priority", "deadline",
    "problem", "issue", "risk", "decision", "next", "because",
    "metric", "kpi", "revenue", "customer", "pipeline", "follow up"
]


def _score_sentence(s: str) -> int:
    s_l = s.lower()
    score = 0
    score += min(len(s) // 40, 3)  # prefer medium-length informative sentences
    for kw in KEYWORDS:
        if kw in s_l:
            score += 2
    if any(x in s_l for x in ["i think", "maybe", "kind of"]):
        score -= 1
    return score


def generate_notes(
    transcript: str,
    max_summary_bullets: int = 10,
    max_key_points: int = 6,
) -> Dict[str, List[str]]:
    sentences = [s.strip() for s in _SENT_SPLIT.split(transcript) if s.strip()]
    if not sentences:
        return {"summary": [], "key_points": [], "questions": []}

    ranked = sorted(sentences, key=_score_sentence, reverse=True)

    summary = ranked[:max_summary_bullets]

    questions = [s for s in sentences if s.endswith("?")][:6]

    key_points = [
        s for s in ranked
        if s not in summary
    ][:max_key_points]

    return {
        "summary": summary,
        "key_points": key_points,
        "questions": questions,
    }

