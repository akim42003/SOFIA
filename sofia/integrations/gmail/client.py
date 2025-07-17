from sofia.integrations.gmail.server import server
from fastmcp import Client
from fastmcp.client.transports import FastMCPTransport
from typing import List, Dict, Optional
import asyncio

def gmail_search_emails(
    sender: Optional[str] = None,
    subject: Optional[str] = None,
    max_results: int = 10
) -> List[Dict[str, str]]:

    async def _call():
        async with Client(FastMCPTransport(server)) as client:
            return await client.call_tool(
                "gmail_search_emails",
                {
                    "sender": sender,
                    "subject": subject,
                    "max_results": max_results
                }
            )
    # run the coroutine and return its result
    return asyncio.run(_call())

def fetch_gmail(
    max_results: int = 5,
    all_inbox: bool = True, #allows listserve emails to be fetched
    unread_only: bool = False,
    since: Optional[str] = "yesterday"        # NEW  ← "yesterday", "3d", "2025‑04‑15", None
) -> List[Dict[str, str]]:
    # build payload, omitting None fields
    payload = {
        "max_results":  max_results,
        "all_inbox":    all_inbox,
        "unread_only":  unread_only
    }
    if since is not None:
        payload["since"] = since

    async def _call():
        async with Client(FastMCPTransport(server)) as client:
            result = await client.call_tool("gmail_fetch_emails", payload)
            # result.content is a list[dict]; adjust if your server wraps differently
            return result

    return asyncio.run(_call())

def send_gmail(
    sender_name: str,
    to: List[str],
    subject: str,
    body: Optional[str] = None,
    cc: Optional[List[str]] = None,
    bcc: Optional[List[str]] = None,
    mode: str = "new",                # "new" | "reply" | "forward"
    thread_id: Optional[str] = None,
    message_id: Optional[str] = None
) -> Dict[str, str]:

    payload: Dict[str, object] = {
        "sender_name": sender_name,
        "to": to,
        "subject": subject,
        "mode": mode,
    }
    if body is not None:
        payload["body"] = body
    if cc:
        payload["cc"] = cc
    if bcc:
        payload["bcc"] = bcc
    if thread_id:
        payload["thread_id"] = thread_id
    if message_id:
        payload["message_id"] = message_id

    async def _call():
        async with Client(FastMCPTransport(server)) as client:
            result = await client.call_tool("gmail_send_emails", payload)
            # For this tool result.content is already the dict we want
            # print(result)
            return result

    return asyncio.run(_call())


def calendar_list_events(
    max_results: int = 10,
    time_min: Optional[str] = None,
    time_max: Optional[str] = None,
    calendar_id: str = "primary"
) -> List[Dict[str, str]]:
    """List upcoming calendar events."""
    
    async def _call():
        async with Client(FastMCPTransport(server)) as client:
            return await client.call_tool(
                "calendar_list_events",
                {
                    "max_results": max_results,
                    "time_min": time_min,
                    "time_max": time_max,
                    "calendar_id": calendar_id
                }
            )
    return asyncio.run(_call())


def calendar_create_event(
    summary: str,
    start_time: str,
    end_time: Optional[str] = None,
    description: Optional[str] = None,
    location: Optional[str] = None,
    attendees: Optional[str] = None,
    calendar_id: str = "primary"
) -> Dict[str, str]:
    """Create a new calendar event."""
    
    async def _call():
        async with Client(FastMCPTransport(server)) as client:
            return await client.call_tool(
                "calendar_create_event",
                {
                    "summary": summary,
                    "start_time": start_time,
                    "end_time": end_time,
                    "description": description,
                    "location": location,
                    "attendees": attendees,
                    "calendar_id": calendar_id
                }
            )
    return asyncio.run(_call())


def calendar_search_events(
    query: str,
    max_results: int = 10,
    time_min: Optional[str] = None,
    time_max: Optional[str] = None,
    calendar_id: str = "primary"
) -> List[Dict[str, str]]:
    """Search calendar events by text query."""
    
    async def _call():
        async with Client(FastMCPTransport(server)) as client:
            return await client.call_tool(
                "calendar_search_events",
                {
                    "query": query,
                    "max_results": max_results,
                    "time_min": time_min,
                    "time_max": time_max,
                    "calendar_id": calendar_id
                }
            )
    return asyncio.run(_call())


def calendar_delete_event(
    event_id: str,
    calendar_id: str = "primary"
) -> Dict[str, str]:
    """Delete a calendar event."""
    
    async def _call():
        async with Client(FastMCPTransport(server)) as client:
            return await client.call_tool(
                "calendar_delete_event",
                {
                    "event_id": event_id,
                    "calendar_id": calendar_id
                }
            )
    return asyncio.run(_call())

