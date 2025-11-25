"""
Database Service: SQL Server connection and query execution
"""

import pyodbc
import pandas as pd
from typing import List, Dict, Any,Optional
from contextlib import contextmanager
import logging

from app.config import settings

logger = logging.getLogger(__name__)


class DatabaseService:
    def __init__(self):
        self.connection_string = None
        self._build_connection_string()

    def _build_connection_string(self):
        """Build SQL Server connection string"""
        # Option 1: Windows Authentication
        if settings.DB_USE_WINDOWS_AUTH:
            self.connection_string = (
                f"DRIVER={{ODBC Driver 17 for SQL Server}};"
                f"SERVER={settings.DB_SERVER};"
                f"DATABASE={settings.DB_NAME};"
                f"Trusted_Connection=yes;"
            )
        # Option 2: SQL Server Authentication
        else:
            self.connection_string = (
                f"DRIVER={{ODBC Driver 17 for SQL Server}};"
                f"SERVER={settings.DB_SERVER};"
                f"DATABASE={settings.DB_NAME};"
                f"UID={settings.DB_USER};"
                f"PWD={settings.DB_PASSWORD};"
            )

    @contextmanager
    def get_connection(self):
        """Context manager for database connections"""
        conn = None
        try:
            conn = pyodbc.connect(self.connection_string, timeout=30)
            yield conn
        except pyodbc.Error as e:
            logger.error(f"Database connection error: {e}")
            raise
        finally:
            if conn:
                conn.close()

    async def execute_query(
        self, query: str, params: tuple = None
    ) -> List[Dict[str, Any]]:
        """
        Execute SELECT query and return results as list of dicts
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)

                # Get column names
                columns = [column[0] for column in cursor.description]

                # Fetch all rows
                rows = cursor.fetchall()

                # Convert to list of dicts
                results = []
                for row in rows:
                    results.append(dict(zip(columns, row)))

                logger.info(
                    f"Query executed successfully. Returned {len(results)} rows."
                )
                return results

        except pyodbc.Error as e:
            logger.error(f"Query execution error: {e}")
            raise Exception(f"Database query failed: {str(e)}")

    async def execute_query_df(self, query: str, params: tuple = None) -> pd.DataFrame:
        """
        Execute query and return pandas DataFrame
        """
        try:
            with self.get_connection() as conn:
                if params:
                    df = pd.read_sql(query, conn, params=params)
                else:
                    df = pd.read_sql(query, conn)

                logger.info(f"Query executed successfully. DataFrame shape: {df.shape}")
                return df

        except Exception as e:
            logger.error(f"Query execution error: {e}")
            raise Exception(f"Database query failed: {str(e)}")

    async def get_schema_info(self) -> Dict[str, List[Dict]]:
        """
        Get database schema information for all tables
        """
        schema_query = """
            SELECT 
                t.TABLE_NAME,
                c.COLUMN_NAME,
                c.DATA_TYPE,
                c.IS_NULLABLE,
                c.CHARACTER_MAXIMUM_LENGTH
            FROM 
                INFORMATION_SCHEMA.TABLES t
            INNER JOIN 
                INFORMATION_SCHEMA.COLUMNS c 
                ON t.TABLE_NAME = c.TABLE_NAME
            WHERE 
                t.TABLE_TYPE = 'BASE TABLE'
                AND t.TABLE_SCHEMA = 'dbo'
            ORDER BY 
                t.TABLE_NAME, c.ORDINAL_POSITION
            """

        results = await self.execute_query(schema_query)

        # Organize by table
        schema = {}
        for row in results:
            table = row["TABLE_NAME"]
            if table not in schema:
                schema[table] = []

            schema[table].append(
                {
                    "column": row["COLUMN_NAME"],
                    "type": row["DATA_TYPE"],
                    "nullable": row["IS_NULLABLE"] == "YES",
                    "max_length": row["CHARACTER_MAXIMUM_LENGTH"],
                }
            )

        return schema

    async def get_sample_data(self, table_name: str, limit: int = 3) -> List[Dict]:
        """
        Get sample data from a table
        """
        query = f"SELECT TOP {limit} * FROM [{table_name}]"
        return await self.execute_query(query)

    def test_connection(self) -> bool:
        """Test database connection"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                cursor.fetchone()
                logger.info("✅ Database connection successful")
                return True
        except Exception as e:
            logger.error(f"❌ Database connection failed: {e}")
            return False
    
    def read_table_data(
        self, 
        table_name: str, 
        columns: Optional[List[str]] = None,
        where_clause: Optional[str] = None,
        limit: Optional[int] = None,
        sample: bool = False
    ) -> pd.DataFrame:
        """
        Read data from a table efficiently
        
        Args:
            table_name: Name of the table to read
            columns: List of columns to select (None = all columns)
            where_clause: WHERE clause filter (without WHERE keyword)
            limit: Maximum number of rows to return
            sample: Use sampling for large datasets
        
        Returns:
            DataFrame containing the data
        """
        try:
            # Build column selection
            col_str = ", ".join(columns) if columns else "*"
            
            # Build query
            if sample and limit:
                # Use TABLESAMPLE for efficient random sampling
                query = f"""
                    SELECT TOP {limit} {col_str}
                    FROM {table_name} TABLESAMPLE ({limit} ROWS)
                """
            elif limit:
                query = f"SELECT TOP {limit} {col_str} FROM {table_name}"
            else:
                query = f"SELECT {col_str} FROM {table_name}"
            
            # Add WHERE clause if provided
            if where_clause:
                query += f" WHERE {where_clause}"
            
            logger.info(f"Executing query: {query}")
            
            with self.get_connection() as conn:
                df = pd.read_sql(query, conn)
            
            logger.info(f"Retrieved {len(df)} rows from {table_name}")
            return df
            
        except Exception as e:
            logger.error(f"Error reading table {table_name}: {e}")
            raise
    
    def read_with_query(self, query: str) -> pd.DataFrame:
        """
        Execute a custom query and return results as DataFrame
        
        Args:
            query: SQL query to execute
        
        Returns:
            DataFrame containing the results
        """
        try:
            logger.info(f"Executing custom query: {query[:200]}...")
            
            with self.get_connection() as conn:
                df = pd.read_sql(query, conn)
            
            logger.info(f"Query returned {len(df)} rows")
            return df
            
        except Exception as e:
            logger.error(f"Error executing query: {e}")
            raise
    
    def get_table_schema(self, table_name: str) -> List[Dict[str, Any]]:
        """
        Get schema information for a table
        
        Args:
            table_name: Name of the table
        
        Returns:
            List of column information dictionaries
        """
        query = f"""
            SELECT 
                COLUMN_NAME,
                DATA_TYPE,
                IS_NULLABLE,
                CHARACTER_MAXIMUM_LENGTH,
                COLUMN_DEFAULT
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_NAME = '{table_name}'
            ORDER BY ORDINAL_POSITION
        """
        
        try:
            with self.get_connection() as conn:
                df = pd.read_sql(query, conn)
            
            return df.to_dict('records')
            
        except Exception as e:
            logger.error(f"Error getting schema for {table_name}: {e}")
            raise
    
    def get_row_count(self, table_name: str, where_clause: Optional[str] = None) -> int:
        """
        Get row count for a table efficiently
        
        Args:
            table_name: Name of the table
            where_clause: Optional WHERE clause filter
        
        Returns:
            Number of rows
        """
        query = f"SELECT COUNT(*) as cnt FROM {table_name}"
        
        if where_clause:
            query += f" WHERE {where_clause}"
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query)
                result = cursor.fetchone()
                return result[0] if result else 0
                
        except Exception as e:
            logger.error(f"Error getting row count: {e}")
            raise
    
    def read_data_in_chunks(self, table_name: str, chunk_size: int = 1000,columns: Optional[List[str]] = None):
        """
        Generator to read large tables in chunks
        
        Args:
            table_name: Name of the table
            chunk_size: Number of rows per chunk
            columns: List of columns to select
        
        Yields:
            DataFrame chunks
        """
        col_str = ", ".join(columns) if columns else "*"
        query = f"SELECT {col_str} FROM {table_name}"
        
        try:
            with self.get_connection() as conn:
                for chunk_df in pd.read_sql(query, conn, chunksize=chunk_size):
                    yield chunk_df
                    
        except Exception as e:
            logger.error(f"Error reading chunks from {table_name}: {e}")
            raise
    
    def get_sample_data(
        self, 
        table_name: str, 
        sample_size: int = 100,
        columns: Optional[List[str]] = None
    ) -> pd.DataFrame:
        """
        Get a random sample of data from a table
        
        Args:
            table_name: Name of the table
            sample_size: Number of rows to sample
            columns: List of columns to select
        
        Returns:
            DataFrame with sampled data
        """
        return self.read_table_data(
            table_name=table_name,
            columns=columns,
            limit=sample_size,
            sample=True
        )
    
    def get_view_data(self,view_name: str,where: Optional[str] = None,limit: Optional[int] = None ) -> pd.DataFrame:
        """
        Execute a SQL view with optional WHERE and LIMIT/TOP.

        Args:
            view_name: Name of the SQL view
            where: SQL WHERE condition (e.g., "status = 'Active'")
            limit: Max rows to return

        Returns:
            DataFrame containing the result
        """

        # Base query
        query = f"SELECT * FROM {view_name}"

        # Add WHERE clause
        if where:
            query += f" WHERE {where}"

        # Add TOP clause (for SQL Server)
        if limit:
            # Insert TOP n after SELECT
            query = query.replace("SELECT", f"SELECT TOP {limit}", 1)

        try:
            with self.get_connection() as conn:
                df = pd.read_sql(query, conn)

            return df

        except Exception as e:
            logger.error(f"Error executing view '{view_name}': {e}")
            raise

# Singleton instance
db_service = DatabaseService()
