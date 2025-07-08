#!/usr/bin/env python3
"""
SOFIA Gmail MCP Server Entry Point
Launches the Gmail MCP server for SOFIA
"""

if __name__ == "__main__":
    from sofia.integrations.gmail.server import main
    main()