from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict
from enum import Enum


class TaskStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class TaskBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255, description="Task title")
    description: Optional[str] = Field(None, description="Task description")
    status: TaskStatus = Field(TaskStatus.PENDING, description="Task status")


class TaskCreate(TaskBase):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "title": "Complete API documentation",
                "description": "Write comprehensive documentation for all API endpoints",
                "status": "pending"
            }
        }
    )


class TaskUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255, description="Task title")
    description: Optional[str] = Field(None, description="Task description")
    status: Optional[TaskStatus] = Field(None, description="Task status")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "title": "Update task title",
                "status": "in_progress"
            }
        }
    )


class TaskResponse(TaskBase):
    id: int = Field(..., description="Task ID")
    created_at: datetime = Field(..., description="Task creation timestamp")
    updated_at: datetime = Field(..., description="Task last update timestamp")

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": 1,
                "title": "Complete API documentation",
                "description": "Write comprehensive documentation for all API endpoints",
                "status": "completed",
                "created_at": "2024-01-15T10:00:00",
                "updated_at": "2024-01-15T14:30:00"
            }
        }
    )


class TaskListResponse(BaseModel):
    tasks: list[TaskResponse] = Field(..., description="List of tasks")
    total: int = Field(..., description="Total number of tasks")
    page: int = Field(..., description="Current page number")
    limit: int = Field(..., description="Number of items per page")
    total_pages: int = Field(..., description="Total number of pages")


class ErrorResponse(BaseModel):
    detail: str = Field(..., description="Error message")
    status_code: int = Field(..., description="HTTP status code")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Error timestamp")