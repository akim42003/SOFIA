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
    all_inbox: bool = False,
    unread_only: bool = False,
    since: Optional[str] = None        # NEW  ← "yesterday", "3d", "2025‑04‑15", None
) -> List[Dict[str, str]]:
    """
    Call the gmail_fetch_emails MCP tool and return its list payload.

    Args
    ----
    max_results  : cap on number of messages
    all_inbox    : include Social/Promotions/etc. if True
    unread_only  : filter unread
    since        : natural‑language or relative date string (optional)

    Returns
    -------
    List[dict] as defined by gmail_fetch_emails
    """
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
