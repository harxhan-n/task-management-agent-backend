import os
import json
import asyncio
from typing import Dict, Any, List
import google.generativeai as genai
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
    
    def get_context_string(self) -> str:
        """Get conversation history as a formatted string"""
        if not self.messages:
            return ""
        
        context = "Previous conversation:\n"
        for msg in self.messages[-5:]:  # Last 5 messages for context
            context += f"{msg['role'].title()}: {msg['content']}\n"
        return context + "\n"
    
    def clear(self):
        """Clear conversation history"""
        self.messages = []


class SimplifiedTaskAgent:
    """Simplified AI agent using Google Gemini directly without LangChain"""
    
    def __init__(self):
        self.context = ConversationContext()
        self._initialize_gemini()
        self.tools = {
            "create_task": create_task_tool,
            "update_task": update_task_tool,
            "delete_task": delete_task_tool,
            "list_tasks": list_tasks_tool,
            "filter_tasks": filter_tasks_tool
        }
    
    def _initialize_gemini(self):
        """Initialize Google Gemini AI"""
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable is required")
        
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash')
    
    def _get_system_prompt(self) -> str:
        """Get system prompt for the AI agent"""
        return """You are a professional Task Management Assistant powered by Google Gemini AI.

CORE RESPONSIBILITIES:
• Help users create, update, delete, list, and filter tasks efficiently
• Maintain conversation context and refer to previous messages when relevant
• Provide clear, concise responses about task operations
• Always confirm successful operations with specific details
• Guide users on proper task management workflows

AVAILABLE TOOLS:
1. create_task - Creates new tasks (requires: title, optional: description, due_date, priority)
2. update_task - Updates existing tasks (requires: task_identifier, optional: any field to update)
3. delete_task - Deletes tasks (requires: task_identifier)
4. list_tasks - Shows all tasks (optional: limit)
5. filter_tasks - Filters tasks by criteria (optional: status, priority, due_date)

TOOL USAGE INSTRUCTIONS:
- When user wants to create a task, use create_task tool
- When user wants to update/modify a task, use update_task tool
- When user wants to delete a task, use delete_task tool
- When user wants to see tasks, use list_tasks tool
- When user wants to find specific tasks, use filter_tasks tool

RESPONSE FORMAT:
1. Analyze the user's request
2. Determine which tool(s) to use
3. Call the appropriate tool(s)
4. Provide a friendly response based on the tool results

IMPORTANT:
- Always call tools when users request task operations
- Provide clear, helpful responses
- Reference previous conversation when relevant
- Handle errors gracefully

Remember: You're helping users stay organized and productive!"""

    async def process_message(self, user_message: str) -> Dict[str, Any]:
        """Process user message and return response"""
        try:
            # Add user message to context
            self.context.add_message("user", user_message)
            
            # Build the full prompt with context
            context_string = self.context.get_context_string()
            full_prompt = f"""{self._get_system_prompt()}

{context_string}
Current user message: {user_message}

Analyze the user's request and determine if you need to use any tools. If so, respond with:
TOOL_CALL: tool_name(param1="value1", param2="value2")

If multiple tools are needed, use multiple TOOL_CALL lines.

After tool calls (or if no tools needed), provide a helpful response to the user."""

            # Get AI response
            response = self.model.generate_content(full_prompt)
            ai_response = response.text
            
            # Process tool calls in the response
            final_response = await self._process_tool_calls(ai_response, user_message)
            
            # Add assistant response to context
            self.context.add_message("assistant", final_response)
            
            return {
                "response": final_response,
                "success": True,
                "context_length": len(self.context.messages)
            }
            
        except Exception as e:
            error_msg = f"I encountered an error: {str(e)}"
            self.context.add_message("assistant", error_msg)
            
            return {
                "response": error_msg,
                "success": False,
                "context_length": len(self.context.messages)
            }
    
    async def _process_tool_calls(self, ai_response: str, user_message: str) -> str:
        """Process any tool calls in the AI response"""
        lines = ai_response.split('\n')
        tool_results = []
        response_parts = []
        
        for line in lines:
            line = line.strip()
            if line.startswith('TOOL_CALL:'):
                # Extract and execute tool call
                tool_call = line[10:].strip()  # Remove 'TOOL_CALL:'
                result = await self._execute_tool_call(tool_call)
                tool_results.append(result)
            else:
                response_parts.append(line)
        
        # If we have tool results, generate a new response based on them
        if tool_results:
            results_text = "\n".join([str(result) for result in tool_results])
            
            new_prompt = f"""The user asked: "{user_message}"

I executed the following tools and got these results:
{results_text}

Based on these results, provide a helpful, friendly response to the user. Summarize what was accomplished and any relevant details from the tool results."""

            final_response = self.model.generate_content(new_prompt)
            return final_response.text
        else:
            # No tool calls, return the original response
            return '\n'.join(response_parts)
    
    async def _execute_tool_call(self, tool_call: str) -> str:
        """Execute a tool call string"""
        try:
            # Parse tool call (simplified parsing)
            if '(' in tool_call and ')' in tool_call:
                tool_name = tool_call.split('(')[0].strip()
                params_str = tool_call.split('(', 1)[1].rsplit(')', 1)[0]
                
                # Parse parameters (very basic parsing)
                params = {}
                if params_str:
                    # Split by comma and parse key=value pairs
                    for param in params_str.split(','):
                        if '=' in param:
                            key, value = param.split('=', 1)
                            key = key.strip()
                            value = value.strip().strip('"\'')
                            params[key] = value
                
                # Execute the tool
                if tool_name in self.tools:
                    tool_func = self.tools[tool_name]
                    if asyncio.iscoroutinefunction(tool_func.func):
                        result = await tool_func.func(**params)
                    else:
                        result = tool_func.func(**params)
                    return result
                else:
                    return f"Unknown tool: {tool_name}"
            else:
                return f"Invalid tool call format: {tool_call}"
                
        except Exception as e:
            return f"Error executing tool call '{tool_call}': {str(e)}"
    
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


# Session-based agent instances
_session_agents: Dict[str, SimplifiedTaskAgent] = {}

def get_agent(session_id: str = "default") -> SimplifiedTaskAgent:
    """Get an agent instance for a specific session"""
    if session_id not in _session_agents:
        _session_agents[session_id] = SimplifiedTaskAgent()
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
    'SimplifiedTaskAgent', 
    'get_agent', 
    'clear_session_context',
    'remove_session',
    'get_all_sessions'
]