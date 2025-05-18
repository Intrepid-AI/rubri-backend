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
    db_type = os.getenv("DATABASE_TYPE", "sqlite")
    
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
        sqlite_path = os.getenv("DATABASE_SQLITE_PATH", "rubri.db")
        sqlite_url = f"sqlite:///{sqlite_path}"
        logger.info(f"Using SQLite database at: {sqlite_url}")
        
        return create_engine(
            sqlite_url,
            connect_args={"check_same_thread": False},
            echo=Constants.APP_DEBUG.value
        )

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

def init_db():
    """
    Initialize the database by creating all tables.
    Call this function when starting the application.
    """
    try:
        # Import models to ensure they're registered with Base
        from app.models import Document, Rubric, RubricHistory, SharedLink
        
        # Create all tables
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
        
        # Test a simple query to verify database is working
        with SessionLocal() as session:
            # Try a simple query
            result = session.execute(text("SELECT 1")).fetchone()
            logger.info(f"Database test query result: {result}")
            
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