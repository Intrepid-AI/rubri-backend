import os
import sys
import pytest
import logging
import coloredlogs
from pathlib import Path

# Add the project root directory to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.logger import get_logger

# Test logger configuration
TEST_LOG_LEVEL = "DEBUG"
TEST_LOG_DIR = "logs/tests"
TEST_LOG_FILE = "test.log"

# Add configuration for enabling/disabling app logging
ENABLE_APP_LOGS_DURING_TESTS = False  # Set to True to see app logs during tests

def get_test_logger(name):
    """Create a logger specifically for tests"""
    print(f"Creating test logger for: {name}")  # Debug print
    logger = logging.getLogger(f"test.{name}")
    
    # Remove any existing handlers
    logger.handlers = []
    
    # Set log level
    logger.setLevel(TEST_LOG_LEVEL)
    
    # Create test log directory
    os.makedirs(TEST_LOG_DIR, exist_ok=True)
    print(f"Test log directory created/verified: {TEST_LOG_DIR}")  # Debug print
    
    # File handler
    log_file_path = os.path.join(TEST_LOG_DIR, TEST_LOG_FILE)
    print(f"Creating log file at: {log_file_path}")  # Debug print
    file_handler = logging.FileHandler(log_file_path, mode='a')
    file_formatter = logging.Formatter(
        "%(asctime)s -- TEST -- %(levelname)s -- %(name)s -- %(funcName)s -- (%(lineno)d) -- %(message)s"
    )
    file_handler.setFormatter(file_formatter)
    file_handler.setLevel(TEST_LOG_LEVEL)
    
    # Console handler with colors
    console_handler = logging.StreamHandler(sys.stdout)
    colored_formatter = coloredlogs.ColoredFormatter(
        fmt="%(asctime)s -- TEST -- %(levelname)s -- %(name)s -- %(funcName)s -- (%(lineno)d) -- %(message)s",
        datefmt='%Y-%m-%d %H:%M:%S',
        level_styles={
            'debug': {'color': 'white'},
            'info': {'color': 'cyan'},
            'warning': {'color': 'yellow'},
            'error': {'color': 'white', 'bold': True, 'background': 'red'}
        }
    )
    console_handler.setFormatter(colored_formatter)
    console_handler.setLevel(TEST_LOG_LEVEL)
    
    # Add handlers
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    logger.propagate = False
    
    # Verify logger setup
    logger.info(f"Test logger initialized for {name}")
    print(f"Logger setup completed for: {name}")  # Debug print
    
    return logger

@pytest.fixture(autouse=True)
def setup_test_env():
    """Setup any test environment variables needed"""
    # Store original environment
    original_env = dict(os.environ)
    
    yield
    
    # Restore original environment
    os.environ.clear()
    os.environ.update(original_env)

@pytest.fixture(scope="session", autouse=True)
def setup_test_logging():
    """Setup logging for the entire test session"""
    print("Setting up test logging...")  # Debug print
    
    # Create test log directory if it doesn't exist
    os.makedirs(TEST_LOG_DIR, exist_ok=True)
    print(f"Created test log directory: {TEST_LOG_DIR}")  # Debug print
    
    if not ENABLE_APP_LOGS_DURING_TESTS:
        # Store original handlers of all existing loggers
        original_loggers = {}
        for name, logger in logging.root.manager.loggerDict.items():
            if isinstance(logger, logging.Logger):
                original_loggers[name] = {
                    'handlers': logger.handlers[:],
                    'level': logger.level,
                    'propagate': logger.propagate
                }
                # Temporarily disable existing loggers
                logger.handlers = []
                logger.addHandler(logging.NullHandler())
                logger.propagate = False
    
    # Clear any existing test logs
    test_log_path = os.path.join(TEST_LOG_DIR, TEST_LOG_FILE)
    if os.path.exists(test_log_path):
        print(f"Removing existing test log: {test_log_path}")  # Debug print
        os.remove(test_log_path)
    
    yield
    
    print("Test logging teardown...")  # Debug print
    if not ENABLE_APP_LOGS_DURING_TESTS:
        # Restore original logger configurations
        for name, config in original_loggers.items():
            if name in logging.root.manager.loggerDict:
                logger = logging.getLogger(name)
                logger.handlers = config['handlers']
                logger.setLevel(config['level'])
                logger.propagate = config['propagate']

@pytest.fixture
def test_logger(request):
    """Fixture to provide a test logger to test functions"""
    return get_test_logger(request.node.name) 