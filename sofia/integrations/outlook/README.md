# Outlook MCP Tools for SOFIA

This module provides Microsoft Outlook integration for SOFIA, enabling email and calendar management through the Microsoft Graph API.

## Features

### Email Tools
- **outlook_search_emails** - Search emails by sender, subject, or folder
- **outlook_fetch_emails** - Fetch emails with filters (unread, date range, attachments)
- **outlook_send_email** - Send new emails or replies
- **outlook_mark_as_read** - Mark emails as read/unread
- **outlook_move_email** - Move emails between folders
- **outlook_delete_email** - Delete emails (trash or permanent)

### Calendar Tools
- **outlook_list_calendar_events** - List events in date range
- **outlook_create_calendar_event** - Create new calendar events
- **outlook_update_calendar_event** - Update existing events
- **outlook_delete_calendar_event** - Delete events with optional cancellation
- **outlook_search_calendar_events** - Search events by text query

## Setup

### 1. Azure App Registration

1. Go to [Azure Portal](https://portal.azure.com)
2. Navigate to Azure Active Directory > App registrations
3. Click "New registration"
4. Configure your app:
   - Name: "SOFIA Outlook Integration" (or your preference)
   - Supported account types: "Accounts in any organizational directory and personal Microsoft accounts"
   - Redirect URI: `http://localhost` (Platform: "Public client/native")
5. Note the **Application (client) ID**

### 2. Configure API Permissions

In your app registration:
1. Go to "API permissions"
2. Click "Add a permission" > "Microsoft Graph"
3. Select "Delegated permissions"
4. Add these permissions:
   - Mail.ReadWrite
   - Mail.Send
   - Calendars.ReadWrite
   - User.Read

### 3. Environment Variables

Add these to your `.env` file in the project root:

```bash
OUTLOOK_CLIENT_ID="your-app-client-id"
OUTLOOK_TENANT_ID="common"  # or your specific tenant ID
```

For organizational accounts with admin consent, you can optionally use a client secret:
```bash
OUTLOOK_CLIENT_SECRET="your-client-secret"  # Optional
```

The server will automatically load these from the `.env` file.

### 4. Install Dependencies

```bash
pip install msal requests dateparser fastmcp
```

## Usage

### Test Authentication

```bash
python sofia_outlook.py auth
```

This will open a browser for Microsoft authentication and save the token.

### Run MCP Server

```bash
python sofia_outlook.py
```

The server will start and expose all Outlook tools via the MCP protocol.

## Tool Examples

### Email Management

```python
# Search for emails from a specific sender
outlook_search_emails(
    sender="john@example.com",
    max_results=5
)

# Fetch unread emails from the last 3 days
outlook_fetch_emails(
    unread_only=True,
    since="3d",
    include_attachments=True
)

# Send an email
outlook_send_email(
    subject="Meeting Follow-up",
    to=["alice@example.com"],
    body="Thanks for the productive meeting today!",
    importance="high"
)

# Move email to archive
outlook_move_email(
    message_id="AAMkAGI2...",
    destination_folder="archive"
)
```

### Calendar Management

```python
# List today's events
outlook_list_calendar_events(
    start_time="today",
    end_time="today"
)

# Create a meeting
outlook_create_calendar_event(
    subject="Team Sync",
    start_time="tomorrow at 2pm",
    end_time="tomorrow at 3pm",
    location="Conference Room A",
    attendees=["team@example.com"],
    reminder_minutes=15
)

# Search for events
outlook_search_calendar_events(
    query="project review",
    start_time="this week"
)

# Update an event
outlook_update_calendar_event(
    event_id="AAMkAGI2...",
    location="Virtual - Teams Link"
)
```

## Natural Language Date Support

The tools support natural language date/time inputs:
- Relative: "today", "tomorrow", "yesterday", "next week"
- Specific: "Monday", "April 15", "2025-04-15"
- Durations: "3d" (3 days), "12h" (12 hours), "90m" (90 minutes)

## Differences from Gmail/Google Calendar Tools

### Authentication
- Uses Microsoft OAuth 2.0 via MSAL instead of Google OAuth
- Requires Azure App Registration instead of Google Cloud Console
- Token stored in `outlook_token_cache.json`

### API Differences
- Uses Microsoft Graph API instead of Google APIs
- Different folder structure (inbox, sentitems, drafts vs labels)
- Supports importance levels (low, normal, high)
- Calendar events use different timezone handling

### Additional Features
- **Email folders**: Better folder management (archive, junk, custom folders)
- **Read status**: Dedicated tool for marking emails read/unread
- **Meeting cancellations**: Option to send cancellation notices
- **Attachment info**: Can include attachment details in fetch

## Error Handling

All tools return structured error responses:
```python
{"error": "Description of what went wrong"}
```

Common errors:
- Authentication failures (expired token, missing permissions)
- Invalid folder/calendar names
- API rate limiting
- Network connectivity issues

## Security Notes

- Tokens are cached locally in `outlook_token_cache.json`
- Uses delegated permissions (acts on behalf of the authenticated user)
- Supports both personal and organizational accounts
- Client secret is optional (only needed for confidential apps)

## Troubleshooting

1. **Authentication fails**: Check CLIENT_ID is correct and app registration is properly configured
2. **Permission errors**: Ensure all required Graph API permissions are granted
3. **Token expires**: Delete `outlook_token_cache.json` and re-authenticate
4. **Rate limiting**: Microsoft Graph has rate limits; implement exponential backoff for production use