from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class Task(Base):
    """
    Task model representing a task in the system.
    
    Attributes:
        id (int): Primary key
        title (str): Task title, required, max 200 chars
        description (str): Task description, optional
        status (str): Task status, defaults to 'pending'
        created_at (datetime): Timestamp when task was created
        updated_at (datetime): Timestamp when task was last updated
    """
    __tablename__ = "tasks"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False, index=True)
    description = Column(Text, nullable=True)
    status = Column(String(50), nullable=False, default="pending", index=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<Task(id={self.id}, title='{self.title}', status='{self.status}')>"