import os
from typing import Dict, Any, List, Annotated
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict
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


class AgentState(TypedDict):
    """State for the LangGraph agent"""
    messages: Annotated[List[HumanMessage | AIMessage | SystemMessage], add_messages]


class ConversationContext:
    """Manages conversation history for context awareness"""
    
    def __init__(self, max_history: int = 10):
        self.messages: List[Dict[str, Any]] = []
        self.max_history = max_history
    
    def add_message(self, role: str, content: str):
        """Add a message to conversation history"""
        self.messages.append({
            "role": role,
            "content": content,
            "timestamp": "now"
        })
        
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
        """Create LangGraph agent manually to avoid input_schema issues"""
        # Bind tools to the LLM
        llm_with_tools = self.llm.bind_tools(self.tools)
        
        def agent_node(state: AgentState):
            """Main agent reasoning node"""
            # Add system message if not present
            messages = state["messages"]
            if not messages or not isinstance(messages[0], SystemMessage):
                system_msg = SystemMessage(content=self._get_system_instructions())
                messages = [system_msg] + messages
            
            response = llm_with_tools.invoke(messages)
            return {"messages": [response]}
        
        def should_continue(state: AgentState):
            """Decide whether to continue or end"""
            last_message = state["messages"][-1]
            if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
                return "tools"
            return END
        
        def tool_node(state: AgentState):
            """Execute tools"""
            last_message = state["messages"][-1]
            tool_responses = []
            
            if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
                for tool_call in last_message.tool_calls:
                    tool_name = tool_call["name"]
                    tool_args = tool_call["args"]
                    
                    # Find and execute the tool
                    for tool in self.tools:
                        if tool.name == tool_name:
                            try:
                                if hasattr(tool, 'func'):
                                    result = tool.func(**tool_args)
                                else:
                                    result = tool(**tool_args)
                                tool_responses.append(AIMessage(content=str(result)))
                            except Exception as e:
                                tool_responses.append(AIMessage(content=f"Error: {str(e)}"))
                            break
            
            return {"messages": tool_responses}
        
        # Build the graph
        workflow = StateGraph(AgentState)
        
        # Add nodes
        workflow.add_node("agent", agent_node)
        workflow.add_node("tools", tool_node)
        
        # Set entry point
        workflow.set_entry_point("agent")
        
        # Add conditional edges
        workflow.add_conditional_edges(
            "agent",
            should_continue,
            {
                "tools": "tools",
                END: END
            }
        )
        
        # Add edge from tools back to agent
        workflow.add_edge("tools", "agent")
        
        return workflow.compile()
    
    def _get_system_instructions(self) -> str:
        """Get comprehensive system instructions for the agent"""
        return """You are a professional Task Management Assistant powered by LangGraph and Google Gemini.

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
            context_messages = self.context.get_context_messages()
            
            # Create the initial state
            initial_state = {
                "messages": context_messages + [HumanMessage(content=user_message)]
            }
            
            # Run the agent
            result = await self.agent.ainvoke(initial_state)
            
            # Extract response from the last AI message
            response_message = "I processed your request."
            for msg in reversed(result["messages"]):
                if isinstance(msg, AIMessage) and not hasattr(msg, 'tool_calls'):
                    response_message = msg.content
                    break
            
            # Add assistant response to context
            self.context.add_message("assistant", response_message)
            
            return {
                "response": response_message,
                "task_updates": [],
                "data_to_show": [],
                "data_format": None,
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