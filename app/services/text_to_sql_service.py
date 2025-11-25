"""
Text-to-SQL Service: Convert natural language to SQL queries using Mistral via Ollama
"""

import re
import sqlparse
from typing import Dict
import logging

from app.services.common.database_service import db_service
from app.config import settings
from app.services.common.llm_factory import llm_factory
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

logger = logging.getLogger(__name__)


class TextToSQLService:
    def __init__(self):
        self.schema_context = None
        self.schema_string = None
        self.llm = None
        self.model = settings.OLLAMA_MODEL  # "mistral:latest"

    async def initialize(self):
        """Load database schema for context"""
        try:
            self.schema_context = await db_service.get_schema_info()
            self.schema_string = self._format_schema_for_prompt()
            self.llm = llm_factory.create_llm()
            logger.info(f"✅ ext-to-SQL service initialized with {settings.LLM_PROVIDER}")

        except Exception as e:
            logger.error(f"Failed to initialize Text-to-SQL service: {e}")
            raise

    def _format_schema_for_prompt(self) -> str:
        """Format schema information for LLM prompt"""
        schema_lines = ["Database Schema:\n"]

        for table_name, columns in self.schema_context.items():
            # Remove this filter if you want all tables
            # if table_name != "Cities":
            #     continue

            schema_lines.append(f"\nTable: {table_name}")
            schema_lines.append("Columns:")
            for col in columns:
                nullable = "NULL" if col["nullable"] else "NOT NULL"
                max_len = f"({col['max_length']})" if col["max_length"] else ""
                schema_lines.append(
                    f"  - {col['column']}: {col['type']}{max_len} {nullable}"
                )

        return "\n".join(schema_lines)

    def _create_sql_prompt(self, user_query: str) -> str:
        """Create prompt for LLM to generate SQL"""
        prompt = f"""You are a SQL expert. Convert the natural language query to a valid SQL Server query.

            {self.schema_string}

            Rules:
            1. Generate ONLY the SQL query, no explanations or preamble
            2. Use proper SQL Server syntax
            3. Always use SELECT statements (no INSERT, UPDATE, DELETE)
            4. Use TOP N instead of LIMIT for SQL Server
            5. Use square brackets [TableName] for table/column names with spaces
            6. Include WHERE clauses when filtering is needed
            7. Return only executable SQL query without any markdown formatting
            8. Do not include ```sql or ``` markers
            9. Use proper JOIN syntax when querying multiple tables
            10. Use appropriate aggregate functions (COUNT, SUM, AVG) when needed

            User Query: {user_query}

            SQL Query:"""

        return prompt

    async def generate_sql(self, user_query: str) -> str:
        """
        Generate SQL query from natural language using Mistral via Ollama + LangChain
        """

        if not self.schema_context:
            await self.initialize()

        # Create prompt
        prompt = self._create_sql_prompt(user_query)

        try:
            logger.info(f"Generating SQL for query: {user_query}")

            # Build LangChain prompt
            structurePrompt = ChatPromptTemplate.from_messages([
                (
                    "system",
                    "You are a SQL expert. Generate only valid SQL Server queries without any explanation or formatting."
                ),
                ("user", prompt),
            ])

            # Create the chain
            chain = structurePrompt | self.llm | StrOutputParser()

            # Run the chain (returns plain string)
            sql_query = await chain.ainvoke({"input": prompt})

            # Clean SQL output
            sql_query = self._clean_sql(sql_query.strip())

            logger.info(f"Generated SQL: {sql_query}")

            return sql_query

        except Exception as e:
            logger.error(f"SQL generation failed: {e}")
            raise Exception(f"Failed to generate SQL query: {str(e)}")

    def _clean_sql(self, sql: str) -> str:
        """Clean and format SQL query"""
        # Remove markdown code blocks if present
        sql = re.sub(r"```sql\s*", "", sql, flags=re.IGNORECASE)
        sql = re.sub(r"```\s*", "", sql)

        # Remove common preamble phrases
        preamble_patterns = [
            r"^Here is the SQL query:?\s*",
            r"^SQL Query:?\s*",
            r"^Query:?\s*",
        ]
        for pattern in preamble_patterns:
            sql = re.sub(pattern, "", sql, flags=re.IGNORECASE)

        # Remove extra whitespace
        sql = " ".join(sql.split())

        # Format SQL using sqlparse
        try:
            sql = sqlparse.format(
                sql, keyword_case="upper", strip_comments=True, reindent=True
            )
        except:
            pass  # If formatting fails, use the original

        return sql.strip()

    def validate_sql(self, sql: str) -> tuple[bool, str]:
        """
        Validate SQL query for safety

        Returns:
            (is_valid, error_message)
        """
        # Convert to uppercase for checking
        sql_upper = sql.upper()

        # Block dangerous operations
        dangerous_keywords = [
            "DROP",
            "DELETE",
            "TRUNCATE",
            "INSERT",
            "UPDATE",
            "ALTER",
            "CREATE",
            "EXEC",
            "EXECUTE",
            "SP_",
            "XP_",
            "BACKUP",
            "RESTORE",
            "GRANT",
            "REVOKE",
        ]

        for keyword in dangerous_keywords:
            if keyword in sql_upper:
                return False, f"Dangerous keyword '{keyword}' not allowed"

        # Must be a SELECT query
        if not sql_upper.strip().startswith("SELECT"):
            return False, "Only SELECT queries are allowed"

        # Check for basic SQL syntax
        try:
            parsed = sqlparse.parse(sql)
            if not parsed:
                return False, "Invalid SQL syntax"
        except Exception as e:
            return False, f"SQL parsing error: {str(e)}"

        return True, "Valid"

    async def execute_natural_query(
        self, user_query: str, return_df: bool = False
    ) -> Dict:
        """
        Complete pipeline: Natural language -> SQL -> Execute -> Results

        Args:
            user_query: Natural language query
            return_df: Whether to return results as DataFrame

        Returns:
            Dictionary with success status, SQL query, and results
        """
        sql_query = None

        try:
            # Generate SQL from natural language
            sql_query = await self.generate_sql(user_query)

            logger.info(f"Generated SQL: {sql_query}")

            # Validate SQL for safety
            is_valid, error_msg = self.validate_sql(sql_query)
            if not is_valid:
                return {
                    "success": False,
                    "error": f"Invalid SQL: {error_msg}",
                    "sql_query": sql_query,
                }

            # Execute query
            if return_df:
                results = await db_service.execute_query_df(sql_query)
                results_dict = results.to_dict("records")
            else:
                results_dict = await db_service.execute_query(sql_query)

            return {
                "success": True,
                "sql_query": sql_query,
                "results": results_dict,
                "row_count": len(results_dict),
            }

        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            return {"success": False, "error": str(e), "sql_query": sql_query}

    async def get_schema_summary(self) -> Dict:
        """Get human-readable schema summary"""
        if not self.schema_context:
            await self.initialize()

        summary = {}
        for table_name, columns in self.schema_context.items():
            summary[table_name] = {
                "column_count": len(columns),
                "columns": [col["column"] for col in columns],
            }

        return summary

# Singleton instance
text_to_sql_service = TextToSQLService()
