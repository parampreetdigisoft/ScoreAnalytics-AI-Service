# =========================================================================== #
#  chat_service.py  (refactored)                                         #
# =========================================================================== #

from datetime import datetime
import logging
from typing import List, Dict, Any, Optional
from app.services.common.llm_base_service import LLMBaseService
from app.services.common.city_prompt import VerdianPromptTemplates
from app.services.common.pillar_prompts import PillarPrompts
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
                relevant_faq_ids = relevant_faq_ids[: 3 if historyText == None else 2]
                ai_context = await self._db.GetLocalContextDataForLLM(relevant_faq_ids,city_id,pillar_id)
            else:
                ai_context = await rag_query_service.get_city_document_context(city_id,questionText, pillar_id)
        else:
             ai_context = await self._db.GetLocalContextDataForLLM([faqid],city_id,pillar_id)
            
        if len(ai_context) < 1:
            ai_context = "\n".join(f"{key}: {value}" for key, value in ai_city_context.items())
        pillar_name =ai_city_context["PillarName"]
        cityName =ai_city_context["CityName"]

        answer = await rag_query_service.send_city_question_to_llm(questionText,ai_context,cityName,pillar_name,historyText)

        return answer
    
    async def answer_global_question (
        self,
        questionText: str,
        historyText: Optional[str] = None,
        faqid: Optional[int] = None
    ) -> str:
        year = datetime.now().year    
        
        relevant_faq_ids =[]
        if faqid is None: 
            faqs = await self._db.get_FAQ_context(True)
            relevant_faq_ids = await rag_query_service.get_related_FAQ_IDs(questionText, faqs)
        else :
            relevant_faq_ids=[faqid]
            
        if len(relevant_faq_ids)>0:
            ai_context = await self._db.GetLocalContextDataForLLM(relevant_faq_ids)
        else:
            ai_context = await rag_query_service.get_global_document_context(questionText)

        cityName="global for all cities"
        pillar_name=""            

        answer = await rag_query_service.send_question_to_llm(questionText, ai_context, cityName, pillar_name, historyText)

        return answer
    # ============================================================
# CHAT SERVICE
# ============================================================

    async def answer_city_executive_slides( self, city_id: int) -> Dict[str, Any]:
        try:
            year = datetime.now().year

            ai_city = await self._db.get_ai_city_context(city_id, year)


            if not ai_city:
                return {
                    "success": False,
                    "message": "city context not found"
                }

            city_name = ai_city["CityName"]

            ai_city_context = "\n".join(
                f"{key}: {value}"
                for key, value in ai_city.items()
            )

            all_pillar_contexts = PillarPrompts.get_all_pillar_names()

            ai_result  = await rag_query_service.city_executive_slides(
                city_name=city_name,
                country=ai_city["Country"],
                ai_city_context=ai_city_context,
                allPillarContexts=all_pillar_contexts,
                year=year
            )

            if not ai_result.get("success"):
                return {
                    "success": False,
                    "message": "Failed to generate executive slides"
                }

            data = ai_result["data"]

            result = {
                "cityId": city_id,
                "cityName": data.get("cityName"),

                "recentPerformance": {
                    "trend": data["recentPerformance"]["trend"],
                    "summary": data["recentPerformance"]["summary"]
                },

                "combinedRisks": data["combinedRisks"]["risks"],

                "earlyWarnings": data["earlyWarnings"]["warnings"]
            }

            return {
                "success": True,
                "message": "Executive slides generated successfully",
                "result": result
            }

        except Exception as exc:

            logger.exception(
                "answer_city_executive_slides_question failed"
            )

            return {
                "success": False,
                "error": str(exc)
            }
        
    async def answer_crossComparision(
        self,
        questionText: str,
        cityIDs: list[int],
        historyText: Optional[str] = None,
    ) -> str:

        year = datetime.now().year

        countries = []

        if len(cityIDs) > 0:
            query = f"""
                SELECT CityName, Country
                FROM Cities
                WHERE CityID IN ({",".join(map(str, cityIDs))})
            """

            cities = await self._db.engine.fetch_dicts_async(query)

        relevant_faq_ids = []

        if len(cityIDs) == 0:
            faqs = await self._db.get_FAQ_context(True)
            relevant_faq_ids = await rag_query_service.get_related_FAQ_IDs(
                questionText,
                faqs
            )
        else:
            relevant_faq_ids = cityIDs

        if len(relevant_faq_ids) > 0:
            ai_context = await self._db.GetCrossComparisionLocalContextDataForLLM(
                relevant_faq_ids
            )
        else:
            ai_context = await rag_query_service.get_global_document_context(
                questionText
            )

        cityName = ", ".join(
            [city["CityName"] for city in cities]
        )

        pillar_name = "Get pillars from provided context"

        answer = await rag_query_service.send_question_to_llm(
            questionText,
            ai_context,
            cityName,
            pillar_name,
            historyText
        )

        return answer
    
chat_service = ChatService()
