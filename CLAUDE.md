# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

### Backend Development
```bash
# Install dependencies
pip install -r requirements.txt

# Run the FastAPI server
uvicorn main:app --reload --host 0.0.0.0 --port 8000
# Or: python main.py

# Start Celery worker (required for async tasks)
python start_celery_worker.py
# Or: celery -A app.celery_app worker --loglevel=info

# Start Redis (required for Celery)
redis-server

# Run tests
pytest tests/
pytest --cov=app tests/  # with coverage

# Access API documentation
# Swagger UI: http://localhost:8000/docs
# ReDoc: http://localhost:8000/redoc
```

### Frontend Development
```bash
cd rubri-frontend
npm install
npm run dev      # Start development server
npm run build    # Build for production
npm run preview  # Preview production build
```

## Architecture Overview

### System Design
This is an interview evaluation platform with a microservices architecture:

1. **FastAPI Backend** - Async Python web framework handling REST APIs and WebSockets
2. **Multi-Agent System** - LangChain-based agents orchestrated for question generation:
   - `SkillExtractionAgent` - Extracts skills from JD/resume
   - `QuestionGenerationAgent` - Generates interview questions
   - `QuestionEvaluationAgent` - Evaluates question quality
   - `ExpectedResponseAgent` - Generates expected answers
   - `ReportAssemblyAgent` - Assembles final report
3. **Celery + Redis** - Async task processing for long-running operations
4. **WebSocket Manager** - Real-time progress updates for async tasks
5. **React Frontend** - TypeScript-based UI with real-time updates

### Key Architectural Patterns

#### 1. Multi-Agent Orchestration
The question generation system uses a sophisticated multi-agent pattern where specialized agents collaborate:
```
app/services/qgen/orchestrator/multi_agent_system.py - Coordinates agents
app/services/qgen/agents/base_agent.py - Base agent class
app/services/qgen/agents/*.py - Specialized agent implementations
```

#### 2. Async Task Processing
Long-running tasks use Celery with Redis broker:
```
app/tasks/question_generation_tasks.py - Main async task
app/tasks/progress_tracker.py - Progress tracking utility
app/websocket_manager.py - WebSocket connections for real-time updates
```

#### 3. LLM Provider Abstraction
Supports multiple LLM providers through a unified interface:
```
app/llm_client_ops.py - LLM client factory and operations
Providers: OpenAI, Gemini, Groq, Azure OpenAI, Portkey
```

#### 4. Authentication Flow
JWT-based auth with Google OAuth support:
```
app/auth/jwt_utils.py - JWT token handling
app/auth/google_oauth.py - Google OAuth integration
app/api/v1/auth_routes.py - Auth endpoints
```

### Database Schema
Using SQLAlchemy ORM with these main models:
- `User` - User accounts and authentication
- `RubricTemplate` - Generated evaluation rubrics
- `Document` - Uploaded JDs and resumes
- `QuestionSet` - Generated interview questions
- `Task` - Async task tracking

### API Design Patterns
- RESTful endpoints under `/api/v1/`
- Async endpoints return task IDs for polling/WebSocket monitoring
- WebSocket endpoint `/ws/progress/{task_id}` for real-time updates
- Consistent error handling with HTTP status codes and error messages

### Frontend Architecture
- React 19 with TypeScript for type safety
- Context API for global state (Auth, WebSocket)
- Custom WebSocket manager with reconnection logic
- Component structure:
  - `pages/` - Route-level components
  - `components/` - Reusable UI components
  - `contexts/` - React contexts for state
  - `hooks/` - Custom React hooks
  - `utils/` - Utility functions

### Environment Configuration
The app uses a layered configuration approach:
1. Base config in `app/configs/app.{dev,prod}.yaml`
2. Environment variables override config values
3. `APP_ENV` determines which config file to load
4. Sensitive data (API keys) must be in .env file

### Critical Dependencies
- **fastapi[all]** - Web framework with WebSocket support
- **langchain** + **langchain-community** - Multi-agent orchestration
- **celery[redis]** - Distributed task queue
- **sqlalchemy** - ORM for database operations
- **pdfplumber**, **python-docx** - Document parsing
- **jinja2** - Template rendering for reports
- Frontend: React 19, TypeScript, Vite, Tailwind CSS