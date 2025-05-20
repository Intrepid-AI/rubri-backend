# Rubri-Backend

## Main User
Interviewer

## What It Does
This tool assists interviewers by generating an evaluation rubric based on the Job Description (JD) and the candidate's resume. It allows for a comprehensive and structured assessment of the candidate against the required criteria. The application enables interviewers to conduct evaluations effectively, providing a consistent framework for assessing candidates holistically based on the defined requirements.

## High-Level Functional Requirements (FRs)

### Key Requirements

1. Rubric Generation and Usage
   - Generate an evaluation rubric based on a provided Job Description (JD) and candidate resume.
   - The rubric must be fillable by the interviewer during the interview.
   - Allow editing of the completed rubric after the interview.
   - Include functionality to export the final evaluation rubric to a PDF document.
   - Rubric Modification: Enable users to modify the evaluation rubric template (potentially involving discussion/interaction, e.g., with an LLM or based on feedback).

2. Rubric Template History
   - Maintain a historical record of all previously generated evaluation rubric templates, accessible to the user.

## Possible APIs

### Upload Operations
- `/upload/file/jd` - Supports PDFs, Text, Word
- `/upload/file/resume` - Supports PDFs, Text, Word
- `/upload/text/jd`
- `/upload/text/resume`

### Rubric Operations
- `/rubric/create` - To create initial rubric based on JD OR Resume OR Both
- `/rubric/chat` - To chat with LLM and update the rubric
- `/rubric/edit` - To edit the generated rubric by user directly
- `/rubric/export/link` - To export the generated rubric as a link
- `/rubric/export/pdf` - To export the generated rubric as PDF
- `/rubric/list` - To list the generated rubrics up till now

## Project Structure

```
.
├── Dockerfile                # Docker configuration for containerization
├── LICENSE                   # Project license
├── main.py                   # Main entry point for the backend application
├── my_packages.txt           # List of additional Python packages
├── requirements.txt          # Python dependencies
├── rubri.db                  # SQLite database file
├── seq_diag.png              # Sequence diagram for system overview
├── app/                      # Main application package
│   ├── __init__.py
│   ├── constants.py          # Application-wide constants
│   ├── llm_client_ops.py     # LLM (Large Language Model) client operations
│   ├── logger.py             # Logging setup and utilities
│   ├── models.py             # Pydantic/ORM models for data structures
│   ├── text_ex.py            # Text extraction utilities
│   ├── utils.py              # General utility functions
│   ├── api/                  # API routes and data models
│   │   ├── __init__.py
│   │   └── v1/               # Version 1 of the API
│   │       ├── __init__.py
│   │       ├── datamodels.py # API request/response models
│   │       └── routes.py     # API route definitions
│   ├── configs/              # Configuration files
│   │   ├── app.dev.yaml      # Development config
│   │   ├── app.prod.yaml     # Production config
│   │   └── prompt_templates/ # Prompt templates for LLM
│   ├── db_ops/               # Database operations
│   │   ├── __init__.py
│   │   ├── crud.py           # CRUD operations
│   │   ├── database.py       # DB connection setup
│   │   └── db_config.py      # DB configuration
│   └── services/             # Service layer
│       ├── __init__.py
│       ├── file_upload_ops.py# File upload logic
│       └── llm_rubric_ops.py # LLM-based rubric generation logic
├── logs/                     # Log files
├── received_data/            # Uploaded and processed files
├── tests/                    # Unit and integration tests
│   ├── conftest.py
│   ├── test_constants.py
│   ├── test_text_ex.py
│   ├── test_utils.py
│   └── artefacts/            # Test artefact files
```

### Code Overview
- **main.py**: Starts the FastAPI server and loads configuration.
- **app/api/v1/routes.py**: Defines API endpoints for file upload, rubric generation, editing, export, and listing.
- **app/services/llm_rubric_ops.py**: Handles rubric generation and modification using LLMs.
- **app/services/file_upload_ops.py**: Manages file uploads and extraction.
- **app/db_ops/**: Contains database models and CRUD operations for rubric templates and history.
- **app/configs/prompt_templates/**: Prompt templates for LLM-based rubric generation.
- **tests/**: Contains unit tests and test artefacts.

For more details, see inline comments in each file.

### Configuration

#### Config Files (`app/configs/`)
- **app.dev.yaml**: Development environment configuration. Typically includes:
  - `debug`: Enables debug mode for verbose logging and error reporting.
  - `database_url`: URI for the development database (e.g., SQLite for local testing).
  - `log_level`: Logging verbosity (e.g., DEBUG, INFO).
  - `llm_api_key`: (Optional) API key for LLM provider (can be overridden by .env).
  - Other development-specific settings such as allowed hosts, CORS origins, or feature flags.
  
  This file is used when `ENV=dev` is set in your `.env` file. It allows safe, local development without affecting production resources.

- **app.prod.yaml**: Production environment configuration. Contains production database URI, logging levels, and other production-specific settings.
- **prompt_templates/**: Directory containing prompt templates (e.g., `rubric_jd.md`, `rubric_jd_res.md`) used for LLM-based rubric generation.

#### Environment Variables (`.env`)
Create a `.env` file in the project root to override or supply sensitive configuration. Common variables include:

- `ENV`: Set to `dev` or `prod` to select the configuration file.
- `DATABASE_URL`: URI for the database connection (overrides config file if set).
- `LLM_API_KEY`: API key for the LLM provider (e.g., OpenAI, Azure, etc.).
- `LOG_LEVEL`: Logging level (e.g., `INFO`, `DEBUG`, `WARNING`).
- `PORT`: Port for the FastAPI server to run on (default: 8000).

Example `.env` file:
```
ENV=dev
DATABASE_URL=sqlite:///rubri.db
LLM_API_KEY=your-llm-api-key-here
LOG_LEVEL=INFO
PORT=8000
```

Configuration is loaded at startup based on the `ENV` variable, with environment variables taking precedence over YAML config values.

## Getting Started

### Prerequisites
- Python 3.8 or higher
- pip package manager

### Installation
1. Clone the repository:
   ```
   git clone <repository-url>
   cd rubri-backend
   ```
2. Create and activate a virtual environment:
   ```
   python3 -m venv venv
   source venv/bin/activate
   ```
3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
4. Create a `.env` file in the project root and configure environment variables as needed (see Configuration section).

### Running the Server
Start the FastAPI server with:
```
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## Usage

### API Examples

- Upload Job Description file:
  ```
  curl -X POST "http://localhost:8000/upload/file/jd" -F "file=@path/to/jd.pdf"
  ```

- Create rubric based on JD and/or Resume:
  ```
  curl -X POST "http://localhost:8000/rubric/create" -H "Content-Type: application/json" -d '{"jd_text": "...", "resume_text": "..."}'
  ```

- Export rubric as PDF:
  ```
  curl -X GET "http://localhost:8000/rubric/export/pdf?rubric_id=<id>"
  ```

## Testing

Run tests using pytest:
```
pytest tests/
```

## Contributing

Contributions are welcome! Please fork the repository and submit pull requests. For major changes, please open an issue first to discuss what you would like to change.

## License

This project is licensed under the terms of the MIT License. See the LICENSE file for details.
