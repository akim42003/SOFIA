import os, sys, json
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import time
import os
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
SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/calendar"
]


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


def calendar_service():
    """Return an authorised Calendar service instance, triggering OAuth if needed."""
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

    return build("calendar", "v3", credentials=creds, cache_discovery=False)

server = FastMCP("gmail-calendar-tools")   # Combined server


def parse_date_with_current_month_default(date_string, start_of_day=False):
    """Parse date with preference for current month when ambiguous"""
    # Configure dateparser to prefer current month
    settings = {
        'PREFER_DATES_FROM': 'current_period',
        'PREFER_DAY_OF_MONTH': 'current'
    }
    parsed = dateparser.parse(date_string, settings=settings)
    
    # For date-only queries like "today", "tomorrow", set to start of day
    if parsed and start_of_day:
        # Check if it's a date-only input (common words like today, tomorrow, etc.)
        date_only_terms = ['today', 'tomorrow', 'yesterday', 'monday', 'tuesday', 'wednesday', 
                          'thursday', 'friday', 'saturday', 'sunday', 'this week', 'next week']
        if any(term in date_string.lower() for term in date_only_terms):
            parsed = parsed.replace(hour=0, minute=0, second=0, microsecond=0)
    
    return parsed


def format_datetime_local(dt):
    """Format datetime with local timezone handling"""
    if dt.tzinfo is None:
        # Convert to local time and check if DST is active for this specific datetime
        timestamp = dt.timestamp()
        local_time = time.localtime(timestamp)
        
        # Use the actual DST status for this specific time
        if local_time.tm_isdst:
            offset_seconds = time.altzone
        else:
            offset_seconds = time.timezone
            
        offset_hours = -offset_seconds // 3600
        offset_minutes = (-offset_seconds % 3600) // 60
        tz_str = f"{offset_hours:+03d}:{offset_minutes:02d}"
        return dt.isoformat() + tz_str
    else:
        return dt.isoformat()


def validate_datetime_string(dt_str):
    """Validate that datetime string is in proper RFC3339 format"""
    if not dt_str:
        return False
    
    # Check for basic RFC3339 format: YYYY-MM-DDTHH:MM:SS[.fff][+/-HH:MM]
    rfc3339_pattern = r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$'
    return bool(re.match(rfc3339_pattern, dt_str))

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
    max_results: int = 5,
    unread_only: bool = False,
    all_inbox: bool = True,
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


