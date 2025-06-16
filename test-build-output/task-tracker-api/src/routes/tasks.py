"""Task API routes with full CRUD operations."""

import logging
from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from ..database import get_db
from ..models import Task, TaskStatus
from ..schemas import (
    TaskCreate, 
    TaskUpdate, 
    TaskResponse, 
    TaskListResponse,
    ErrorResponse
)
from ..auth import require_api_key

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/tasks",
    tags=["tasks"],
    responses={
        401: {"model": ErrorResponse, "description": "Authentication failed"},
        403: {"model": ErrorResponse, "description": "Invalid API key"},
        429: {"model": ErrorResponse, "description": "Rate limit exceeded"},
    }
)


@router.post(
    "/",
    response_model=TaskResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new task",
    description="Create a new task with the provided details. Requires valid API key authentication.",
    response_description="The newly created task",
    responses={
        400: {"model": ErrorResponse, "description": "Invalid input data"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    }
)
async def create_task(
    task_data: TaskCreate,
    db: Session = Depends(get_db),
    api_key: str = Depends(require_api_key)
) -> TaskResponse:
    """Create a new task in the database."""
    try:
        logger.info(f"Creating new task with title: {task_data.title}")
        
        # Create new task instance
        new_task = Task(
            title=task_data.title,
            description=task_data.description,
            status=task_data.status or TaskStatus.PENDING
        )
        
        # Add to database
        db.add(new_task)
        db.commit()
        db.refresh(new_task)
        
        logger.info(f"Task created successfully with ID: {new_task.id}")
        return TaskResponse(**new_task.to_dict())
        
    except SQLAlchemyError as e:
        logger.error(f"Database error creating task: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create task due to database error"
        )
    except Exception as e:
        logger.error(f"Unexpected error creating task: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while creating the task"
        )


@router.get(
    "/",
    response_model=TaskListResponse,
    summary="List all tasks",
    description="Retrieve a paginated list of all tasks. Supports filtering by status and pagination.",
    response_description="Paginated list of tasks"
)
async def list_tasks(
    status: Optional[TaskStatus] = Query(None, description="Filter tasks by status"),
    limit: int = Query(default=10, ge=1, le=100, description="Number of tasks to return"),
    offset: int = Query(default=0, ge=0, description="Number of tasks to skip"),
    db: Session = Depends(get_db),
    api_key: str = Depends(require_api_key)
) -> TaskListResponse:
    """Get a paginated list of tasks with optional status filtering."""
    try:
        logger.info(f"Fetching tasks - status: {status}, limit: {limit}, offset: {offset}")
        
        # Build query
        query = db.query(Task)
        
        # Apply status filter if provided
        if status:
            query = query.filter(Task.status == status)
        
        # Get total count before pagination
        total = query.count()
        
        # Apply pagination
        tasks = query.offset(offset).limit(limit).all()
        
        # Convert to response models
        task_responses = [TaskResponse(**task.to_dict()) for task in tasks]
        
        # Calculate pagination info
        page = (offset // limit) + 1
        total_pages = (total + limit - 1) // limit  # Ceiling division
        
        logger.info(f"Retrieved {len(tasks)} tasks out of {total} total")
        
        return TaskListResponse(
            tasks=task_responses,
            total=total,
            page=page,
            limit=limit,
            total_pages=total_pages
        )
        
    except SQLAlchemyError as e:
        logger.error(f"Database error listing tasks: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve tasks due to database error"
        )
    except Exception as e:
        logger.error(f"Unexpected error listing tasks: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while retrieving tasks"
        )


@router.get(
    "/{task_id}",
    response_model=TaskResponse,
    summary="Get a specific task",
    description="Retrieve details of a specific task by its ID.",
    response_description="The requested task",
    responses={
        404: {"model": ErrorResponse, "description": "Task not found"},
    }
)
async def get_task(
    task_id: int,
    db: Session = Depends(get_db),
    api_key: str = Depends(require_api_key)
) -> TaskResponse:
    """Get a specific task by ID."""
    try:
        logger.info(f"Fetching task with ID: {task_id}")
        
        task = db.query(Task).filter(Task.id == task_id).first()
        
        if not task:
            logger.warning(f"Task not found with ID: {task_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Task with ID {task_id} not found"
            )
        
        logger.info(f"Retrieved task: {task.id} - {task.title}")
        return TaskResponse(**task.to_dict())
        
    except HTTPException:
        raise
    except SQLAlchemyError as e:
        logger.error(f"Database error fetching task {task_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve task due to database error"
        )
    except Exception as e:
        logger.error(f"Unexpected error fetching task {task_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while retrieving the task"
        )


@router.put(
    "/{task_id}",
    response_model=TaskResponse,
    summary="Update a task",
    description="Update an existing task with new data. All fields are optional.",
    response_description="The updated task",
    responses={
        404: {"model": ErrorResponse, "description": "Task not found"},
        400: {"model": ErrorResponse, "description": "Invalid input data"},
    }
)
async def update_task(
    task_id: int,
    task_update: TaskUpdate,
    db: Session = Depends(get_db),
    api_key: str = Depends(require_api_key)
) -> TaskResponse:
    """Update a task with new data."""
    try:
        logger.info(f"Updating task with ID: {task_id}")
        
        # Fetch the task
        task = db.query(Task).filter(Task.id == task_id).first()
        
        if not task:
            logger.warning(f"Task not found for update with ID: {task_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Task with ID {task_id} not found"
            )
        
        # Update fields if provided
        update_data = task_update.dict(exclude_unset=True)
        
        if not update_data:
            logger.warning(f"No update data provided for task {task_id}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No fields to update provided"
            )
        
        for field, value in update_data.items():
            setattr(task, field, value)
        
        # Update the updated_at timestamp
        task.updated_at = datetime.utcnow()
        
        # Commit changes
        db.commit()
        db.refresh(task)
        
        logger.info(f"Task {task_id} updated successfully")
        return TaskResponse(**task.to_dict())
        
    except HTTPException:
        raise
    except SQLAlchemyError as e:
        logger.error(f"Database error updating task {task_id}: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update task due to database error"
        )
    except Exception as e:
        logger.error(f"Unexpected error updating task {task_id}: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while updating the task"
        )


@router.delete(
    "/{task_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a task",
    description="Delete a task from the database permanently.",
    responses={
        404: {"model": ErrorResponse, "description": "Task not found"},
    }
)
async def delete_task(
    task_id: int,
    db: Session = Depends(get_db),
    api_key: str = Depends(require_api_key)
) -> None:
    """Delete a task by ID."""
    try:
        logger.info(f"Deleting task with ID: {task_id}")
        
        # Fetch the task
        task = db.query(Task).filter(Task.id == task_id).first()
        
        if not task:
            logger.warning(f"Task not found for deletion with ID: {task_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Task with ID {task_id} not found"
            )
        
        # Delete the task
        db.delete(task)
        db.commit()
        
        logger.info(f"Task {task_id} deleted successfully")
        
    except HTTPException:
        raise
    except SQLAlchemyError as e:
        logger.error(f"Database error deleting task {task_id}: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete task due to database error"
        )
    except Exception as e:
        logger.error(f"Unexpected error deleting task {task_id}: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while deleting the task"
        )