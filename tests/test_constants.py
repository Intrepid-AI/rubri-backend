import os
import pytest
from app.constants import Constants

def test_constants_values():
    """Test that all constant values are correctly defined"""
    assert Constants.LOGS_FOLDER.value == "logs"
    assert Constants.LOGS_FILE.value == "evalflow.log"
    assert Constants.LOG_LEVEL.value == "DEBUG"
    assert Constants.RECEIVED_DATA.value == "received_data"
    assert Constants.RESUME_PATH.value == "resume"
    assert Constants.RESUME_AND_JD.value == "resume_and_jd"
    assert Constants.JD.value == "job_description"

def test_config_app_path():
    """Test CONFIG_APP path based on environment"""
    # Test development environment (default)
    if not os.getenv("APP_ENV"):
        assert Constants.CONFIG_APP.value == os.path.join("configs", "app.dev.yaml")
    
    # Note: For production environment, you would need to set APP_ENV=PROD
    # This can be tested in a CI/CD pipeline or with environment manipulation

def test_constants_immutability():
    """Test that constants cannot be modified"""
    with pytest.raises(AttributeError):
        Constants.LOGS_FOLDER.value = "new_logs"

def test_constants_uniqueness():
    """Test that all constant values are unique"""
    values = [const.value for const in Constants]
    assert len(values) == len(set(values)), "All constant values should be unique"

def test_constants_types():
    """Test that all constant values are strings"""
    for const in Constants:
        assert isinstance(const.value, str), f"{const.name} should be a string" 