@server.tool()
def calendar_list_events(
    max_results: int = 10,
    time_min: Optional[str] = None,
    time_max: Optional[str] = None,
    calendar_id: str = "primary"
) -> List[Dict[str, str]]:
    """
    List upcoming calendar events.

    Args:
      max_results: Maximum number of events to return (default: 10).
      time_min:    RFC3339 timestamp or natural language date for start range (e.g., "today", "tomorrow").
      time_max:    RFC3339 timestamp or natural language date for end range.
      calendar_id: Calendar ID to query (default: "primary").

    Returns:
      List of calendar events with details.
    """
    try:
        service = calendar_service()
        
        # Handle natural language dates and datetime strings without timezone info
        if time_min:
            # Check if it's a natural language date OR a datetime string without timezone
            if not validate_datetime_string(time_min):
                parsed_date = parse_date_with_current_month_default(time_min, start_of_day=True)
                if parsed_date:
                    time_min = format_datetime_local(parsed_date)
                    # Validate the formatted datetime
                    if not validate_datetime_string(time_min):
                        time_min = format_datetime_local(datetime.now())
        else:
            # Default to now in local timezone
            time_min = format_datetime_local(datetime.now())
            
        if time_max:
            # Check if it's a natural language date OR a datetime string without timezone
            if not validate_datetime_string(time_max):
                # For time_max, we want end of day for date-only queries
                parsed_date = parse_date_with_current_month_default(time_max, start_of_day=False)
                if parsed_date:
                    # If it's a date-only query, set to end of day
                    date_only_terms = ['today', 'tomorrow', 'yesterday', 'monday', 'tuesday', 'wednesday', 
                                      'thursday', 'friday', 'saturday', 'sunday', 'this week', 'next week']
                    if any(term in time_max.lower() for term in date_only_terms):
                        parsed_date = parsed_date.replace(hour=23, minute=59, second=59, microsecond=999999)
                    
                    time_max = format_datetime_local(parsed_date)
                    # Validate the formatted datetime
                    if not validate_datetime_string(time_max):
                        time_max = None  # Let API use default end time

        events_result = service.events().list(
            calendarId=calendar_id,
            timeMin=time_min,
            timeMax=time_max,
            maxResults=max_results,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        events = events_result.get('items', [])
        
        formatted_events = []
        for event in events:
            start = event['start'].get('dateTime', event['start'].get('date'))
            end = event['end'].get('dateTime', event['end'].get('date'))
            
            formatted_events.append({
                'id': event['id'],
                'summary': event.get('summary', 'No Title'),
                'description': event.get('description', ''),
                'start': start,
                'end': end,
                'location': event.get('location', ''),
                'attendees': ', '.join([att.get('email', '') for att in event.get('attendees', [])]),
                'creator': event.get('creator', {}).get('email', ''),
                'html_link': event.get('htmlLink', '')
            })
            
        return formatted_events
        
    except Exception as e:
        return [{"error": f"Failed to list events: {str(e)}"}]


@server.tool()
def calendar_create_event(
    summary: str,
    start_time: str,
    end_time: Optional[str] = None,
    description: Optional[str] = None,
    location: Optional[str] = None,
    attendees: Optional[str] = None,
    calendar_id: str = "primary"
) -> Dict[str, str]:
    """
    Create a new calendar event.

    Args:
      summary:     Event title/summary.
      start_time:  RFC3339 timestamp or natural language date/time for event start.
      end_time:    RFC3339 timestamp or natural language date/time for event end.
      description: Event description (optional).
      location:    Event location (optional).
      attendees:   Comma-separated list of attendee email addresses (optional).
      calendar_id: Calendar ID to create event in (default: "primary").

    Returns:
      Created event details or error message.
    """
    try:
        service = calendar_service()
        
        # Parse start time with local timezone
        if not start_time.endswith('Z') and 'T' not in start_time:
            parsed_start = parse_date_with_current_month_default(start_time)
            if not parsed_start:
                return {"error": f"Could not parse start time: {start_time}"}
            start_time = format_datetime_local(parsed_start)
        
        # Parse end time or default to 1 hour after start
        if end_time:
            if not end_time.endswith('Z') and 'T' not in end_time:
                parsed_end = parse_date_with_current_month_default(end_time)
                if not parsed_end:
                    return {"error": f"Could not parse end time: {end_time}"}
                end_time = format_datetime_local(parsed_end)
        else:
            # Default to 1 hour duration in local timezone
            if 'T' in start_time:
                start_dt = datetime.fromisoformat(start_time.split('+')[0].split('-')[0] if '+' in start_time or start_time.count('-') > 2 else start_time.replace('Z', ''))
            else:
                start_dt = parse_date_with_current_month_default(start_time)
            
            end_dt = start_dt + timedelta(hours=1)
            end_time = format_datetime_local(end_dt)
        
        # Build event object
        event = {
            'summary': summary,
            'start': {'dateTime': start_time},
            'end': {'dateTime': end_time},
        }
        
        if description:
            event['description'] = description
        if location:
            event['location'] = location
        if attendees:
            attendee_emails = [email.strip() for email in attendees.split(',')]
            event['attendees'] = [{'email': email} for email in attendee_emails]
        
        # Create the event
        created_event = service.events().insert(
            calendarId=calendar_id,
            body=event
        ).execute()
        
        return {
            'id': created_event['id'],
            'summary': created_event.get('summary'),
            'start': created_event['start'].get('dateTime'),
            'end': created_event['end'].get('dateTime'),
            'html_link': created_event.get('htmlLink'),
            'status': 'created'
        }
        
    except Exception as e:
        return {"error": f"Failed to create event: {str(e)}"}


@server.tool()
def calendar_search_events(
    query: str,
    max_results: int = 10,
    time_min: Optional[str] = None,
    time_max: Optional[str] = None,
    calendar_id: str = "primary"
) -> List[Dict[str, str]]:
    """
    Search calendar events by text query.

    Args:
      query:       Text to search for in event summary and description.
      max_results: Maximum number of events to return (default: 10).
      time_min:    RFC3339 timestamp or natural language date for start range (optional).
      time_max:    RFC3339 timestamp or natural language date for end range (optional).
      calendar_id: Calendar ID to search (default: "primary").

    Returns:
      List of matching calendar events.
    """
    try:
        service = calendar_service()
        
        # Handle natural language dates with local timezone
        if time_min:
            if not time_min.endswith('Z') and 'T' not in time_min:
                parsed_date = parse_date_with_current_month_default(time_min)
                if parsed_date:
                    time_min = format_datetime_local(parsed_date)
                    
        if time_max:
            if not time_max.endswith('Z') and 'T' not in time_max:
                parsed_date = parse_date_with_current_month_default(time_max)
                if parsed_date:
                    time_max = format_datetime_local(parsed_date)

        events_result = service.events().list(
            calendarId=calendar_id,
            q=query,
            timeMin=time_min,
            timeMax=time_max,
            maxResults=max_results,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        events = events_result.get('items', [])
        
        formatted_events = []
        for event in events:
            start = event['start'].get('dateTime', event['start'].get('date'))
            end = event['end'].get('dateTime', event['end'].get('date'))
            
            formatted_events.append({
                'id': event['id'],
                'summary': event.get('summary', 'No Title'),
                'description': event.get('description', ''),
                'start': start,
                'end': end,
                'location': event.get('location', ''),
                'attendees': ', '.join([att.get('email', '') for att in event.get('attendees', [])]),
                'creator': event.get('creator', {}).get('email', ''),
                'html_link': event.get('htmlLink', '')
            })
            
        return formatted_events
        
    except Exception as e:
        return [{"error": f"Failed to search events: {str(e)}"}]


@server.tool()
def calendar_delete_event(
    event_id: str,
    calendar_id: str = "primary"
) -> Dict[str, str]:
    """
    Delete a calendar event.

    Args:
      event_id:    ID of the event to delete.
      calendar_id: Calendar ID where event exists (default: "primary").

    Returns:
      Deletion status or error message.
    """
    try:
        service = calendar_service()
        
        # Delete the event
        service.events().delete(calendarId=calendar_id, eventId=event_id).execute()
        
        return {
            'event_id': event_id,
            'status': 'deleted'
        }
        
    except Exception as e:
        return {"error": f"Failed to delete event: {str(e)}"}


def main():
    gmail_service()
    if len(sys.argv) > 1 and sys.argv[1] == "auth":
                  # runs OAuth, saves token.json
        print("OAuth finished. Run without 'auth' to start MCP server.")
    else:
        server.run()               # speaks MCP on stdin/stdout

if __name__ == "__main__":
    main()
