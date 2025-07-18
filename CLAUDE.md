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

#### 2. Async Task Processing with Real-time Streaming
Long-running tasks use Celery with Redis broker and real-time streaming:
```
app/tasks/question_generation_tasks.py - Main async task
app/tasks/progress_tracker.py - Progress tracking utility
app/websocket_manager.py - WebSocket connections for real-time updates
app/services/qgen/streaming/ - Real-time streaming system
```

**Real-time Streaming Architecture:**
- **Problem**: Celery workers run in separate processes and can't access WebSocket connections
- **Solution**: Redis Pub/Sub bridge for cross-process communication
- **Flow**: Celery Worker → Redis Pub/Sub → FastAPI Server → WebSocket → Frontend
- **Components**:
  - `app/services/qgen/streaming/redis_publisher.py` - Publishes events from Celery
  - `app/services/streaming/redis_subscriber.py` - Subscribes to events in FastAPI
  - `app/services/qgen/streaming/stream_manager_redis.py` - Simplified event emission
  - `app/websocket_manager.py` - WebSocket management with Redis integration

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
- **celery[redis]** - Distributed task queue with Redis broker
- **redis** - Redis client for streaming and caching
- **sqlalchemy** - ORM for database operations
- **pdfplumber**, **python-docx** - Document parsing
- **jinja2** - Template rendering for reports
- Frontend: React 19, TypeScript, Vite, Tailwind CSS

**Streaming Dependencies:**
- **redis** - Pub/Sub for cross-process communication
- **asyncio** - Async Redis client for FastAPI
- **websockets** - WebSocket implementation in FastAPI
- **json** - Event serialization/deserialization

## Detailed Architecture Documentation

### Backend Structure

#### Main Application (main.py)
- FastAPI app with CORS middleware (all origins allowed in dev)
- Global exception handlers for HTTP, validation, and general errors
- Database initialization on startup
- WebSocket endpoint for progress tracking
- API router mounted at `/api/v1`

#### API Endpoints

**Authentication Routes (`/api/v1/auth/`)**
- `/google/login` - Initiates Google OAuth flow
- `/google/callback` - OAuth callback, creates/updates users
- `/logout` - Invalidates session
- `/me` - Gets current user
- `/me/preferences` - Updates preferences
- `/refresh` - Refreshes JWT token

**Upload Routes (`/api/v1/upload/`)**
- `/file/jd` - Upload job description (PDF/DOCX/TXT)
- `/file/resume` - Upload resume
- `/text/jd` - Plain text job description
- `/text/resume` - Plain text resume

**Question Generation (`/api/v1/questions/`)**
- `/generate` - Sync generation (deprecated)
- `/generate/quick` - Quick sync generation
- `/generate/async` - Async with progress tracking
- `/generate/quick/async` - Quick async generation

**Rubric Management (`/api/v1/rubric/`)**
- `/create` - Create evaluation rubric
- `/chat` - Update via LLM chat
- `/edit/{rubric_id}` - Direct edit
- `/export/link/{rubric_id}` - Shareable link
- `/export/pdf/{rubric_id}` - PDF export (stub)
- `/list` - List with pagination

**Task Management (`/api/v1/tasks/`)**
- `/{task_id}/status` - Get task status/results
- `/` - List tasks with filters

#### Database Models (app/db_ops/models.py)

1. **User** - OAuth users
   - Fields: user_id, google_id, email, name, picture_url, preferences
   - Relationships: rubrics, task_statuses

2. **Document** - Uploaded files
   - Fields: doc_id, filename, file_path, content_type, document_type, extracted_text
   - Types: 'jd' or 'resume'

3. **Rubric** - Generated evaluations
   - Fields: rubric_id, title, description, status, content (JSON)
   - Relationships: user, jd_document, resume_document, history

4. **RubricHistory** - Audit trail
   - Fields: rubhis_id, content, change_type, change_description
   - Change types: created, updated, chat

