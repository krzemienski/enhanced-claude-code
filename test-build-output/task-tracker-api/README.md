# Task Tracker API

A production-ready RESTful API for task management built with FastAPI and SQLAlchemy.

## Description

Task Tracker API is a robust backend service that provides comprehensive task management capabilities. It features user authentication, task CRUD operations, and efficient data persistence using SQLAlchemy ORM.

## Features

- RESTful API endpoints for task management
- User authentication with API keys
- SQLAlchemy ORM for database operations
- Comprehensive error handling and validation
- Production-ready configuration management
- Automated testing with pytest

## Prerequisites

- Python 3.8 or higher
- pip (Python package installer)

## Setup Instructions

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd task-tracker-api
   ```

2. **Create a virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables:**
   ```bash
   cp .env.example .env
   ```
   Edit the `.env` file and update the `API_KEY` with your secure key.

5. **Run database migrations:**
   ```bash
   alembic upgrade head
   ```

6. **Start the development server:**
   ```bash
   uvicorn src.main:app --reload
   ```

   The API will be available at `http://localhost:8000`

## API Documentation

Once the server is running, you can access:
- Interactive API documentation (Swagger UI): `http://localhost:8000/docs`
- Alternative API documentation (ReDoc): `http://localhost:8000/redoc`

## Testing

Run the test suite:
```bash
pytest
```

Run tests with coverage:
```bash
pytest --cov=src tests/
```

## Project Structure

```
task-tracker-api/
├── src/
│   ├── __init__.py
│   └── main.py         # FastAPI application entry point
├── tests/
│   └── __init__.py
├── .env.example        # Environment variables template
├── .gitignore          # Git ignore patterns
├── README.md           # Project documentation
├── requirements.txt    # Python dependencies
└── pyproject.toml      # Project configuration
```

## License

This project is licensed under the MIT License.