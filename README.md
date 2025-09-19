# 🤖 AI-Powered Task Management Backend

> **Smart task management API with natural language processing powered by Google Gemini AI**

## 📖 Project Overview

This FastAPI backend provides an intelligent task management system that understands natural language commands. Users can interact with the system using conversational queries like "Delete all completed tasks" or "Show me high priority items due this week". The AI agent powered by LangGraph and Google Gemini processes these requests and performs the appropriate task operations.

**Key Capabilities:**
- Natural language task management
- Smart bulk operations (delete all, filter by status/priority)
- Real-time updates via WebSocket
- Frontend-ready structured responses
- RESTful API with comprehensive documentation

## 🛠️ Tech Stack

- **Framework**: FastAPI (Python 3.11+)
- **AI Engine**: LangGraph + Google Gemini 1.5 Flash
- **Database**: PostgreSQL with async SQLAlchemy
- **Real-time**: WebSocket connections
- **Validation**: Pydantic v2 schemas
- **Migrations**: Alembic
- **Deployment**: Docker + Railway
- **Documentation**: Swagger UI / ReDoc

## 📁 Project Structure

```
back-end/
├── app/
│   ├── main.py              # FastAPI application entry point
│   ├── db.py               # Database connection & session management
│   ├── models.py           # SQLAlchemy Task model
│   ├── schemas.py          # Pydantic request/response schemas
│   ├── crud.py             # Database CRUD operations
│   ├── agent.py            # LangGraph + Gemini AI agent
│   ├── tools.py            # AI tools (create, update, delete, list, filter)
│   └── routes/
│       ├── tasks.py        # REST API endpoints
│       └── chat.py         # AI chat & WebSocket endpoints
├── alembic/                # Database migrations
├── requirements.txt        # Python dependencies
├── .env.example           # Environment variables template
├── Dockerfile             # Production Docker configuration
├── docker-compose.yml     # Local development setup
├── railway.json           # Railway deployment config
└── README.md              # This file
```

## 🌐 API Endpoints

### REST API
- `GET /` - API information
- `GET /health` - Health check
- `GET /docs` - Interactive API documentation

### Task Management (`/api/tasks`)
- `POST /api/tasks` - Create new task
- `GET /api/tasks` - List all tasks (with pagination)
- `GET /api/tasks/{id}` - Get specific task
- `PUT /api/tasks/{id}` - Update task
- `DELETE /api/tasks/{id}` - Delete task
- `GET /api/tasks/filter` - Filter tasks by criteria

### AI Chat (`/api/chat`)
- `POST /api/chat` - Send message to AI agent
- `WS /api/chat/ws` - Real-time chat WebSocket

### Example Usage
```bash
# Create task via AI
curl -X POST "http://localhost:8000/api/chat" \
  -H "Content-Type: application/json" \
  -d '{"message": "Create a high priority task: Review budget proposal"}'

# Smart bulk operations
curl -X POST "http://localhost:8000/api/chat" \
  -H "Content-Type: application/json" \
  -d '{"message": "Delete all completed tasks"}'
```

## � Environment Variables Setup

Create a `.env` file with the following variables:

```env
# Database Configuration
DATABASE_URL=postgresql+asyncpg://user:password@host:5432/database

# AI Configuration
GEMINI_API_KEY=your_gemini_api_key_here

# Application Configuration  
DEBUG=True
SECRET_KEY=your_secret_key_here

# CORS Configuration
ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
```

### Getting API Keys:
1. **Google Gemini API**: Visit [Google AI Studio](https://makersuite.google.com/app/apikey)
2. **Database**: Use Supabase, local PostgreSQL, or Railway's built-in database

## 💻 Local Development

### Option 1: Docker Compose (Recommended)
```bash
# 1. Clone repository
git clone https://github.com/harxhan-n/task-management-agent-backend.git
cd task-management-agent-backend

# 2. Setup environment
cp .env.example .env
# Edit .env with your DATABASE_URL and GEMINI_API_KEY

# 3. Start services
docker-compose up -d

# 4. API available at: http://localhost:8000
```

### Option 2: Manual Setup
```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Setup database
alembic upgrade head

# 3. Start server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## 🚀 Railway Deployment

### Quick Deploy
1. **Fork this repository**
2. **Create Railway project**: [railway.app/dashboard](https://railway.app/dashboard)
3. **Connect GitHub repository**
4. **Set environment variables**:
   ```
   DATABASE_URL=postgresql+asyncpg://...
   GEMINI_API_KEY=your_key_here
   ALLOWED_ORIGINS=https://your-frontend-domain.com
   ```
5. **Deploy!** Railway builds automatically from `Dockerfile`

### Deployment Features
- ✅ Automatic HTTPS and custom domains
- ✅ Built-in PostgreSQL database
- ✅ Auto-scaling and monitoring
- ✅ Health check integration (`/health` endpoint)

### Validate Deployment
```bash
# Check if ready for deployment
python quick_deploy_check.py
```

---

**🎉 Ready for production deployment!**

For detailed API documentation, visit `/docs` endpoint when running locally.