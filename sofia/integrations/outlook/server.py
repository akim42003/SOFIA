import os, sys, json
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import time
import re
import base64
from email.message import EmailMessage
import dateparser
import msal
import requests
from fastmcp import FastMCP
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

TOKEN_CACHE_FILE = "outlook_token_cache.json"
CLIENT_ID = os.getenv("OUTLOOK_CLIENT_ID")  # Azure App Registration Client ID
CLIENT_SECRET = os.getenv("OUTLOOK_CLIENT_SECRET")  # Optional: for confidential apps
TENANT_ID = os.getenv("OUTLOOK_TENANT_ID", "common")  # or specific tenant
SCOPES = [
    "https://graph.microsoft.com/Mail.ReadWrite",
    "https://graph.microsoft.com/Mail.Send",
    "https://graph.microsoft.com/Calendars.ReadWrite",
    "https://graph.microsoft.com/User.Read"
]

GRAPH_API_BASE = "https://graph.microsoft.com/v1.0"


class OutlookAuth:
    """Handle Microsoft OAuth authentication for Outlook/Graph API"""
    
    def __init__(self):
        self.cache = msal.SerializableTokenCache()
        self._load_cache()
        
        # Public client app (no secret needed for desktop/CLI apps)
        self.app = msal.PublicClientApplication(
            CLIENT_ID,
            authority=f"https://login.microsoftonline.com/{TENANT_ID}",
            token_cache=self.cache
        )
    
    def _load_cache(self):
        """Load token cache from file"""
        if os.path.exists(TOKEN_CACHE_FILE):
            with open(TOKEN_CACHE_FILE, "r") as f:
                self.cache.deserialize(f.read())
    
    def _save_cache(self):
        """Save token cache to file"""
        with open(TOKEN_CACHE_FILE, "w") as f:
            f.write(self.cache.serialize())
    
    def get_token(self):
        """Get access token, refreshing or acquiring as needed"""
        accounts = self.app.get_accounts()
        
        if accounts:
            # Try silent token acquisition
            result = self.app.acquire_token_silent(SCOPES, account=accounts[0])
            if result and "access_token" in result:
                self._save_cache()
                return result["access_token"]
        
        # Interactive authentication needed
        result = self.app.acquire_token_interactive(
            SCOPES,
            prompt="select_account"
        )
        
        if "access_token" in result:
            self._save_cache()
            return result["access_token"]
        else:
            raise Exception(f"Authentication failed: {result.get('error_description', 'Unknown error')}")


def get_graph_headers():
    """Get headers with authentication for Graph API requests"""
    auth = OutlookAuth()
    token = auth.get_token()
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }


def parse_date_with_current_month_default(date_string, start_of_day=False):
    """Parse date with preference for current month when ambiguous"""
    settings = {
        'PREFER_DATES_FROM': 'current_period',
        'PREFER_DAY_OF_MONTH': 'current'
    }
    parsed = dateparser.parse(date_string, settings=settings)
    
    if parsed and start_of_day:
        date_only_terms = ['today', 'tomorrow', 'yesterday', 'monday', 'tuesday', 'wednesday', 
                          'thursday', 'friday', 'saturday', 'sunday', 'this week', 'next week']
        if any(term in date_string.lower() for term in date_only_terms):
            parsed = parsed.replace(hour=0, minute=0, second=0, microsecond=0)
    
    return parsed


def format_datetime_iso(dt):
    """Format datetime as ISO 8601 for Graph API"""
    if dt.tzinfo is None:
        # Assume local timezone and convert to UTC
        timestamp = dt.timestamp()
        utc_dt = datetime.utcfromtimestamp(timestamp)
        return utc_dt.isoformat() + "Z"
    else:
        return dt.isoformat()


server = FastMCP("outlook-tools")


