"""Routes module for Task Tracker API.

This module contains all API route definitions organized by resource type.
"""

from .tasks import router as tasks_router

__all__ = ["tasks_router"]