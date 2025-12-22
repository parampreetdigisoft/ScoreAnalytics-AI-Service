"""
Pydantic models for request/response validation
"""
from pydantic import BaseModel, Field
from typing import List, Dict, Optional

class NaturalQueryRequest(BaseModel):
    query: str
    return_dataframe: Optional[bool] = False
    
    class Config:
        json_schema_extra = {
            "example": {
                "query": "Show me top 5 cities",
                "return_dataframe": False
            }
        }


class SQLGenerationRequest(BaseModel):
    query: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "query": "Get the top 10 cities by population"
            }
        }


class SQLValidationRequest(BaseModel):
    sql: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "sql": "SELECT * FROM Cities WHERE Population > 1000000"
            }
        }
