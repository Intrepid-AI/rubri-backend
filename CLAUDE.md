# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Running the Main Application
```bash
# Start the main FastAPI server (Rubri-Backend)
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Run directly with Python (production mode)
python main.py
```

### Running the Async Task System
```bash
# Start Redis server (required for Celery)
redis-server

# Start Celery worker for background tasks (in a separate terminal)
python start_celery_worker.py

# Alternative: Start Celery worker with more control
celery -A app.celery_app worker --loglevel=info --concurrency=4 --queues=questions,emails
```

### Testing
```bash
# Run all tests
pytest tests/

# Run specific test file
pytest tests/test_utils.py

# Run with verbose output
pytest tests/ -v
```

### Database Operations
The application uses SQLite by default for development. Database initialization happens automatically on startup via `init_db()` in main.py.

## Architecture Overview

### Main Application Structure
- **FastAPI Backend**: Main service for rubric generation and interview question generation
- **Database Layer**: SQLAlchemy ORM with SQLite/PostgreSQL support
- **LLM Integration**: Multi-provider LLM client supporting OpenAI, Gemini, Groq, and Azure OpenAI
- **File Processing**: Document upload and text extraction from PDF, DOCX, and plain text
- **Multi-Agent System**: Five specialized agents for comprehensive interview question generation

### Key Components

#### Database Models (app/db_ops/models.py)
- `Document`: Stores uploaded files (JD/Resume) with extracted text
- `Rubric`: Main rubric records with JSON content and document references  
- `RubricHistory`: Version control for rubric changes
- `SharedLink`: Temporary access tokens for rubric sharing

#### Core Services
- **File Upload Service** (app/services/file_upload_ops.py): Handles document upload and text extraction
- **LLM Rubric Service** (app/services/llm_rubric_ops.py): Rubric generation using conversation chains with memory
- **LLM Client** (app/llm_client_ops.py): Unified interface for multiple LLM providers

#### API Structure
All endpoints are under `/api/v1/` with the following main routes:
- Upload: `/upload/file/{jd|resume}`, `/upload/text/{jd|resume}`
- Rubric: `/rubric/{create|chat|edit|export|list}`
- Questions: `/questions/generate`, `/questions/generate/quick`

### Question Generation System (app/qgen/)
Integrated multi-agent system for generating interview questions:
- **Multi-Agent Architecture**: Five orchestrated agents working sequentially
- **Skill Extraction**: Analyzes JD/resume to identify technical skills and experience levels
- **Question Generation**: Creates deep, non-generic technical questions targeting specific skills
- **Question Evaluation**: Evaluates question quality, relevance, and appropriateness
- **Expected Response Generation**: Creates interviewer guidance with scoring rubrics
- **Report Assembly**: Formats comprehensive interview evaluation reports

### Configuration Management
- **YAML Configs**: Separate dev/prod configurations in `app/configs/`
- **Environment Variables**: Override config values via `.env` file
- **LLM Provider Config**: Detailed provider-specific parameters for constructor and invoke methods

### Key Implementation Details

#### LLM Integration Pattern
The system uses a factory pattern for LLM providers with separate constructor and invoke parameters:
```python
# Constructor params: model, temperature, etc.
# Invoke params: streaming, max_tokens, config
```

#### Conversation Memory
Rubric generation uses LangChain's ConversationBufferMemory with message serialization/deserialization for persistent chat sessions.

#### Database Foreign Keys
- Rubrics reference Document entities via `jd_document_id` and `resume_document_id`
- RubricHistory tracks all changes with proper foreign key relationships

## Environment Setup

### Required Environment Variables
```bash
ENV=dev  # or prod
DATABASE_URL=sqlite:///rubri.db  # Optional override
LLM_API_KEY=your-api-key  # For chosen LLM provider
LOG_LEVEL=INFO
PORT=8000

# Redis Configuration (for async tasks)
REDIS_URL=redis://localhost:6379/0

# Email Configuration (for notifications)
SMTP_USERNAME=your-email@example.com
SMTP_PASSWORD=your-app-password
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
FROM_EMAIL=noreply@rubri.ai
FROM_NAME="Rubri Interview Assistant"

# Frontend URL (for email links)
FRONTEND_URL=http://localhost:3000

# Google OAuth Configuration
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
GOOGLE_REDIRECT_URI=http://localhost:8000/api/v1/auth/google/callback

# JWT Configuration
JWT_SECRET_KEY=your-super-secret-jwt-key-change-in-production
```

### LLM Provider Configuration
Configure your chosen provider in the YAML config files with appropriate API keys in environment variables.

## Question Generation Endpoints

### Synchronous Endpoints (Legacy)
- `/questions/generate` - Generate from uploaded documents (5-minute timeout)
- `/questions/generate/quick` - Generate from raw text (5-minute timeout)

### Async Endpoints (Recommended)
- `/questions/generate/async` - Start async generation from uploaded documents
- `/questions/generate/quick/async` - Start async generation from raw text
- `/tasks/{task_id}/status` - Get task status and progress
- `/tasks` - List all background tasks
- `/ws/progress/{task_id}` - WebSocket for real-time progress updates

### Authentication Endpoints
- `/auth/google/login` - Get Google OAuth authorization URL
- `/auth/google/callback` - Handle Google OAuth callback
- `/auth/me` - Get current user profile
- `/auth/me/preferences` - Update user preferences
- `/auth/logout` - Logout current user
- `/auth/refresh` - Refresh access token

### Email Notifications & Authentication
- **Automatic Email Detection**: Authenticated users automatically get email notifications (if enabled in preferences)
- **Gmail Integration**: Sign in with Google to automatically use your Gmail for notifications
- **Manual Email**: Non-authenticated users can provide email manually
- **Preference Control**: Users can enable/disable email notifications in their profile

## Multi-Agent Question Generation Workflow

1. **Skill Extraction Agent**: Identifies technical skills, experience levels, and categories
2. **Question Generation Agent**: Creates targeted questions with appropriate difficulty
3. **Question Evaluation Agent**: Ensures quality and relevance of generated questions
4. **Expected Response Agent**: Provides interviewer guidance and scoring rubrics
5. **Report Assembly Agent**: Creates final comprehensive interview evaluation report