import json
from datetime import datetime
from typing import Dict, Any, List, Optional
from langchain_core.tools import tool
from sqlalchemy.ext.asyncio import AsyncSession
from . import crud
from .schemas import TaskCreate, TaskUpdate, TaskFilter, TaskResponse
from .db import AsyncSessionLocal


async def get_db_session() -> AsyncSession:
    """Get database session for tools"""
    return AsyncSessionLocal()


@tool
async def create_task_tool(
    title: str,
    description: str = None,
    due_date: str = None,
    priority: str = "medium"
) -> str:
    """Create a new task.
    
    Args:
        title: The task title (required)
        description: Optional task description
        due_date: Optional due date in ISO format (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)
        priority: Task priority (low, medium, high)
    
    Returns:
        JSON string with the created task details
    """
    try:
        async with AsyncSessionLocal() as db:
            # Parse due_date if provided
            parsed_due_date = None
            if due_date:
                try:
                    if 'T' in due_date:
                        parsed_due_date = datetime.fromisoformat(due_date.replace('Z', '+00:00'))
                    else:
                        parsed_due_date = datetime.fromisoformat(due_date + 'T00:00:00')
                except ValueError:
                    return json.dumps({"error": "Invalid due_date format. Use YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS"})
            
            task_data = TaskCreate(
                title=title,
                description=description,
                due_date=parsed_due_date,
                priority=priority
            )
            
            task = await crud.create_task(db, task_data)
            task_response = TaskResponse.model_validate(task)
            
            return json.dumps({
                "success": True,
                "task": task_response.model_dump(),
                "message": f"Created task: {title}"
            }, default=str)
    
    except Exception as e:
        return json.dumps({"error": f"Failed to create task: {str(e)}"})


@tool
async def update_task_tool(
    task_identifier: str,
    title: str = None,
    description: str = None,
    status: str = None,
    due_date: str = None,
    priority: str = None
) -> str:
    """Update an existing task by ID or title.
    
    Args:
        task_identifier: Task ID (number) or partial title to search for
        title: New task title
        description: New task description
        status: New status (pending, in_progress, done)
        due_date: New due date in ISO format
        priority: New priority (low, medium, high)
    
    Returns:
        JSON string with the updated task details
    """
    try:
        async with AsyncSessionLocal() as db:
            # Try to parse as ID first, then search by title
            task = None
            search_method = "ID"
            
            try:
                task_id = int(task_identifier)
                task = await crud.get_task(db, task_id)
                search_method = f"ID {task_id}"
            except ValueError:
                # Search by title - try exact match first, then partial
                tasks = await crud.get_tasks(db)
                
                # Try exact title match first (case-insensitive)
                for t in tasks:
                    if t.title.lower() == task_identifier.lower():
                        task = t
                        search_method = f"exact title '{task_identifier}'"
                        break
                
                # If no exact match, try partial match
                if not task:
                    for t in tasks:
                        if task_identifier.lower() in t.title.lower():
                            task = t
                            search_method = f"partial title '{task_identifier}'"
                            break
            
            if not task:
                return json.dumps({
                    "error": f"Task not found with identifier: {task_identifier}",
                    "suggestion": "Please provide the exact task title or ID number"
                })
            
            # Validate that we have at least one field to update
            update_fields = {}
            if title is not None and title.strip():
                update_fields["title"] = title.strip()
            if description is not None:
                update_fields["description"] = description.strip() if description.strip() else None
            if status is not None and status.strip():
                if status.lower() in ["pending", "in_progress", "done"]:
                    update_fields["status"] = status.lower()
                else:
                    return json.dumps({"error": f"Invalid status: {status}. Must be: pending, in_progress, or done"})
            if priority is not None and priority.strip():
                if priority.lower() in ["low", "medium", "high"]:
                    update_fields["priority"] = priority.lower()
                else:
                    return json.dumps({"error": f"Invalid priority: {priority}. Must be: low, medium, or high"})
            
            # Parse due_date if provided
            if due_date is not None and due_date.strip():
                try:
                    if 'T' in due_date:
                        update_fields["due_date"] = datetime.fromisoformat(due_date.replace('Z', '+00:00'))
                    else:
                        update_fields["due_date"] = datetime.fromisoformat(due_date + 'T00:00:00')
                except ValueError:
                    return json.dumps({"error": "Invalid due_date format. Use YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS"})
            
            if not update_fields:
                return json.dumps({
                    "error": "No valid fields provided for update",
                    "current_task": {
                        "id": task.id,
                        "title": task.title,
                        "status": task.status,
                        "priority": task.priority
                    }
                })
            
            # Create update object with only the fields that were provided
            update_data = TaskUpdate(**update_fields)
            
            updated_task = await crud.update_task(db, task.id, update_data)
            if not updated_task:
                return json.dumps({"error": f"Failed to update task with ID {task.id}"})
                
            task_response = TaskResponse.model_validate(updated_task)
            
            return json.dumps({
                "success": True,
                "task": task_response.model_dump(),
                "message": f"Successfully updated task '{updated_task.title}' (found by {search_method})",
                "updated_fields": list(update_fields.keys())
            }, default=str)
    
    except Exception as e:
        return json.dumps({
            "error": f"Failed to update task: {str(e)}",
            "identifier_used": task_identifier
        })


