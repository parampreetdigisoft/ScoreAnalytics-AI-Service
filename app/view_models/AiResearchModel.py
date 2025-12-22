from pydantic import BaseModel, Field
from typing import Optional, List
# =============================================
# REQUEST/RESPONSE MODELS
# =============================================

class QuestionResearchRequest(BaseModel):
    """Request for AI to research and score a question"""
    city_id: int
    city_name: str
    city_address: str
    pillar_id: int
    pillar_name: str
    question_id: int
    question_text: str
    question_category: str
    evaluator_score: Optional[float] = Field(None, ge=0, le=4)
    year: Optional[int] = None


class PillarResearchRequest(BaseModel):
    """Request for AI to research and score a pillar"""
    city_id: int
    city_name: str
    city_address: str
    pillar_id: int
    pillar_name: str
    evaluator_score: Optional[float] = Field(None, ge=0, le=4)
    year: Optional[int] = None


class CityResearchRequest(BaseModel):
    """Request for AI to research and score entire city"""
    city_id: int
    city_name: str
    city_address: str
    evaluator_score: Optional[float] = Field(None, ge=0, le=4)
    year: Optional[int] = None


class SourceCitation(BaseModel):
    """Evidence source citation"""
    source_type: str
    source_name: str
    source_url: str
    data_year: Optional[int]
    trust_level: int = Field(ge=1, le=7)
    data_extract: str


class ResearchResponse(BaseModel):
    """Standard response for research results"""
    success: bool
    ai_score: Optional[float]
    evaluator_score: Optional[float]
    discrepancy: Optional[float]
    confidence_level: Optional[str]
    evidence_summary: Optional[str]
    data_sources_count: Optional[int]
    sources: List[SourceCitation] = []
    red_flags: List[str] = []
    geographic_equity_note: Optional[str] = ""
