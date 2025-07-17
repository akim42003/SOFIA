#!/usr/bin/env python3
"""
SOFIA Gmail & Calendar MCP Server Entry Point
Launches the combined Gmail and Calendar MCP server for SOFIA
"""

if __name__ == "__main__":
    from sofia.integrations.gmail.server import main
    main()