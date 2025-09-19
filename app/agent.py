import os
from typing import Dict, Any, List
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.prebuilt import create_react_agent
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from dotenv import load_dotenv
from .tools import (
    create_task_tool,
    update_task_tool, 
    delete_task_tool,
    list_tasks_tool,
    filter_tasks_tool
)

# Load environment variables
load_dotenv()


class ConversationContext:
    """Manages conversation history for context awareness"""
    
    def __init__(self, max_history: int = 10):
        self.messages: List[Dict[str, Any]] = []
        self.max_history = max_history
        self.last_task_mentioned = None  # Track the most recent task for context updates
    
    def add_message(self, role: str, content: str, task_info: Dict = None):
        """Add a message to conversation history"""
        self.messages.append({
            "role": role,
            "content": content,
            "timestamp": "now",
            "task_info": task_info
        })
        
        # Update last mentioned task if provided
        if task_info and "title" in task_info:
            self.last_task_mentioned = task_info
        
        # Keep only recent messages to avoid token limits
        if len(self.messages) > self.max_history:
            self.messages = self.messages[-self.max_history:]
    
    def get_context_messages(self) -> List:
        """Convert conversation history to LangChain messages"""
        langchain_messages = []
        
        for msg in self.messages:
            if msg["role"] == "user":
                langchain_messages.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "assistant":
                langchain_messages.append(AIMessage(content=msg["content"]))
        
        return langchain_messages
    
    def clear(self):
        """Clear conversation history"""
        self.messages = []


