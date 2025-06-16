# Todo App API Specification

## Overview
Build a simple REST API for a todo application with the following features:

### Core Features
- Create, read, update, and delete todos
- Mark todos as complete/incomplete
- Filter todos by status
- User authentication with JWT tokens
- SQLite database for persistence

### Technical Requirements
- Python 3.9+
- FastAPI framework
- SQLAlchemy ORM
- JWT authentication
- Pydantic for data validation
- pytest for testing

### API Endpoints
- POST /auth/register - Register new user
- POST /auth/login - Login user
- GET /todos - List all todos for authenticated user
- POST /todos - Create new todo
- GET /todos/{id} - Get specific todo
- PUT /todos/{id} - Update todo
- DELETE /todos/{id} - Delete todo
- PATCH /todos/{id}/complete - Mark todo as complete

### Database Schema
- Users table (id, username, email, password_hash)
- Todos table (id, user_id, title, description, completed, created_at, updated_at)

### Project Structure
```
todo-api/
├── src/
│   ├── __init__.py
│   ├── main.py
│   ├── models.py
│   ├── schemas.py
│   ├── database.py
│   ├── auth.py
│   └── routers/
│       ├── __init__.py
│       ├── auth.py
│       └── todos.py
├── tests/
│   ├── __init__.py
│   ├── test_auth.py
│   └── test_todos.py
├── requirements.txt
├── .env.example
├── README.md
└── .gitignore
```