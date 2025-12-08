"""
    Veridian Urban Index AI Research Service
    Independent research-based scoring with evidence tracking
"""

import json
import logging
import pandas as pd
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from app.config import settings
from app.services.common.llm_factory import llm_factory
from app.services.common.pillar_prompts import PillarPrompts

logger = logging.getLogger(__name__)


class SourceTrustLevel:
    """Trust level hierarchy based on Veridian TSC framework"""
    
    LEVELS = {
        7: "Primary Government/Institutional Records",
        6: "Independent Oversight Bodies", 
        5: "International Organizations (UN, World Bank, etc.)",
        4: "Peer-Reviewed Academic Research",
        3: "Credible NGOs/Think Tanks",
        2: "Private Sector/Technical Data",
        1: "Media/Public Sentiment"
    }
    
    @staticmethod
    def classify_source(source_type: str, source_name: str) -> int:
        """Classify source trust level based on type and name"""
        source_lower = f"{source_type} {source_name}".lower()
        
        # Tier 7: Primary government/institutional
        govt_keywords = ['government', 'municipal', 'ministry', 'department', 
                        'census', 'registry', 'official', 'gazette', 'city hall']
        if any(kw in source_lower for kw in govt_keywords):
            return 7
            
        # Tier 6: Oversight bodies
        oversight_keywords = ['ombudsman', 'auditor', 'inspector general', 
                             'anti-corruption', 'watchdog', 'regulator']
        if any(kw in source_lower for kw in oversight_keywords):
            return 6
            
        # Tier 5: International organizations
        intl_orgs = ['un-habitat', 'who', 'unesco', 'undp', 'unep', 'world bank',
                    'imf', 'oecd', 'unicef', 'ilo', 'fao', 'iea', 'ipcc']
        if any(org in source_lower for org in intl_orgs):
            return 5
            
        # Tier 4: Academic/research
        academic_keywords = ['university', 'journal', 'research', 'study', 
                            'peer-reviewed', 'academic', 'institute']
        if any(kw in source_lower for kw in academic_keywords):
            return 4
            
        # Tier 3: NGOs/Think tanks
        ngo_keywords = ['ngo', 'transparency international', 'brookings', 
                       'chatham house', 'think tank', 'foundation']
        if any(kw in source_lower for kw in ngo_keywords):
            return 3
            
        # Tier 2: Private/technical
        private_keywords = ['company', 'telecom', 'satellite', 'utility', 
                           'transport', 'private']
        if any(kw in source_lower for kw in private_keywords):
            return 2
            
        # Tier 1: Media/social
        return 1


