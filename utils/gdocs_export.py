from __future__ import annotations
from typing import Optional
import os
import pathlib

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/documents"]


def get_creds(client_secret_path: str, token_path: str = "gdocs_token.json") -> Credentials:
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
        if creds and creds.valid:
            return creds

    flow = InstalledAppFlow.from_client_secrets_file(client_secret_path, SCOPES)
    creds = flow.run_local_server(port=0)
    with open(token_path, "w") as f:
        f.write(creds.to_json())
    return creds


def export_to_google_doc(
    client_secret_path: str,
    title: str,
    markdown_body: str,
    token_path: str = "gdocs_token.json",
) -> str:
    """
    Creates a Google Doc and inserts markdown as plain text.
    Returns the document URL.
    """
    creds = get_creds(client_secret_path, token_path=token_path)
    service = build("docs", "v1", credentials=creds)

    doc = service.documents().create(body={"title": title}).execute()
    doc_id = doc["documentId"]

    # Insert as plain text
    requests = [
        {
            "insertText": {
                "location": {"index": 1},
                "text": markdown_body,
            }
        }
    ]
    service.documents().batchUpdate(documentId=doc_id, body={"requests": requests}).execute()

    return f"https://docs.google.com/document/d/{doc_id}/edit"
