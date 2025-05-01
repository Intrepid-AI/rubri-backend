import os
import pytest
from datetime import datetime, timedelta
from unittest.mock import patch

from app.utils import make_directories, Directory_Structure
from app.constants import Constants

@pytest.fixture(autouse=True)
def reset_directory_structure():
    """Reset Directory_Structure class variables before each test"""
    Directory_Structure.date_today = None
    Directory_Structure.date_old = None
    Directory_Structure.todays_folder = None
    yield

@pytest.fixture
def cleanup_test_dirs():
    # Setup
    test_dirs = ["test_dir1", "test_dir2"]
    yield test_dirs
    # Teardown
    for dir_name in test_dirs:
        if os.path.exists(dir_name):
            os.rmdir(dir_name)

def test_make_directories(test_logger, cleanup_test_dirs):
    """Test directory creation functionality"""
    test_logger.info("Starting make_directories test")
    test_dirs = cleanup_test_dirs
    
    # Test creating directories
    test_logger.debug(f"Creating test directories: {test_dirs}")
    make_directories(test_dirs)
    
    for dir_name in test_dirs:
        test_logger.debug(f"Verifying directory: {dir_name}")
        assert os.path.exists(dir_name)
        assert os.path.isdir(dir_name)
    
    test_logger.info("Directory creation test completed successfully")

def test_make_directories_existing(cleanup_test_dirs):
    """Test handling of existing directories"""
    test_dirs = cleanup_test_dirs
    
    # Create directories first time
    make_directories(test_dirs)
    # Try creating same directories again
    make_directories(test_dirs)  # Should not raise any exception
    
    for dir_name in test_dirs:
        assert os.path.exists(dir_name)

@pytest.fixture
def dir_structure():
    return Directory_Structure()

def test_directory_structure_initialization(dir_structure):
    """Test Directory_Structure initialization"""
    assert dir_structure.date_today is None
    assert dir_structure.date_old is None
    assert dir_structure.todays_folder is None

@patch('app.utils.datetime')
def test_isit_newday(mock_datetime, dir_structure):
    """Test new day detection"""
    test_date = datetime(2024, 1, 1)
    mock_datetime.now.return_value = test_date
    
    # First call should always be a new day
    assert dir_structure._isit_newday() is True
    assert Directory_Structure.date_today == test_date.date()
    
    # Second immediate call should not be a new day
    assert dir_structure._isit_newday() is False

@patch('app.utils.datetime')
def test_isit_newday_different_dates(mock_datetime, dir_structure):
    """Test new day detection with different dates"""
    today = datetime(2024, 1, 1)
    tomorrow = datetime(2024, 1, 2)
    
    # Set initial date
    mock_datetime.now.return_value = today
    dir_structure._isit_newday()
    
    # Change to next day
    mock_datetime.now.return_value = tomorrow
    assert dir_structure._isit_newday() is True
    assert Directory_Structure.date_old == today.date()
    assert Directory_Structure.date_today == tomorrow.date()

def test_name_received_data_folder(dir_structure):
    """Test folder naming convention"""
    test_date = datetime(2024, 1, 1).date()
    expected_path = os.path.join(
        Constants.RECEIVED_DATA.value,
        "2024",
        "January_2024",
        "01_01_2024"
    )
    
    actual_path = dir_structure._name_received_data_folder(test_date)
    assert actual_path == expected_path

@pytest.fixture
def mock_received_data():
    """Setup and cleanup for received_data directory structure"""
    # Setup
    base_dir = Constants.RECEIVED_DATA.value
    if not os.path.exists(base_dir):
        os.makedirs(base_dir)
    yield base_dir
    # Cleanup
    if os.path.exists(base_dir):
        import shutil
        shutil.rmtree(base_dir)

@patch('app.utils.datetime')
def test_directory_structure_call(mock_datetime, dir_structure, mock_received_data):
    """Test the __call__ method"""
    # Mock today's date
    test_date = datetime(2024, 1, 1)
    mock_datetime.now.return_value = test_date
    
    # First call should create new directory and return path
    path1 = dir_structure()
    
    # Verify path exists and is correct
    assert path1 is not None
    expected_path = os.path.join(
        Constants.RECEIVED_DATA.value,
        "2024",
        "January_2024",
        "01_01_2024"
    )
    assert path1 == expected_path
    assert os.path.exists(path1)
    assert Directory_Structure.todays_folder == path1
    
    # Second call should return same path
    path2 = dir_structure()
    assert path2 == path1 