"""
Analysis Router - API endpoints for data analysis features
"""

from fastapi import APIRouter, HTTPException
import logging
from app.models.AnalysisRequest import (
    AnalysisResponse,
    CommentAnalysisRequest,
    QueryInsightsRequest,
    TableAnalysisRequest,
)
from app.services.data_analyzer_service import data_analyzer_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/analysis", tags=["Data Analysis"])


# Endpoints
@router.post("/table", response_model=AnalysisResponse)
async def analyze_table(request: TableAnalysisRequest):
    """
    Analyze table data and answer questions using LLM

    Example questions:
    - "What are the main patterns in this data?"
    - "Summarize the key insights from this table"
    - "What trends can you identify?"
    """
    try:
        result = await data_analyzer_service.analyze_table_data(
            table_name=request.table_name,
            question=request.question,
            columns=request.columns,
            where_clause=request.where_clause,
            use_sampling=request.use_sampling,
        )

        if result["success"]:
            return AnalysisResponse(
                success=True, message="Analysis completed successfully", data=result
            )
        else:
            raise HTTPException(
                status_code=400, detail=result.get("error", "Analysis failed")
            )

    except Exception as e:
        logger.error(f"Error in table analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/comments", response_model=AnalysisResponse)
async def analyze_comments(request: CommentAnalysisRequest):
    """
    Analyze comments from a table and provide comprehensive insights

    Provides:
    - Overall sentiment analysis
    - Main themes and topics
    - Key concerns or praise
    - Patterns and trends
    """
    try:
        result = await data_analyzer_service.analyze_comments(
            table_name=request.table_name,
            comment_column=request.comment_column,
            question=request.question,
            additional_columns=request.additional_columns,
        )

        if result["success"]:
            return AnalysisResponse(
                success=True,
                message="Comment analysis completed successfully",
                data=result,
            )
        else:
            raise HTTPException(
                status_code=400, detail=result.get("error", "Comment analysis failed")
            )

    except Exception as e:
        logger.error(f"Error in comment analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/insights", response_model=AnalysisResponse)
async def get_query_insights(request: QueryInsightsRequest):
    """
    Execute SQL query and get LLM-powered insights

    Analysis types:
    - general: Comprehensive overview with key insights
    - trend: Identify trends and patterns over time
    - summary: Executive summary with key metrics
    - comparison: Compare different segments
    """
    try:
        result = await data_analyzer_service.get_data_insights(
            query=request.query, analysis_type=request.analysis_type
        )

        if result["success"]:
            return AnalysisResponse(
                success=True, message="Insights generated successfully", data=result
            )
        else:
            raise HTTPException(
                status_code=400,
                detail=result.get("error", "Insights generation failed"),
            )

    except Exception as e:
        logger.error(f"Error getting insights: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/health")
async def analysis_health_check():
    """Health check for analysis service"""
    try:
        is_initialized = data_analyzer_service.llm is not None

        return {
            "status": "healthy" if is_initialized else "not_initialized",
            "service": "Data Analyzer",
            "llm_initialized": is_initialized,
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
