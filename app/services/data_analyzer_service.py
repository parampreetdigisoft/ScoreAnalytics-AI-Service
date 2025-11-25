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
from app.services.common.database_service import db_service

logger = logging.getLogger(__name__)


class DataAnalyzerService:
    """Service for analyzing SQL Server data using LLM"""

    def __init__(self):
        self.llm = None
        self.data_reader = db_service
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
        table_name: str,
        question: str,
        columns: Optional[List[str]] = None,
        where_clause: Optional[str] = None,
        use_sampling: bool = True,
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

            # Determine if we should use sampling
            row_count = self.data_reader.get_row_count(table_name, where_clause)

            if row_count > settings.MAX_RECORDS_FOR_ANALYSIS and use_sampling:
                logger.info(f"Table has {row_count} rows, using sampling")
                df = self.data_reader.get_sample_data(
                    table_name=table_name,
                    sample_size=settings.SAMPLE_SIZE,
                    columns=columns,
                )
                sampling_note = f" (sampled {len(df)} rows from {row_count} total)"
            else:
                df = self.data_reader.read_table_data(
                    table_name=table_name,
                    columns=columns,
                    where_clause=where_clause,
                    limit=(
                        settings.MAX_RECORDS_FOR_ANALYSIS if not use_sampling else None
                    ),
                )
                sampling_note = ""

            if df.empty:
                return {
                    "success": False,
                    "error": "No data found in the table",
                    "table_name": table_name,
                }

            # Prepare data context
            data_context = self._prepare_data_context(df)

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
                    ("user", "{question}"),
                ]
            )

            # Create chain
            chain = prompt | self.llm | StrOutputParser()

            # Run analysis
            logger.info(f"Analyzing {len(df)} rows for question: {question}")
            analysis = await chain.ainvoke(
                {"data_context": data_context, "question": question}
            )

            return {
                "success": True,
                "table_name": table_name,
                "rows_analyzed": len(df),
                "total_rows": row_count,
                "sampling_note": sampling_note,
                "question": question,
                "analysis": analysis,
                "data_summary": {
                    "columns": list(df.columns),
                    "row_count": len(df),
                    "column_types": df.dtypes.astype(str).to_dict(),
                },
            }

        except Exception as e:
            logger.error(f"Error analyzing table data: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "table_name": table_name,
                "question": question,
            }

    async def analyze_comments(
        self,
        table_name: str,
        comment_column: str,
        question: Optional[str] = None,
        additional_columns: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Analyze comments from a table and provide insights

        Args:
            table_name: Name of the table containing comments
            comment_column: Name of the comment column
            question: Specific question about comments (optional)
            additional_columns: Additional context columns to include

        Returns:
            Dictionary with comment analysis
        """
        try:
            # Ensure LLM is initialized
            await self._ensure_initialized()

            # Prepare columns to read
            columns = [comment_column]
            if additional_columns:
                columns.extend(additional_columns)

            # Read data
            row_count = self.data_reader.get_row_count(table_name)

            if row_count > settings.MAX_RECORDS_FOR_ANALYSIS:
                df = self.data_reader.get_sample_data(
                    table_name=table_name,
                    sample_size=settings.SAMPLE_SIZE,
                    columns=columns,
                )
                sampling_note = f" (analyzed {len(df)} comments from {row_count} total)"
            else:
                df = self.data_reader.read_table_data(
                    table_name=table_name,
                    columns=columns,
                    limit=settings.MAX_RECORDS_FOR_ANALYSIS,
                )
                sampling_note = ""

            # Remove null/empty comments
            df = df[df[comment_column].notna() & (df[comment_column].str.strip() != "")]

            if df.empty:
                return {
                    "success": False,
                    "error": "No valid comments found in the table",
                    "table_name": table_name,
                }

            # Prepare comments for analysis
            comments_text = "\n\n".join(
                [
                    f"Comment {i+1}: {comment}"
                    for i, comment in enumerate(df[comment_column].head(100))
                ]
            )

            # Default question if none provided
            if not question:
                question = """Provide a comprehensive overview of these comments including:
                1. Main themes and topics
                2. Overall sentiment
                3. Key concerns or praise
                4. Patterns or trends
                5. Notable insights"""

            # Create prompt
            prompt = ChatPromptTemplate.from_messages(
                [
                    (
                        "system",
                        """You are an expert in analyzing customer feedback and comments. 
                        Analyze the provided comments and provide detailed insights.

                        Comments to analyze ({comment_count} total{sampling_note}):
                        {comments}
                        """,
                    ),
                    ("user", "{question}"),
                ]
            )

            # Create chain
            chain = prompt | self.llm | StrOutputParser()

            # Run analysis
            logger.info(f"Analyzing {len(df)} comments")
            analysis = await chain.ainvoke(
                {
                    "comments": comments_text,
                    "question": question,
                    "comment_count": len(df),
                    "sampling_note": sampling_note,
                }
            )

            return {
                "success": True,
                "table_name": table_name,
                "comment_column": comment_column,
                "comments_analyzed": len(df),
                "total_comments": row_count,
                "sampling_note": sampling_note,
                "question": question,
                "analysis": analysis,
            }

        except Exception as e:
            logger.error(f"Error analyzing comments: {e}", exc_info=True)
            return {"success": False, "error": str(e), "table_name": table_name}

    async def get_data_insights(
        self, query: str, analysis_type: str = "general"
    ) -> Dict[str, Any]:
        """
        Execute SQL query and get LLM insights on the results

        Args:
            query: SQL query to execute
            analysis_type: Type of analysis (general, trend, summary, etc.)

        Returns:
            Dictionary with query results and insights
        """
        try:
            # Ensure LLM is initialized
            await self._ensure_initialized()

            # Execute query
            df = self.data_reader.read_with_query(query)

            if df.empty:
                return {"success": False, "error": "Query returned no results"}

            # Prepare data context
            data_context = self._prepare_data_context(df)

            # Create analysis prompt based on type
            analysis_questions = {
                "general": "Provide a comprehensive analysis of this data including key insights, patterns, and notable findings.",
                "trend": "Analyze trends in this data. Identify increasing/decreasing patterns, anomalies, and predictions.",
                "summary": "Provide a concise executive summary of this data with key metrics and highlights.",
                "comparison": "Compare different segments in this data and highlight significant differences.",
            }

            question = analysis_questions.get(
                analysis_type, analysis_questions["general"]
            )

            # Create prompt
            prompt = ChatPromptTemplate.from_messages(
                [
                    (
                        "system",
                        """You are a data insights expert. Analyze the provided query results and provide actionable insights.

                        Query Results:
                        {data_context}
                        """,
                    ),
                    ("user", "{question}"),
                ]
            )

            # Create chain
            chain = prompt | self.llm | StrOutputParser()

            # Run analysis
            insights = await chain.ainvoke(
                {"data_context": data_context, "question": question}
            )

            return {
                "success": True,
                "rows_returned": len(df),
                "analysis_type": analysis_type,
                "data": df.to_dict("records")[:100],  # Limit to 100 rows in response
                "insights": insights,
                "data_summary": {
                    "columns": list(df.columns),
                    "row_count": len(df),
                    "column_types": df.dtypes.astype(str).to_dict(),
                },
            }

        except Exception as e:
            logger.error(f"Error getting data insights: {e}", exc_info=True)
            return {"success": False, "error": str(e)}


# Singleton instance
data_analyzer_service = DataAnalyzerService()
