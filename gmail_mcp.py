import os, sys, json
from typing import List

from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

from fastmcp import FastMCP

TOKEN_FILE = "token.json"
CREDS_FILE = "credentials.json"
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

# ───────────────────────────────────────────────────────── helpers ──
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

# ───────────────────────────────────────────────────────── MCP ─────
server = FastMCP("gmail-labels")   # arbitrary server id

@server.tool()
def gmail_list_labels() -> List[str]:
    """
    List all Gmail label names for the authenticated user.
    """
    service = gmail_service()
    res = service.users().labels().list(userId="me").execute()
    return [lab["name"] for lab in res.get("labels", [])]

# ───────────────────────────────────────────────────────── entry ────
if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "auth":
        gmail_service()            # runs OAuth, saves token.json
        print("OAuth finished. Run without 'auth' to start MCP server.")
    else:
        server.run()               # speaks MCP on stdin/stdout
