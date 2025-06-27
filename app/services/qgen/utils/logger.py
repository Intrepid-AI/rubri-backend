"""
Logger utility for QGen agents - adapts to use app.logger
"""

from app.logger import get_logger as app_get_logger

def get_logger(name):
    """Get logger instance using app.logger instead of qgen's own logger."""
    return app_get_logger(name)