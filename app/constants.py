import os
from enum import Enum

class Constants(Enum):

    LOGS_FOLDER = "logs"
    LOGS_FILE = "evalflow.log"
    LOG_LEVEL = "DEBUG"
    CONFIG_APP = os.path.join("app",(
        os.path.join("configs", "app.prod.yaml")
        if os.getenv("APP_ENV") == "PROD"
        else os.path.join("configs", "app.dev.yaml")
    ))
    RECEIVED_DATA = "received_data"
    RESUME_PATH = "resume"
    RESUME_AND_JD = "resume_and_jd"
    JD = "job_description"
    SPACE = " "
    ALLOWED_FILE_TYPES = {
        "pdf": "pdf",
        "txt": "txt",
        "docx": "docx",
        "doc": "doc"
    }
    APP_NAME = "Rubri-Backend"
    APP_VERSION = "0.1.0"
    APP_DEBUG = False
    APP_HOST = "0.0.0.0"
    APP_PORT = 8000
    STORAGE_BASE_DIR = "received_data"
    LLM_PROVIDER = "openai"
    LLM_MODEL = "gpt-4"
    LLM_TEMPERATURE = 0.2
    SENSITIVE_FILTERS = ["password", "api_key"]
    PROMPTS_DIR = os.path.join("app", "configs", "prompt_templates")