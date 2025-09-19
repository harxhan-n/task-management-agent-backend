from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class TaskBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    status: str = Field(default="pending", pattern="^(pending|in_progress|done)$")
    due_date: Optional[datetime] = None
    priority: str = Field(default="medium", pattern="^(low|medium|high)$")


class TaskCreate(TaskBase):
    pass


class TaskUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    status: Optional[str] = Field(None, pattern="^(pending|in_progress|done)$")
    due_date: Optional[datetime] = None
    priority: Optional[str] = Field(None, pattern="^(low|medium|high)$")


class TaskResponse(TaskBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TaskFilter(BaseModel):
    status: Optional[str] = Field(None, pattern="^(pending|in_progress|done)$")
    priority: Optional[str] = Field(None, pattern="^(low|medium|high)$")
    due_before: Optional[datetime] = None
    due_after: Optional[datetime] = None


# Chat related schemas
class ChatMessage(BaseModel):
    message: str = Field(..., min_length=1, max_length=1000)


class ChatResponse(BaseModel):
    response: str
    task_updates: Optional[list[TaskResponse]] = None
    data_to_show: Optional[list[dict]] = None
    data_format: Optional[str] = None


# WebSocket message schemas
class WebSocketMessage(BaseModel):
    type: str = Field(..., pattern="^(chat|task_update|system)$")
    data: dict