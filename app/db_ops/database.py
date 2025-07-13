import os
import time

from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from app.logger import get_logger
from app.db_ops import db_config
from app.constants import Constants

logger = get_logger(__name__)

db_config_dict = db_config.load_database_config()

DATABASE_URL = db_config_dict["database"]["url"]

USE_SQLITE_FALLBACK = os.getenv("DATABASE_USE_SQLITE_FALLBACK", "true").lower() == "true"
SQLITE_DB_PATH = os.getenv("DATABASE_SQLITE_PATH", "rubri.db")

def create_db_engine():
    """
    Create database engine with fallback to SQLite if PostgreSQL is not available
    """
    # Force sqlite for now to avoid configuration issues
    db_type = "sqlite"  # os.getenv("DATABASE_TYPE", "sqlite")
    
    if db_type == "postgresql":

        try:
            logger.info(f"Attempting to connect to PostgreSQL database: {DATABASE_URL}")
            engine = create_engine(
                DATABASE_URL,
                pool_pre_ping=True,                           # Helps with connection drops
                pool_recycle=3600,                            # Recycle connections after 1 hour
                pool_size=int(os.getenv("DATABASE_POOL_SIZE", "5")),
                max_overflow=int(os.getenv("DATABASE_MAX_OVERFLOW", "10")),
                echo=Constants.APP_DEBUG.value,          # Log SQL queries in debug mode
                connect_args={"connect_timeout": 5}           # Timeout for connection attempts
            )
            
            # Test connection
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
                logger.info("Successfully connected to PostgreSQL database")
            
            return engine
        except Exception as e:
            logger.error(f"Error connecting to PostgreSQL database: {str(e)}")
            raise
    
    else:
        # Use project directory for database file - accessible from both Windows and WSL
        # This allows easy access and backup of the database
        # Get path from config, with environment override support
        config_sqlite_path = db_config_dict["database"].get("sqlite_path", "rubri.db")
        sqlite_path = os.environ.get("DB_PATH", os.path.abspath(config_sqlite_path))
        sqlite_url = f"sqlite:///{sqlite_path}"
        logger.info(f"Using SQLite database at: {sqlite_url}")
        
        # Ensure directory exists (in case DB_PATH points to a subdirectory)
        os.makedirs(os.path.dirname(sqlite_path), exist_ok=True)
        
        # Check if database exists 
        if os.path.exists(sqlite_path):
            logger.info(f"Using existing database file: {sqlite_path}")
        else:
            logger.info(f"Database file will be created: {sqlite_path}")
            # Create empty file with proper permissions
            try:
                with open(sqlite_path, 'w') as f:
                    pass
                # Use more permissive mode for cross-platform compatibility
                os.chmod(sqlite_path, 0o666)
            except Exception as e:
                logger.warning(f"Could not pre-create database file: {e}")
        
        # Configure engine for WSL compatibility (no WAL mode for stability)
        engine = create_engine(
            sqlite_url,
            connect_args={
                "check_same_thread": False,
                "timeout": 60,  # Reasonable timeout for Linux filesystem
            },
            echo=False,  # Disable SQL logging to reduce noise
            pool_pre_ping=True,     # Verify connections before use
            pool_recycle=3600,      # Recycle connections after 1 hour
            pool_size=10,           # Increased pool size for concurrent requests
            max_overflow=20,        # Allow overflow for peak loads
            pool_timeout=30,        # Timeout for getting connection from pool
        )
        
        # Set basic SQLite optimizations (avoiding WAL mode for WSL compatibility)
        try:
            with engine.connect() as conn:
                # Use DELETE journal mode for better WSL compatibility
                conn.execute(text("PRAGMA journal_mode=DELETE"))
                # Set synchronous mode to FULL for data integrity
                conn.execute(text("PRAGMA synchronous=FULL"))
                # Increase cache size for better performance
                conn.execute(text("PRAGMA cache_size=10000"))
                # Store temporary tables in memory
                conn.execute(text("PRAGMA temp_store=MEMORY"))
                # Set reasonable busy timeout
                conn.execute(text("PRAGMA busy_timeout=30000"))  # 30 seconds
                # Enable foreign key constraints
                conn.execute(text("PRAGMA foreign_keys=ON"))
                conn.commit()
                logger.info("Configured SQLite with WSL-compatible settings")
        except Exception as e:
            logger.warning(f"Could not configure SQLite settings: {e}")
        
        return engine

# Create engine
engine = create_db_engine()

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create base class for declarative models
Base = declarative_base()

def get_db():
    """
    Dependency function to get a database session.
    
    Usage:
        @app.get("/endpoint")
        def endpoint(db: Session = Depends(get_db)):
            # Use db session here
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_db_session():
    """
    Get a database session for use in Celery tasks or other contexts 
    where we need a session that we manually manage.
    
    Returns:
        Session object that must be closed after use
    """
    return SessionLocal()

def init_db():
    """
    Initialize the database by creating all tables.
    Call this function when starting the application.
    """
    try:
        # Import models to ensure they're registered with Base
        from app.db_ops.models import Document, Rubric, RubricHistory, SharedLink, TaskStatus, User, UserSession
        
        # Create all tables
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
        
        # Test a simple query to verify database is working
        try:
            with SessionLocal() as session:
                # Try a simple query
                result = session.execute(text("SELECT 1")).fetchone()
                logger.info(f"Database test query result: {result}")
        except Exception as test_e:
            logger.warning(f"Database test query failed: {test_e}")
            
        return True
    except Exception as e:
        logger.error(f"Error initializing database: {str(e)}")
        logger.error("Check your database configuration and ensure the database server is running")
        
        # If we're using SQLite, we should still be able to proceed
        if "sqlite" in str(engine.url):
            logger.warning("Using SQLite database, attempting to continue...")
            return True
        else:
            # Re-raise the exception for PostgreSQL
            raise