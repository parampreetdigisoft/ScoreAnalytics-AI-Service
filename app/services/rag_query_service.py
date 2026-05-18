# =========================================================================== #
#  rag_query_service.py  (refactored)                                         #
# =========================================================================== #
"""
RAGQueryService  (refactored)
------------------------------
Two-stage RAG pipeline for city document Q&A.

Stage 1 — LLM-driven TOC routing  (which sections are relevant?)
Stage 2 — ChromaDB vector search within those sections

LLM calls are handled by LLMBaseService.
All prompt text comes from PEMPromptTemplates.
"""
from datetime import datetime
import os
import re
import chromadb
import logging
import json
from chromadb.utils import embedding_functions
from typing import List, Dict, Any, Optional
from app.services.common.city_prompt import VerdianPromptTemplates
from app.services.common.llm_base_service import LLMBaseService
from app.services.core.repository import DatabaseRepository
from app.services.common import json_response_parser as jrp
logger = logging.getLogger(__name__)

CHROMA_PATH = "./chroma_store"


class RAGQueryService:
    """
    Hybrid RAG service: LLM-routed TOC selection + ChromaDB vector retrieval.

    LLM mechanics live in LLMBaseService (injected).
    Prompt text lives in PEMPromptTemplates.
    """

    def __init__(self) -> None:
        self._llm_svc = LLMBaseService(max_retries=3, retry_delay=1.0)
        # Ensure directory exists
        if not os.path.exists(CHROMA_PATH):
            os.makedirs(CHROMA_PATH)

        try:
            self.client = chromadb.PersistentClient(
                path=CHROMA_PATH,
                settings=chromadb.config.Settings(anonymized_telemetry=False),
            )

        except Exception as e:
            logger.error(f"ChromaDB initialization failed: {e}")
            raise

        self.embed_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="all-MiniLM-L6-v2"
        )
        self._db = DatabaseRepository()
        # --- LLM (shared base service) ---
        self._llm_svc = LLMBaseService(max_retries=3, retry_delay=1.0)

    # ------------------------------------------------------------------ #
    #  Initialisation                                                    #
    # ------------------------------------------------------------------ #

    async def initialize(self) -> None:
        """Initialise the shared LLM service."""
        await self._llm_svc.initialize()

    # ------------------------------------------------------------------ #
    #  Public API                                                          #
    # ------------------------------------------------------------------ #

    async def get_city_document_context(
        self,
        city_id: int,
        msg_text: str,
        pillar_id: Optional[int] = None,
    ) -> str:
        """
        Answer a natural-language question about a city using:
          1. LLM-selected TOC sections
          2. ChromaDB vector search within those sections
          3. LLM synthesis of retrieved chunks + chat history
        """
        # Stage 1 — TOC routing
        toc = await self._get_city_toc(city_id, pillar_id)

        relevant_toc_ids = []
        if len(toc) > 4:
            relevant_toc_ids = await self._route_via_toc(msg_text, toc)
        else:
            relevant_toc_ids = [row["TOCID"] for row in toc]

        # Stage 2 — Vector retrieval
        chunks = self._fetch_relevant_chunks(
            city_id=city_id,
            question=msg_text,
            toc_ids=relevant_toc_ids,
            top_k=10,
            pillar_id=pillar_id,
        )

        # Build context and history strings
        local_context = self._build_context_block(chunks)

        return local_context
    

    async def answer_city_question(
        self,
        city_id: int,
        question: str,
        pillar_id: Optional[int] = None,
    ) -> str:
        """
        Answer a natural-language question about a city using:
          1. LLM-selected TOC sections
          2. ChromaDB vector search within those sections
          3. LLM synthesis of retrieved chunks + chat history
          
        """
        # Stage 1 — TOC routing
        toc = await self._get_city_toc(city_id, pillar_id)

        relevant_toc_ids = []
        if len(toc) > 4:
            relevant_toc_ids = await self._route_via_toc(question, toc)
        else:
            relevant_toc_ids = [row["TOCID"] for row in toc]

        # Stage 2 — Vector retrieval
        chunks = self._fetch_relevant_chunks(
            city_id=city_id,
            question=question,
            toc_ids=relevant_toc_ids,
            top_k=5,
            pillar_id=pillar_id,
        )

        # Build context and history strings
        local_context = self._build_context_block(chunks)
        year = datetime.now().year      
        ai_city= await self._db.get_ai_city_context(city_id, year)

        if len(local_context)  < 50 :
           
            local_context = "\n".join(f"{key}: {value}" for key, value in ai_city.items())

        history_str =""
        pillar_name =""
        cityName =ai_city["CityName"]

        # Stage 3 — LLM answer synthesis
        answer = await self._llm_svc.invoke_messages(
            messages=[
                {
                    "role": "system",
                    "content": VerdianPromptTemplates.rag_answer_system_prompt(),
                },
                {
                    "role": "user",
                    "content": VerdianPromptTemplates.rag_answer_user_prompt(
                        local_context, history_str, question,
                        cityName, pillar_name
                    ),
                },
            ],
            label=f"rag_answer|city{city_id}",
        )

        return answer

    async def send_city_question_to_llm(
        self,
        questionText: str,
        ai_context: str,
        cityName: str,
        pillar_name: str,
        historyText: Optional[str] = None
    ) -> str:

        # Stage 3 — LLM answer synthesis
        answer = await self._llm_svc.invoke_messages(
            messages=[
                {
                    "role": "system",
                    "content": VerdianPromptTemplates.chat_city_system_prompt(),
                },
                {
                    "role": "user",
                    "content": VerdianPromptTemplates.chat_answer_user_prompt(
                        ai_context, historyText, questionText,
                        cityName, pillar_name
                    ),
                },
            ],
            label=f"rag_answer|city{cityName}",
        )

        return answer


    async def send_question_to_llm(
        self,
        questionText: str,
        ai_context: str,
        cityName: str,
        pillar_name: str,
        historyText: Optional[str] = None,
    ) -> str:

        # Stage 3 — LLM answer synthesis
        answer = await self._llm_svc.invoke_messages(
            messages=[
                {
                    "role": "system",
                    "content": VerdianPromptTemplates.chat_system_prompt(),
                },
                {
                    "role": "user",
                    "content": VerdianPromptTemplates.chat_answer_user_prompt(
                        ai_context, historyText, questionText, cityName, pillar_name
                    ),
                },
            ],
            label=f"rag_answer|city{cityName}",
        )

        return answer

    async def send_cross_comparision_question_to_llm(
        self,
        questionText: str,
        ai_context: str,
        cityName: str,
        pillar_name: str,
        historyText: Optional[str] = None,
    ) -> str:

        # Stage 3 — LLM answer synthesis
        answer = await self._llm_svc.invoke_messages(
            messages=[
                {
                    "role": "system",
                    "content": VerdianPromptTemplates.chat_system_prompt(),
                },
                {
                    "role": "user",
                    "content": VerdianPromptTemplates.chat_answer_user_prompt(
                        ai_context, historyText, questionText, cityName, pillar_name
                    ),
                },
            ],
            label=f"rag_answer|city{cityName}",
        )

        return answer

    # ------------------------------------------------------------------ #
    #  Stage 1 — DB: fetch TOC                                           #
    #  ⚡ Tenant migration point: only this method touches the DB        #
    # ------------------------------------------------------------------ #

    async def _get_city_toc(
        self,
        city_id: int,
        pillar_id: Optional[int] = None,
    ) -> List[Dict]:
        """
        Fetch the Table-of-Contents entries for a city's uploaded documents.

        Returns a list of dicts with keys:
            TOCID, SectionPath, SectionTitle, SectionLevel, PillarID, FileName
        """
        query = """
            SELECT t.TOCID, t.SectionPath, t.SectionTitle, t.SectionLevel,
                   t.PillarID, cd.FileName
            FROM DocumentTOC t
            JOIN CityDocuments cd ON cd.CityDocumentID = t.CityDocumentID
            WHERE t.CityID = ? AND cd.IsDeleted = 0
        """
        # Future: add   AND t.TenantID = ?   when multi-tenant
        return await self._db.engine.fetch_dicts_async(query, (city_id,))

    # ------------------------------------------------------------------ #
    #  Stage 1 — LLM: route question to relevant TOC sections            #
    # ------------------------------------------------------------------ #

    async def _route_via_toc(
        self,
        question: str,
        toc: List[Dict],
    ) -> List[int]:
        """
        Ask the LLM which TOC section IDs are most relevant to the question.
        Returns a list of TOCID integers (may be empty).
        """
        if not toc:
            return []

        toc_text = "\n".join(
            f"[{row['TOCID']}] (Level {row['SectionLevel']}) {row['SectionPath']}"
            for row in toc
        )
        prompt = VerdianPromptTemplates.rag_routing_prompt(toc_text, question)
        raw = await self._llm_svc.invoke_raw(
            prompt, label=f"rag_routing|q={question[:40]}"
        )

        match = re.search(r"\[[\d,\s]*\]", raw)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
        return []

    # ------------------------------------------------------------------ #
    #  Stage 2 — ChromaDB: vector search within sections                 #
    # ------------------------------------------------------------------ #

    def _fetch_relevant_chunks(
        self,
        city_id: int,
        question: str,
        toc_ids: List[int],
        top_k: int = 5,
        pillar_id: Optional[int] = None,
    ) -> List[Dict]:
        """
        Run a vector similarity search against the ChromaDB collection and
        return the top-k chunks, optionally filtered to the routed TOC IDs.
        """
        collection_name = f"city_{city_id}"
        try:
            #    collections = self.client.list_collections()

            collection = self.client.get_collection(
                name=collection_name, embedding_function=self.embed_fn
            )
        except Exception as e:
            logger.error(f"Error fetching collection {collection_name}: {e}")
            return []

        where_filter = {"toc_id": {"$in": toc_ids}} if toc_ids else None
        results = collection.query(
            query_texts=[question],
            n_results=top_k,
            where=where_filter,
            include=["documents", "metadatas", "distances"],
        )

        chunks = []
        for doc, meta, dist in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        ):
            chunks.append(
                {
                    "text": doc,
                    "section": meta.get("section_path", ""),
                    "file": meta.get("section_title", ""),
                    "relevance": round(1 - dist, 3),
                }
            )
        return chunks
    
    async def get_global_document_context(self, msg_text: str) -> str:

        toc = await self._get_global_toc()

        relevant_toc_ids = []
        if len(toc) > 4:
            relevant_toc_ids = await self._get_relevant_Id(msg_text, toc)
        else:
            relevant_toc_ids = [row["TOCID"] for row in toc]

        # Stage 2 — Vector retrieval
        chunks = self._fetch_relevant_chunks(
            question=msg_text,
            toc_ids=relevant_toc_ids,
            city_id=None,
            pillar_id=None,
            top_k=10,
        )

        # Build context and history strings
        local_context = self._build_context_block(chunks)

        return local_context
    
    async def _get_relevant_Id(
        self,
        question: str,
        toc: List[Dict],
    ) -> List[int]:
        """
        Ask the LLM which TOC section IDs are most relevant to the question.
        Returns a list of TOCID integers (may be empty).
        """
        if not toc:
            return []

        toc_text = "\n".join(
            f"[{row['TOCID']}] (Level {row['SectionLevel']}) {row['SectionPath']}"
            for row in toc
        )
        prompt = VerdianPromptTemplates.get_relevant_Id_prompt(toc_text, question)
        raw = await self._llm_svc.invoke_raw(
            prompt, label=f"rag_routing|q={question[:40]}"
        )

        match = re.search(r"\[[\d,\s]*\]", raw)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
        return []

    
    async def get_related_FAQ_IDs(self,question: str,toc: List[Dict],) -> List[int]:
        """
            Ask the LLM which FAQ section IDs are most relevant to the question.
            Returns a list of FAQIDs integers (may be empty).
        """
        if not toc:
            return []

        toc_text = "\n".join(
            f"[{row['FAQID']}] (QuestionText {row['QuestionText']}) {row['Category']}"
            for row in toc
        )
        prompt = VerdianPromptTemplates.get_relevant_faqId_prompt(toc_text, question)
        raw = await self._llm_svc.invoke_raw(
            prompt, label=f"rag_routing|q={question[:80]}"
        )

        match = re.search(r"\[[\d,\s]*\]", raw)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
        return []
    
    async def _get_global_toc(self) -> List[Dict]:

        query = """
            SELECT t.TOCID, t.SectionPath, t.SectionTitle, t.SectionLevel,
                   t.PillarID, cd.FileName
            FROM DocumentTOC t
            JOIN CityDocuments cd ON cd.CityDocumentID = t.CityDocumentID
            WHERE  cd.IsDeleted = 0 or DocumentLevel Like ?
        """
        documentLevel = "Global"

        return await self._db.engine.fetch_dicts_async(query, (documentLevel))

    # ------------------------------------------------------------------ #
    #  Helpers                                                            #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _build_context_block(chunks: List[Dict]) -> str:
        if not chunks:
            return ""
        lines = ["=== FROM UPLOADED CITY DOCUMENTS ==="]
        for chunk in chunks:
            lines.append(f"[{chunk['section']}]\n{chunk['text']}\n")
        return "\n".join(lines)

    @staticmethod
    def _build_history_str(chat_history: Optional[List[Dict]]) -> str:
        if not chat_history:
            return ""
        lines = []
        for msg in chat_history[-6:]:  # last 3 turns (user + assistant × 3)
            role = "User" if msg["role"] == "user" else "Assistant"
            lines.append(f"{role}: {msg['content']}")
        return "\n".join(lines)

    # ============================================================
