import re
from datetime import datetime
from typing import Optional


def parse_natural_date(date_string: str) -> Optional[datetime]:
    """Parse natural language date strings into datetime objects"""
    if not date_string:
        return None
    
    date_string = date_string.lower().strip()
    
    # Handle relative dates
    if "today" in date_string:
        return datetime.now().replace(hour=23, minute=59, second=59)
    
    if "tomorrow" in date_string:
        from datetime import timedelta
        return (datetime.now() + timedelta(days=1)).replace(hour=23, minute=59, second=59)
    
    # Handle "in X days"
    days_match = re.search(r'in (\d+) days?', date_string)
    if days_match:
        days = int(days_match.group(1))
        from datetime import timedelta
        return (datetime.now() + timedelta(days=days)).replace(hour=23, minute=59, second=59)
    
    # Try to parse ISO format
    try:
        if 'T' in date_string:
            return datetime.fromisoformat(date_string.replace('Z', '+00:00'))
        else:
            return datetime.fromisoformat(date_string + 'T23:59:59')
    except ValueError:
        pass
    
    return None


def extract_task_identifier(text: str) -> Optional[str]:
    """Extract task identifier (ID or title) from natural language text"""
    text = text.strip()
    
    # Check if it's a number (task ID)
    if text.isdigit():
        return text
    
    # Look for patterns like "task 5" or "task #5"
    id_match = re.search(r'task\s*#?(\d+)', text, re.IGNORECASE)
    if id_match:
        return id_match.group(1)
    
    # Remove common prefixes and return as title
    prefixes = ['task', 'the task', 'my task', 'task called', 'task titled']
    for prefix in prefixes:
        if text.lower().startswith(prefix):
            return text[len(prefix):].strip()
    
    return text


def parse_priority(text: str) -> str:
    """Parse priority from natural language text"""
    text = text.lower()
    
    if any(word in text for word in ['urgent', 'critical', 'asap', 'important', 'high']):
        return 'high'
    elif any(word in text for word in ['low', 'minor', 'sometime', 'eventually']):
        return 'low'
    else:
        return 'medium'


def parse_status_update(text: str) -> Optional[str]:
    """Parse status updates from natural language"""
    text = text.lower()
    
    if any(phrase in text for phrase in ['mark as done', 'complete', 'finished', 'mark done', 'set to done']):
        return 'done'
    elif any(phrase in text for phrase in ['start', 'begin', 'working on', 'in progress', 'mark as started']):
        return 'in_progress'
    elif any(phrase in text for phrase in ['pending', 'todo', 'not started', 'mark as pending']):
        return 'pending'
    
    return None


def clean_text(text: str) -> str:
    """Clean and normalize text"""
    if not text:
        return ""
    
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text.strip())
    
    # Remove special characters but keep basic punctuation
    text = re.sub(r'[^\w\s\-.,!?]', '', text)
    
    return text


def format_task_summary(tasks: list) -> str:
    """Format a list of tasks into a readable summary"""
    if not tasks:
        return "No tasks found."
    
    summary = f"Found {len(tasks)} task{'s' if len(tasks) > 1 else ''}:\n"
    
    for i, task in enumerate(tasks, 1):
        status_emoji = {
            'pending': '⏳',
            'in_progress': '🔄',
            'done': '✅'
        }.get(task.get('status', 'pending'), '⏳')
        
        priority_indicator = {
            'high': '🔴',
            'medium': '🟡',
            'low': '🟢'
        }.get(task.get('priority', 'medium'), '🟡')
        
        due_date = ""
        if task.get('due_date'):
            try:
                due = datetime.fromisoformat(task['due_date'].replace('Z', '+00:00'))
                due_date = f" (Due: {due.strftime('%Y-%m-%d')})"
            except:
                pass
        
        summary += f"{i}. {status_emoji} {priority_indicator} {task.get('title', 'Untitled')}{due_date}\n"
        
        if task.get('description'):
            description = task['description'][:100] + ('...' if len(task['description']) > 100 else '')
            summary += f"   Description: {description}\n"
    
    return summary.strip()


def validate_task_data(task_data: dict) -> tuple[bool, str]:
    """Validate task data and return (is_valid, error_message)"""
    if not task_data.get('title') or not task_data['title'].strip():
        return False, "Task title is required"
    
    if len(task_data['title']) > 200:
        return False, "Task title must be 200 characters or less"
    
    if task_data.get('description') and len(task_data['description']) > 1000:
        return False, "Task description must be 1000 characters or less"
    
    valid_statuses = ['pending', 'in_progress', 'done']
    if task_data.get('status') and task_data['status'] not in valid_statuses:
        return False, f"Status must be one of: {', '.join(valid_statuses)}"
    
    valid_priorities = ['low', 'medium', 'high']
    if task_data.get('priority') and task_data['priority'] not in valid_priorities:
        return False, f"Priority must be one of: {', '.join(valid_priorities)}"
    
    return True, ""