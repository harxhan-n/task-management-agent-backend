# Task Management Backend

A FastAPI backend with AI-powered task management using LangGraph and Google Gemini.

## Features

- 🚀 **FastAPI** - Modern, fast web framework for building APIs
- 🤖 **AI Agent** - LangGraph + Google Gemini for natural language task management
- 🗄️ **PostgreSQL** - Robust database with async SQLAlchemy ORM
- 🔄 **Real-time** - WebSocket support for live updates
- 🛠️ **CRUD Operations** - Complete task management with filtering
- 🐳 **Docker** - Containerized deployment ready
- 📊 **Alembic** - Database migrations
- ✅ **Validation** - Pydantic schemas for data validation

## Tech Stack

- **Framework**: FastAPI (Python 3.11+)
- **Database**: PostgreSQL (via Supabase or local)
- **ORM**: SQLAlchemy with async support
- **AI**: LangGraph + Google Gemini (ChatGoogleGenerativeAI)
- **Real-time**: WebSockets
- **Migrations**: Alembic
- **Container**: Docker + Docker Compose

## Project Structure

```
back-end/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application entry point
│   ├── db.py               # Database connection and session management
│   ├── models.py           # SQLAlchemy models
│   ├── schemas.py          # Pydantic request/response schemas
│   ├── crud.py             # Database operations
│   ├── tools.py            # LangGraph tools for task operations
│   ├── agent.py            # LangGraph + Gemini agent setup
│   ├── utils.py            # Helper functions
│   └── routes/
│       ├── __init__.py
│       ├── tasks.py        # Task CRUD endpoints
│       └── chat.py         # Chat and WebSocket endpoints
├── alembic/                # Database migration files
│   └── env.py              # Alembic configuration
├── requirements.txt        # Python dependencies
├── .env.example            # Environment variables template
├── .gitignore             # Git ignore rules
├── Dockerfile             # Docker container configuration
├── docker-compose.yml     # Multi-service Docker setup
├── alembic.ini            # Alembic configuration
├── init.sql               # Database initialization script
└── README.md              # This file
```

## Quick Start

### 1. Environment Setup

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your configuration
# Required variables:
# - DATABASE_URL (PostgreSQL connection string)
# - GEMINI_API_KEY (Google AI API key)
```

### 2. Using Docker (Recommended)

```bash
# Start all services (PostgreSQL + FastAPI + Redis)
docker-compose up -d

# View logs
docker-compose logs -f backend

# Stop services
docker-compose down
```

The API will be available at `http://localhost:8000`

### 3. Manual Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Set up database (update DATABASE_URL in .env first)
alembic upgrade head

# Run the application
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## API Endpoints

### REST API

- **GET** `/` - API information
- **GET** `/health` - Health check
- **GET** `/api/info` - Detailed API information

#### Tasks
- **GET** `/api/tasks` - List all tasks (with pagination)
- **POST** `/api/tasks` - Create a new task
- **GET** `/api/tasks/{id}` - Get specific task
- **PUT** `/api/tasks/{id}` - Update specific task
- **DELETE** `/api/tasks/{id}` - Delete specific task
- **GET** `/api/tasks/filter` - Filter tasks by criteria
- **GET** `/api/tasks/count/total` - Get task count

#### Chat
- **POST** `/api/chat` - Send message to AI agent

### WebSocket Endpoints

- **WS** `/api/chat/ws` - Real-time chat with AI agent
- **WS** `/api/chat/ws/tasks` - Real-time task updates

## AI Agent Capabilities

The AI agent can understand natural language commands like:

- **Create tasks**: "Create a task to review the project proposal"
- **Update tasks**: "Mark the project review task as done"
- **List tasks**: "Show me all my pending tasks"
- **Filter tasks**: "List all high priority tasks due this week"
- **Delete tasks**: "Delete the completed marketing task"

### Supported Task Operations

1. **create_task_tool** - Create new tasks with title, description, due date, priority
2. **update_task_tool** - Update tasks by ID or title
3. **delete_task_tool** - Delete tasks by ID or title
4. **list_tasks_tool** - List all tasks with pagination
5. **filter_tasks_tool** - Filter by status, priority, due date

## Database Schema

### Task Model
```python
class Task:
    id: int (Primary Key)
    title: str (Required)
    description: str (Optional)
    status: str (pending|in_progress|done)
    priority: str (low|medium|high)
    due_date: datetime (Optional)
    created_at: datetime
    updated_at: datetime
```

## Environment Variables

Create a `.env` file with:

```env
# Database Configuration
DATABASE_URL=postgresql+asyncpg://user:password@host:5432/database_name

# AI Configuration
GEMINI_API_KEY=your_gemini_api_key_here

# Application Configuration
DEBUG=True
SECRET_KEY=your_secret_key_here

# CORS Configuration
ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000

# Optional: Server Configuration
HOST=0.0.0.0
PORT=8000
```

## Database Migrations

```bash
# Create a new migration
alembic revision --autogenerate -m "Description of changes"

# Apply migrations
alembic upgrade head

# Downgrade migrations
alembic downgrade -1
```

## Development

### Running Tests
```bash
# Install test dependencies
pip install pytest pytest-asyncio httpx

# Run tests
pytest
```

### Code Formatting
```bash
# Format code
black .

# Lint code
flake8 .
```

## Deployment

### Using Docker
```bash
# Build and run with Docker Compose
docker-compose up -d

# Scale backend service
docker-compose up -d --scale backend=3
```

### Manual Deployment
```bash
# Install production dependencies
pip install -r requirements.txt

# Set environment to production
export DEBUG=False

# Run with Gunicorn
pip install gunicorn
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

## API Documentation

Once running, visit:
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

## WebSocket Usage Example

### JavaScript Client
```javascript
// Connect to chat WebSocket
const chatWS = new WebSocket('ws://localhost:8000/api/chat/ws');

// Send message
chatWS.send(JSON.stringify({
    message: "Create a task to review the budget proposal"
}));

// Receive responses
chatWS.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log('AI Response:', data.data.response);
    console.log('Task Updates:', data.data.task_updates);
};

// Connect to task updates
const taskWS = new WebSocket('ws://localhost:8000/api/chat/ws/tasks');

taskWS.onmessage = (event) => {
    const data = JSON.parse(event.data);
    if (data.type === 'task_update') {
        console.log('Tasks updated:', data.data.tasks);
        // Update your UI with the new task data
    }
};
```

## Troubleshooting

### Common Issues

1. **Database connection failed**
   - Check DATABASE_URL in `.env`
   - Ensure PostgreSQL is running
   - Verify credentials and database exists

2. **Gemini API errors**
   - Verify GEMINI_API_KEY is correct
   - Check API quota and billing
   - Ensure internet connectivity

3. **WebSocket connection issues**
   - Check CORS settings
   - Verify WebSocket URL format
   - Check firewall settings

### Logs

```bash
# Docker logs
docker-compose logs -f backend

# Application logs
tail -f logs/app.log
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

This project is licensed under the MIT License.