class VerdianAIResearchService:
    """AI service that conducts independent research and evidence-based scoring"""

    def __init__(self):
        self.llm = None
        self._initialized = False

    async def initialize(self):
        """Initialize the LLM"""
        if self._initialized:
            return

        try:
            self.llm = llm_factory.create_llm()
            self._initialized = True
            logger.info(f"✅ Veridian AI Research Service initialized with {settings.LLM_PROVIDER}")
        except Exception as e:
            logger.error(f"Failed to initialize service: {e}")
            raise

    async def _ensure_initialized(self):
        """Ensure LLM is initialized before use"""
        if not self._initialized or self.llm is None:
            await self.initialize()

    async def research_and_score_question(
        self,
        city_name: str,
        city_address: str,
        pillarID:int,
        pillar_name: str,
        question_text: str,
        scoreProgress: float,
        evaluator_score: Optional[float] = None,
        year: int = None
    ) -> Dict[str, Any]:
        """
        Conduct independent research for a question and provide evidence-based score
        
        Args:
            city_name: Name of the city
            city_address: Full address for geographic context
            question_text: The question being evaluated
            pillar_name: Associated pillar name
            evaluator_score: Human evaluator's score (for comparison)
            year: Assessment year
            
        Returns:
            Dict with AI score, evidence, sources, and confidence level
        """
        try:
            await self._ensure_initialized()
            
            if year is None:
                year = datetime.now().year
            
            pillar_context = PillarPrompts.get_pillar_context(pillarID)

            prompt = ChatPromptTemplate.from_messages([
                (
                    "system",
                    """You are an expert urban analyst conducting independent research for the Veridian Urban Index.

                    **CRITICAL MISSION**: Research real evidence and provide verifiable, source-backed scoring.

                    **YOUR RESEARCH PROCESS**:

                    1. **SEARCH FOR EVIDENCE** using web_search tool:
                    - Search for: "{city_name}" official data
                    - Search for: "{city_name}" government reports on this topic
                    - Search for: "{city_name}" + relevant pillar keywords
                    - Search international databases: World Bank, UN-Habitat, WHO data for this city
                    - Search academic research on this city's performance in this area

                    2. **APPLY TRUSTWORTHY SOURCE CHAIN (TSC)**:
                    **TIER 7** (Strongest): City government portals, municipal databases, official statistics
                    **TIER 6**: Auditor reports, ombudsman data, regulatory oversight
                    **TIER 5**: UN agencies (UN-Habitat, WHO, UNESCO), World Bank, OECD
                    **TIER 4**: Peer-reviewed academic journals, university research
                    **TIER 3**: Credible NGOs (Transparency International, etc.)
                    **TIER 2**: Private sector data (telecom, utilities, satellites)
                    **TIER 1**: News media, social media (context only, not primary evidence)

                    3. **CROSS-VERIFICATION REQUIREMENTS**:
                    - Find AT LEAST 2 independent sources (Tiers 5-7 preferred)
                    - Structural data > perception surveys
                    - Recent data (within 3 years) strongly preferred
                    - City-specific data > national averages
                    - Check for geographic inequality within the city

                    4. **RED FLAGS TO DETECT**:
                    - Missing data in sensitive areas (potential suppression)
                    - "Perfect scores" without verification
                    - CBD showcase vs peripheral neglect
                    - Claims without institutional backing
                    - Outdated data (flag if >3 years old)

                    **PILLAR-SPECIFIC CONTEXT**:
                    {pillar_context}

                    **SCORING RUBRIC (0-4)**:
                    - **4 (Excellent)**: Multiple Tier 5-7 sources confirm strong, equitable performance
                    - Verified institutional data
                    - Recent evidence (≤2 years)
                    - Documented across city geography
                    - Sustained performance over time

                    - **3 (Good)**: Solid evidence from Tier 4-6 sources
                    - Generally positive indicators
                    - Some limitations or data gaps
                    - Room for improvement noted

                    - **2 (Basic)**: Mixed or limited evidence
                    - Inconsistent data
                    - Significant gaps in coverage
                    - Equity concerns present

                    - **1 (Poor)**: Weak evidence from lower-tier sources OR
                    - Clear deficiencies documented
                    - Major institutional gaps
                    - Contradictory evidence

                    - **0 (Critical)**: Tier 5+ sources document systemic failure OR
                    - Severe gaps with no contradicting evidence
                    - Critical institutional breakdown
                    - High-confidence evidence of poor performance

                    **CONFIDENCE LEVELS**:
                    - **High**: 3+ sources from Tiers 5-7, recent data, cross-verified, city-specific
                    - **Medium**: 2 sources from Tiers 4-6, OR recent national data, limited cross-verification
                    - **Low**: Single source, Tiers 1-3 only, outdated data, national-level only, or significant data gaps

                    **EVALUATOR CONTEXT** (if provided):
                    Human evaluator scored this as: {evaluator_score} and scoreProgress: {scoreProgress}%.
                    Use this as context but conduct INDEPENDENT research. Your score may differ based on evidence.

                    **OUTPUT REQUIREMENTS** (JSON format):
                    {{
                        "ai_score": <0.00-4.00>,
                        "ai_progress": <0.00-100>,
                        "confidence_level": "<High|Medium|Low>",
                        "evidence_summary": "<100-150 words summarizing key findings and rationale>",
                        "red_flag": "<any concerns found>",
                        "geographic_equity_note": "<comment on inequality if detected>",
                        "data_sources_count": <number of sources cited, >,
                        "source_type": "<Government|International|Academic|NGO|Private|Media>",
                        "source_name": "<organization name>",
                        "source_url": "<URL if available, or 'Not available'>",
                        "source_data_year": <year of data>,
                        "source_trust_level": <1-7>,
                        "source_data_extract": "<specific finding/data point from this source>",
                    }}

                    **RESEARCH NOW for**: {city_name} {city_address}
                    Question: {question_text}
                    Pillar: {pillar_name}
                    """
                ),
                ("user", """Conduct independent research and provide evidence-based scoring.

                    City: {city_name}
                    Address: {city_address}
                    Question: {question_text}
                    Pillar: {pillar_name}
                    Year: {year}
                    {evaluator_context}

                    Search the web for verifiable evidence and provide your assessment.""")
            ])

            evaluator_context = ""
            if evaluator_score is not None:
                evaluator_context = f"Evaluator's Score: {evaluator_score}/4.0"
                
            chain = prompt | self.llm | StrOutputParser()
            
            result = await chain.ainvoke({
                "city_name": city_name,
                "city_address": city_address,
                "question_text": question_text,
                "pillar_name": pillar_name,
                "pillar_context": pillar_context,
                "year": year,
                "evaluator_score": evaluator_score if evaluator_score else "Not provided",
                "scoreProgress": scoreProgress if scoreProgress else 0,
                "evaluator_context": evaluator_context
            })
            
            # Parse response
            cleaned = self._clean_json_response(result)
            analysis = json.loads(cleaned)
            
            # Calculate discrepancy if evaluator score provided
            discrepancy = None
            if evaluator_score is not None:
                discrepancy = abs(analysis['ai_score'] - evaluator_score)
            
            return {
                "success": True,
                "question": question_text,
                "year": year,
                "ai_score": analysis['ai_score'],
                "ai_progress": analysis['ai_progress'],
                "evaluator_score": evaluator_score,
                "discrepancy": discrepancy,
                "confidence_level": analysis['confidence_level'],
                "data_sources_count": analysis['data_sources_count'],
                "evidence_summary": analysis['evidence_summary'],
                "red_flag": analysis['red_flag'],
                "geographic_equity_note": analysis.get('geographic_equity_note', ''),
                "source_type": analysis['source_type'],
                "source_name": analysis['source_name'],
                "source_url": analysis['source_url'],
                "source_data_year": analysis['source_data_year'],
                "source_data_extract": analysis['source_data_extract'],
                "source_trust_level": analysis['source_trust_level']
            }

        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing error: {e}\nResponse: {result}")
            return {
                "success": False,
                "error": f"Invalid JSON response: {str(e)}",
                "raw_response": result
            }
        except Exception as e:
            logger.error(f"Error in question research: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }

    async def research_and_score_pillar1(
        self,
        city_name: str,
        city_address: str,
        pillarId:int,
        pillar_name: str,# name of the pillar
        questions_context: str = None,#comme all question of this pillar like: question Are mental and psychosocial services available to survivors of urban violence and displacement? Ai_Score 2.50 --- question so on 
        evaluator_score: Optional[float] = None,
        aIScore: Optional[float] = None, # asi score for this pillar if available
        year: int = None
    ) -> Dict[str, Any]:
        """
        Conduct independent research for an entire pillar
        
        Args:
            city_name: Name of the city
            city_address: Full address
            pillar_name: Name of the pillar
            evaluator_score: Human evaluator's pillar score
            question_scores: Optional list of AI question scores for this pillar
            year: Assessment year
        """
        try:
            await self._ensure_initialized()
            
            if year is None:
                year = datetime.now().year
            
            pillar_context = PillarPrompts.get_pillar_context(pillarId)

            evaluator_context = (
                f"Human Evaluator Score: {evaluator_score}/4.0" if evaluator_score is not None
                else "No evaluator score provided."
            )

            ai_input_context = (
                f"Previous AI Pillar Score: {aIScore}/4.0" if aIScore is not None
                else "No prior AI score available."
            )

            question_research_context = (
                f"Question-Level Evidence & Scores:\n{questions_context}"
                if questions_context else
                "No question-level research data was provided."
            )
            
            # Build context from question-level research if available
            
            prompt = ChatPromptTemplate.from_messages([
                (
                    "system",
                    """ You are an expert urban analyst conducting independent research for the Veridian Urban Index.

                 **CRITICAL MISSION**: Research real evidence and provide verifiable, source-backed scoring.

                   **YOUR RESEARCH PROCESS**:

                 🔎 **MANDATORY RESEARCH PROCESS**
                    1. Search web using:
                    - "{city_name} {city_address}" official data
                    - "{city_name}" government reports for "{pillar_name}"
                    - World Bank, UN-Habitat, WHO, OECD
                    - Peer-reviewed academic research

                    2. **APPLY TRUSTWORTHY SOURCE CHAIN (TSC)**:
                    **TIER 7** (Strongest): City government portals, municipal databases, official statistics
                    **TIER 6**: Auditor reports, ombudsman data, regulatory oversight
                    **TIER 5**: UN agencies (UN-Habitat, WHO, UNESCO), World Bank, OECD
                    **TIER 4**: Peer-reviewed academic journals, university research
                    **TIER 3**: Credible NGOs (Transparency International, etc.)
                    **TIER 2**: Private sector data (telecom, utilities, satellites)
                    **TIER 1**: News media, social media (context only, not primary evidence)

                    3. **CROSS-VERIFICATION REQUIREMENTS**:
                    - Find AT LEAST 2 independent sources (Tiers 5-7 preferred)
                    - Structural data > perception surveys
                    - Recent data (within 1 year) strongly preferred
                    - City-specific data > national averages
                    - Check for geographic inequality within the city

                    4. **RED FLAGS TO DETECT**:
                    - Missing data in sensitive areas (potential suppression)
                    - "Perfect scores" without verification
                    - CBD showcase vs peripheral neglect
                    - Claims without institutional backing
                    - Outdated data (flag if >1 year old)

                    5. **CROSS-CUTTING ANALYSIS**:
                    - Identify patterns across multiple dimensions of this pillar
                    - Look for systemic strengths or failures
                    - Assess institutional capacity
                    - Evaluate geographic equity
                    - Check temporal trends (improving/declining)

                    6. **SCORING RUBRIC (0-4)**:
                    - **4 (Excellent)**: Multiple Tier 5-7 sources confirm strong, equitable performance
                    - Verified institutional data
                    - Recent evidence (≤2 years)
                    - Documented across city geography
                    - Sustained performance over time

                    - **3 (Good)**: Solid evidence from Tier 4-6 sources
                    - Generally positive indicators
                    - Some limitations or data gaps
                    - Room for improvement noted

                    - **2 (Basic)**: Mixed or limited evidence
                    - Inconsistent data
                    - Significant gaps in coverage
                    - Equity concerns present

                    - **1 (Poor)**: Weak evidence from lower-tier sources OR
                    - Clear deficiencies documented
                    - Major institutional gaps
                    - Contradictory evidence

                    - **0 (Critical)**: Tier 5+ sources document systemic failure OR
                    - Severe gaps with no contradicting evidence
                    - Critical institutional breakdown
                    - High-confidence evidence of poor performance

                    7. **CONFIDENCE LEVELS**:
                    - **High**: 3+ sources from Tiers 5-7, recent data, cross-verified, city-specific
                    - **Medium**: 2 sources from Tiers 4-6, OR recent national data, limited cross-verification
                    - **Low**: Single source, Tiers 1-3 only, outdated data, national-level only, or significant data gaps
                
                ====================================================
                
                📘 **PILLAR CONTEXT**
                {pillar_context}

                📊 **QUESTION-LEVEL CONTEXT**
                {question_research_context}

                👨‍⚖️ **HUMAN & PRIOR AI CONTEXT** *(for reference only)*
                {evaluator_context}  
                {ai_input_context}
                ====================================================

                🔐 **OUTPUT FORMAT (STRICT JSON ONLY — NO TEXT OUTSIDE JSON)**
                {{
                    "ai_score": <0.00-4.00>,
                    "ai_progress": <0.00-100>,
                    "confidence_level": "<High|Medium|Low>",
                    "evidence_summary": "<150-200 words: key findings, patterns, gaps>",
                    "sources": [
                        {{
                            "source_type": "<Government|International|Academic|NGO|Private|Media>",
                            "source_name": "<organization name>",
                            "source_url": "<URL if available, or 'Not available'>",
                            "data_year": <year of data>,
                            "trust_level": <1-7>,
                            "data_extract": "<specific finding/data point from this source>"
                        }}
                    ],
                    "red_flag": "<systemic concerns>",
                    "geographic_equity_note": "<inequality assessment>",
                    "institutional_assessment": "<capacity and governance quality>",
                    "data_gap_analysis": "<critical missing information>"
                }}

               🚨 **DO NOT include markdown. DO NOT explain your answer. Return JSON only.**
                ====================================================
                
                """),
                ("user", """Conduct independent research and provide evidence-based scoring of pillar performance.

                City: {city_name}
                Address: {city_address}
                Pillar: {pillar_name}
                Year: {year}

                Conduct full independent research and produce final scoring.""")
            ])

            chain = prompt | self.llm | StrOutputParser()
            
            result = await chain.ainvoke({
                "city_name": city_name,
                "city_address": city_address,
                "pillar_name": pillar_name,
                "year": year,
                "pillar_context": pillar_context,
                "question_research_context": question_research_context,
                "ai_input_context": ai_input_context,
                "evaluator_context": evaluator_context 
            })
            
            cleaned = self._clean_json_response(result)
            analysis = json.loads(cleaned)
            
            discrepancy = None
            if evaluator_score is not None:
                discrepancy = abs(analysis['ai_score'] - evaluator_score)
            
            return {
                "success": True,
                "pillar": pillar_name,
                "ai_score": analysis['ai_score'],
                "ai_progress": analysis['ai_progress'],
                "evaluator_score": evaluator_score,
                "discrepancy": discrepancy,
                "confidence_level": analysis['confidence_level'],
                "evidence_summary": analysis['evidence_summary'],
                "sources": analysis['sources'],
                "red_flag": analysis.get('red_flag',''),
                "geographic_equity_note": analysis.get('geographic_equity_note', ''),
                "institutional_assessment": analysis.get('institutional_assessment', ''),
                "data_gap_analysis": analysis.get('data_gap_analysis', ''),
                "year": year
            }

        except Exception as e:
            logger.error(f"Error in pillar research: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    async def research_and_score_city(
        self,
        city_name: str,
        city_address: str,
        evaluator_score: Optional[float] = None,
        aIScore: Optional[float] = None,
        pillars_context: Optional[str] = None,
        year: int = None
    ) -> Dict[str, Any]:
        """
        Conduct comprehensive city-level assessment
        
        Args:
            city_name: Name of the city
            city_address: Full address
            evaluator_score: Human evaluator's city score
            pillar_scores: Optional list of AI pillar scores
            year: Assessment year
        """
        try:
            await self._ensure_initialized()
            
            if year is None:
                year = datetime.now().year
            
            # Build pillar summary context
            pillars_context = "\n**PILLAR-LEVEL FINDINGS** (for synthesis):\n" + pillars_context
            
            
            prompt = ChatPromptTemplate.from_messages([
                (
                    "system",
                    """You are conducting city-wide Veridian Urban Index assessment.

                        **CITY-LEVEL SYNTHESIS STRATEGY**:

                        1. **HOLISTIC RESEARCH**:
                        - Search for city-wide governance indicators
                        - Look for urban development plans and progress reports
                        - Find comparative data (peer cities, regional benchmarks)
                        - Identify systemic patterns across all 14 pillars

                        2. **CROSS-PILLAR INTEGRATION**:
                        - Are institutional strengths/weaknesses consistent?
                        - Do infrastructure and service delivery align?
                        - Is economic growth reaching all residents?
                        - Are environmental and social pillars balanced?

                        3. **EVIDENCE HIERARCHY**:
                        - Prioritize city master plans, municipal reports (Tier 7)
                        - Cross-check with UN-Habitat city profiles (Tier 5)
                        - Validate with academic urban studies (Tier 4)
                        - Consider think tank city assessments (Tier 3)

                        4. **CRITICAL CITY-LEVEL QUESTIONS**:
                        - Institutional capacity: Strong or fragmented?
                        - Equity: Inclusive or deeply divided?
                        - Sustainability: Short-term gains or structural progress?
                        - Data transparency: Open or opaque governance?
                        - Trajectory: Improving, stable, or declining?

                        5. **SCORING FRAMEWORK** (0-4):
                        - **4**: Strong across all pillars, verified equity, robust institutions
                        - **3**: Solid performance, some weak areas, generally inclusive
                        - **2**: Mixed results, significant gaps, inequality concerns
                        - **1**: Weak institutions, major deficiencies, limited data
                        - **0**: Systemic failure, severe inequality, institutional collapse

                        **OUTPUT** (JSON):
                        {{
                            "ai_score": <0.00-4.00>,
                            "ai_progress": <0.00-100>,
                            "confidence_level": "<High|Medium|Low>",
                            "evidence_summary": "<200-250 words: holistic assessment>",
                            "source": "<Tier 5-7 sources prioritized>",
                            "cross_pillar_patterns": "<2-200 words: systemic observations>",
                            "institutional_capacity": "<2-200 words: governance quality assessment>",
                            "equity_assessment": "<2-200 words: geographic and social inclusion>",
                            "sustainability_outlook": "<20-200 words: trajectory and resilience>",
                            "strategic_recommendation": "<20-200 words: priority actions> ",
                            "data_transparency_note": "<2-200 words: information availability>"
                        }}

                        {pillars_context}
                        **RESEARCH NOW for**: {city_name} {city_address}
                """),
                ("user", """Conduct comprehensive city assessment:

                City: {city_name}
                Address: {city_address}
                Year: {year}
                aIScore:{aIScore}
                {evaluator_context}

                Provide holistic Veridian Urban Index evaluation.""")
            ])

            evaluator_context = ""
            if evaluator_score is not None:
                evaluator_context = f"Evaluator's City Score: {evaluator_score}/4.0"

            chain = prompt | self.llm | StrOutputParser()
            
            result = await chain.ainvoke({
                "city_name": city_name,
                "city_address": city_address,
                "pillars_context": pillars_context,
                "year": year,
                "aIScore":aIScore if aIScore else "Not provided",
                "evaluator_context": evaluator_context
            })
            
            cleaned = self._clean_json_response(result)
            analysis = json.loads(cleaned)
            
            discrepancy = None
            if evaluator_score is not None:
                discrepancy = abs(analysis['ai_score'] - evaluator_score)
            
            return {
                "success": True,
                "city": city_name,
                "ai_score": analysis['ai_score'],
                "ai_progress": analysis['ai_progress'],
                "evaluator_score": evaluator_score,
                "discrepancy": discrepancy,
                "confidence_level": analysis['confidence_level'],
                "evidence_summary": analysis['evidence_summary'],
                "source": analysis['source'],
                "cross_pillar_patterns": analysis.get('cross_pillar_patterns', ''),
                "institutional_capacity": analysis.get('institutional_capacity', ''),
                "equity_assessment": analysis.get('equity_assessment', ''),
                "sustainability_outlook": analysis.get('sustainability_outlook', ''),
                "strategic_recommendation": analysis.get('strategic_recommendation', ''),
                "data_transparency_note": analysis.get('data_transparency_note', ''),
                "year": year
            }

        except Exception as e:
            logger.error(f"Error in city research: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    async def research_and_score_pillar(
        self,
        city_name: str,
        city_address: str,
        pillarId: int,
        pillar_name: str,
        questions_context: str = None,
        evaluator_score: Optional[float] = None,
        aIScore: Optional[float] = None,
        year: int = None
    ) -> Dict[str, Any]:
        """
        Conduct independent research for an entire pillar with comprehensive web search.
        
        Args:
            city_name: Name of the city
            city_address: Full address of the city
            pillarId: ID of the pillar (1-14)
            pillar_name: Name of the pillar
            questions_context: Context from pillar questions with scores
            evaluator_score: Human evaluator's pillar score (0-4)
            aIScore: Previous AI score for this pillar (0-4)
            year: Assessment year
        
        Returns:
            Dictionary with research results and scoring
        """
        try:
            await self._ensure_initialized()
            
            if year is None:
                year = datetime.now().year
            
            # Get pillar-specific context
            pillar_context = PillarPrompts.get_pillar_context(pillarId)
            
            # Build human context
            evaluator_context = (
                f"Human Evaluator Score: {evaluator_score}/4.0"
                if evaluator_score is not None
                else "No human evaluator score available."
            )
            
            # Build AI context
            ai_input_context = (
                f"Previous AI Score: {aIScore}/4.0"
                if aIScore is not None
                else "No previous AI score available."
            )
            
            # Build question context
            question_research_context = (
                f"Question-Level Research Data:\n{questions_context}"
                if questions_context
                else "No question-level research data provided."
            )
            
            # Create the prompt
            prompt = ChatPromptTemplate.from_messages([
                (
                    "system",
                    """You are an expert urban analyst for the Veridian Urban Index. Your task is to conduct independent research and provide evidence-based scoring for a city pillar.

                        **YOUR MISSION:**
                        Research real evidence from trustworthy sources and provide a verifiable score (0-4) with clear justification.

                        **RESEARCH REQUIREMENTS:**

                        1. **Search Strategy** - You MUST search for:
                        - Official city/municipal data: "{city_name} {pillar_name} official statistics"
                        - Government reports: "{city_name} government {pillar_name} report"
                        - International data: "World Bank {city_name}" OR "UN-Habitat {city_name}"
                        - Academic research: "{city_name} {pillar_name} peer-reviewed study"
                        - Recent news: "{city_name} {pillar_name} {year}"

                        2. **Source Quality Hierarchy (Trustworthy Source Chain)**:
                        - **TIER 7** (Strongest): Official city government portals, municipal databases, city statistics
                        - **TIER 6**: Government audit reports, ombudsman data, regulatory oversight
                        - **TIER 5**: UN agencies (UN-Habitat, WHO, UNESCO), World Bank, OECD reports
                        - **TIER 4**: Peer-reviewed academic journals, university research centers
                        - **TIER 3**: Established NGOs (Transparency International, Human Rights Watch)
                        - **TIER 2**: Private sector reports (utilities, telecom companies)
                        - **TIER 1**: News media (for context only, NOT primary evidence)

                        3. **Verification Standards**:
                        - Find AT LEAST 2 independent sources (preferably Tier 5-7)
                        - Prioritize: City-specific data > National averages
                        - Prioritize: Recent data (within 2 years) > Old data
                        - Prioritize: Structural metrics > Perception surveys
                        - Check for geographic inequality within the city

                        4. **Red Flags to Identify**:
                        - Missing data in politically sensitive areas
                        - Claims of "perfect" performance without evidence
                        - CBD showcase areas vs neglected periphery
                        - Outdated data presented as current
                        - Contradictions between official claims and credible reports

                        5. **Scoring Rubric (0-4 scale)**:

                        **4.0 (Excellent)**:
                        - Multiple Tier 5-7 sources confirm strong performance
                        - Recent verified data (≤2 years old)
                        - Evidence of equity across city geography
                        - Sustained positive trends over time
                        - Strong institutional capacity documented

                        **3.0 (Good)**:
                        - Solid evidence from Tier 4-6 sources
                        - Generally positive indicators with some limitations
                        - Minor data gaps but overall strong performance
                        - Some room for improvement identified

                        **2.0 (Basic/Adequate)**:
                        - Mixed evidence or limited data availability
                        - Inconsistent performance across indicators
                        - Significant gaps in service coverage or equity
                        - Concerns about sustainability

                        **1.0 (Poor)**:
                        - Weak evidence OR clear deficiencies documented
                        - Major institutional gaps
                        - Significant inequity or service failures
                        - Contradictory or unreliable data

                        **0.0 (Critical Failure)**:
                        - Tier 5+ sources document systemic failure
                        - Severe gaps with strong evidence
                        - Critical institutional breakdown
                        - High-confidence evidence of very poor performance

                        6. **Confidence Assessment**:
                        - **High Confidence**: 3+ sources from Tiers 5-7, recent city-specific data, cross-verified
                        - **Medium Confidence**: 2 sources from Tiers 4-6, OR national data applied locally
                        - **Low Confidence**: Single source, Tiers 1-3 only, outdated data, or major data gaps

                        **CONTEXT PROVIDED:**

                        **Pillar Focus Areas:**
                        {pillar_context}

                        **Question-Level Context:**
                        {question_research_context}

                        **Reference Scores (for context only - DO NOT copy these):**
                        {evaluator_context}
                        {ai_input_context}

                        **OUTPUT FORMAT:**

                        You MUST return ONLY valid JSON in this exact structure (no markdown, no explanations):

                        {{
                        "ai_score": 2.75,
                        "ai_progress": 68.75,
                        "confidence_level": "High",
                        "evidence_summary": "Concise 150-200 word summary of key findings, patterns discovered, and critical gaps identified based on your research.",
                        "sources": [
                            {{
                            "source_type": "Government",
                            "source_name": "City Department of X",
                            "source_url": "https://example.com/report",
                            "data_year": 2024,
                            "trust_level": 7,
                            "data_extract": "Specific finding or data point from this source"
                            }},
                            {{
                            "source_type": "International",
                            "source_name": "World Bank",
                            "source_url": "https://worldbank.org/data",
                            "data_year": 2023,
                            "trust_level": 5,
                            "data_extract": "Another specific data point"
                            }}
                        ],
                        "red_flag": "Concise 150-200 word Description of any systemic concerns, contradictions, or warning signs identified ",
                        "geographic_equity_note": "Concise 150-200 word Assessment of whether services/outcomes are equitably distributed across the city",
                        "institutional_assessment": " Concise 150-200 word Evaluation of government capacity, governance quality, and institutional effectiveness",
                        "data_gap_analysis": "Concise 150-200 word Critical information that was missing or unavailable during research"
                        }}

                        **CRITICAL RULES:**
                        - ai_score must be between 0.00 and 4.00
                        - ai_progress = (ai_score / 4.0) * 100
                        - Include AT LEAST 2 sources in the sources array
                        - Each source must have all required fields
                        - Return ONLY the JSON object, nothing else
                        """
                                    ),
                                    (
                                        "user",
                                        """Research and score the following pillar:

                        City: {city_name}
                        Full Address: {city_address}
                        Pillar: {pillar_name}
                        Assessment Year: {year}

                        Conduct comprehensive web research using the search strategies outlined above. Find real evidence from trustworthy sources and provide your independent scoring with clear justification.

                        Remember: Search for official data, government reports, international organization data, and academic research. Provide verifiable evidence-based scoring."""
                )
            ])
            
            # Execute the chain
            chain = prompt | self.llm | StrOutputParser()
            
            result = await chain.ainvoke({
                "city_name": city_name,
                "city_address": city_address,
                "pillar_name": pillar_name,
                "year": year,
                "pillar_context": pillar_context,
                "question_research_context": question_research_context,
                "ai_input_context": ai_input_context,
                "evaluator_context": evaluator_context
            })
            
            # Clean and parse JSON response
            cleaned = self._clean_json_response(result)
            
            # Add detailed logging
            logger.info(f"Raw LLM response length: {len(result)}")
            logger.info(f"Cleaned response: {cleaned[:500]}...")  # First 500 chars
            
            analysis = json.loads(cleaned)
            
            # Validate required fields
            required_fields = ['ai_score', 'ai_progress', 'confidence_level', 
                            'evidence_summary', 'sources']
            missing_fields = [f for f in required_fields if f not in analysis]
            if missing_fields:
                raise ValueError(f"Missing required fields in LLM response: {missing_fields}")
            
            # Calculate discrepancy if evaluator score exists
            discrepancy = None
            if evaluator_score is not None:
                discrepancy = abs(analysis['ai_score'] - evaluator_score)
            
            return {
                "success": True,
                "pillar": pillar_name,
                "pillar_id": pillarId,
                "ai_score": analysis['ai_score'],
                "ai_progress": analysis['ai_progress'],
                "evaluator_score": evaluator_score,
                "discrepancy": discrepancy,
                "confidence_level": analysis['confidence_level'],
                "evidence_summary": analysis['evidence_summary'],
                "sources": analysis.get('sources', []),
                "red_flag": analysis.get('red_flag', ''),
                "geographic_equity_note": analysis.get('geographic_equity_note', ''),
                "institutional_assessment": analysis.get('institutional_assessment', ''),
                "data_gap_analysis": analysis.get('data_gap_analysis', ''),
                "year": year,
                "timestamp": datetime.now().isoformat()
            }
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing error: {e}")
            logger.error(f"Attempted to parse: {cleaned[:1000]}")
            return {
                "success": False,
                "error": f"Failed to parse JSON response: {str(e)}",
                "raw_response": result[:500] if 'result' in locals() else "No response"
            }
        except Exception as e:
            logger.error(f"Error in pillar research for {pillar_name}: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "pillar": pillar_name
            }

    def _clean_json_response1(self, response: str) -> str:
            """Clean JSON response from markdown formatting"""
            cleaned = response.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            if cleaned.startswith("```"):
                cleaned = cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            return cleaned.strip()

    def _clean_json_response(self, response: str) -> str:
        """
        Clean LLM response to extract valid JSON.
        
        Args:
            response: Raw response from LLM
            
        Returns:
            Cleaned JSON string
        """
        # Remove markdown code blocks
        response = response.strip()
        
        # Remove ```json and ``` markers
        if response.startswith('```'):
            response = response.split('```', 2)[1]
            if response.startswith('json'):
                response = response[4:]
            response = response.strip()
        
        # Find JSON object boundaries
        start_idx = response.find('{')
        end_idx = response.rfind('}')
        
        if start_idx == -1 or end_idx == -1:
            raise ValueError("No valid JSON object found in response")
        
        json_str = response[start_idx:end_idx + 1]
        
        # Remove any text before or after JSON
        return json_str.strip()
# Singleton instance
veridian_ai_research_service = VerdianAIResearchService()