5. **TaskStatus** - Async task tracking
   - Fields: task_id, task_type, status, progress, current_step, result_data

6. **UserSession** - JWT sessions
   - Fields: session_id, access_token_hash, refresh_token_hash, expires_at

7. **SharedLink** - Shareable rubrics
   - Fields: link_id, rubric_id, token, expires_at

#### Multi-Agent System Details

**Agent Workflow:**
1. **SkillExtractionAgent**
   - Extracts technical skills with confidence scores (1-5)
   - Determines experience levels
   - Groups skills into categories
   - Provides evidence/context
   - **Streaming**: Emits `skill_found` events for real-time updates

2. **QuestionGenerationAgent**
   - Creates 2-3 questions per skill
   - 7 question types (mathematical, implementation, optimization, etc.)
   - Tailored to candidate experience
   - Includes rationale
   - **Streaming**: Emits `question_generated` events with progress

3. **QuestionEvaluationAgent**
   - 4-dimensional scoring (technical depth, relevance, difficulty, specificity)
   - Approves/rejects questions
   - Provides improvement feedback
   - **Streaming**: Emits `evaluation_result` events for each question

4. **ExpectedResponseAgent**
   - Key concepts checklist
   - Good answer indicators
   - Red flags
   - Follow-up questions
   - Scoring rubrics
   - **Streaming**: Emits `response_generated` events with progress

5. **ReportAssemblyAgent**
   - Groups by skill category
   - Time estimates
   - Candidate summary
   - Hiring recommendations
   - **Streaming**: Emits `section_assembled` events for each section

**State Management:**
- Shared `MultiAgentInterviewState` TypedDict
- Progressive enhancement pattern
- Error tracking and recovery

#### Celery Configuration

**Setup (app/celery_app.py):**
- Redis broker/backend
- JSON serialization
- 1-hour result expiration
- Extended result tracking
- Queue routing (questions, emails)

**Worker Config (start_celery_worker.py):**
- Concurrency: 4
- Queues: questions, emails
- Loglevel: info

**Tasks:**
- `generate_interview_questions_async` - Main generation
- `generate_quick_questions_async` - Quick generation
- `send_completion_email` - Success notifications
- `send_error_email` - Failure notifications

**Progress Tracking:**
- Database-based progress updates
- 5-step workflow with percentages
- Real-time WebSocket notifications

### Frontend Architecture Details

#### Component Structure
```
rubri-frontend/src/
├── components/
│   ├── forms/          # Form components
│   ├── generation/     # Progress tracking UI
│   ├── layout/         # Header, Footer
│   ├── report/         # Report viewer
│   └── ui/             # Base UI components
├── contexts/           # React contexts
│   ├── AuthContext.tsx # Authentication state
│   └── ThemeContext.tsx # Theme management
├── hooks/              # Custom hooks
│   └── useWebSocket.ts # WebSocket integration
├── pages/              # Page components
│   ├── GeneratorPage.tsx
│   └── HomePage.tsx
├── services/           # API layer
│   └── api.ts         # Axios configuration
├── types/              # TypeScript definitions
└── utils/              # Utilities
    └── WebSocketManager.ts
```

#### Key Frontend Features

**WebSocket Manager:**
- Singleton pattern
- Auto-reconnection (2s delay)
- Connection pooling (max 10)
- Rate limiting
- Message type handling

**API Service:**
- Axios with 20-minute timeout
- Request/response interceptors
- Error transformation
- Environment-based base URL

**Authentication:**
- JWT storage in localStorage
- Auto-refresh before expiry
- Context-based state management

**UI Components:**
- Tailwind CSS styling
- Dark/light theme toggle
- File upload with drag-drop
- Real-time progress bars
- Markdown report rendering

### Integration Points

#### Backend-Frontend Communication
1. **REST API:**
   - Standard CRUD operations
   - File uploads via FormData
   - JSON request/response

2. **WebSocket:**
   - Task-specific connections
   - Progress updates
   - Error notifications
   - Auto-close on completion

