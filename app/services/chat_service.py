# =========================================================================== #
#  chat_service.py  (refactored)                                         #
# =========================================================================== #

from datetime import datetime
import logging
from typing import List, Dict, Any, Optional
from app.services.common.llm_base_service import LLMBaseService
from app.services.common.city_prompt import VerdianPromptTemplates
from app.services.core.repository import DatabaseRepository
from app.services.rag_query_service import rag_query_service

logger = logging.getLogger(__name__)

CHROMA_PATH = "./chroma_store"


class ChatService:
    """
    Hybrid RAG service: LLM-routed TOC selection + ChromaDB vector retrieval.

    LLM mechanics live in LLMBaseService (injected).
    Prompt text lives in VerdianPromptTemplates.
    """

    def __init__(self) -> None:
        self._db = DatabaseRepository()
        self._llm_svc = LLMBaseService(max_retries=3, retry_delay=1.0)

    async def initialize(self) -> None:
        """Initialise the shared LLM service."""
        await self._llm_svc.initialize()

    # ------------------------------------------------------------------ #
    #  Public Methods                                                    #
    # ------------------------------------------------------------------ #

    async def answer_city_question (
        self,
        city_id: int,
        questionText: str,
        historyText: Optional[str] = None,
        faqid : Optional[int] = None,
        pillar_id: Optional[int] = None,
    ) -> str:
        year = datetime.now().year      

        ai_city_context = await self._db.get_ai_city_context(city_id, year,pillar_id)

        if faqid is None :
            faqs = await self._db.get_FAQ_context()
            relevant_faq_ids = await rag_query_service.get_related_FAQ_IDs(questionText, faqs)

            if len(relevant_faq_ids)>0:
                ai_context = await self._db.GetLocalContextDataForLLM(relevant_faq_ids,city_id,pillar_id)
            else:
                ai_context = await rag_query_service.get_city_document_context(city_id,questionText, pillar_id)
        else:
            ai_context = await self._db.usp_GetCityDataForLLM(city_id,[faqid],pillar_id)
            
        if len(ai_context) < 1:
            ai_context = "\n".join(f"{key}: {value}" for key, value in ai_city_context.items())
        pillar_name =ai_city_context["PillarName"]
        cityName =ai_city_context["CityName"]

        answer = await rag_query_service.send_city_question_to_llm(questionText,ai_context,cityName,pillar_name,historyText)

        return answer
    
    async def answer_global_question (
        self,
        questionText: str,
        historyText: Optional[str] = None
    ) -> str:
        year = datetime.now().year      

        query = """
            select 
              FAQID,Related,Category,QuestionText 
            from AIAssistantFAQ 
            where Related like '%global%'
        """
        faqs = await self._db.engine.fetch_dicts_async(query)


        relevant_faq_ids = await rag_query_service.get_related_FAQ_IDs(questionText, faqs)

        if len(relevant_faq_ids)>0:
            ai_context = await self._db.GetLocalContextDataForLLM(relevant_faq_ids)
        else:
            ai_context = await rag_query_service.get_global_document_context(questionText)

        cityName="global for all cities"
        pillar_name=""            

        answer = await rag_query_service.send_question_to_llm(questionText, ai_context, cityName, pillar_name, historyText)

        return answer



chat_service = ChatService()
