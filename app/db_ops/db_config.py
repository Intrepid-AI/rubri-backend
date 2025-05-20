import os
import yaml
from pathlib import Path
from dotenv import load_dotenv
from app.logger import get_logger
from app.constants import Constants

logger = get_logger(__name__)

DEFAULT_CONFIG = {
    "database": {
        "type": "sqlite",  # Default to SQLite
        "sqlite_path": "rubri.db",
        "pool_size": 5,
        "max_overflow": 10,
        # PostgreSQL configuration (used if type is postgresql)
        "host": "localhost",
        "port": 5432,
        "username": "postgres",
        "password": "password",
        "database": "rubri",
    }
}

def load_database_config():
    """Load database configuration from environment variables and YAML."""
    config = DEFAULT_CONFIG.copy()
    _load_yaml_config(config)
    _override_from_env(config)
    _setup_database_url(config)
    return config

def _load_yaml_config(config):
    config_path = Constants.CONFIG_APP.value
    try:
        with open(config_path, "r") as f:
            yaml_config = yaml.safe_load(f)
            if yaml_config:
                _update_dict_recursive(config, yaml_config)
        logger.info(f"Loaded configuration from {config_path}")
    except Exception as e:
        logger.warning(f"Failed to load configuration from {config_path}: {str(e)}")

def _update_dict_recursive(target, source):
    for key, value in source.items():
        if isinstance(value, dict) and key in target and isinstance(target[key], dict):
            _update_dict_recursive(target[key], value)
        else:
            target[key] = value

def _override_from_env(config):
    if os.getenv("DB_TYPE"):
        config["database"]["type"] = os.getenv("DB_TYPE")
    if os.getenv("DB_SQLITE_PATH"):
        config["database"]["sqlite_path"] = os.getenv("DB_SQLITE_PATH")
    if os.getenv("DB_USE_SQLITE_FALLBACK"):
        config["database"]["use_sqlite_fallback"] = os.getenv("DB_USE_SQLITE_FALLBACK").lower() == "true"

    if os.getenv("DB_HOST"):
        config["database"]["host"] = os.getenv("DB_HOST")
    if os.getenv("DB_PORT"):
        config["database"]["port"] = int(os.getenv("DB_PORT"))
    if os.getenv("DB_USERNAME"):
        config["database"]["username"] = os.getenv("DB_USERNAME")
    if os.getenv("DB_PASSWORD"):
        config["database"]["password"] = os.getenv("DB_PASSWORD")
    if os.getenv("DB_NAME"):
        config["database"]["database"] = os.getenv("DB_NAME")

def _setup_database_url(config):
    db_config = config["database"]
    db_type = db_config["type"]

    if db_type == "sqlite":
        sqlite_path = db_config.get("sqlite_path", "rubri.db")
        config["database"]["url"] = f"sqlite:///{sqlite_path}"
    elif db_type == "postgresql":
        config["database"]["url"] = (
            f"postgresql+psycopg2://"
            f"{db_config['username']}:{db_config['password']}@"
            f"{db_config['host']}:{db_config['port']}/"
            f"{db_config['database']}"
        )
    else:
        logger.warning(f"Unknown database type: {db_type}, defaulting to SQLite")
        sqlite_path = db_config.get("sqlite_path", "rubri.db")
        config["database"]["url"] = f"sqlite:///{sqlite_path}"

    os.environ["DATABASE_URL"] = config["database"]["url"]
    logger.info(f"Database URL set to: {config['database']['url']}")

if __name__ == "__main__":
    config = load_database_config()
    import pprint
    pp = pprint.PrettyPrinter(indent=2)
    pp.pprint(config)
