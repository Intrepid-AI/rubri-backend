import logging, logging.handlers
import yaml
from pathlib import Path
import sys
import os
import coloredlogs
import re

FILE = Path(__file__).resolve()
ROOT = FILE.parents[0]  # project root directory
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))  # add ROOT to PATH

from app.constants import Constants
os.makedirs(Constants.LOGS_FOLDER.value, exist_ok=True)

# Define the new logging level "SUCCESS" with a custom numeric value
SUCCESS = logging.ERROR + 10
logging.addLevelName(SUCCESS, "SUCCESS")
def success(self, message, *args, **kws):
    # Yes, logger takes its '*args' as 'args'.
    self._log(SUCCESS, message, args, **kws) 
logging.Logger.success = success

file_loc = os.path.join(Constants.LOGS_FOLDER.value, Constants.LOGS_FILE.value)

# Create a ColoredFormatter instance and set color codes
colored_formatter = coloredlogs.ColoredFormatter(
    fmt="%(asctime)s -- %(levelname)s -- %(name)s -- %(funcName)s -- (%(lineno)d) -- %(message)s",
    datefmt='%Y-%m-%d %H:%M:%S',
    level_styles={
        'debug': {'color': 'white'},
        'info': {'color': 'green'},
        'warning': {'color': 'yellow'},
        'success': {'color': 'green', 'bold': True},
        'error': {'color': 'white', 'bold': True, 'background': 'red'}
    },
    field_styles={
        'asctime': {'color': 'white'},
        'levelname': {'color': 'black', 'bold': True},
        'message': {'color': 'white'},
    }
)

class SensitiveDataFilter(logging.Filter):
    def __init__(self, sensitive_fields):
        super().__init__()
        self.sensitive_fields = sensitive_fields

    def filter(self, record):
       msg = record.getMessage()
       for field in self.sensitive_fields:
           pattern = re.compile(rf"('{field}'\s*:\s*)(['\"])(.*?)(\2)")
           msg = pattern.sub(r"\1\2***REDACTED***\2", msg)
       record.msg = msg
       record.args = ()  # clear args to avoid additional formatting
       return True
    

def get_logger(name):
    log_level = Constants.LOG_LEVEL.value
    LOGGER = logging.getLogger(name)
    eval("LOGGER.setLevel(logging.{0})".format(log_level))

    # Remove any existing handlers to avoid duplication
    for handler in LOGGER.handlers:
        LOGGER.removeHandler(handler)

    handler_file = logging.handlers.RotatingFileHandler(
        file_loc,
        mode="a",
        maxBytes=10 * 1024 * 1024,
        backupCount=50,
        encoding=None,
        delay=0,
    )

    log_formatter = logging.Formatter(
        "%(asctime)s -- %(levelname)s -- %(name)s -- %(funcName)s -- (%(lineno)d) -- %(message)s"
    )

    handler_file.setFormatter(log_formatter)
    eval("handler_file.setLevel(logging.{0})".format(log_level))
    
    # Add the filter to the file handler
    sensitive_filter = SensitiveDataFilter(['password', 'api_key']) # Customize sensitive fields
    handler_file.addFilter(sensitive_filter)

    LOGGER.addHandler(handler_file)

    colored_handler = logging.StreamHandler(sys.stdout)
    colored_handler.setFormatter(colored_formatter)
    eval("colored_handler.setLevel(logging.{0})".format(log_level))
    
    # Add the filter to the console handler
    colored_handler.addFilter(sensitive_filter)

    LOGGER.addHandler(colored_handler)
    LOGGER.propagate = False

    return LOGGER

if __name__ == "__main__":
    logger = get_logger(__name__)
    logger.info("This is a test log message.")
    sensitive_data = {"password": "mysecretpassword", "api_key": "mysecretapikey"}
    logger.info(f"Sensitive data: {sensitive_data}")
