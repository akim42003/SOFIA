import os, sys, json
from typing import List, Dict, Optional

from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

from fastmcp import FastMCP

TOKEN_FILE = "token.json"
CREDS_FILE = "credentials.json"
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]


def gmail_service():
    """Return an authorised Gmail service instance, triggering OAuth if needed."""
    creds: Credentials | None = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, "w") as f:
            f.write(creds.to_json())

    return build("gmail", "v1", credentials=creds, cache_discovery=False)

server = FastMCP("gmail-tools")   # arbitrary server id

@server.tool()
def gmail_search_emails(
    sender: Optional[str] = None,
    subject: Optional[str] = None,
    max_results: int = 10
) -> List[Dict[str, str]]:
    """
    Search Gmail for messages matching a given sender and/or subject.

    Args:
      sender:    email address (or name) to filter by (e.g. "alice@example.com").
      subject:   substring to match in the Subject header.
      max_results: how many messages to return at most.

    Returns:
      A list of dicts, each containing:
        - id       : the message ID
        - threadId : the thread ID
        - snippet  : a short preview of the message body
        - from     : the From header
        - subject  : the Subject header
        - date     : the Date header
    """
    service = gmail_service()

    # build the Gmail 'q=' query string
    q_parts = []
    if sender:
        q_parts.append(f"from:{sender}")
    if subject:
        q_parts.append(f"subject:{subject}")
    query = " ".join(q_parts)

    # list matching messages
    resp = service.users().messages().list(
        userId="me",
        q=query,
        maxResults=max_results
    ).execute()

    results = []
    for msg_meta in resp.get("messages", []):
        # fetch headers & snippet
        msg = service.users().messages().get(
            userId="me",
            id=msg_meta["id"],
            format="metadata",
            metadataHeaders=["From", "Subject", "Date"]
        ).execute()

        headers = {h["name"]: h["value"] for h in msg.get("payload", {}).get("headers", [])}
        results.append({
            "id":       msg_meta["id"],
            "threadId": msg_meta.get("threadId", ""),
            "snippet":  msg.get("snippet", ""),
            "from":     headers.get("From", ""),
            "subject":  headers.get("Subject", ""),
            "date":     headers.get("Date", ""),
        })

    return results


@server.tool()
def gmail_fetch_emails(
    max_results: int = 10,
    unread_only: bool = False,
    all_inbox: bool = False
) -> List[Dict[str, str]]:
    service = gmail_service()

    # base Gmail search clause
    if all_inbox:
        clause = "in:inbox"
    else:
        # Primary = inbox minus the other categories
        clause = (
            "in:inbox "
            "-category:social "
            "-category:promotions "
            "-category:updates "
            "-category:forums"
        )

    # add unread filter
    if unread_only:
        clause += " is:unread"

    # issue the list call
    resp = service.users().messages().list(
        userId="me",
        q=clause,
        maxResults=max_results
    ).execute()

    # fetch snippets
    results: List[Dict[str,str]] = []
    for m in resp.get("messages", []):
        msg = service.users().messages().get(
            userId="me",
            id=m["id"],
            format="metadata"
        ).execute()
        results.append({
            "id":      m["id"],
            "snippet": msg.get("snippet", "")
        })

    return results



if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "auth":
        gmail_service()            # runs OAuth, saves token.json
        print("OAuth finished. Run without 'auth' to start MCP server.")
    else:
        server.run()               # speaks MCP on stdin/stdout
