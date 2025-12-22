from pydantic import BaseModel, Field
from typing import Optional, List


# Response Models
class AnalysisResponse(BaseModel):
    """Generic analysis response"""
    success: bool
    message: Optional[str] = None
    data: Optional[dict] = None