class TaskManagementAgent:
    """LangGraph + Gemini agent with conversation context awareness"""
    
    def __init__(self):
        self.llm = self._initialize_llm()
        self.tools = [
            create_task_tool,
            update_task_tool,
            delete_task_tool,
            list_tasks_tool,
            filter_tasks_tool
        ]
        self.agent = self._create_langgraph_agent()
        self.context = ConversationContext()
    
    def _initialize_llm(self) -> ChatGoogleGenerativeAI:
        """Initialize the Gemini LLM as specified in requirements"""
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable is required")
        
        return ChatGoogleGenerativeAI(
            model="gemini-1.5-flash",
            google_api_key=api_key,
            temperature=0.1,
            max_tokens=1000
        )
    
    def _create_langgraph_agent(self):
        """Create LangGraph agent with tools as per requirements"""
        # Use the simple create_react_agent API (compatible with current LangGraph versions)
        return create_react_agent(
            model=self.llm,
            tools=self.tools
        )
    
    def _get_system_instructions(self) -> str:
        """Get comprehensive system instructions for the agent"""
        
        # Include context about the last mentioned task
        last_task_context = ""
        if self.context.last_task_mentioned:
            last_task_context = f"\n\nCONTEXT - LAST MENTIONED TASK:\nTitle: {self.context.last_task_mentioned.get('title', 'Unknown')}\nID: {self.context.last_task_mentioned.get('id', 'Unknown')}\nStatus: {self.context.last_task_mentioned.get('status', 'Unknown')}\n"
        
        return f"""You are a professional Task Management Assistant powered by LangGraph and Google Gemini.{last_task_context}

CORE RESPONSIBILITIES:
• Help users create, update, delete, list, and filter tasks efficiently
• Maintain conversation context and refer to previous messages when relevant
• Provide clear, concise responses about task operations
• Always confirm successful operations with specific details
• Guide users on proper task management workflows
• Handle task identification robustly to avoid null/empty field errors

CONTEXT AWARENESS:
• You have access to previous messages in our conversation
• Reference previous context when users say "those tasks", "the one I mentioned", etc.
• If a user asks a follow-up question, consider the previous context
• Use phrases like "from the tasks I just listed" or "as mentioned earlier" when appropriate

AVAILABLE TOOLS & USAGE:
1. create_task_tool: Creates new tasks
   - Required: title (must not be empty)
   - Optional: description, due_date (YYYY-MM-DD format), priority (low/medium/high)
   - Example: "Create a high priority task to review code with due date 2025-09-25"

2. update_task_tool: Updates existing tasks
   - Required: task_identifier (ID or title - be specific)
   - Optional: Any field to update (status, title, description, priority, due_date)
   - Example: "Mark task 'Review code' as done" or "Update task #5 status to in_progress"
   - IMPORTANT: When updating status, use exact values: 'pending', 'in_progress', 'done'
   - IMPORTANT: For priorities, use exact values: 'low', 'medium', 'high'

3. delete_task_tool: Removes tasks
   - Required: task_identifier (ID or title - be specific)
   - Example: "Delete task 'Old meeting notes'"

4. list_tasks_tool: Shows all tasks
   - Optional: limit (default 20)
   - Example: "Show me all my tasks" or "List 5 recent tasks"

5. filter_tasks_tool: Filters tasks by criteria
   - Optional: status (pending/in_progress/done), priority (low/medium/high), due_date
   - Example: "Show high priority tasks" or "Find pending tasks due today"

TASK IDENTIFICATION BEST PRACTICES:
• When updating/deleting tasks, use exact titles or ID numbers
• If user says "mark it as done", ask which specific task they mean
• If user mentions "the task I just created", refer to the most recent task from context
• Always verify task exists before attempting operations
• If task not found, suggest showing all tasks to help user identify the correct one

ERROR HANDLING:
• If you encounter "null value" or "title field" errors, it means:
  - You're trying to update a task that doesn't exist, OR
  - You're passing empty/null values where required fields are needed
• Solution: Always provide specific task identifiers and valid field values
• If unsure about task identity, list tasks first to help user identify the right one

RESPONSE GUIDELINES:
• Always use the appropriate tool for user requests
• Provide clear confirmation of what was accomplished
• For task creation/updates, mention the task title and new status
• For lists, summarize the count and key details
• If unclear what the user wants, ask for clarification
• Be helpful and proactive in suggesting task management best practices
• Reference previous conversation when relevant
• If errors occur, explain the issue and suggest solutions

PROACTIVE TASK ENHANCEMENT:
• When a user creates a basic task (only title), after successful creation, offer to enhance it:
  - "Task created successfully! Would you like to add a description or due date to make it more detailed?"
  - "I've created the task. Would you like to set a priority (high/medium/low) or add a due date?"
• Be context-aware - don't ask for details the user already provided
• Make suggestions based on task type:
  - Work-related tasks: suggest high/medium priority and due dates
  - Personal tasks: suggest descriptions for clarity
  - Meeting/event tasks: always suggest due dates
• Keep enhancement suggestions brief and natural

INTERACTION PATTERNS:
• "Create task..." → Use create_task_tool, then offer enhancements if basic
• "Add task..." → Use create_task_tool, then suggest missing details
• "Mark as done..." → Use update_task_tool with status='done'
• "Update..." → Use update_task_tool
• "Delete..." → Use delete_task_tool
• "Show/List..." → Use list_tasks_tool
• "Find/Filter..." → Use filter_tasks_tool
• "From those..." → Reference previous context + appropriate tool
• "Is there any..." → Check against previous context if relevant

CRITICAL CONTEXT AWARENESS RULES:
• "Add description/Add the description" → ALWAYS UPDATE existing task, never create new one
• "Set priority/Add priority" → ALWAYS UPDATE existing task, never create new one
• "Add due date/Set due date" → ALWAYS UPDATE existing task, never create new one
• When user says "add X" without "task" keyword → UPDATE the most recently mentioned task
• When user says "add task X" → CREATE new task
• If unclear which task to update, ask for clarification or show task list
• NEVER create duplicate tasks when user wants to enhance existing ones

BULK OPERATIONS INTELLIGENCE:
• "Delete all", "Remove all", "Clear all tasks" → Use multiple delete_task_tool calls
• "Mark all as done", "Complete all tasks" → Use multiple update_task_tool calls  
• "Delete completed tasks" → Filter then delete matching tasks
• "Remove pending tasks" → Filter then delete by status
• Handle bulk operations by:
  1. First use list_tasks_tool or filter_tasks_tool to get target tasks
  2. Then perform the operation on each task individually
  3. Provide summary of bulk operation results

SMART QUERY INTERPRETATION:
• "all", "everything", "all tasks" → Apply operation to all existing tasks
• "completed", "done tasks" → Filter by status='done' first
• "pending tasks" → Filter by status='pending' first  
• "high priority" → Filter by priority='high' first
• Always confirm bulk operations before executing
• Provide clear feedback on how many items were affected

INTUITIVE ENHANCEMENT EXAMPLES:
• User: "Create task buy groceries"
  → Create task, then: "Task created! Would you like to add a due date (like today or tomorrow) or specify what groceries you need in the description?"

• User: "Add task meeting with client"
  → Create task, then: "Meeting task created! Should I set this as high priority and would you like to add the meeting date/time?"

• User: "Create task review code"
  → Create task, then: "Code review task added! Would you like to set a due date or specify which code/project needs reviewing?"

SMART SUGGESTIONS BASED ON KEYWORDS:
• Tasks with "meeting", "call", "appointment" → Always suggest due date/time
• Tasks with "urgent", "important", "asap" → Suggest high priority
• Tasks with "buy", "purchase", "get" → Suggest description for details
• Tasks with "review", "check", "analyze" → Suggest due date and description
• Work-related keywords → Suggest priority and due date
• Personal keywords ("clean", "organize") → Suggest description

Remember: You're helping users stay organized and productive. Always be encouraging, efficient, and context-aware! When in doubt about task identification, show the task list first."""

    async def process_message(self, user_message: str) -> Dict[str, Any]:
        """Process user message with conversation context"""
        try:
            # Add user message to context
            self.context.add_message("user", user_message)
            
            # Build messages with context
            messages = [SystemMessage(content=self._get_system_instructions())]
            
            # Add conversation history for context
            context_messages = self.context.get_context_messages()
            messages.extend(context_messages)
            
            # Process with LangGraph agent
            result = await self.agent.ainvoke({
                "messages": messages
            })
            
            # Extract response
            response_message = result["messages"][-1].content if result["messages"] else "I processed your request."
            
            # Clean up response message - remove raw data formatting
            response_message = self._clean_agent_response(response_message)
            
            # Extract task information from agent results for context tracking
            task_info = await self._extract_task_from_result(result)
            
            # Add assistant response to context with task info
            self.context.add_message("assistant", response_message, task_info)
            
            # Extract task updates for WebSocket notifications
            task_updates = []
            
            # Extract structured data for frontend display
            data_to_show = await self._extract_display_data(user_message, response_message, result)
            
            # Extract display format from data_to_show if present
            data_format = None
            if data_to_show:
                # Get the display format from the first item (assuming all items have the same format)
                data_format = data_to_show[0].get("display_format")
                # Remove display_format from individual items since it's now at the top level
                for item in data_to_show:
                    item.pop("display_format", None)
            
            return {
                "response": response_message,
                "task_updates": task_updates,
                "data_to_show": data_to_show,
                "data_format": data_format,
                "success": True,
                "context_length": len(self.context.messages)
            }
            
        except Exception as e:
            error_msg = f"I encountered an error: {str(e)}"
            self.context.add_message("assistant", error_msg)
            
            return {
                "response": error_msg,
                "task_updates": [],
                "data_to_show": [],
                "data_format": None,
                "success": False,
                "context_length": len(self.context.messages)
            }

    def _clean_agent_response(self, response: str) -> str:
        """Clean up agent response by removing raw data formatting and improving readability"""
        import re
        
        # Remove bullet points with IDs like "• ••ID: 1••"
        response = re.sub(r'•\s*••ID:\s*\d+••', '', response)
        
        # Clean up raw field listings like "Title: string. Status: pending."
        response = re.sub(r'Title:\s*string\.?\s*', '', response)
        response = re.sub(r'Description:\s*string\.?\s*', '', response)
        
        # Replace technical status terms with user-friendly language
        response = re.sub(r'Status:\s*pending', 'Status: To Do', response)
        response = re.sub(r'Status:\s*in_progress', 'Status: In Progress', response)
        response = re.sub(r'Status:\s*done', 'Status: Completed', response)
        
        # Clean up priority formatting
        response = re.sub(r'Priority:\s*low', 'Priority: Low', response)
        response = re.sub(r'Priority:\s*medium', 'Priority: Medium', response)
        response = re.sub(r'Priority:\s*high', 'Priority: High', response)
        
        # Remove excessive dots and clean up formatting
        response = re.sub(r'\.{2,}', '.', response)
        response = re.sub(r'\s+', ' ', response)
        response = response.strip()
        
        # If response is still very technical or empty, provide a friendly fallback
        if len(response) < 10 or 'string' in response.lower() or not response:
            response = "I've processed your request successfully!"
        
        return response

    async def _extract_task_from_result(self, agent_result: Dict) -> Dict:
        """Extract task information from agent results for context tracking"""
        import json
        import re
        
        try:
            if "messages" in agent_result:
                for message in agent_result["messages"]:
                    if hasattr(message, 'content') and isinstance(message.content, str):
                        # Try to parse JSON from tool results
                        json_matches = re.findall(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', message.content)
                        
                        for json_str in json_matches:
                            try:
                                tool_result = json.loads(json_str)
                                
                                # Look for task in results
                                if "task" in tool_result and isinstance(tool_result["task"], dict):
                                    task = tool_result["task"]
                                    return {
                                        "id": task.get("id"),
                                        "title": task.get("title"),
                                        "status": task.get("status"),
                                        "priority": task.get("priority")
                                    }
                                    
                            except json.JSONDecodeError:
                                continue
                                
        except Exception:
            pass
            
        return None

    async def _extract_display_data(self, user_message: str, response_message: str, agent_result: Dict) -> List[Dict]:
        """Extract structured data for frontend display from agent results"""
        import json
        import re
        
        data_to_show = []
        
        try:
            # Check if agent used any tools and extract their results
            if "messages" in agent_result:
                for message in agent_result["messages"]:
                    # Look for tool call results in the agent's execution
                    if hasattr(message, 'additional_kwargs') and 'tool_calls' in message.additional_kwargs:
                        continue  # This is a tool call, not a result
                    
                    # Check if this is a tool result message
                    if hasattr(message, 'content') and isinstance(message.content, str):
                        # Try to parse JSON from tool results
                        json_matches = re.findall(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', message.content)
                        
                        for json_str in json_matches:
                            try:
                                tool_result = json.loads(json_str)
                                
                                # Handle list_tasks_tool results
                                if "tasks" in tool_result and isinstance(tool_result["tasks"], list):
                                    data_to_show.extend(self._format_tasks_for_display(tool_result["tasks"], "table"))
                                
                                # Handle single task results (create, update, get)
                                elif "task" in tool_result and isinstance(tool_result["task"], dict):
                                    data_to_show.append(self._format_single_task_for_display(tool_result["task"], "card"))
                                
                                # Handle filter results
                                elif "count" in tool_result and "tasks" in tool_result:
                                    data_to_show.extend(self._format_tasks_for_display(tool_result["tasks"], "table"))
                                    
                            except json.JSONDecodeError:
                                continue
            
            # Fallback: Detect display intent from user message
            if not data_to_show:
                data_to_show = await self._detect_display_intent(user_message, response_message)
            
        except Exception as e:
            # If extraction fails, return empty array - frontend will use text response
            pass
            
        return data_to_show

    def _format_tasks_for_display(self, tasks: List[Dict], display_type: str = "table") -> List[Dict]:
        """Format task list for frontend table display"""
        formatted_tasks = []
        
        for task in tasks:
            formatted_task = {
                "type": "task",
                "display_format": display_type,
                "data": {
                    "id": task.get("id"),
                    "title": task.get("title"),
                    "description": task.get("description"),
                    "status": task.get("status"),
                    "priority": task.get("priority"),
                    "due_date": task.get("due_date"),
                    "created_at": task.get("created_at"),
                    "updated_at": task.get("updated_at")
                }
            }
            formatted_tasks.append(formatted_task)
            
        return formatted_tasks

    def _format_single_task_for_display(self, task: Dict, display_type: str = "card") -> Dict:
        """Format single task for frontend card display"""
        return {
            "type": "task",
            "display_format": display_type,
            "data": {
                "id": task.get("id"),
                "title": task.get("title"),
                "description": task.get("description"),
                "status": task.get("status"),
                "priority": task.get("priority"),
                "due_date": task.get("due_date"),
                "created_at": task.get("created_at"),
                "updated_at": task.get("updated_at")
            }
        }

    async def _detect_display_intent(self, user_message: str, response_message: str) -> List[Dict]:
        """Detect if user wants structured data display based on message content"""
        # Keywords that suggest user wants to see task lists
        list_keywords = ["show", "list", "all tasks", "my tasks", "tasks", "what are", "display"]
        
        user_lower = user_message.lower()
        if any(keyword in user_lower for keyword in list_keywords):
            # User likely wants to see tasks - try to get them
            try:
                from .crud import get_tasks
                from .db import AsyncSessionLocal
                
                async with AsyncSessionLocal() as db:
                    tasks = await get_tasks(db, limit=20)
                    if tasks:
                        task_dicts = []
                        for task in tasks:
                            task_dicts.append({
                                "id": task.id,
                                "title": task.title,
                                "description": task.description,
                                "status": task.status,
                                "priority": task.priority,
                                "due_date": task.due_date.isoformat() if task.due_date else None,
                                "created_at": task.created_at.isoformat() if task.created_at else None,
                                "updated_at": task.updated_at.isoformat() if task.updated_at else None
                            })
                        return self._format_tasks_for_display(task_dicts, "table")
            except:
                pass
        
        return []

    def _detect_task_action(self, task: Dict) -> str:
        """Detect what action was performed on the task"""
        # This could be enhanced to track the actual action performed
        return "view"  # Default action

    def clear_context(self):
        """Clear conversation context"""
        self.context.clear()
    
    def get_context_summary(self) -> Dict[str, Any]:
        """Get summary of current conversation context"""
        return {
            "message_count": len(self.context.messages),
            "recent_messages": self.context.messages[-3:] if self.context.messages else [],
            "max_history": self.context.max_history
        }


# Session-based agent instances for maintaining separate conversations
_session_agents: Dict[str, TaskManagementAgent] = {}

def get_agent(session_id: str = "default") -> TaskManagementAgent:
    """Get an agent instance for a specific session (with context)"""
    if session_id not in _session_agents:
        _session_agents[session_id] = TaskManagementAgent()
    return _session_agents[session_id]

def clear_session_context(session_id: str):
    """Clear context for a specific session"""
    if session_id in _session_agents:
        _session_agents[session_id].clear_context()

def remove_session(session_id: str):
    """Remove a session completely"""
    if session_id in _session_agents:
        del _session_agents[session_id]

def get_all_sessions() -> List[str]:
    """Get all active session IDs"""
    return list(_session_agents.keys())

__all__ = [
    'TaskManagementAgent', 
    'get_agent', 
    'clear_session_context',
    'remove_session',
    'get_all_sessions'
]