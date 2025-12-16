from __future__ import annotations
from typing import List, Dict

def to_markdown(title: str, transcript: str, notes: Dict[str, List[str]], action_items: List[str]) -> str:
    def bullets(items: List[str]) -> str:
        return "\n".join([f"- {x}" for x in items]) if items else "- (none)"

    md = []
    md.append(f"# {title}\n")
    md.append("## Summary\n" + bullets(notes.get("summary", [])) + "\n")
    md.append("## Action Items\n" + bullets(action_items) + "\n")
    md.append("## Key Points\n" + bullets(notes.get("key_points", [])) + "\n")
    md.append("## Questions\n" + bullets(notes.get("questions", [])) + "\n")
    md.append("## Full Transcript\n" + transcript.strip() + "\n")
    return "\n".join(md)
