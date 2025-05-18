import os
from enum import Enum

class Constants(Enum):

    LOGS_FOLDER = "logs"
    LOGS_FILE = "evalflow.log"
    LOG_LEVEL = "DEBUG"
    CONFIG_APP = (
        os.path.join("configs", "app.prod.yaml")
        if os.getenv("APP_ENV") == "PROD"
        else os.path.join("configs", "app.dev.yaml")
    )
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