# RAG QUERY SERVICE
# ============================================================

    async def city_executive_slides( self,  city_name: str, country: str, ai_city_context: str, allPillarContexts: str, year: int = None) -> Dict[str, Any]:

        try:

            # ---------------------------------------------------------
            # SYSTEM PROMPT
            # ---------------------------------------------------------
            system_prompt = (
                VerdianPromptTemplates.city_executive_slides_prompt(
                    publicContext=ai_city_context,                   
                    allPillarContexts=allPillarContexts
                )
            )

            # ---------------------------------------------------------
            # USER TEMPLATE
            # ---------------------------------------------------------
            user_template = """
            City:
            {city_name}

            Country:
            {country}

            Year:
            {year}
            """

            # ---------------------------------------------------------
            # LLM CALL
            # ---------------------------------------------------------
            raw = await self._llm_svc.invoke_chain(
                system_prompt=system_prompt,
                user_template=user_template,
                variables={
                    "city_name": city_name,
                    "country": country,
                    "year": year
                },
                label=f"city-executive-slides|{city_name}",
            )

            analysis = json.loads(
                jrp.clean_json_response(raw)
            )

            return {
                "success": True,
                "data": analysis
            }

        except Exception as exc:

            logger.exception(
                "city_executive_slides failed"
            )

            return {
                "success": False,
                "error": str(exc)
            }

rag_query_service = RAGQueryService()
