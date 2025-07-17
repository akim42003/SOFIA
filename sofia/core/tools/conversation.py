import os
import json
import glob
from datetime import datetime
from typing import List, Dict, Optional
from openai import OpenAI


def save_conversation(title: str = None, include_tools: bool = False) -> Dict:
    """
    Save the current conversation as a summarized markdown file
    
    Args:
        title: Optional title for the conversation. If not provided, will be auto-generated
        include_tools: Whether to include tool call details in the summary
        
    Returns:
        Dict with status and file path
    """
    try:
        # Import here to avoid circular imports
        from sofia.core.openai_brain import OpenAIChatBrain
        
        # This will be populated by the brain when it calls this function
        # For now, we'll need to pass the messages through the function call
        # We'll modify this approach below
        
        return {
            "status": "error", 
            "message": "This function needs to be called with conversation context"
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to save conversation: {str(e)}"
        }


def _summarize_conversation(messages: List[Dict], client: OpenAI, model: str = "gpt-4o") -> str:
    """
    Summarize conversation using OpenAI API
    
    Args:
        messages: List of conversation messages
        client: OpenAI client instance
        model: Model to use for summarization
        
    Returns:
        Summarized conversation as markdown string
    """
    try:
        # Filter out system messages and tool calls for summarization
        content_messages = []
        for msg in messages:
            if msg.get('role') in ['user', 'assistant'] and msg.get('content'):
                content_messages.append({
                    'role': msg['role'],
                    'content': msg['content']
                })
        
        if not content_messages:
            return "# Empty Conversation\n\nNo meaningful content found in this conversation."
        
        # Create summarization prompt
        summary_prompt = """Please summarize this conversation in a clear, structured markdown format. Include:

1. A brief overview of the main topic(s) discussed
2. Key points or decisions made
3. Any important outcomes or next steps
4. Preserve important details but make it concise

Format as clean markdown with appropriate headers and bullet points. Do not include system messages or technical details about tool calls unless they're relevant to the conversation content.

Here's the conversation to summarize:

"""
        
        # Add conversation history to prompt
        for msg in content_messages:
            role = "**User**" if msg['role'] == 'user' else "**Assistant**"
            summary_prompt += f"\n{role}: {msg['content']}\n"
        
        # Get summary from OpenAI
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a helpful assistant that creates clear, well-structured conversation summaries in markdown format."},
                {"role": "user", "content": summary_prompt}
            ],
            temperature=0.3,
            max_tokens=2000
        )
        
        summary = response.choices[0].message.content
        
        # Add metadata header
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        message_count = len(content_messages)
        
        markdown_content = f"""# Conversation Summary

**Date:** {timestamp}
**Messages:** {message_count}

---

{summary}

---

*This summary was generated automatically by SOFIA.*
"""
        
        return markdown_content
        
    except Exception as e:
        return f"# Conversation Summary\n\n**Error:** Failed to generate summary: {str(e)}"


def _save_markdown_file(content: str, title: str = None) -> str:
    """
    Save markdown content to file
    
    Args:
        content: Markdown content to save
        title: Optional title for filename
        
    Returns:
        File path where content was saved
    """
    # Create conversations directory if it doesn't exist
    conversations_dir = os.path.expanduser("~/SOFIA/conversations")
    os.makedirs(conversations_dir, exist_ok=True)
    
    # Generate filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    if title:
        # Clean title for filename
        clean_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).rstrip()
        clean_title = clean_title.replace(' ', '_')[:50]  # Limit length
        filename = f"{timestamp}_{clean_title}.md"
    else:
        filename = f"conversation_{timestamp}.md"
    
    file_path = os.path.join(conversations_dir, filename)
    
    # Save file
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    return file_path


def load_conversations(query: str = None, max_results: int = 10) -> Dict:
    """
    Load and search through saved conversation summaries
    
    Args:
        query: Optional search query to filter conversations by content
        max_results: Maximum number of conversations to return
        
    Returns:
        Dict with conversation summaries and metadata
    """
    try:
        conversations_dir = os.path.expanduser("~/SOFIA/conversations")
        
        # Check if conversations directory exists
        if not os.path.exists(conversations_dir):
            return {
                "status": "success",
                "conversations": [],
                "message": "No conversations directory found. No conversations have been saved yet."
            }
        
        # Get all markdown files in conversations directory
        pattern = os.path.join(conversations_dir, "*.md")
        conversation_files = glob.glob(pattern)
        
        if not conversation_files:
            return {
                "status": "success", 
                "conversations": [],
                "message": "No conversation files found in the conversations directory."
            }
        
        # Sort files by modification time (most recent first)
        conversation_files.sort(key=os.path.getmtime, reverse=True)
        
        conversations = []
        for file_path in conversation_files[:max_results * 2]:  # Load extra in case filtering removes some
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Extract metadata from filename and content
                filename = os.path.basename(file_path)
                modified_time = datetime.fromtimestamp(os.path.getmtime(file_path))
                
                # Parse title from filename (format: timestamp_title.md or conversation_timestamp.md)
                if filename.startswith('conversation_'):
                    title = "Untitled Conversation"
                else:
                    # Extract title from filename
                    parts = filename.replace('.md', '').split('_', 1)
                    if len(parts) > 1:
                        title = parts[1].replace('_', ' ').title()
                    else:
                        title = "Untitled Conversation"
                
                # Extract preview from content (first few lines after headers)
                lines = content.split('\n')
                preview = ""
                for line in lines[10:]:  # Skip metadata headers
                    if line.strip() and not line.startswith('#') and not line.startswith('**') and not line.startswith('---'):
                        preview = line.strip()[:200] + "..." if len(line.strip()) > 200 else line.strip()
                        break
                
                conversation_data = {
                    "filename": filename,
                    "title": title,
                    "date": modified_time.strftime("%Y-%m-%d %H:%M:%S"),
                    "preview": preview,
                    "file_path": file_path,
                    "content": content if not query else content  # Include full content for searching
                }
                
                # Filter by query if provided
                if query:
                    query_lower = query.lower()
                    searchable_text = f"{title} {preview} {content}".lower()
                    if query_lower in searchable_text:
                        conversations.append(conversation_data)
                else:
                    conversations.append(conversation_data)
                
                # Stop if we have enough results
                if len(conversations) >= max_results:
                    break
                    
            except Exception as e:
                # Skip files that can't be read
                continue
        
        # Remove full content from response to keep it manageable
        for conv in conversations:
            conv.pop('content', None)
        
        return {
            "status": "success",
            "conversations": conversations,
            "total_found": len(conversations),
            "message": f"Found {len(conversations)} conversation(s)" + (f" matching '{query}'" if query else "")
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to load conversations: {str(e)}"
        }


def get_conversation_content(filename: str) -> Dict:
    """
    Get the full content of a specific conversation file
    
    Args:
        filename: Name of the conversation file to retrieve
        
    Returns:
        Dict with conversation content
    """
    try:
        conversations_dir = os.path.expanduser("~/SOFIA/conversations")
        file_path = os.path.join(conversations_dir, filename)
        
        if not os.path.exists(file_path):
            return {
                "status": "error",
                "message": f"Conversation file '{filename}' not found."
            }
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        return {
            "status": "success",
            "filename": filename,
            "content": content,
            "message": f"Successfully loaded conversation '{filename}'"
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to load conversation: {str(e)}"
        }