@server.tool()
def outlook_search_emails(
    sender: Optional[str] = None,
    subject: Optional[str] = None,
    max_results: int = 10,
    folder: str = "inbox"
) -> List[Dict[str, str]]:
    """
    Search Outlook for messages matching a given sender and/or subject.

    Args:
      sender:      email address (or name) to filter by
      subject:     substring to match in the Subject header
      max_results: how many messages to return at most
      folder:      folder to search in (inbox, sentitems, drafts, etc.)

    Returns:
      A list of dicts, each containing:
        - id             : the message ID
        - conversationId : the conversation/thread ID
        - subject        : the Subject header
        - bodyPreview    : a short preview of the message body
        - from           : the sender info
        - receivedDateTime: when the message was received
        - isRead         : read status
        - importance     : message importance level
    """
    headers = get_graph_headers()
    
    # Build OData filter query
    filters = []
    if sender:
        # Search in from/emailAddress/address and from/emailAddress/name
        filters.append(f"(from/emailAddress/address eq '{sender}' or from/emailAddress/name eq '{sender}')")
    if subject:
        filters.append(f"contains(subject, '{subject}')")
    
    filter_query = " and ".join(filters) if filters else None
    
    # Build request URL
    url = f"{GRAPH_API_BASE}/me/mailFolders/{folder}/messages"
    params = {
        "$top": max_results,
        "$orderby": "receivedDateTime desc",
        "$select": "id,conversationId,subject,bodyPreview,from,receivedDateTime,isRead,importance,hasAttachments"
    }
    if filter_query:
        params["$filter"] = filter_query
    
    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()
    
    messages = response.json().get("value", [])
    
    results = []
    for msg in messages:
        results.append({
            "id": msg.get("id", ""),
            "conversationId": msg.get("conversationId", ""),
            "subject": msg.get("subject", ""),
            "bodyPreview": msg.get("bodyPreview", ""),
            "from": f"{msg.get('from', {}).get('emailAddress', {}).get('name', '')} <{msg.get('from', {}).get('emailAddress', {}).get('address', '')}>",
            "receivedDateTime": msg.get("receivedDateTime", ""),
            "isRead": msg.get("isRead", False),
            "importance": msg.get("importance", "normal"),
            "hasAttachments": msg.get("hasAttachments", False)
        })
    
    return results


