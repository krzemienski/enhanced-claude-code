# Task Manager CLI

A command-line task management application with persistent storage.

# Description

This project creates a feature-rich command-line interface for managing personal tasks and to-dos. The application provides a clean, intuitive interface for creating, updating, organizing, and tracking tasks with support for categories, priorities, due dates, and persistent storage using SQLite.

# Features

### Task Management
- Create new tasks with title and description
- Update existing tasks
- Delete tasks
- Mark tasks as complete/incomplete
- View all tasks or filter by status

### Organization
- Categorize tasks (work, personal, urgent, etc.)
- Set priority levels (high, medium, low)
- Add due dates and reminders
- Tag tasks for easy filtering

### Data Persistence
- SQLite database for reliable storage
- Automatic backups
- Import/export functionality
- Data migration support

### User Interface
- Colorful terminal output using Rich
- Interactive menus
- Progress indicators
- Keyboard shortcuts
- Help system

# Technologies
- Python 3.8+ (required)
- Click 8.0+ (required)
- Rich 13.0+ (required)
- SQLite3 (required)
- python-dateutil 2.8+ (required)

# Technical Requirements

### Performance
- Instant response time for all operations
- Support for 10,000+ tasks
- Efficient search and filtering

### Usability
- Clear command structure
- Comprehensive help text
- Input validation
- Error recovery

### Reliability
- ACID-compliant data storage
- Automatic backups
- Crash recovery
- Data integrity checks

# Project Structure
```
task-manager-cli/
├── src/
│   ├── __init__.py
│   ├── cli.py          # Main CLI entry point
│   ├── commands/       # CLI commands
│   ├── models/         # Data models
│   ├── database/       # Database operations
│   └── utils/          # Utility functions
├── tests/
│   ├── test_cli.py
│   ├── test_models.py
│   └── test_database.py
├── docs/
│   └── README.md
├── requirements.txt
├── setup.py
└── .gitignore
```

# CLI Commands

### task add
Add a new task
- Options: --title, --description, --category, --priority, --due

### task list
List all tasks
- Options: --status, --category, --priority, --sort

### task update
Update an existing task
- Arguments: task_id
- Options: --title, --description, --status, --priority

### task delete
Delete a task
- Arguments: task_id
- Options: --force

### task complete
Mark task as complete
- Arguments: task_id

### task export
Export tasks to JSON/CSV
- Options: --format, --output

### task import
Import tasks from file
- Arguments: file_path
- Options: --format, --merge