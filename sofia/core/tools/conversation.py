import os
import json
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