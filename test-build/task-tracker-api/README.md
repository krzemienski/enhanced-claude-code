# Task Tracker API

A production-ready RESTful API built with FastAPI for managing tasks and projects. This API provides comprehensive task management capabilities including user authentication, task CRUD operations, and project organization.

## Features

- **FastAPI Framework**: Modern, fast web framework for building APIs
- **SQLAlchemy ORM**: Robust database interactions with SQLite/PostgreSQL support
- **Pydantic Models**: Automatic request/response validation
- **JWT Authentication**: Secure API access with token-based authentication
- **Comprehensive Testing**: Full test suite with pytest
- **Environment Configuration**: Flexible configuration via environment variables
- **Type Safety**: Full type hints throughout the codebase

## Prerequisites

- Python 3.8 or higher
- pip package manager
- Virtual environment (recommended)

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd task-tracker-api
```

2. Create and activate a virtual environment:
```bash
python -m venv venv

# On Windows
venv\Scripts\activate

# On macOS/Linux
source venv/bin/activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
```bash
cp .env.example .env
```

Edit `.env` and configure your settings:
- `API_KEY`: Your secret API key for authentication
- `DATABASE_URL`: Database connection string (defaults to SQLite)
- `SECRET_KEY`: Secret key for JWT token signing
- Other configuration options as needed

## Running the Application

### Development Mode

Run the application in development mode with auto-reload:

```bash
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

### Production Mode

For production deployment:

```bash
uvicorn src.main:app --host 0.0.0.0 --port 8000 --workers 4
```

## API Documentation

Once the application is running, you can access:

- **Interactive API documentation (Swagger UI)**: http://localhost:8000/docs
- **Alternative API documentation (ReDoc)**: http://localhost:8000/redoc
- **OpenAPI schema**: http://localhost:8000/openapi.json

## Project Structure

```
task-tracker-api/
├── src/
│   ├── __init__.py
│   ├── main.py           # FastAPI application entry point
│   ├── api/              # API endpoints and routers
│   ├── models/           # SQLAlchemy models
│   ├── services/         # Business logic layer
│   └── utils/            # Utility functions and helpers
├── tests/
│   └── __init__.py       # Test suite
├── docs/                 # Additional documentation
├── requirements.txt      # Python dependencies
├── .env.example         # Environment variables template
├── .gitignore          # Git ignore patterns
└── README.md           # This file
```

## Testing

Run the test suite with pytest:

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src

# Run specific test file
pytest tests/test_api.py

# Run in verbose mode
pytest -v
```

## Development

### Code Style

This project uses:
- **Black** for code formatting
- **Flake8** for linting
- **MyPy** for type checking

Run code quality checks:

```bash
# Format code
black src/ tests/

# Check linting
flake8 src/ tests/

# Type checking
mypy src/
```

### Database Migrations

When making changes to database models, use Alembic for migrations:

```bash
# Create a new migration
alembic revision --autogenerate -m "Description of changes"

# Apply migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For issues, questions, or contributions, please open an issue in the GitHub repository.