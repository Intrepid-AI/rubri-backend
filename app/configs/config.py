import os
import yaml
from pathlib import Path
from dotenv import load_dotenv
from app.logger import get_logger
from app.constants import Constants

logger = get_logger(__name__)

class Config:
    """
    Configuration class for loading and accessing application settings.
    
    This class loads configuration from:
    1. Environment variables
    2. YAML configuration files
    3. Default values
    """
    
    # Default configuration
    DEFAULT_CONFIG = {
        "app": {
            "name": "Rubri-Backend",
            "version": "0.1.0",
            "debug": False,
            "host": "0.0.0.0",
            "port": 8000,
        },
        "database": {
            "type": "sqlite",  # Default to SQLite
            "sqlite_path": "rubri.db",
            "use_sqlite_fallback": True,
            "pool_size": 5,
            "max_overflow": 10,
            # PostgreSQL configuration (used if type is postgresql)
            "host": "localhost",
            "port": 5432,
            "username": "postgres",
            "password": "password",
            "database": "rubri",
        },
        "storage": {
            "base_dir": "received_data",
        },
        "llm": {
            "provider": "openai",
            "model": "gpt-4",
            "temperature": 0.2,
        },
    }
    
    def __init__(self):
        """Initialize configuration by loading from various sources"""
        # Load environment variables from .env file
        load_dotenv()
        
        # Load configuration from YAML file
        self.config = self.DEFAULT_CONFIG.copy()
        self._load_yaml_config()
        
        # Override with environment variables
        self._override_from_env()
        
        # Set up database URL
        self._setup_database_url()
        
        logger.info("Configuration loaded successfully")
    
    def _load_yaml_config(self):
        """Load configuration from YAML file"""
        config_path = Constants.CONFIG_APP.value
        try:
            with open(config_path, "r") as f:
                yaml_config = yaml.safe_load(f)
                if yaml_config:
                    # Update config recursively
                    self._update_dict_recursive(self.config, yaml_config)
            logger.info(f"Loaded configuration from {config_path}")
        except Exception as e:
            logger.warning(f"Failed to load configuration from {config_path}: {str(e)}")
    
    def _update_dict_recursive(self, target, source):
        """Update dictionary recursively"""
        for key, value in source.items():
            if isinstance(value, dict) and key in target and isinstance(target[key], dict):
                self._update_dict_recursive(target[key], value)
            else:
                target[key] = value
    
    def _override_from_env(self):
        """Override configuration with environment variables"""
        # Database configuration
        if os.getenv("DB_TYPE"):
            self.config["database"]["type"] = os.getenv("DB_TYPE")
        if os.getenv("DB_SQLITE_PATH"):
            self.config["database"]["sqlite_path"] = os.getenv("DB_SQLITE_PATH")
        if os.getenv("DB_USE_SQLITE_FALLBACK"):
            self.config["database"]["use_sqlite_fallback"] = os.getenv("DB_USE_SQLITE_FALLBACK").lower() == "true"
        
        # PostgreSQL configuration
        if os.getenv("DB_HOST"):
            self.config["database"]["host"] = os.getenv("DB_HOST")
        if os.getenv("DB_PORT"):
            self.config["database"]["port"] = int(os.getenv("DB_PORT"))
        if os.getenv("DB_USERNAME"):
            self.config["database"]["username"] = os.getenv("DB_USERNAME")
        if os.getenv("DB_PASSWORD"):
            self.config["database"]["password"] = os.getenv("DB_PASSWORD")
        if os.getenv("DB_NAME"):
            self.config["database"]["database"] = os.getenv("DB_NAME")
        
        # App configuration
        if os.getenv("APP_DEBUG"):
            self.config["app"]["debug"] = os.getenv("APP_DEBUG").lower() == "true"
        if os.getenv("APP_HOST"):
            self.config["app"]["host"] = os.getenv("APP_HOST")
        if os.getenv("APP_PORT"):
            self.config["app"]["port"] = int(os.getenv("APP_PORT"))
        
        # LLM configuration
        if os.getenv("LLM_PROVIDER"):
            self.config["llm"]["provider"] = os.getenv("LLM_PROVIDER")
        if os.getenv("LLM_MODEL"):
            self.config["llm"]["model"] = os.getenv("LLM_MODEL")
        if os.getenv("LLM_TEMPERATURE"):
            self.config["llm"]["temperature"] = float(os.getenv("LLM_TEMPERATURE"))
    
    def _setup_database_url(self):
        """Set up database URL based on configuration"""
        db_config = self.config["database"]
        db_type = db_config["type"]
        
        # Construct database URL based on type
        if db_type == "sqlite":
            sqlite_path = db_config.get("sqlite_path", "rubri.db")
            self.config["database"]["url"] = f"sqlite:///{sqlite_path}"
        elif db_type == "postgresql":
            self.config["database"]["url"] = (
                f"postgresql+psycopg2://"
                f"{db_config['username']}:{db_config['password']}@"
                f"{db_config['host']}:{db_config['port']}/"
                f"{db_config['database']}"
            )
        else:
            logger.warning(f"Unknown database type: {db_type}, defaulting to SQLite")
            sqlite_path = db_config.get("sqlite_path", "rubri.db")
            self.config["database"]["url"] = f"sqlite:///{sqlite_path}"
        
        # Set environment variable for SQLAlchemy
        os.environ["DATABASE_URL"] = self.config["database"]["url"]
        
        logger.info(f"Database URL set to: {self.config['database']['url']}")
    
    def get(self, key, default=None):
        """Get configuration value by key with dot notation"""
        keys = key.split(".")
        value = self.config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value

# Create singleton instance
config = Config()