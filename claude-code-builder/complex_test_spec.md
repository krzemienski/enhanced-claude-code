# Todo List API

A RESTful API for managing todo lists with user authentication.

## Description

A comprehensive todo list application backend built with Python and FastAPI. The API provides full CRUD operations for todo items, user authentication with JWT tokens, and data persistence using SQLAlchemy with PostgreSQL. The application follows RESTful principles and includes proper error handling, input validation, and comprehensive documentation.

## Features

### User Authentication
Secure user registration and login system with JWT token-based authentication. Includes password hashing, token refresh mechanisms, and protected endpoints.

### Todo Management
Complete CRUD operations for todo items including create, read, update, and delete. Support for filtering by status, due date, and priority. Pagination for large datasets.

### Data Validation
Comprehensive input validation using Pydantic models. Custom validators for email formats, password strength, and date ranges.

### API Documentation
Auto-generated interactive API documentation using FastAPI's built-in Swagger UI and ReDoc interfaces.

## Technologies

- Python 3.11 (required)
- FastAPI 0.104.1 (required)
- SQLAlchemy 2.0.23 (required)
- PostgreSQL 15 (required)
- Pydantic 2.5.0 (required)
- python-jose[cryptography] 3.3.0 (required)
- passlib[bcrypt] 1.7.4 (required)
- python-multipart 0.0.6 (required)
- alembic 1.12.1 (required)
- pytest 7.4.3 (optional)
- pytest-asyncio 0.21.1 (optional)
- httpx 0.25.2 (optional)