@tool
async def delete_task_tool(task_identifier: str) -> str:
    """Delete a task by ID or title. Can also handle bulk operations.
    
    Args:
        task_identifier: Task ID (number), partial title, or bulk keywords:
                        - "all" or "all tasks" = delete all tasks
                        - "completed" or "done" = delete all completed tasks  
                        - "pending" = delete all pending tasks
                        - "high priority" = delete all high priority tasks
    
    Returns:
        JSON string with confirmation message
    """
    try:
        async with AsyncSessionLocal() as db:
            # Handle bulk operations
            if task_identifier.lower() in ["all", "all tasks", "everything"]:
                # Delete all tasks
                tasks = await crud.get_tasks(db, limit=1000)
                if not tasks:
                    return json.dumps({
                        "success": True,
                        "message": "No tasks found to delete",
                        "deleted_count": 0
                    })
                
                deleted_count = 0
                for task in tasks:
                    success = await crud.delete_task(db, task.id)
                    if success:
                        deleted_count += 1
                
                return json.dumps({
                    "success": True,
                    "message": f"Successfully deleted all {deleted_count} tasks from the database",
                    "deleted_count": deleted_count,
                    "bulk_operation": True
                })
            
            elif task_identifier.lower() in ["completed", "done", "finished"]:
                # Delete all completed tasks
                from .schemas import TaskFilter
                task_filter = TaskFilter(status="done")
                tasks = await crud.get_tasks(db, limit=1000, task_filter=task_filter)
                
                if not tasks:
                    return json.dumps({
                        "success": True,
                        "message": "No completed tasks found to delete",
                        "deleted_count": 0
                    })
                
                deleted_count = 0
                for task in tasks:
                    success = await crud.delete_task(db, task.id)
                    if success:
                        deleted_count += 1
                
                return json.dumps({
                    "success": True,
                    "message": f"Successfully deleted {deleted_count} completed tasks",
                    "deleted_count": deleted_count,
                    "bulk_operation": True
                })
            
            elif task_identifier.lower() in ["pending", "not started", "todo"]:
                # Delete all pending tasks
                from .schemas import TaskFilter
                task_filter = TaskFilter(status="pending")
                tasks = await crud.get_tasks(db, limit=1000, task_filter=task_filter)
                
                if not tasks:
                    return json.dumps({
                        "success": True,
                        "message": "No pending tasks found to delete",
                        "deleted_count": 0
                    })
                
                deleted_count = 0
                for task in tasks:
                    success = await crud.delete_task(db, task.id)
                    if success:
                        deleted_count += 1
                
                return json.dumps({
                    "success": True,
                    "message": f"Successfully deleted {deleted_count} pending tasks",
                    "deleted_count": deleted_count,
                    "bulk_operation": True
                })
            
            # Handle single task deletion (existing logic)
            task = None
            search_method = "ID"
            
            try:
                task_id = int(task_identifier)
                task = await crud.get_task(db, task_id)
                search_method = f"ID {task_id}"
            except ValueError:
                # Search by title - try exact match first, then partial
                tasks = await crud.get_tasks(db)
                
                # Try exact title match first (case-insensitive)
                for t in tasks:
                    if t.title.lower() == task_identifier.lower():
                        task = t
                        search_method = f"exact title '{task_identifier}'"
                        break
                
                # If no exact match, try partial match
                if not task:
                    for t in tasks:
                        if task_identifier.lower() in t.title.lower():
                            task = t
                            search_method = f"partial title '{task_identifier}'"
                            break
            
            if not task:
                return json.dumps({
                    "error": f"Task not found with identifier: {task_identifier}",
                    "suggestion": "Please provide the exact task title, ID number, or use bulk keywords like 'all', 'completed', 'pending'"
                })
            
            task_title = task.title
            task_id = task.id
            
            success = await crud.delete_task(db, task_id)
            
            if success:
                return json.dumps({
                    "success": True,
                    "message": f"Successfully deleted task '{task_title}' (found by {search_method})"
                })
            else:
                return json.dumps({
                    "error": f"Failed to delete task '{task_title}' with ID {task_id}"
                })
    
    except Exception as e:
        return json.dumps({
            "error": f"Failed to delete task: {str(e)}",
            "identifier_used": task_identifier
        })