@server.tool()
def outlook_fetch_emails(
    max_results: int = 5,
    unread_only: bool = False,
    folder: str = "inbox",
    since: Optional[str] = None,
    include_attachments: bool = False
) -> List[Dict[str, str]]:
    """
    Fetch up to `max_results` messages from Outlook.

    Args:
      max_results:        cap on returned messages
      unread_only:        only unread if True
      folder:             folder to fetch from (inbox, sentitems, drafts, etc.)
      since:              natural-language time (e.g. "yesterday", "3d", "2025-04-01")
      include_attachments: include attachment info if True

    Returns:
      List[dict] with message details
    """
    headers = get_graph_headers()
    
    filters = []
    if unread_only:
        filters.append("isRead eq false")
    
    if since:
        # Handle relative patterns like "3d", "12h"
        m = re.fullmatch(r"(\d+)([dhm])", since.strip().lower())
        if m:
            num = int(m.group(1))
            unit = m.group(2)
            if unit == 'd':
                cutoff = datetime.now() - timedelta(days=num)
            elif unit == 'h':
                cutoff = datetime.now() - timedelta(hours=num)
            elif unit == 'm':
                cutoff = datetime.now() - timedelta(minutes=num)
            filters.append(f"receivedDateTime ge {format_datetime_iso(cutoff)}")
        else:
            # Parse with dateparser
            dt = dateparser.parse(since, settings={"TIMEZONE": "UTC"})
            if dt:
                filters.append(f"receivedDateTime ge {format_datetime_iso(dt)}")
    
    filter_query = " and ".join(filters) if filters else None
    
    url = f"{GRAPH_API_BASE}/me/mailFolders/{folder}/messages"
    params = {
        "$top": max_results,
        "$orderby": "receivedDateTime desc",
        "$select": "id,conversationId,subject,body,bodyPreview,from,toRecipients,ccRecipients,receivedDateTime,isRead,importance,hasAttachments"
    }
    if filter_query:
        params["$filter"] = filter_query
    
    if include_attachments:
        params["$expand"] = "attachments($select=id,name,contentType,size)"
    
    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()
    
    messages = response.json().get("value", [])
    
    results = []
    for msg in messages:
        result = {
            "id": msg.get("id", ""),
            "conversationId": msg.get("conversationId", ""),
            "subject": msg.get("subject", ""),
            "bodyPreview": msg.get("bodyPreview", ""),
            "from": f"{msg.get('from', {}).get('emailAddress', {}).get('name', '')} <{msg.get('from', {}).get('emailAddress', {}).get('address', '')}>",
            "to": ", ".join([f"{r.get('emailAddress', {}).get('name', '')} <{r.get('emailAddress', {}).get('address', '')}>" 
                            for r in msg.get("toRecipients", [])]),
            "cc": ", ".join([f"{r.get('emailAddress', {}).get('name', '')} <{r.get('emailAddress', {}).get('address', '')}>" 
                            for r in msg.get("ccRecipients", [])]),
            "receivedDateTime": msg.get("receivedDateTime", ""),
            "isRead": msg.get("isRead", False),
            "importance": msg.get("importance", "normal")
        }
        
        if include_attachments and msg.get("hasAttachments"):
            attachments = msg.get("attachments", [])
            result["attachments"] = [
                {
                    "id": att.get("id"),
                    "name": att.get("name"),
                    "contentType": att.get("contentType"),
                    "size": att.get("size")
                }
                for att in attachments
            ]
        
        results.append(result)
    
    return results


@server.tool()
def outlook_send_email(
    subject: str,
    to: List[str],
    body: str,
    cc: Optional[List[str]] = None,
    bcc: Optional[List[str]] = None,
    importance: str = "normal",
    reply_to_id: Optional[str] = None,
    save_to_sent: bool = True
) -> Dict[str, str]:
    """
    Send a new email or reply through Outlook.

    Args:
      subject:      Email subject
      to:           List of recipient email addresses
      body:         Email body (HTML supported)
      cc:           List of CC recipients (optional)
      bcc:          List of BCC recipients (optional)
      importance:   Email importance (low, normal, high)
      reply_to_id:  Message ID to reply to (optional)
      save_to_sent: Save to Sent Items folder

    Returns:
      Dict with send status and message ID
    """
    headers = get_graph_headers()
    
    # Build message object
    message = {
        "subject": subject,
        "body": {
            "contentType": "HTML" if "<" in body else "Text",
            "content": body
        },
        "toRecipients": [{"emailAddress": {"address": addr}} for addr in to],
        "importance": importance
    }
    
    if cc:
        message["ccRecipients"] = [{"emailAddress": {"address": addr}} for addr in cc]
    if bcc:
        message["bccRecipients"] = [{"emailAddress": {"address": addr}} for addr in bcc]
    
    if reply_to_id:
        # Reply to existing message
        url = f"{GRAPH_API_BASE}/me/messages/{reply_to_id}/reply"
        payload = {
            "message": message,
            "comment": body
        }
    else:
        # Send new message
        url = f"{GRAPH_API_BASE}/me/sendMail"
        payload = {
            "message": message,
            "saveToSentItems": save_to_sent
        }
    
    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()
    
    return {
        "status": "sent",
        "subject": subject,
        "to": to,
        "timestamp": datetime.now().isoformat()
    }


