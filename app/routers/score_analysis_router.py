
"""
Score analysis Router - API endpoints for data analysis features
"""
from typing import Optional
from fastapi import APIRouter,HTTPException
import logging

from app.models.AnalysisRequest import AnalysisResponse
from app.services.score_analyzer_service import score_analyzer_service


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/score-analysis", tags=["Score Analysis"])

@router.post("/analysisAllCities", response_model = AnalysisResponse)
async def analyze_city_score(Id:Optional[int]=None):
    """
        Analyze table data and provide gloable summery for the assessment result for the city 

        Example questions:
        - "combine the comment of each question and give global overview for the user and score"
        - "Summarize the key insights from this table"
        - "What trends can you identify?"
    """
    try:
        result = await score_analyzer_service.analyze_all_cities_questions(Id);
        if result:
            return AnalysisResponse(
                success=True,
                message="City analysis completed successfully",
            )
        else:
            raise HTTPException(
                status_code=400, detail=result.get("error", "Comment analysis failed")
            )
    except Exception as e:
        logger.error(f"Error in city analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    



