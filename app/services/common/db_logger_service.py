"""
Database Logger Service - Logs exceptions and messages to database
"""
import logging
import traceback
from datetime import datetime
from typing import Optional
import pyodbc
from contextlib import contextmanager

from app.config import settings


class DatabaseLogHandler(logging.Handler):
    """Custom logging handler that writes to database"""

    def __init__(self, connection_string: str):
        super().__init__()
        self.connection_string = connection_string

    @contextmanager
    def get_connection(self):
        """Context manager for database connections"""
        conn = None
        try:
            conn = pyodbc.connect(self.connection_string, timeout=10)
            yield conn
        except pyodbc.Error as e:
            # Fallback to console if DB connection fails
            print(f"Database logging connection error: {e}")
            raise
        finally:
            if conn:
                conn.close()

    def emit(self, record: logging.LogRecord):
        """
        Write log record to database
        """
        try:
            # Format the exception if present
            exception_text = None
            if record.exc_info:
                exception_text = ''.join(traceback.format_exception(*record.exc_info))

            # Prepare log data
            level = record.levelname
            message = self.format(record)
            created_at = datetime.fromtimestamp(record.created)

            # Insert into database
            self._insert_log(level, message, exception_text, created_at)

        except Exception as e:
            # Don't let logging errors break the application
            print(f"Failed to write log to database: {e}")
            self.handleError(record)

    def _insert_log(self, level: str, message: str, exception: Optional[str], created_at: datetime):
        """Insert log entry into AppLogs table"""
        level='AI_'+level
        query = """
            INSERT INTO AppLogs (Level, Message, Exception, CreatedAt)
            VALUES (?, ?, ?, ?)
        """
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, (level, message, exception, created_at))
                conn.commit()
        except Exception as e:
            print(f"Error inserting log: {e}")


class DatabaseLoggerService:
    """Service for logging to database"""

    def __init__(self):
        self.connection_string = self._build_connection_string()
        self._ensure_table_exists()

    def _build_connection_string(self) -> str:
        """Build SQL Server connection string"""
        if settings.DB_USE_WINDOWS_AUTH:
            return (
                f"DRIVER={{ODBC Driver 17 for SQL Server}};"
                f"SERVER={settings.DB_SERVER};"
                f"DATABASE={settings.DB_NAME};"
                f"Trusted_Connection=yes;"
            )
        else:
            return (
                f"DRIVER={{ODBC Driver 17 for SQL Server}};"
                f"SERVER={settings.DB_SERVER};"
                f"DATABASE={settings.DB_NAME};"
                f"UID={settings.DB_USER};"
                f"PWD={settings.DB_PASSWORD};"
            )

    def _ensure_table_exists(self):
        """Create AppLogs table if it doesn't exist"""
        create_table_query = """
        IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='AppLogs' AND xtype='U')
        CREATE TABLE AppLogs (
            Id INT IDENTITY(1,1) PRIMARY KEY,
            Level NVARCHAR(50) NOT NULL DEFAULT 'Info',
            Message NVARCHAR(MAX),
            Exception NVARCHAR(MAX),
            CreatedAt DATETIME NOT NULL DEFAULT GETDATE()
        )
        """
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(create_table_query)
                conn.commit()
        except Exception as e:
            print(f"Warning: Could not ensure AppLogs table exists: {e}")

    @contextmanager
    def get_connection(self):
        """Context manager for database connections"""
        conn = None
        try:
            conn = pyodbc.connect(self.connection_string, timeout=10)
            yield conn
        except pyodbc.Error as e:
            print(f"Database connection error: {e}")
            raise
        finally:
            if conn:
                conn.close()

    def log_exception(self, level: str, message: str, exception: Exception):
        """
        Log an exception to the database
        
        Args:
            level: Log level (ERROR, WARNING, INFO, etc.)
            message: Log message
            exception: Exception object
        """
        level='AI_'+level
        exception_text = ''.join(traceback.format_exception(
            type(exception), exception, exception.__traceback__
        ))
        
        query = """
            INSERT INTO AppLogs (Level, Message, Exception, CreatedAt)
            VALUES (?, ?, ?, GETDATE())
        """
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, (level, message, exception_text))
                conn.commit()
        except Exception as e:
            print(f"Failed to log exception to database: {e}")

    def log_message(self, level: str, message: str):
        """
        Log a message to the database without exception
        
        Args:
            level: Log level (ERROR, WARNING, INFO, etc.)
            message: Log message
        """
        level='AI_'+level
        query = """
            INSERT INTO AppLogs (Level, Message, CreatedAt)
            VALUES (?, ?, GETDATE())
        """
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, (level, message))
                conn.commit()
        except Exception as e:
            print(f"Failed to log message to database: {e}")

    def get_handler(self) -> DatabaseLogHandler:
        """Get a logging handler for Python's logging framework"""
        return DatabaseLogHandler(self.connection_string)


# Singleton instance
db_logger_service = DatabaseLoggerService()