@server.tool()
def outlook_mark_as_read(
    message_id: str,
    is_read: bool = True
) -> Dict[str, str]:
    """
    Mark an email as read or unread.

    Args:
      message_id: The message ID to update
      is_read:    True to mark as read, False to mark as unread

    Returns:
      Update status
    """
    headers = get_graph_headers()
    url = f"{GRAPH_API_BASE}/me/messages/{message_id}"
    
    payload = {"isRead": is_read}
    
    response = requests.patch(url, headers=headers, json=payload)
    response.raise_for_status()
    
    return {
        "message_id": message_id,
        "isRead": is_read,
        "status": "updated"
    }


@server.tool()
def outlook_move_email(
    message_id: str,
    destination_folder: str
) -> Dict[str, str]:
    """
    Move an email to a different folder.

    Args:
      message_id:         The message ID to move
      destination_folder: Target folder name (e.g., "archive", "junkEmail", "deletedItems")

    Returns:
      Move status
    """
    headers = get_graph_headers()
    
    # Get destination folder ID
    folder_url = f"{GRAPH_API_BASE}/me/mailFolders"
    folder_response = requests.get(folder_url, headers=headers)
    folder_response.raise_for_status()
    
    folders = folder_response.json().get("value", [])
    dest_folder_id = None
    
    for folder in folders:
        if folder.get("displayName", "").lower() == destination_folder.lower():
            dest_folder_id = folder.get("id")
            break
    
    if not dest_folder_id:
        return {"error": f"Folder '{destination_folder}' not found"}
    
    # Move the message
    url = f"{GRAPH_API_BASE}/me/messages/{message_id}/move"
    payload = {"destinationId": dest_folder_id}
    
    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()
    
    return {
        "message_id": message_id,
        "moved_to": destination_folder,
        "status": "moved"
    }


@server.tool()
def outlook_delete_email(
    message_id: str,
    permanent: bool = False
) -> Dict[str, str]:
    """
    Delete an email (move to Deleted Items or permanently delete).

    Args:
      message_id: The message ID to delete
      permanent:  If True, permanently delete; if False, move to Deleted Items

    Returns:
      Deletion status
    """
    headers = get_graph_headers()
    
    if permanent:
        # Permanent deletion
        url = f"{GRAPH_API_BASE}/me/messages/{message_id}"
        response = requests.delete(url, headers=headers)
    else:
        # Move to Deleted Items
        return outlook_move_email(message_id, "deletedItems")
    
    response.raise_for_status()
    
    return {
        "message_id": message_id,
        "status": "deleted",
        "permanent": permanent
    }


