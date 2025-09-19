from datetime import datetime
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import and_, or_
from .models import Task
from .schemas import TaskCreate, TaskUpdate, TaskFilter


async def create_task(db: AsyncSession, task: TaskCreate) -> Task:
    """Create a new task"""
    db_task = Task(**task.model_dump())
    db.add(db_task)
    await db.commit()
    await db.refresh(db_task)
    return db_task


async def get_task(db: AsyncSession, task_id: int) -> Optional[Task]:
    """Get a task by ID"""
    result = await db.execute(select(Task).filter(Task.id == task_id))
    return result.scalar_one_or_none()


async def get_task_by_title(db: AsyncSession, title: str) -> Optional[Task]:
    """Get a task by title (case-insensitive)"""
    result = await db.execute(
        select(Task).filter(Task.title.ilike(f"%{title}%"))
    )
    return result.scalar_one_or_none()


async def get_tasks(
    db: AsyncSession, 
    skip: int = 0, 
    limit: int = 100,
    task_filter: Optional[TaskFilter] = None
) -> List[Task]:
    """Get tasks with optional filtering"""
    query = select(Task)
    
    if task_filter:
        conditions = []
        
        if task_filter.status:
            conditions.append(Task.status == task_filter.status)
        
        if task_filter.priority:
            conditions.append(Task.priority == task_filter.priority)
        
        if task_filter.due_before:
            conditions.append(Task.due_date <= task_filter.due_before)
        
        if task_filter.due_after:
            conditions.append(Task.due_date >= task_filter.due_after)
        
        if conditions:
            query = query.filter(and_(*conditions))
    
    query = query.offset(skip).limit(limit).order_by(Task.created_at.desc())
    result = await db.execute(query)
    return result.scalars().all()


async def update_task(
    db: AsyncSession, 
    task_id: int, 
    task_update: TaskUpdate
) -> Optional[Task]:
    """Update a task"""
    db_task = await get_task(db, task_id)
    if not db_task:
        return None
    
    update_data = task_update.model_dump(exclude_unset=True)
    if update_data:
        update_data["updated_at"] = datetime.utcnow()
        for field, value in update_data.items():
            setattr(db_task, field, value)
        
        await db.commit()
        await db.refresh(db_task)
    
    return db_task


async def update_task_by_title(
    db: AsyncSession, 
    title: str, 
    task_update: TaskUpdate
) -> Optional[Task]:
    """Update a task by title"""
    db_task = await get_task_by_title(db, title)
    if not db_task:
        return None
    
    return await update_task(db, db_task.id, task_update)


async def delete_task(db: AsyncSession, task_id: int) -> bool:
    """Delete a task"""
    db_task = await get_task(db, task_id)
    if not db_task:
        return False
    
    await db.delete(db_task)
    await db.commit()
    return True


async def delete_task_by_title(db: AsyncSession, title: str) -> bool:
    """Delete a task by title"""
    db_task = await get_task_by_title(db, title)
    if not db_task:
        return False
    
    await db.delete(db_task)
    await db.commit()
    return True


async def get_tasks_count(
    db: AsyncSession,
    task_filter: Optional[TaskFilter] = None
) -> int:
    """Get total count of tasks with optional filtering"""
    from sqlalchemy import func
    
    query = select(func.count(Task.id))
    
    if task_filter:
        conditions = []
        
        if task_filter.status:
            conditions.append(Task.status == task_filter.status)
        
        if task_filter.priority:
            conditions.append(Task.priority == task_filter.priority)
        
        if task_filter.due_before:
            conditions.append(Task.due_date <= task_filter.due_before)
        
        if task_filter.due_after:
            conditions.append(Task.due_date >= task_filter.due_after)
        
        if conditions:
            query = query.filter(and_(*conditions))
    
    result = await db.execute(query)
    return result.scalar()