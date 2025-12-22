from pydantic import BaseModel, Field
from typing import Optional, List
# Request Models
class TableAnalysisRequest(BaseModel):
    """Request model for table data analysis"""
    table_name: str = Field(..., description="Name of the table to analyze")
    question: str = Field(..., description="Question to answer about the data")
    columns: Optional[List[str]] = Field(None, description="Specific columns to analyze")
    where_clause: Optional[str] = Field(None, description="WHERE clause filter")
    use_sampling: bool = Field(True, description="Use sampling for large datasets")


class CommentAnalysisRequest(BaseModel):
    """Request model for comment analysis"""
    table_name: str = Field(..., description="Name of the table containing comments")
    comment_column: str = Field(..., description="Name of the comment column")
    question: Optional[str] = Field(None, description="Specific question about comments")
    additional_columns: Optional[List[str]] = Field(None, description="Additional context columns")


class QueryInsightsRequest(BaseModel):
    """Request model for query insights"""
    query: str = Field(..., description="SQL query to execute")
    analysis_type: str = Field("general", description="Type of analysis: general, trend, summary, comparison")


# Response Models
class AnalysisResponse(BaseModel):
    """Generic analysis response"""
    success: bool
    message: Optional[str] = None
    data: Optional[dict] = None