@server.tool()
def outlook_list_calendar_events(
    max_results: int = 10,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    calendar_name: Optional[str] = None
) -> List[Dict[str, str]]:
    """
    List upcoming calendar events from Outlook.

    Args:
      max_results:   Maximum number of events to return
      start_time:    Start of time range (natural language or ISO format)
      end_time:      End of time range (natural language or ISO format)
      calendar_name: Specific calendar to query (optional, defaults to primary)

    Returns:
      List of calendar events with details
    """
    headers = get_graph_headers()
    
    # Parse time parameters
    if start_time:
        if not start_time.endswith('Z') and 'T' not in start_time:
            parsed_start = parse_date_with_current_month_default(start_time, start_of_day=True)
            if parsed_start:
                start_time = format_datetime_iso(parsed_start)
    else:
        start_time = format_datetime_iso(datetime.now())
    
    if end_time:
        if not end_time.endswith('Z') and 'T' not in end_time:
            parsed_end = parse_date_with_current_month_default(end_time, start_of_day=False)
            if parsed_end:
                # For date-only queries, set to end of day
                date_only_terms = ['today', 'tomorrow', 'yesterday', 'monday', 'tuesday', 
                                 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
                if any(term in end_time.lower() for term in date_only_terms):
                    parsed_end = parsed_end.replace(hour=23, minute=59, second=59)
                end_time = format_datetime_iso(parsed_end)
    
    # Build calendar URL
    if calendar_name:
        # Get calendar ID by name
        cal_url = f"{GRAPH_API_BASE}/me/calendars"
        cal_response = requests.get(cal_url, headers=headers)
        cal_response.raise_for_status()
        
        calendars = cal_response.json().get("value", [])
        calendar_id = None
        for cal in calendars:
            if cal.get("name", "").lower() == calendar_name.lower():
                calendar_id = cal.get("id")
                break
        
        if not calendar_id:
            return [{"error": f"Calendar '{calendar_name}' not found"}]
        
        url = f"{GRAPH_API_BASE}/me/calendars/{calendar_id}/events"
    else:
        url = f"{GRAPH_API_BASE}/me/calendar/events"
    
    params = {
        "$top": max_results,
        "$orderby": "start/dateTime",
        "$select": "id,subject,body,bodyPreview,start,end,location,attendees,organizer,isAllDay,isCancelled,responseStatus,webLink"
    }
    
    if start_time and end_time:
        params["$filter"] = f"start/dateTime ge '{start_time}' and start/dateTime le '{end_time}'"
    elif start_time:
        params["$filter"] = f"start/dateTime ge '{start_time}'"
    
    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()
    
    events = response.json().get("value", [])
    
    formatted_events = []
    for event in events:
        formatted_events.append({
            "id": event.get("id", ""),
            "subject": event.get("subject", "No Title"),
            "bodyPreview": event.get("bodyPreview", ""),
            "start": event.get("start", {}).get("dateTime", ""),
            "end": event.get("end", {}).get("dateTime", ""),
            "location": event.get("location", {}).get("displayName", ""),
            "isAllDay": event.get("isAllDay", False),
            "organizer": f"{event.get('organizer', {}).get('emailAddress', {}).get('name', '')} <{event.get('organizer', {}).get('emailAddress', {}).get('address', '')}>",
            "attendees": ", ".join([f"{att.get('emailAddress', {}).get('name', '')} ({att.get('status', {}).get('response', '')})" 
                                   for att in event.get("attendees", [])]),
            "responseStatus": event.get("responseStatus", {}).get("response", ""),
            "webLink": event.get("webLink", "")
        })
    
    return formatted_events


@server.tool()
def outlook_create_calendar_event(
    subject: str,
    start_time: str,
    end_time: Optional[str] = None,
    body: Optional[str] = None,
    location: Optional[str] = None,
    attendees: Optional[List[str]] = None,
    is_all_day: bool = False,
    reminder_minutes: Optional[int] = 15,
    calendar_name: Optional[str] = None
) -> Dict[str, str]:
    """
    Create a new calendar event in Outlook.

    Args:
      subject:          Event title
      start_time:       Start time (natural language or ISO format)
      end_time:         End time (optional, defaults to 1 hour after start)
      body:             Event description
      location:         Event location
      attendees:        List of attendee email addresses
      is_all_day:       Mark as all-day event
      reminder_minutes: Minutes before event to show reminder
      calendar_name:    Specific calendar to create event in

    Returns:
      Created event details
    """
    headers = get_graph_headers()
    
    # Parse times
    if not start_time.endswith('Z') and 'T' not in start_time:
        parsed_start = parse_date_with_current_month_default(start_time)
        if not parsed_start:
            return {"error": f"Could not parse start time: {start_time}"}
        start_dt = parsed_start
        start_time = format_datetime_iso(parsed_start)
    else:
        start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
    
    if end_time:
        if not end_time.endswith('Z') and 'T' not in end_time:
            parsed_end = parse_date_with_current_month_default(end_time)
            if not parsed_end:
                return {"error": f"Could not parse end time: {end_time}"}
            end_time = format_datetime_iso(parsed_end)
    else:
        # Default to 1 hour duration
        end_dt = start_dt + timedelta(hours=1)
        end_time = format_datetime_iso(end_dt)
    
    # Build event object
    event = {
        "subject": subject,
        "start": {
            "dateTime": start_time,
            "timeZone": "UTC"
        },
        "end": {
            "dateTime": end_time,
            "timeZone": "UTC"
        },
        "isAllDay": is_all_day
    }
    
    if body:
        event["body"] = {
            "contentType": "HTML" if "<" in body else "Text",
            "content": body
        }
    
    if location:
        event["location"] = {"displayName": location}
    
    if attendees:
        event["attendees"] = [
            {
                "emailAddress": {"address": email},
                "type": "required"
            }
            for email in attendees
        ]
    
    if reminder_minutes is not None:
        event["isReminderOn"] = True
        event["reminderMinutesBeforeStart"] = reminder_minutes
    
    # Determine calendar URL
    if calendar_name:
        # Get calendar ID by name
        cal_url = f"{GRAPH_API_BASE}/me/calendars"
        cal_response = requests.get(cal_url, headers=headers)
        cal_response.raise_for_status()
        
        calendars = cal_response.json().get("value", [])
        calendar_id = None
        for cal in calendars:
            if cal.get("name", "").lower() == calendar_name.lower():
                calendar_id = cal.get("id")
                break
        
        if not calendar_id:
            return {"error": f"Calendar '{calendar_name}' not found"}
        
        url = f"{GRAPH_API_BASE}/me/calendars/{calendar_id}/events"
    else:
        url = f"{GRAPH_API_BASE}/me/calendar/events"
    
    response = requests.post(url, headers=headers, json=event)
    response.raise_for_status()
    
    created_event = response.json()
    
    return {
        "id": created_event.get("id"),
        "subject": created_event.get("subject"),
        "start": created_event.get("start", {}).get("dateTime"),
        "end": created_event.get("end", {}).get("dateTime"),
        "webLink": created_event.get("webLink"),
        "status": "created"
    }


@server.tool()
def outlook_update_calendar_event(
    event_id: str,
    subject: Optional[str] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    body: Optional[str] = None,
    location: Optional[str] = None,
    attendees: Optional[List[str]] = None
) -> Dict[str, str]:
    """
    Update an existing calendar event.

    Args:
      event_id:    ID of the event to update
      subject:     New event title (optional)
      start_time:  New start time (optional)
      end_time:    New end time (optional)
      body:        New description (optional)
      location:    New location (optional)
      attendees:   New attendee list (optional)

    Returns:
      Update status
    """
    headers = get_graph_headers()
    url = f"{GRAPH_API_BASE}/me/events/{event_id}"
    
    update_data = {}
    
    if subject:
        update_data["subject"] = subject
    
    if start_time:
        if not start_time.endswith('Z') and 'T' not in start_time:
            parsed_start = parse_date_with_current_month_default(start_time)
            if parsed_start:
                start_time = format_datetime_iso(parsed_start)
        update_data["start"] = {"dateTime": start_time, "timeZone": "UTC"}
    
    if end_time:
        if not end_time.endswith('Z') and 'T' not in end_time:
            parsed_end = parse_date_with_current_month_default(end_time)
            if parsed_end:
                end_time = format_datetime_iso(parsed_end)
        update_data["end"] = {"dateTime": end_time, "timeZone": "UTC"}
    
    if body:
        update_data["body"] = {
            "contentType": "HTML" if "<" in body else "Text",
            "content": body
        }
    
    if location:
        update_data["location"] = {"displayName": location}
    
    if attendees:
        update_data["attendees"] = [
            {
                "emailAddress": {"address": email},
                "type": "required"
            }
            for email in attendees
        ]
    
    response = requests.patch(url, headers=headers, json=update_data)
    response.raise_for_status()
    
    return {
        "event_id": event_id,
        "status": "updated",
        "updated_fields": list(update_data.keys())
    }


@server.tool()
def outlook_delete_calendar_event(
    event_id: str,
    send_cancellation: bool = True
) -> Dict[str, str]:
    """
    Delete a calendar event.

    Args:
      event_id:          ID of the event to delete
      send_cancellation: Send cancellation to attendees

    Returns:
      Deletion status
    """
    headers = get_graph_headers()
    url = f"{GRAPH_API_BASE}/me/events/{event_id}"
    
    # If there are attendees and we want to send cancellation
    if send_cancellation:
        # First get the event to check for attendees
        get_response = requests.get(url, headers=headers)
        if get_response.status_code == 200:
            event = get_response.json()
            if event.get("attendees"):
                # Cancel the event (which sends notifications)
                cancel_url = f"{url}/cancel"
                cancel_payload = {"comment": "This event has been cancelled."}
                requests.post(cancel_url, headers=headers, json=cancel_payload)
    
    # Delete the event
    response = requests.delete(url, headers=headers)
    response.raise_for_status()
    
    return {
        "event_id": event_id,
        "status": "deleted",
        "cancellation_sent": send_cancellation
    }


@server.tool()
def outlook_search_calendar_events(
    query: str,
    max_results: int = 10,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None
) -> List[Dict[str, str]]:
    """
    Search calendar events by text query.

    Args:
      query:       Text to search for in event subject and body
      max_results: Maximum number of events to return
      start_time:  Start of search range (optional)
      end_time:    End of search range (optional)

    Returns:
      List of matching calendar events
    """
    headers = get_graph_headers()
    
    # Parse time parameters
    filters = []
    
    if start_time:
        if not start_time.endswith('Z') and 'T' not in start_time:
            parsed_start = parse_date_with_current_month_default(start_time)
            if parsed_start:
                start_time = format_datetime_iso(parsed_start)
        filters.append(f"start/dateTime ge '{start_time}'")
    
    if end_time:
        if not end_time.endswith('Z') and 'T' not in end_time:
            parsed_end = parse_date_with_current_month_default(end_time)
            if parsed_end:
                end_time = format_datetime_iso(parsed_end)
        filters.append(f"start/dateTime le '{end_time}'")
    
    # Add search query
    filters.append(f"contains(subject, '{query}') or contains(body/content, '{query}')")
    
    filter_query = " and ".join(filters)
    
    url = f"{GRAPH_API_BASE}/me/calendar/events"
    params = {
        "$top": max_results,
        "$filter": filter_query,
        "$orderby": "start/dateTime",
        "$select": "id,subject,body,bodyPreview,start,end,location,attendees,organizer,webLink"
    }
    
    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()
    
    events = response.json().get("value", [])
    
    formatted_events = []
    for event in events:
        formatted_events.append({
            "id": event.get("id", ""),
            "subject": event.get("subject", "No Title"),
            "bodyPreview": event.get("bodyPreview", ""),
            "start": event.get("start", {}).get("dateTime", ""),
            "end": event.get("end", {}).get("dateTime", ""),
            "location": event.get("location", {}).get("displayName", ""),
            "organizer": f"{event.get('organizer', {}).get('emailAddress', {}).get('name', '')} <{event.get('organizer', {}).get('emailAddress', {}).get('address', '')}>",
            "attendees": ", ".join([f"{att.get('emailAddress', {}).get('name', '')}" 
                                   for att in event.get("attendees", [])]),
            "webLink": event.get("webLink", "")
        })
    
    return formatted_events


def main():
    """Main entry point for the Outlook MCP server"""
    if not CLIENT_ID:
        print("Error: OUTLOOK_CLIENT_ID environment variable not set")
        print("Please set up an Azure App Registration and provide the Client ID")
        sys.exit(1)
    
    if len(sys.argv) > 1 and sys.argv[1] == "auth":
        # Test authentication
        auth = OutlookAuth()
        token = auth.get_token()
        print("OAuth authentication successful. Token acquired.")
        print("Run without 'auth' argument to start MCP server.")
    else:
        # Start MCP server
        server.run()


if __name__ == "__main__":
    main()