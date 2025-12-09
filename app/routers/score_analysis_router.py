"""
Score analysis Router - API endpoints with database exception logging
"""
import logging
from fastapi import APIRouter, HTTPException
from app.models.AnalysisRequest import AnalysisResponse
from app.services.score_analyzer_service import score_analyzer_service
from app.services.common.db_logger_service import db_logger_service


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/cities-score-analysis", tags=["Score Analysis"])

@router.post("/analyze/full", response_model=AnalysisResponse)
async def analyze_all_cities_full():
    """
    Analyze table data and provide global summary for the assessment result for all cities
    """
    try:

        result = await score_analyzer_service.analyze_all_cities_questions()
        
        if result:
            return AnalysisResponse(
                success=True,
                message="City analysis completed successfully",
            )
        else:
            error_msg = "Comment analysis failed - no results returned"
            db_logger_service.log_message("WARNING", error_msg)
            raise HTTPException(status_code=400, detail=error_msg)
            
    except HTTPException:
        # Re-raise HTTP exceptions without additional logging
        raise
    except Exception as e:
        error_msg = f"Error in city analysis : {str(e)}"
        logger.error(error_msg, exc_info=True)
        
        # Log to database
        db_logger_service.log_exception(
            "ERROR",
            f"City analysis failed analysisAllCities",
            e
        )
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/analyze/{city_id}/full", response_model=AnalysisResponse)
async def analyze_single_city_full(city_id: int):
    """
    Analyze table data and provide global summary for a single city
    """
    try:
        if not city_id:
            raise HTTPException(status_code=400, detail="City ID is required")
        
        result = await score_analyzer_service.analyze_all_cities_questions(city_id)
        
        if result:
            return AnalysisResponse(
                success=True,
                message=f"City {city_id} analysis completed successfully",
            )
        else:
            error_msg = f"Analysis failed for city {city_id} - no results returned"
            db_logger_service.log_message("WARNING", error_msg)
            raise HTTPException(status_code=400, detail=error_msg)
            
    except HTTPException:
        # Re-raise HTTP exceptions without additional logging
        raise
    except Exception as e:
        error_msg = f"Error in single city analysis (ID: {city_id}): {str(e)}"
        logger.error(error_msg, exc_info=True)
        
        # Log to database
        db_logger_service.log_exception(
            "ERROR",
            f"Single city analysis failed for ID: {city_id}",
            e
        )
        
        raise HTTPException(status_code=500, detail=str(e))
    
@router.post("/analyze/{city_id}", response_model=AnalysisResponse)
async def analyze_single_City(city_id: int):
    """
    Analyze only the city summary (no pillars/questions)
    """
    try:
        if not city_id:
            raise HTTPException(status_code=400, detail="City ID is required")
        
        result = await score_analyzer_service.analyze_single_City(city_id)
        
        if result:
            return AnalysisResponse(
                success=True,
                message=f"City {city_id} analysis completed successfully",
            )
        else:
            error_msg = f"Analysis failed for city {city_id} - no results returned"
            db_logger_service.log_message("WARNING", error_msg)
            raise HTTPException(status_code=400, detail=error_msg)
            
    except HTTPException:
        # Re-raise HTTP exceptions without additional logging
        raise
    except Exception as e:
        error_msg = f"Error in single city analysis (ID: {city_id}): {str(e)}"
        logger.error(error_msg, exc_info=True)
        
        # Log to database
        db_logger_service.log_exception(
            "ERROR",
            f"Single city analysis failed for ID: {city_id}",
            e
        )
        
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/analyze/{city_id}/pillars", response_model=AnalysisResponse)
async def analyze_city_pillars(city_id: int):
    """
   Analyze pillars for a specific city
    """
    try:
        if not city_id:
            raise HTTPException(status_code=400, detail="City ID is required")
        
        result = await score_analyzer_service.analyze_city_pillars(city_id)
        
        if result:
            return AnalysisResponse(
                success=True,
                message=f"City {city_id} analysis completed successfully",
            )
        else:
            error_msg = f"Analysis failed for city {city_id} - no results returned"
            db_logger_service.log_message("WARNING", error_msg)
            raise HTTPException(status_code=400, detail=error_msg)
            
    except HTTPException:
        # Re-raise HTTP exceptions without additional logging
        raise
    except Exception as e:
        error_msg = f"Error in single city analysis (ID: {city_id}): {str(e)}"
        logger.error(error_msg, exc_info=True)
        
        # Log to database
        db_logger_service.log_exception(
            "ERROR",
            f"Single city analysis failed for ID: {city_id}",
            e
        )
        
        raise HTTPException(status_code=500, detail=str(e))
  
@router.post("/analyze/{city_id}/questions", response_model=AnalysisResponse)
async def analyze_questions_of_city(city_id: int):
    """
    Analyze all questions for all pillars of a city
    """
    try:
        if not city_id:
            raise HTTPException(status_code=400, detail="City ID is required")
        
        result = await score_analyzer_service.analyze_questions_of_city_pillar(city_id)
        
        if result:
            return AnalysisResponse(
                success=True,
                message=f"City {city_id} analysis completed successfully",
            )
        else:
            error_msg = f"Analysis failed for city {city_id} - no results returned"
            db_logger_service.log_message("WARNING", error_msg)
            raise HTTPException(status_code=400, detail=error_msg)
            
    except HTTPException:
        # Re-raise HTTP exceptions without additional logging
        raise
    except Exception as e:
        error_msg = f"Error in single city analysis (ID: {city_id}): {str(e)}"
        logger.error(error_msg, exc_info=True)
        
        # Log to database
        db_logger_service.log_exception(
            "ERROR",
            f"Single city analysis failed for ID: {city_id}",
            e
        )
        
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/analyze/{city_id}/pillars/{pillar_id}/questions", response_model=AnalysisResponse)
async def analyze_questions_of_city_pillar(city_id: int,pillar_id: int):
    """
    Analyze all questions of a particular pillar for a city
    """
    try:
        if not city_id:
            raise HTTPException(status_code=400, detail="City ID is required")
        
        result = await score_analyzer_service.analyze_questions_of_city_pillar(city_id,pillar_id)
        
        if result:
            return AnalysisResponse(
                success=True,
                message=f"City {city_id} analysis completed successfully",
            )
        else:
            error_msg = f"Analysis failed for city {city_id} - no results returned"
            db_logger_service.log_message("WARNING", error_msg)
            raise HTTPException(status_code=400, detail=error_msg)
            
    except HTTPException:
        # Re-raise HTTP exceptions without additional logging
        raise
    except Exception as e:
        error_msg = f"Error in single city analysis (ID: {city_id}): {str(e)}"
        logger.error(error_msg, exc_info=True)
        
        # Log to database
        db_logger_service.log_exception(
            "ERROR",
            f"Single city analysis failed for ID: {city_id}",
            e
        )
        
        raise HTTPException(status_code=500, detail=str(e))
     