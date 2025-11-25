"""
Data Analyzer Service - LLM-powered analysis of SQL Server data
"""

import pandas as pd
import logging
import json

from typing import Dict, List, Any, Optional
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from app.config import settings
from app.services.common.llm_factory import llm_factory

logger = logging.getLogger(__name__)


class LLMExecutionService:
    """Service for analyzing SQL Server data using LLM"""

    def __init__(self):
        self.llm = None
        self._initialized = False

    async def initialize(self):
        """Initialize the LLM"""
        if self._initialized:
            return

        try:
            self.llm = llm_factory.create_llm()
            self._initialized = True
            logger.info(f"✅ Data Analyzer initialized with {settings.LLM_PROVIDER}")
        except Exception as e:
            logger.error(f"Failed to initialize Data Analyzer: {e}")
            raise

    async def _ensure_initialized(self):
        """Ensure LLM is initialized before use"""
        if not self._initialized or self.llm is None:
            await self.initialize()

    def _prepare_data_context(self, df: pd.DataFrame, max_rows: int = 50) -> str:
        """
        Prepare data context for LLM (limited to avoid token overflow)

        Args:
            df: DataFrame containing the data
            max_rows: Maximum number of rows to include

        Returns:
            String representation of data context
        """
        # Get basic statistics
        stats = {
            "total_rows": len(df),
            "columns": list(df.columns),
            "dtypes": df.dtypes.astype(str).to_dict(),
        }

        # Add sample data (limited)
        sample_df = df.head(max_rows) if len(df) > max_rows else df

        # Build context
        context = f"""
            Data Statistics:
            - Total Rows: {stats['total_rows']}
            - Columns: {', '.join(stats['columns'])}

            Column Types:
            {json.dumps(stats['dtypes'], indent=2)}

            Sample Data (first {len(sample_df)} rows):
            {sample_df.to_string(index=False, max_rows=max_rows)}
            """

        # Add numeric statistics if available
        numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()
        if numeric_cols:
            context += f"\n\nNumeric Column Statistics:\n{df[numeric_cols].describe().to_string()}"

        return context

    async def analyze_table_data(
        self,
        data_context: str,
        action:str
    ) -> Dict[str, Any]:
        """
        Analyze table data and answer questions using LLM

        Args:
            table_name: Name of the table to analyze
            question: User's question about the data
            columns: Specific columns to analyze
            where_clause: Filter clause
            use_sampling: Whether to use sampling for large datasets

        Returns:
            Dictionary with analysis results
        """
        try:
            # Ensure LLM is initialized
            await self._ensure_initialized()
            # Create prompt
            prompt = ChatPromptTemplate.from_messages(
                [
                    (
                        "system",
                        """You are a data analyst expert. Analyze the provided data and answer the user's question accurately.

                        Guidelines:
                        1. Provide specific insights based on the actual data
                        2. Include relevant statistics and patterns
                        3. Be concise but comprehensive
                        4. If you need to make assumptions, state them clearly
                        5. Format your response in a clear, structured way
                        6. If the data is sampled, acknowledge this in your analysis

                        Data Context:
                        {data_context}
                        """,
                    ),
                    ("user", "{action}"),
                ]
            )

            # Create chain
            chain = prompt | self.llm | StrOutputParser()

            # Run analysis
            analysis = await chain.ainvoke(
                {"data_context": data_context, "question": action}
            )

            return {
                "success": True,
                "question": action,
                "analysis": analysis
            }

        except Exception as e:
            logger.error(f"Error analyzing table data: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "question": action,
            }

# Singleton instance
llm_Execution_service = LLMExecutionService()
