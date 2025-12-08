"""
FastAPI endpoints for Veridian AI Research Service
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import Field
from typing import List
import logging

from app.models.AiResearchModel import (
    ResearchResponse,
    QuestionResearchRequest,
    CityResearchRequest,
    PillarResearchRequest,
    SourceCitation
)

from app.services.common.veridian_ai_research_service import veridian_ai_research_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/ai-research", tags=["AI Research"])


# =============================================
# ENDPOINTS
# =============================================

@router.post("/question/research", response_model=ResearchResponse)
async def research_question(request: QuestionResearchRequest):
    """
    AI conducts independent research for a question and provides evidence-based score
    
    Process:
    1. AI searches web for city-specific evidence
    2. Applies Veridian TSC framework to evaluate sources
    3. Cross-verifies findings across multiple sources
    4. Assigns score based on evidence quality (0-4)
    5. Documents all sources with trust levels
    6. Stores results in database with full evidence trail
    
    Returns:
    - AI-generated score with confidence level
    - Evidence summary (100-150 words)
    - All source citations with trust levels (1-7)
    - Red flags identified
    - Comparison with evaluator score if provided
    """
    try:
        logger.info(f"Starting question research: {request.question_text} for {request.city_name}")
        
        # Conduct research
        result = await veridian_ai_research_service.research_and_score_question(
            city_name=request.city_name,
            city_address=request.city_address,
            question_text=request.question_text,
            question_category=request.question_category,
            pillar_name=request.pillar_name,
            evaluator_score=request.evaluator_score,
            year=request.year
        )
        
        if not result.get('success'):
            raise HTTPException(status_code=500, detail=result.get('error', 'Research failed'))
        
        # # Save to database
        # question_score_id = await veridian_ai_research_db.save_question_research(
        #     city_id=request.city_id,
        #     pillar_id=request.pillar_id,
        #     question_id=request.question_id,
        #     year=result['year'],
        #     research_result=result
        # )
        
        # logger.info(f"✅ Question research completed: QuestionScoreID={question_score_id}")
        
        return ResearchResponse(
            success=True,
            ai_score=result['ai_score'],
            evaluator_score=result['evaluator_score'],
            discrepancy=result['discrepancy'],
            confidence_level=result['confidence_level'],
            evidence_summary=result['evidence_summary'],
            data_sources_count=result['data_sources_count'],
            sources=[SourceCitation(**s) for s in result['sources']],
            red_flags=result['red_flags'],
            geographic_equity_note=result['geographic_equity_note']
        )
        
    except Exception as e:
        logger.error(f"Error in question research: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/pillar/research")
async def research_pillar(request: PillarResearchRequest):
    """
    AI conducts comprehensive pillar-level research
    
    Process:
    1. Searches for city-wide pillar performance data
    2. Analyzes institutional capacity and equity
    3. Cross-verifies across multiple dimensions
    4. Synthesizes findings into pillar score
    5. Documents systemic patterns and data gaps
    
    Returns:
    - Pillar-level AI score with evidence
    - Institutional assessment
    - Geographic equity analysis
    - Data gap identification
    """
    try:
        logger.info(f"Starting pillar research: {request.pillar_name} for {request.city_name}")
        
        result = await veridian_ai_research_service.research_and_score_pillar(
            city_name=request.city_name,
            city_address=request.city_address,
            pillar_name=request.pillar_name,
            evaluator_score=request.evaluator_score,
            year=request.year
        )
        
        if not result.get('success'):
            raise HTTPException(status_code=500, detail=result.get('error'))
        
        # Save to database
        # pillar_score_id = await veridian_ai_research_db.save_pillar_research(
        #     city_id=request.city_id,
        #     pillar_id=request.pillar_id,
        #     year=result['year'],
        #     research_result=result
        # )
        
        # logger.info(f"✅ Pillar research completed: PillarScoreID={pillar_score_id}")
        
        return {
            "success": True,
            "pillar_score_id": 1, #pillar_score_id,
            "pillar": result['pillar'],
            "ai_score": result['ai_score'],
            "evaluator_score": result['evaluator_score'],
            "discrepancy": result['discrepancy'],
            "confidence_level": result['confidence_level'],
            "evidence_summary": result['evidence_summary'],
            "institutional_assessment": result['institutional_assessment'],
            "data_gap_analysis": result['data_gap_analysis'],
            "sources": result['sources']
        }
        
    except Exception as e:
        logger.error(f"Error in pillar research: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/city/research")
async def research_city(request: CityResearchRequest):
    """
    AI conducts holistic city-level assessment
    
    Process:
    1. Analyzes cross-pillar patterns
    2. Evaluates institutional capacity city-wide
    3. Assesses equity and sustainability
    4. Provides strategic recommendations
    5. Documents data transparency
    
    Returns:
    - Comprehensive city score
    - Cross-pillar synthesis
    - Strategic recommendations
    - Sustainability outlook
    """
    try:
        logger.info(f"Starting city research: {request.city_name}")
        
        result = await veridian_ai_research_service.research_and_score_city(
            city_name=request.city_name,
            city_address=request.city_address,
            evaluator_score=request.evaluator_score,
            year=request.year
        )
        
        if not result.get('success'):
            raise HTTPException(status_code=500, detail=result.get('error'))
        
        # # Save to database
        # city_score_id = await veridian_ai_research_db.save_city_research(
        #     city_id=request.city_id,
        #     year=result['year'],
        #     research_result=result
        # )
        # logger.info(f"✅ City research completed: CityScoreID={city_score_id}")
        
        return {
            "success": True,
            "city_score_id": 12,#city_score_id,
            "city": result['city'],
            "ai_score": result['ai_score'],
            "evaluator_score": result['evaluator_score'],
            "discrepancy": result['discrepancy'],
            "confidence_level": result['confidence_level'],
            "evidence_summary": result['evidence_summary'],
            "cross_pillar_patterns": result['cross_pillar_patterns'],
            "institutional_capacity": result['institutional_capacity'],
            "equity_assessment": result['equity_assessment'],
            "sustainability_outlook": result['sustainability_outlook'],
            "strategic_recommendations": result['strategic_recommendations']
        }
        
    except Exception as e:
        logger.error(f"Error in city research: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/batch/questions")
async def batch_research_questions(
    requests: List[QuestionResearchRequest],
    parallel: bool = False
):
    """
    Batch process multiple questions
    
    Args:
        requests: List of question research requests
        parallel: If True, process in parallel (faster but more resource-intensive)
    
    Returns:
        Summary of results with success/failure counts
    """
    try:
        results = []
        success_count = 0
        failure_count = 0
        
        if parallel:
            # Process in parallel (implement with asyncio.gather)
            import asyncio
            tasks = [research_question(req) for req in requests]
            results = await asyncio.gather(*tasks, return_exceptions=True)
        else:
            # Process sequentially
            for req in requests:
                try:
                    result = await research_question(req)
                    results.append(result)
                    success_count += 1
                except Exception as e:
                    results.append({"success": False, "error": str(e), "question": req.question_text})
                    failure_count += 1
        
        return {
            "total": len(requests),
            "success": success_count,
            "failure": failure_count,
            "results": results
        }
        
    except Exception as e:
        logger.error(f"Error in batch processing: {e}")
        raise HTTPException(status_code=500, detail=str(e))

