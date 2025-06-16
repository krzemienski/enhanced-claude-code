from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class TaskCreate(BaseModel):
    """
    Schema for creating a new task.
    
    Attributes:
        title (str): Task title, required, max 200 chars
        description (Optional[str]): Task description, optional
        status (Optional[str]): Task status, defaults to 'pending'
    """
    title: str = Field(..., min_length=1, max_length=200, description="Task title")
    description: Optional[str] = Field(None, description="Task description")
    status: Optional[str] = Field("pending", regex="^(pending|in_progress|completed|cancelled)$", description="Task status")
    
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "title": "Complete project documentation",
            "description": "Write comprehensive documentation for the API endpoints",
            "status": "pending"
        }
    })


class TaskUpdate(BaseModel):
    """
    Schema for updating an existing task.
    All fields are optional.
    
    Attributes:
        title (Optional[str]): Task title, max 200 chars
        description (Optional[str]): Task description
        status (Optional[str]): Task status
    """
    title: Optional[str] = Field(None, min_length=1, max_length=200, description="Task title")
    description: Optional[str] = Field(None, description="Task description")
    status: Optional[str] = Field(None, regex="^(pending|in_progress|completed|cancelled)$", description="Task status")
    
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "title": "Updated task title",
            "status": "in_progress"
        }
    })


class TaskResponse(BaseModel):
    """
    Schema for task response.
    
    Attributes:
        id (int): Task ID
        title (str): Task title
        description (Optional[str]): Task description
        status (str): Task status
        created_at (datetime): Creation timestamp
        updated_at (datetime): Last update timestamp
    """
    id: int = Field(..., description="Task ID")
    title: str = Field(..., description="Task title")
    description: Optional[str] = Field(None, description="Task description")
    status: str = Field(..., description="Task status")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": 1,
                "title": "Complete project documentation",
                "description": "Write comprehensive documentation for the API endpoints",
                "status": "pending",
                "created_at": "2024-01-01T12:00:00",
                "updated_at": "2024-01-01T12:00:00"
            }
        }
    )