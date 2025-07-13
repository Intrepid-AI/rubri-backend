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

2. **QuestionGenerationAgent**
   - Creates 2-3 questions per skill
   - 7 question types (mathematical, implementation, optimization, etc.)
   - Tailored to candidate experience
   - Includes rationale

3. **QuestionEvaluationAgent**
   - 4-dimensional scoring (technical depth, relevance, difficulty, specificity)
   - Approves/rejects questions
   - Provides improvement feedback

4. **ExpectedResponseAgent**
   - Key concepts checklist
   - Good answer indicators
   - Red flags
   - Follow-up questions
   - Scoring rubrics

5. **ReportAssemblyAgent**
   - Groups by skill category
   - Time estimates
   - Candidate summary
   - Hiring recommendations

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
   - Add frontend UI/logic
   - Test integration
   - Handle errors gracefully

### Code Style Guidelines
- Python: Black formatter, type hints
- TypeScript: Strict mode, interfaces
- React: Functional components, hooks
- API: RESTful conventions
- Database: Explicit transactions
- Errors: Comprehensive handling