3. **Authentication:**
   - Google OAuth flow
   - JWT in Authorization header
   - Token refresh mechanism

#### Async Task Flow
1. User uploads files/text
2. Frontend calls async endpoint
3. Backend creates task record
4. Celery worker processes task
5. Progress updates via WebSocket
6. Final results via API/WebSocket

### Real-time Streaming Implementation

#### Problem & Solution
**Initial Issue**: UI stuck on "Initializing..." because Celery workers couldn't access WebSocket connections due to process isolation.

**Solution**: Implemented Redis Pub/Sub bridge for cross-process communication.

#### Architecture Components

**1. Redis Event Publisher (`app/services/qgen/streaming/redis_publisher.py`)**
- Singleton pattern for connection reuse
- Publishes events from Celery workers to Redis channels
- Channel naming: `stream:task:{task_id}`
- Automatic reconnection and error handling

**2. Redis Event Subscriber (`app/services/streaming/redis_subscriber.py`)**
- Subscribes to Redis channels in FastAPI process
- Forwards events to WebSocket manager
- Async Redis client for non-blocking I/O
- Per-task subscription management

**3. Simplified Stream Manager (`app/services/qgen/streaming/stream_manager_redis.py`)**
- Removed complex buffering/retry logic
- Direct Redis publishing for all agent events
- Supports all event types: `agent_start`, `agent_thinking`, `skill_found`, `question_generated`, `evaluation_result`, `response_generated`, `section_assembled`, `agent_complete`, `error`

**4. Enhanced WebSocket Manager (`app/websocket_manager.py`)**
- Subscribes to Redis events on WebSocket connect
- Unsubscribes on disconnect
- Connection limits (3 per task, 100 global)
- Automatic cleanup and monitoring

#### Event Flow
```
AI Agent (Celery) → Redis Publisher → Redis Channel → Redis Subscriber (FastAPI) → WebSocket Manager → Frontend
```

#### Supported Event Types
- `AGENT_START` - Agent begins processing
- `AGENT_THINKING` - Agent status/progress updates
- `SKILL_FOUND` - Skill extracted from documents
- `QUESTION_GENERATED` - Interview question created
- `EVALUATION_RESULT` - Question quality evaluation
- `RESPONSE_GENERATED` - Expected answer generated
- `SECTION_ASSEMBLED` - Report section completed
- `AGENT_COMPLETE` - Agent finished successfully
- `ERROR` - Processing error occurred

#### Recent Fixes & Improvements

**1. Schema Compatibility Fix**
- Fixed `ReportAssemblyAgent` to use correct `InterviewSection` schema
- Changed `section.category_name` → `section.section_name`
- Changed `section.estimated_time_minutes` → `section.estimated_total_time`
- Fixed question counting logic for sections

**2. Agent Event Methods**
- Added missing event emission methods to stream manager
- `emit_evaluation_result_sync/async`
- `emit_response_generated_sync/async`
- `emit_section_assembled_sync/async`
- `emit_agent_output_sync/async`
- `emit_agent_progress_sync/async`

**3. WebSocket URL Handling**
- Fixed frontend WebSocket URL construction for HTTPS
- Regex replacement: `replace(/^https?/, 'ws')`

#### Testing & Monitoring
- Test script: `test_redis_streaming.py`
- Redis monitoring: `redis-cli MONITOR | grep stream:task`
- WebSocket debugging in browser DevTools
- Comprehensive logging throughout the pipeline

#### Benefits
- **Real-time Updates**: No more "Initializing..." - users see live progress
- **Process Independence**: Celery and FastAPI communicate via Redis
- **Scalability**: Multiple workers and FastAPI instances supported
- **Reliability**: Redis handles message delivery and persistence
- **Simplicity**: Removed complex buffering logic

### Deployment Considerations

#### Current Limitations
1. No frontend routing (state-based)
2. No visible login UI
3. CORS allows all origins
4. No rate limiting
5. SQLite in dev mode
6. No automated tests visible

