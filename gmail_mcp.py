import os, sys, json
from typing import List, Dict, Optional
from datetime import datetime
import re
import base64, email.utils
from email.message import EmailMessage
import dateparser
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

from fastmcp import FastMCP

TOKEN_FILE = "token.json"
CREDS_FILE = "credentials.json"
SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]


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
    unread_only: bool = True,
    all_inbox: bool = False,
    since: Optional[str] = None   # NEW  ← "yesterday", "2025‑04‑10", "3d", None
) -> List[Dict[str, str]]:
    """
    Fetch up to `max_results` messages from Gmail.

    Args
    ----
    max_results   : cap on returned messages
    unread_only   : only unread if True
    all_inbox     : include Social/Promotions/etc. if True
    since         : natural‑language time (e.g. "yesterday", "3d", "2025‑04‑01")

    Returns
    -------
    List[dict] with keys id, snippet, date, subject, from
    """
    service = gmail_service()

    if all_inbox:
        clause = "in:inbox"
    else:
        clause = ("in:inbox "
                  "-category:social "
                  "-category:promotions "
                  "-category:updates "
                  "-category:forums")

    if unread_only:
        clause += " is:unread"

    if since:
        # 2a. purely relative pattern like "3d", "12h", "90m"
        m = re.fullmatch(r"(\d+)([dhm])", since.strip().lower())
        if m:
            clause += f" newer_than:{m.group(1)}{m.group(2)}"
        else:
            # 2b. parse with dateparser
            dt: datetime | None = dateparser.parse(since, settings={"TIMEZONE": "UTC"})
            if dt is None:
                raise ValueError(f"Could not interpret `since='{since}'`")
            clause += f" after:{dt.strftime('%Y/%m/%d')}"

    resp = service.users().messages().list(
        userId="me",
        q=clause,
        maxResults=max_results
    ).execute()

    results: List[Dict[str, str]] = []
    for meta in resp.get("messages", []):
        msg = service.users().messages().get(
            userId="me",
            id=meta["id"],
            format="metadata",
            metadataHeaders=["Subject", "From", "Date"]
        ).execute()

        hdr = {h["name"]: h["value"] for h in msg["payload"]["headers"]}
        results.append({
            "id":       meta["id"],
            "snippet":  msg.get("snippet", ""),
            "subject":  hdr.get("Subject", ""),
            "from":     hdr.get("From", ""),
            "date":     hdr.get("Date", "")
        })

    return results

@server.tool()
def gmail_send_emails(
    sender_name: str,
    subject: str,
    to: List[str] | None = None,
    cc: List[str] | None = None,
    bcc: List[str] | None = None,
    body: str | None = None,
    mode: str = "new",
    thread_id: str | None = None,
    message_id: str | None = None
) -> Dict[str, str]:
    """
    Send (new / reply / forward) an e‑mail.

    Returns { id: <gmail id>, threadId: <gmail threadId> }.
    """
    svc = gmail_service()
    me_profile = svc.users().getProfile(userId="me").execute()
    sender_addr = me_profile["emailAddress"]
    sender_formatted = email.utils.formataddr((sender_name, sender_addr))

    if mode in {"reply", "forward"} and not (thread_id or message_id):
        raise ValueError("thread_id or message_id required for reply/forward")

    msg = EmailMessage()
    msg["From"] = sender_formatted

    if to:
        msg["To"] = ", ".join(to)
    if cc:
        msg["Cc"] = ", ".join(cc)
    if bcc:
        msg["Bcc"] = ", ".join(bcc)

    msg["Subject"] = subject
    msg.set_content(body or "(no body)")

    if mode == "reply":
        msg["In-Reply-To"] = message_id
        msg["References"] = message_id

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode().rstrip("=")

    request_body = {"raw": raw}
    if thread_id:
        request_body["threadId"] = thread_id

    sent: dict = svc.users().messages().send(
        userId="me",
        body=request_body
    ).execute()

    content = {
        "id": sent["id"],          # ← use dict indexing, not .data
        "subject": subject,
        "to": to,
        "body": body
    }
    return content



if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "auth":
        gmail_service()            # runs OAuth, saves token.json
        print("OAuth finished. Run without 'auth' to start MCP server.")
    else:
        server.run()               # speaks MCP on stdin/stdout