@tool
async def list_tasks_tool(limit: int = 20, skip: int = 0) -> str:
    """List all tasks.
    
    Args:
        limit: Maximum number of tasks to return (default: 20)
        skip: Number of tasks to skip (default: 0)
    
    Returns:
        JSON string with list of tasks
    """
    try:
        async with AsyncSessionLocal() as db:
            tasks = await crud.get_tasks(db, skip=skip, limit=limit)
            task_responses = [TaskResponse.model_validate(task) for task in tasks]
            
            return json.dumps({
                "success": True,
                "tasks": [task.model_dump() for task in task_responses],
                "count": len(task_responses),
                "message": f"Found {len(task_responses)} tasks"
            }, default=str)
    
    except Exception as e:
        return json.dumps({"error": f"Failed to list tasks: {str(e)}"})


@tool
async def filter_tasks_tool(
    status: str = None,
    priority: str = None,
    due_before: str = None,
    due_after: str = None,
    limit: int = 20
) -> str:
    """Filter tasks by various criteria.
    
    Args:
        status: Filter by status (pending, in_progress, done)
        priority: Filter by priority (low, medium, high)
        due_before: Show tasks due before this date (YYYY-MM-DD)
        due_after: Show tasks due after this date (YYYY-MM-DD)
        limit: Maximum number of tasks to return
    
    Returns:
        JSON string with filtered tasks
    """
    try:
        async with AsyncSessionLocal() as db:
            # Parse dates
            parsed_due_before = None
            parsed_due_after = None
            
            if due_before:
                try:
                    parsed_due_before = datetime.fromisoformat(due_before + 'T23:59:59')
                except ValueError:
                    return json.dumps({"error": "Invalid due_before format. Use YYYY-MM-DD"})
            
            if due_after:
                try:
                    parsed_due_after = datetime.fromisoformat(due_after + 'T00:00:00')
                except ValueError:
                    return json.dumps({"error": "Invalid due_after format. Use YYYY-MM-DD"})
            
            task_filter = TaskFilter(
                status=status,
                priority=priority,
                due_before=parsed_due_before,
                due_after=parsed_due_after
            )
            
            tasks = await crud.get_tasks(db, limit=limit, task_filter=task_filter)
            task_responses = [TaskResponse.model_validate(task) for task in tasks]
            
            filter_description = []
            if status:
                filter_description.append(f"status={status}")
            if priority:
                filter_description.append(f"priority={priority}")
            if due_before:
                filter_description.append(f"due before {due_before}")
            if due_after:
                filter_description.append(f"due after {due_after}")
            
            filter_text = ", ".join(filter_description) if filter_description else "no filters"
            
            return json.dumps({
                "success": True,
                "tasks": [task.model_dump() for task in task_responses],
                "count": len(task_responses),
                "filters": filter_text,
                "message": f"Found {len(task_responses)} tasks with {filter_text}"
            }, default=str)
    
    except Exception as e:
        return json.dumps({"error": f"Failed to filter tasks: {str(e)}"})


# List of all available tools
TASK_TOOLS = [
    create_task_tool,
    update_task_tool,
    delete_task_tool,
    list_tasks_tool,
    filter_tasks_tool
]