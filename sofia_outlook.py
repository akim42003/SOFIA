#!/usr/bin/env python3
"""
SOFIA Outlook MCP Server Entry Point
Launches the Outlook Mail and Calendar MCP server for SOFIA
"""

if __name__ == "__main__":
    from sofia.integrations.outlook.server import main
    main()