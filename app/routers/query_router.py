"""
FastAPI endpoints for Text-to-SQL functionality
"""

from fastapi import APIRouter, HTTPException
import logging
from app.models.schemas import (
    NaturalQueryRequest,
    SQLGenerationRequest,
    SQLValidationRequest,
)
from app.services.text_to_sql_service import text_to_sql_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/text-to-sql", tags=["Text-to-SQL"])


@router.post("/query", summary="Execute natural language query")
async def execute_natural_query(request: NaturalQueryRequest):
    """
    Convert natural language to SQL and execute it.

    Example queries:
    - "Show me all cities"
    - "Get top 10 cities by population"
    - "Count cities in each country"
    - "Find cities with population over 1 million"
    """
    try:
        if not request.query or len(request.query.strip()) < 3:
            raise HTTPException(
                status_code=400, detail="Query must be at least 3 characters long"
            )

        result = await text_to_sql_service.execute_natural_query(
            user_query=request.query, return_df=request.return_dataframe
        )

        if not result["success"]:
            raise HTTPException(
                status_code=400, detail=result.get("error", "Query execution failed")
            )

        return {
            "status": "success",
            "natural_query": request.query,
            "generated_sql": result["sql_query"],
            "row_count": result["row_count"],
            "results": result["results"],
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error executing natural query: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate-sql", summary="Generate SQL from natural language")
async def generate_sql(request: SQLGenerationRequest):
    """
    Generate SQL query from natural language without executing it.
    Useful for previewing the generated SQL before execution.
    """
    try:
        if not request.query or len(request.query.strip()) < 3:
            raise HTTPException(
                status_code=400, detail="Query must be at least 3 characters long"
            )

        sql_query = await text_to_sql_service.generate_sql(request.query)

        # Validate the generated SQL
        is_valid, validation_message = text_to_sql_service.validate_sql(sql_query)

        # Generate explanation

        return {
            "status": "success",
            "natural_query": request.query,
            "generated_sql": sql_query,
            "is_valid": is_valid,
            "validation_message": validation_message,
            "explanation": "",
        }

    except Exception as e:
        logger.error(f"Error generating SQL: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/validate-sql", summary="Validate SQL query")
async def validate_sql(request: SQLValidationRequest):
    """
    Validate a SQL query for safety and correctness.
    """
    try:
        is_valid, message = text_to_sql_service.validate_sql(request.sql)

        return {
            "status": "success",
            "sql": request.sql,
            "is_valid": is_valid,
            "message": message,
        }

    except Exception as e:
        logger.error(f"Error validating SQL: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/schema", summary="Get database schema")
async def get_schema():
    """
    Get the database schema information that the AI uses for context.
    """
    try:
        schema_summary = await text_to_sql_service.get_schema_summary()

        return {
            "status": "success",
            "schema": schema_summary,
            "table_count": len(schema_summary),
        }

    except Exception as e:
        logger.error(f"Error getting schema: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/examples", summary="Get example queries")
async def get_examples():
    """
    Get example natural language queries that can be used.
    """
    examples = [
        {
            "category": "Basic Selection",
            "queries": [
                "Show me all cities",
                "Get all records from Cities table",
                "List all cities",
            ],
        },
        {
            "category": "Filtering",
            "queries": [
                "Find cities with population over 1 million",
                "Show cities where population is greater than 500000",
                "Get cities with name starting with 'New'",
            ],
        },
        {
            "category": "Sorting",
            "queries": [
                "Get top 10 cities by population",
                "Show cities sorted by name",
                "List 5 largest cities",
            ],
        },
        {
            "category": "Aggregation",
            "queries": [
                "Count total number of cities",
                "Calculate average population",
                "Sum total population of all cities",
            ],
        },
        {
            "category": "Grouping",
            "queries": [
                "Count cities by country",
                "Average population by region",
                "Total population per state",
            ],
        },
    ]

    return {"status": "success", "examples": examples}