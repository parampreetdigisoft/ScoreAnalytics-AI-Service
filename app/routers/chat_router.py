"""
Score analysis Router - API endpoints with database exception logging
Fire-and-forget pattern for long-running analysis tasks
"""
import logging
from fastapi import APIRouter, HTTPException
from app.view_models.ChatRequest import ChatCityExecutiveSlidesRequest, ChatCityExecutiveSlidesResponse, ChatCityRequest,ChatGlobalRequest, ChatRequest
from app.view_models.AnalysisRequest import ChatResponse
from app.view_models.CityExecutiveSlidesResult import CityExecutiveSlidesResult
logger = logging.getLogger(__name__)
from app.services.chat_service import chat_service


router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("/ask", response_model=ChatResponse)
async def ask(request: ChatRequest):
    """
    Chat endpoint:
    - Accepts user question in body
    - Runs RAG pipeline
    - Returns AI-generated answer
    """
    try:
        result = await chat_service.answer_city_question (
            city_id = request.cityID,
            questionText = request.questionText,
            historyText = request.historyText,
            faqid = request.faqid,
            pillar_id = request.pillarID 
        )

        return ChatResponse(
            success=True,
            message="Response fetched successfully",
            result=result
        )
    except Exception as e:
        logger.error(f"Error in chat API: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/city", response_model=ChatResponse)
async def ask(request: ChatCityRequest):
    """
    Chat endpoint:
    - Accepts user question in body
    - Runs RAG pipeline
    - Returns AI-generated answer
    """
    try:
        result = await chat_service.answer_city_question (
            city_id = request.cityID,
            questionText = request.questionText,
            historyText = request.historyText,
            faqid = request.faqid,
            pillar_id = request.pillarID 
        )

        return ChatResponse (
            success=True,
            message="Response fetched successfully",
            result=result
        )
    except Exception as e:
        logger.error(f"Error in chat API: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
    
@router.post("/global", response_model = ChatResponse)
async def ask(request: ChatGlobalRequest):
    """
    Chat endpoint:
    - Accepts user question in body
    - Runs RAG pipeline
    - Returns AI-generated answer
    """
    try:
        result = await chat_service.answer_global_question (
            questionText = request.questionText,
            historyText = request.historyText 
        )

        return ChatResponse(
            success=True,
            message="Response fetched successfully",
            result=result
        )
    except Exception as e:
        logger.error(f"Error in chat API: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
    
# ============================================================
# ROUTER
# ============================================================

@router.post(
    "/executive-slides",
    response_model=ChatCityExecutiveSlidesResponse
)
async def ask_city_executive_slides(
    request: ChatCityExecutiveSlidesRequest
):
    """
    Executive intelligence dashboard endpoint.

    Returns:
    - Daily performance
    - Weekly performance
    - Monthly performance
    - Combined risks
    - Early warnings
    """

    try:

        response = await chat_service.answer_city_executive_slides(
            city_id=request.cityId
        )

        return ChatCityExecutiveSlidesResponse(
            success=response["success"],
            message=response["message"],
            result=response["result"]
        )

    except Exception as e:

        logger.error(
            f"Error in executive slides API: {str(e)}",
            exc_info=True
        )

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )
