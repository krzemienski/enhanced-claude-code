# Simple Task Tracker API

## Overview
Build a simple REST API for task tracking with the following features:
- Create, read, update, and delete tasks
- SQLite database for persistence
- Basic authentication with API keys
- JSON responses
- Error handling and validation

## Technical Requirements
- Python 3.8+
- FastAPI framework
- SQLAlchemy ORM
- SQLite database
- Pydantic for data validation
- pytest for testing

## API Endpoints
- `POST /tasks` - Create a new task
- `GET /tasks` - List all tasks
- `GET /tasks/{id}` - Get a specific task
- `PUT /tasks/{id}` - Update a task
- `DELETE /tasks/{id}` - Delete a task
- `GET /health` - Health check endpoint

## Task Model
```python
{
    "id": "uuid",
    "title": "string",
    "description": "string",
    "status": "pending|in_progress|completed",
    "created_at": "datetime",
    "updated_at": "datetime"
}
```

## Authentication
- Simple API key authentication via header: `X-API-Key`
- Store API keys in environment variables

## Project Structure
```
task-tracker-api/
├── src/
│   ├── __init__.py
│   ├── main.py
│   ├── models.py
│   ├── schemas.py
│   ├── database.py
│   ├── auth.py
│   └── routes/
│       ├── __init__.py
│       └── tasks.py
├── tests/
│   ├── __init__.py
│   ├── test_api.py
│   └── test_models.py
├── requirements.txt
├── README.md
└── .env.example
```

## Additional Requirements
- Include comprehensive error handling
- Add request/response logging
- Create docker support with Dockerfile
- Include API documentation with Swagger
- Add input validation for all endpoints
- Include unit tests with >80% coverage