#### Production Requirements
1. PostgreSQL database
2. Redis server
3. Celery workers
4. Static file serving
5. HTTPS/WSS support
6. Environment variables for secrets
7. Proper CORS configuration
8. Rate limiting implementation

#### Scaling Considerations
1. Multiple Celery workers
2. Redis clustering
3. Database connection pooling
4. Load balancer for WebSockets
5. CDN for static assets
6. Horizontal scaling for API servers

### Development Workflow

1. **Backend Changes:**
   - Update models → migrate database
   - Add endpoints → update OpenAPI docs
   - Modify agents → test with mock data

2. **Frontend Changes:**
   - Update types → TypeScript validation
   - Add components → Tailwind styling
   - API changes → update service layer

3. **Full Stack Features:**
   - Design API contract
   - Implement backend endpoint

4. **Streaming System Development:**
   - Test Redis connectivity: `redis-cli ping`
   - Run streaming tests: `python test_redis_streaming.py`
   - Monitor Redis events: `redis-cli MONITOR | grep stream:task`
   - Debug WebSocket in browser DevTools Network tab

### Troubleshooting Guide

#### Common Issues

**1. Streaming Events Not Appearing**
- Check Redis connectivity: `redis-cli ping`
- Verify WebSocket connection in browser DevTools
- Monitor Redis channels: `redis-cli MONITOR`
- Check task_id matches between publisher and subscriber

**2. "Initializing..." Stuck State**
- Ensure Redis server is running
- Check Celery worker logs for errors
- Verify WebSocket URL construction (HTTP vs HTTPS)
- Test with `test_redis_streaming.py`

**3. Agent Workflow Errors**
- Check for missing stream manager event methods
- Verify schema compatibility (e.g., `InterviewSection` fields)
- Review agent logs for specific error messages

**4. Performance Issues**
- Monitor Redis memory usage: `redis-cli INFO memory`
- Check WebSocket connection counts
- Review event frequency and batching

#### Development Commands

**Start Full Development Environment:**
```bash
# Terminal 1: Start Redis
redis-server

# Terminal 2: Start FastAPI
python main.py

# Terminal 3: Start Celery Worker
python start_celery_worker.py

# Terminal 4: Start Frontend
cd rubri-frontend && npm run dev
```

**Docker Compose Local Testing:**
```bash
# 1. Ensure Docker is running
docker --version

# 2. Create .env file if not exists
cp .env.example .env

# 3. Edit .env file with your API keys and URLs
# Required variables:
# - OPENAI_API_KEY or other LLM provider key
# - GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET
# - JWT_SECRET_KEY (generate with: openssl rand -hex 32)
# - FRONTEND_URL=http://localhost:3000
# - FRONTEND_API_URL=http://localhost:8000

# 4. Build and run all services
docker-compose up --build

# 5. Access the application
# Frontend: http://localhost:3000
# Backend API: http://localhost:8000
# API Docs: http://localhost:8000/docs

# 6. To run in background
docker-compose up -d

# 7. To stop all services
docker-compose down

# 8. To rebuild after code changes
docker-compose build
docker-compose up

# 9. View logs
docker-compose logs -f backend    # Backend logs
docker-compose logs -f frontend   # Frontend logs
docker-compose logs -f redis      # Redis logs

# 10. Debug issues
docker-compose ps                 # Check container status
docker-compose exec backend bash  # Access backend container
```

**Note on Docker Compose Build Errors:**
If you encounter TypeScript errors during frontend build, the Dockerfile is configured to fall back to `vite build` without TypeScript checking. This allows the build to complete while you fix type issues separately.

**Test Streaming System:**
```bash
# Test Redis streaming
python test_redis_streaming.py

# Monitor Redis events
redis-cli MONITOR | grep stream:task

# Subscribe to specific task
redis-cli SUBSCRIBE 'stream:task:your_task_id'
```

