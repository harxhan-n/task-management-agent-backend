from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from .. import crud
from ..db import get_db
from ..schemas import TaskCreate, TaskUpdate, TaskResponse, TaskFilter

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.post("/", response_model=TaskResponse)
async def create_task(
    task: TaskCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a new task"""
    try:
        db_task = await crud.create_task(db, task)
        return TaskResponse.model_validate(db_task)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/", response_model=List[TaskResponse])
async def get_tasks(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db)
):
    """Get all tasks with pagination"""
    tasks = await crud.get_tasks(db, skip=skip, limit=limit)
    return [TaskResponse.model_validate(task) for task in tasks]


@router.get("/filter", response_model=List[TaskResponse])
async def filter_tasks(
    status: Optional[str] = Query(None, regex="^(pending|in_progress|done)$"),
    priority: Optional[str] = Query(None, regex="^(low|medium|high)$"),
    due_before: Optional[str] = Query(None),
    due_after: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db)
):
    """Filter tasks by various criteria"""
    from datetime import datetime
    
    # Parse dates
    parsed_due_before = None
    parsed_due_after = None
    
    if due_before:
        try:
            parsed_due_before = datetime.fromisoformat(due_before + 'T23:59:59')
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid due_before format. Use YYYY-MM-DD")
    
    if due_after:
        try:
            parsed_due_after = datetime.fromisoformat(due_after + 'T00:00:00')
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid due_after format. Use YYYY-MM-DD")
    
    task_filter = TaskFilter(
        status=status,
        priority=priority,
        due_before=parsed_due_before,
        due_after=parsed_due_after
    )
    
    tasks = await crud.get_tasks(db, skip=skip, limit=limit, task_filter=task_filter)
    return [TaskResponse.model_validate(task) for task in tasks]


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get a specific task by ID"""
    task = await crud.get_task(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return TaskResponse.model_validate(task)


@router.put("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: int,
    task_update: TaskUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update a specific task"""
    task = await crud.update_task(db, task_id, task_update)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return TaskResponse.model_validate(task)


@router.delete("/{task_id}")
async def delete_task(
    task_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Delete a specific task"""
    success = await crud.delete_task(db, task_id)
    if not success:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"message": "Task deleted successfully"}


@router.get("/count/total")
async def get_tasks_count(
    status: Optional[str] = Query(None, regex="^(pending|in_progress|done)$"),
    priority: Optional[str] = Query(None, regex="^(low|medium|high)$"),
    due_before: Optional[str] = Query(None),
    due_after: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Get total count of tasks with optional filtering"""
    from datetime import datetime
    
    # Parse dates
    parsed_due_before = None
    parsed_due_after = None
    
    if due_before:
        try:
            parsed_due_before = datetime.fromisoformat(due_before + 'T23:59:59')
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid due_before format. Use YYYY-MM-DD")
    
    if due_after:
        try:
            parsed_due_after = datetime.fromisoformat(due_after + 'T00:00:00')
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid due_after format. Use YYYY-MM-DD")
    
    task_filter = TaskFilter(
        status=status,
        priority=priority,
        due_before=parsed_due_before,
        due_after=parsed_due_after
    ) if any([status, priority, due_before, due_after]) else None
    
    count = await crud.get_tasks_count(db, task_filter)
    return {"count": count}