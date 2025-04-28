from gmail_mcp import server
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
    all_inbox: bool = True,
    unread_only: bool = False,
    since: Optional[str] = None        # NEW  ← "yesterday", "3d", "2025‑04‑15", None
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