**Debug WebSocket:**
- Open browser DevTools → Network tab
- Look for WebSocket connections
- Check connection status and messages
- Verify task_id in WebSocket URL

## URL Configuration Guide

### Single Source of Truth: Environment Variables

All URLs are now configured through environment variables ONLY. No URLs should be in config.yaml files.

### Local Development Setup

#### Option 1: Running Services Individually

1. **Backend Setup**:
   ```bash
   # Create .env file from example
   cp .env.example .env
   
   # Edit .env and set URLs for local development:
   FRONTEND_URL=http://localhost:3000
   GOOGLE_REDIRECT_URI=http://localhost:8000/api/v1/auth/google/callback
   
   # The backend will automatically use these values
   python main.py
   ```

2. **Frontend Setup**:
   ```bash
   cd rubri-frontend
   
   # Development mode automatically uses .env.development
   # which has VITE_API_BASE_URL=http://localhost:8000
   npm run dev
   ```

#### Option 2: Docker Compose Local Testing

1. **Create .env file**:
   ```bash
   cp .env.example .env
   ```

2. **Set local URLs in .env**:
   ```env
   # Frontend URLs
   FRONTEND_URL=http://localhost:3000
   FRONTEND_API_URL=http://localhost:8000
   
   # OAuth redirect for local testing
   GOOGLE_REDIRECT_URI=http://localhost:8000/api/v1/auth/google/callback
   
   # Other required variables...
   ```

3. **Run Docker Compose**:
   ```bash
   docker-compose up --build
   ```

### Production Deployment (Coolify/Hetzner)

#### 1. Environment Variables in Coolify

Set these in Coolify's environment variables section:

```env
# Your domain URLs
FRONTEND_URL=https://rubri.ai
FRONTEND_API_URL=https://api.rubri.ai
GOOGLE_REDIRECT_URI=https://api.rubri.ai/api/v1/auth/google/callback

# API Keys and secrets
OPENAI_API_KEY=sk-...
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
JWT_SECRET_KEY=...
```

#### 2. No Code Changes Required

The same code works in all environments because:
- Backend reads URLs from environment variables
- Frontend build process uses `FRONTEND_API_URL` build arg
- Docker Compose passes the correct values

### URL Configuration Locations

| URL Variable | Where Used | Purpose |
|-------------|------------|---------|
| `FRONTEND_URL` | Backend (auth_routes.py, email_tasks.py) | OAuth redirect base, email links |
| `FRONTEND_API_URL` | Docker Compose → Frontend build | API endpoint for frontend |
| `GOOGLE_REDIRECT_URI` | Backend (google_oauth.py) | OAuth callback URL |
| `VITE_API_BASE_URL` | Frontend (.env files) | Frontend's API endpoint |

### Important Notes

1. **Never hardcode URLs** in the code
2. **Config.yaml files** should NOT contain URLs
3. **All URLs** must come from environment variables
4. **Frontend builds** bake in the API URL at build time

### Testing Different Environments

```bash
# Test with production URLs locally
FRONTEND_URL=https://rubri.ai FRONTEND_API_URL=https://api.rubri.ai docker-compose up

# Test with staging URLs
FRONTEND_URL=https://staging.rubri.ai FRONTEND_API_URL=https://api-staging.rubri.ai docker-compose up
```

### Verifying URL Configuration

1. **Check backend is using correct URLs**:
   ```python
   # In any Python file
   from app.db_ops.db_config import load_app_config
   config = load_app_config()
   print(config.get('frontend_url'))  # Should show your FRONTEND_URL env var
   ```

2. **Check frontend build has correct API URL**:
   - Open browser DevTools
   - Check Network tab for API calls
   - Should go to the URL you set in FRONTEND_API_URL

### Code Style Guidelines
- Python: Black formatter, type hints
- TypeScript: Strict mode, interfaces
- React: Functional components, hooks
- API: RESTful conventions
- Database: Explicit transactions
- Errors: Comprehensive handling