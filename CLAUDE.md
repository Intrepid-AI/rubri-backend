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

### Running the Question Generation Service
```bash
# Start the question generation FastAPI server
cd q_gen
python main.py
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
```

### LLM Provider Configuration
Configure your chosen provider in the YAML config files with appropriate API keys in environment variables.

## New Question Generation Endpoints

### `/questions/generate` - Generate from Uploaded Documents
Creates comprehensive interview questions using uploaded JD/resume documents.
- Uses the multi-agent system for deep technical question generation
- Stores results in database as rubric records
- Returns complete evaluation with interviewer guidance

### `/questions/generate/quick` - Generate from Raw Text
Creates interview questions directly from text input without file upload.
- Accepts resume_text and/or job_description as direct input
- Same comprehensive multi-agent processing
- Ideal for quick evaluations or API integrations

## Multi-Agent Question Generation Workflow

1. **Skill Extraction Agent**: Identifies technical skills, experience levels, and categories
2. **Question Generation Agent**: Creates targeted questions with appropriate difficulty
3. **Question Evaluation Agent**: Ensures quality and relevance of generated questions
4. **Expected Response Agent**: Provides interviewer guidance and scoring rubrics
5. **Report Assembly Agent**: Creates final comprehensive interview evaluation report