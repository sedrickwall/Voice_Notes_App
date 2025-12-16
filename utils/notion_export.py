from __future__ import annotations
from typing import List, Dict, Optional
from notion_client import Client
from datetime import datetime

def export_to_notion_database(
    notion_token: str,
    database_id: str,
    title: str,
    markdown_body: str,
    action_items: List[str],
) -> str:
    """
    Creates a page in a Notion database with:
    - Name (title)
    - Date
    - Action Items (as rich text)
    - Body (as page content blocks - basic chunking)
    Returns created page URL.
    """
    client = Client(auth=notion_token)

    # Notion block text limit ~2000 chars per rich_text item; keep chunks smaller
    def chunk_text(text: str, chunk_size: int = 1800):
        return [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)]

    action_text = "\n".join([f"- {x}" for x in action_items]) if action_items else "(none)"

    page = client.pages.create(
        parent={"database_id": database_id},
        properties={
            "Name": {"title": [{"text": {"content": title}}]},
            "Date": {"date": {"start": datetime.utcnow().isoformat()}},
            "Action Items": {"rich_text": [{"text": {"content": action_text[:1900]}}]},
        },
        children=[
            {
                "object": "block",
                "type": "heading_2",
                "heading_2": {"rich_text": [{"type": "text", "text": {"content": "Notes"}}]},
            },
            *[
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {"rich_text": [{"type": "text", "text": {"content": chunk}}]},
                }
                for chunk in chunk_text(markdown_body)
            ],
        ],
    )

    return page.get("url", "")
