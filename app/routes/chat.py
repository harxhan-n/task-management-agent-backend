import json
import asyncio
import uuid
from typing import Dict, Set
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import JSONResponse
from ..schemas import ChatMessage, ChatResponse
from ..agent import get_agent, clear_session_context, remove_session

router = APIRouter(prefix="/chat", tags=["chat"])

# WebSocket connection manager with session support
class ConnectionManager:
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
        self.chat_connections: Dict[str, WebSocket] = {}  # session_id -> websocket
        self.task_connections: Set[WebSocket] = set()
        self.websocket_sessions: Dict[WebSocket, str] = {}  # websocket -> session_id

    async def connect_chat(self, websocket: WebSocket, session_id: str = None):
        await websocket.accept()
        if not session_id:
            session_id = str(uuid.uuid4())
        
        self.active_connections.add(websocket)
        self.chat_connections[session_id] = websocket
        self.websocket_sessions[websocket] = session_id
        
        return session_id

    async def connect_tasks(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)
        self.task_connections.add(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.discard(websocket)
        self.task_connections.discard(websocket)
        
        # Handle chat session cleanup
        if websocket in self.websocket_sessions:
            session_id = self.websocket_sessions[websocket]
            if session_id in self.chat_connections:
                del self.chat_connections[session_id]
            del self.websocket_sessions[websocket]
            
            # Optionally clear session context (or keep it for reconnection)
            # clear_session_context(session_id)
        self.task_connections.discard(websocket)

    async def broadcast_to_chat(self, message: dict):
        disconnected = set()
        for session_id, connection in self.chat_connections.items():
            try:
                await connection.send_text(json.dumps(message))
            except:
                disconnected.add(connection)
        
        # Remove disconnected connections
        for connection in disconnected:
            self.disconnect(connection)

    async def broadcast_task_updates(self, tasks: list):
        disconnected = set()
        message = {
            "type": "task_update",
            "data": {"tasks": tasks}
        }
        
        for connection in self.task_connections:
            try:
                await connection.send_text(json.dumps(message))
            except:
                disconnected.add(connection)
        
        # Remove disconnected connections
        for connection in disconnected:
            self.disconnect(connection)

# Global connection manager
manager = ConnectionManager()


@router.post("/", response_model=ChatResponse)
async def chat_with_agent(message: ChatMessage):
    """Send a message to the AI agent"""
    try:
        agent = get_agent()
        result = await agent.process_message(message.message)
        
        # Get updated tasks to broadcast
        from .. import crud
        from ..db import AsyncSessionLocal
        
        async with AsyncSessionLocal() as db:
            all_tasks = await crud.get_tasks(db, limit=100)
            tasks_data = []
            for task in all_tasks:
                tasks_data.append({
                    "id": task.id,
                    "title": task.title,
                    "description": task.description,
                    "status": task.status,
                    "priority": task.priority,
                    "due_date": task.due_date.isoformat() if task.due_date else None,
                    "created_at": task.created_at.isoformat() if task.created_at else None,
                    "updated_at": task.updated_at.isoformat() if task.updated_at else None
                })
            
            # Broadcast updated tasks to all task listeners
            await manager.broadcast_task_updates(tasks_data)
        
        # Include structured data for frontend display
        return ChatResponse(
            response=result["response"],
            task_updates=tasks_data,
            data_to_show=result.get("data_to_show", []),
            data_format=result.get("data_format")
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing message: {str(e)}")


@router.websocket("/ws")
async def websocket_chat_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time chat with context awareness"""
    # Connect and get session ID
    session_id = await manager.connect_chat(websocket)
    
    try:
        # Send welcome message with session info
        await websocket.send_text(json.dumps({
            "type": "connection",
            "data": {
                "message": "Connected to Task Management Assistant! 🎉",
                "session_id": session_id,
                "features": ["Context-aware conversation", "Task management", "Real-time updates"]
            }
        }))
        
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            
            try:
                message_data = json.loads(data)
                user_message = message_data.get("message", "")
                
                if not user_message:
                    await websocket.send_text(json.dumps({
                        "type": "error",
                        "data": {"message": "Message is required"}
                    }))
                    continue
                
                # Process with context-aware agent for this session
                agent = get_agent(session_id)
                result = await agent.process_message(user_message)
                
                # Get updated tasks to broadcast
                from .. import crud
                from ..db import AsyncSessionLocal
                
                async with AsyncSessionLocal() as db:
                    all_tasks = await crud.get_tasks(db, limit=100)
                    tasks_data = []
                    for task in all_tasks:
                        tasks_data.append({
                            "id": task.id,
                            "title": task.title,
                            "description": task.description,
                            "status": task.status,
                            "priority": task.priority,
                            "due_date": task.due_date.isoformat() if task.due_date else None,
                            "created_at": task.created_at.isoformat() if task.created_at else None,
                            "updated_at": task.updated_at.isoformat() if task.updated_at else None
                        })
                    
                    # Broadcast updated tasks to all task listeners
                    await manager.broadcast_task_updates(tasks_data)
                
                # Send response back to client
                response_message = {
                    "type": "chat_response",
                    "data": {
                        "response": result["response"],
                        "task_updates": tasks_data
                    }
                }
                
                await websocket.send_text(json.dumps(response_message))
                
            except json.JSONDecodeError:
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "data": {"message": "Invalid JSON format"}
                }))
            
            except Exception as e:
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "data": {"message": f"Error processing message: {str(e)}"}
                }))
    
    except WebSocketDisconnect:
        manager.disconnect(websocket)


@router.websocket("/ws/tasks")
async def websocket_tasks_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time task updates"""
    await manager.connect_tasks(websocket)
    
    try:
        # Send initial connection confirmation
        await websocket.send_text(json.dumps({
            "type": "connection",
            "data": {"message": "Connected to task updates"}
        }))
        
        # Send initial tasks
        try:
            from .. import crud
            from ..db import AsyncSessionLocal
            
            async with AsyncSessionLocal() as db:
                all_tasks = await crud.get_tasks(db, limit=100)
                tasks_data = []
                for task in all_tasks:
                    tasks_data.append({
                        "id": task.id,
                        "title": task.title,
                        "description": task.description,
                        "status": task.status,
                        "priority": task.priority,
                        "due_date": task.due_date.isoformat() if task.due_date else None,
                        "created_at": task.created_at.isoformat() if task.created_at else None,
                        "updated_at": task.updated_at.isoformat() if task.updated_at else None
                    })
                
                # Send initial tasks to this connection
                initial_message = {
                    "type": "task_update",
                    "data": {"tasks": tasks_data}
                }
                await websocket.send_text(json.dumps(initial_message))
                
        except Exception as e:
            print(f"Error sending initial tasks: {e}")
            # Send empty array if there's an error
            await websocket.send_text(json.dumps({
                "type": "task_update",
                "data": {"tasks": []}
            }))
        
        # Keep connection alive
        while True:
            # Wait for ping/pong or other control messages
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
                # Echo back any ping messages
                if data == "ping":
                    await websocket.send_text("pong")
            except asyncio.TimeoutError:
                # Send a keepalive ping
                await websocket.send_text(json.dumps({
                    "type": "ping",
                    "data": {}
                }))
    
    except WebSocketDisconnect:
        manager.disconnect(websocket)


@router.get("/health")
async def chat_health():
    """Health check for chat service"""
    return {
        "status": "healthy",
        "active_connections": len(manager.active_connections),
        "chat_connections": len(manager.chat_connections),
        "task_connections": len(manager.task_connections)
    }