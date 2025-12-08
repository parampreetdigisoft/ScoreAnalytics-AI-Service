"""
Data Analyzer Service - LLM-powered analysis of SQL Server data
"""

import pandas as pd
import logging
import json

from typing import Dict, List, Any, Optional
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from app.config import settings
from app.services.common.llm_factory import llm_factory
from app.services.common.pillar_prompts import PillarPrompts

logger = logging.getLogger(__name__)


class LLMExecutionService:
    """Service for analyzing SQL Server data using LLM with Veridian Urban Index framework"""

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
            logger.info(f"✅ Data Analyzer initialized with {settings.LLM_PROVIDER}")
        except Exception as e:
            logger.error(f"Failed to initialize Data Analyzer: {e}")
            raise

    async def _ensure_initialized(self):
        """Ensure LLM is initialized before use"""
        if not self._initialized or self.llm is None:
            await self.initialize()

    async def analyze_PillarQuestion_data(
        self,
        data_context: str,
        question: str,
        pillar_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Analyze individual question responses using Veridian framework
        
        Args:
            data_context: Response data with scores
            question: The question being analyzed
            pillar_name: Optional pillar name for context-specific analysis
            
        Returns:
            Dictionary with QualitativeScore, QualitativeProgress, QualitativeComment
        """
        try:
            await self._ensure_initialized()
            
            # Get pillar-specific context if provided
            pillar_context = ""
            if pillar_name:
                pillar_context = f"\nPILLAR CONTEXT:\n{PillarPrompts.get_pillar_context(pillar_name)}"
            
            prompt = ChatPromptTemplate.from_messages([
                (
                    "system",
                    """You are an expert urban data analyst trained in the Veridian Urban Index framework.

                        CRITICAL ANALYSIS RULES:
                        1. Base your analysis on VERIFIABLE EVIDENCE and institutional data quality
                        2. Apply cross-verification: look for contradictions, gaps, and missing data
                        3. Weight structural data (budgets, laws, operational records) over perception
                        4. Flag geographic inequalities - CBD vs periphery, formal vs informal settlements
                        5. Identify data gaps explicitly - absence of data is itself significant
                        6. Never treat "zero complaints" or "perfect scores" as automatically positive
                        7. Consider the Trustworthy Source Chain (TSC): government records → oversight bodies → international organizations → peer-reviewed research

                        SCORING FRAMEWORK (0-4):
                        - 0: Critical failure - severe gaps, systemic breakdown, or contradictory evidence
                        - 1: Poor performance - major deficiencies, weak institutional capacity
                        - 2: Basic functionality - inconsistent, significant gaps in coverage/quality
                        - 3: Good performance - solid evidence, some limitations, room for improvement  
                        - 4: Excellent - strong institutional evidence, equitable, sustained performance

                        DATA YOU WILL RECEIVE:
                        - Question asked to multiple stakeholders
                        - Individual responses with scores (0-4) 
                        - Format: "Score 4: response1 --- Score 2: response2 --- Score 3: response3..."
                        - Overall progress calculation: total_score / (number_of_answers × 4)
                        {pillar_context}

                        YOUR TASKS:
                        1. Analyze all responses critically through the Veridian framework lens
                        2. Look for evidence quality: Are claims backed by data? Which sources?
                        3. Identify patterns: consensus, outliers, contradictions
                        4. Check for red flags specific to this domain
                        5. Assess geographic equity: Do responses cover all populations?
                        6. Determine QualitativeScore (0-4) based on evidence strength, not just sentiment
                        7. Calculate QualitativeProgress as (QualitativeScore / 4) × 100
                        8. Write QualitativeComment (50-70 words) highlighting:
                        - Key evidence-based findings
                        - Data quality/gaps
                        - Geographic or social inequalities if present
                        - Critical concerns or strengths

                        OUTPUT FORMAT (valid JSON only, no markdown, no explanations):
                        {{
                        "QualitativeScore": <number 0-4>,
                        "QualitativeProgress": <number 0-100>,
                        "QualitativeComment": "<50-70 words>"
                        }}

                        DATA:
                        {data_context}
                    """
                ),
                ("user", "Question: {question}\n\nProvide evidence-based analysis following Veridian framework.")
            ])

            chain = prompt | self.llm | StrOutputParser()
            analysis = await chain.ainvoke({
                "data_context": data_context,
                "question": question,
                "pillar_context": pillar_context
            })
            
            # Clean potential markdown formatting
            cleaned = analysis.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            if cleaned.startswith("```"):
                cleaned = cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            cleaned = cleaned.strip()
            
            return {
                "success": True,
                "question": question,
                "analysis": json.loads(cleaned)
            }

        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing error: {e}\nResponse: {analysis}")
            return {
                "success": False,
                "error": f"Invalid JSON response: {str(e)}",
                "question": question,
                "raw_response": analysis
            }
        except Exception as e:
            logger.error(f"Error analyzing question data: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "question": question
            }

    async def analyze_CityPillar_data(
        self,
        data_context: str,
        pillar_name: str
    ) -> Dict[str, Any]:
        """
        Analyze all questions within a pillar for comprehensive pillar assessment
        
        Args:
            data_context: All question responses for the pillar
            pillar_name: Name of the pillar (e.g., "Governance", "Education")
            
        Returns:
            Dictionary with pillar-level assessment
        """
        try:
            await self._ensure_initialized()
            
            pillar_context = PillarPrompts.get_pillar_context(pillar_name)
            
            prompt = ChatPromptTemplate.from_messages([
                (
                    "system",
                    """You are an expert urban analyst synthesizing data for the Veridian Urban Index.

                    PILLAR-SPECIFIC CONTEXT:
                    {pillar_context}

                    SYNTHESIS REQUIREMENTS:
                    1. Apply the Trustworthy Source Chain (TSC) methodology:
                    - Primary: Government/institutional records (budgets, registries, audits)
                    - Secondary: Oversight bodies (ombudsman, auditors, anti-corruption)
                    - Tertiary: International organizations (UN agencies, World Bank, OECD)
                    - Supporting: Peer-reviewed research and credible NGOs
                    
                    2. Cross-verification imperatives:
                    - NO single-source conclusions
                    - Structural data outweighs perception
                    - Local data > national generalizations
                    - Timestamp all evidence
                    - Map spatial inequalities
                    
                    3. Red flag detection:
                    - Political narratives vs operational reality
                    - CBD showcase vs peripheral neglect
                    - Data silence in known problem areas
                    - Perfect scores without verification
                    - Excluded populations (informal settlements, minorities)

                    4. Evidence quality assessment:
                    - Strong: Multiple verified institutional sources, operational data
                    - Moderate: Single reliable source or triangulated perception data
                    - Weak: Unverified claims, outdated data, perception-only
                    - Missing: Critical gaps that indicate problems

                    DATA PROVIDED:
                    Multiple questions with scored responses across this pillar domain.
                    Format: "Question X: Score 4: ans1 --- Score 2: ans2..."

                    YOUR SYNTHESIS TASK:
                    1. Evaluate evidence strength across all questions using TSC hierarchy
                    2. Identify cross-cutting patterns: systemic strengths or failures
                    3. Highlight critical data gaps and what they reveal
                    4. Assess geographic equity: Are marginalized areas covered?
                    5. Flag contradictions between official claims and ground reality
                    6. Determine pillar-level QualitativeScore (0-4) based on:
                    - Institutional evidence quality
                    - Cross-verification success
                    - Equity across populations
                    - Sustainability of performance
                    7. Calculate QualitativeProgress: (QualitativeScore / 4) × 100
                    8. Write QualitativeComment (90-120 words) that:
                    - States key institutional findings
                    - Notes evidence gaps or contradictions
                    - Highlights inequality patterns
                    - Provides actionable insights

                    OUTPUT (valid JSON only):
                    {{
                    "QualitativeScore": <number 0-4>,
                    "QualitativeProgress": <number 0-100>,
                    "QualitativeComment": "<90-120 words>"
                    }}

                    DATA:
                    {data_context}
                    """
                ),
                ("user", "Pillar: {pillarName}\n\nProvide comprehensive evidence-based pillar assessment.")
            ])

            chain = prompt | self.llm | StrOutputParser()
            analysis = await chain.ainvoke({
                "data_context": data_context,
                "pillarName": pillar_name,
                "pillar_context": pillar_context
            })
            
            # Clean response
            cleaned = analysis.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            if cleaned.startswith("```"):
                cleaned = cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            cleaned = cleaned.strip()
            
            return {
                "success": True,
                "pillar": pillar_name,
                "analysis": json.loads(cleaned)
            }

        except Exception as e:
            logger.error(f"Error analyzing pillar data: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "pillar": pillar_name
            }

    async def analyze_City_data(
        self,
        data_context: str,
        city_name: str
    ) -> Dict[str, Any]:
        """
        Analyze all pillars for comprehensive city assessment
        
        Args:
            data_context: All pillar summaries for the city
            city_name: Name of the city
            
        Returns:
            Dictionary with city-level assessment
        """
        try:
            await self._ensure_initialized()
            
            prompt = ChatPromptTemplate.from_messages([
                (
                    "system",
                    """You are a senior urban analyst synthesizing the Veridian Urban Index for a city.

                    VERIDIAN FRAMEWORK PRINCIPLES:
                    1. EVIDENCE HIERARCHY - Trustworthy Source Chain (TSC):
                    Tier 1: Municipal operational data (budgets, service logs, registries)
                    Tier 2: National oversight (audits, inspections, regulators)
                    Tier 3: International verification (UN, World Bank, ILO, WHO, UNESCO)
                    Tier 4: Academic peer-review and credible think tanks
                    
                    2. UNIVERSAL VERIFICATION RULES:
                    - Cross-verify ALL claims with 2+ independent sources
                    - Structural data > perception surveys
                    - Recent data required; flag outdated information
                    - City-level > national averages
                    - Geographic inequality is CENTRAL, not peripheral
                    - Data absence = red flag, not neutral

                    3. CRITICAL RED FLAGS ACROSS PILLARS:
                    - Governance: Zero complaints, missing oversight data
                    - Education: National-only data, public-private system gaps
                    - Business: Informal contradiction, weak property rights
                    - Digital: Smart branding without adoption metrics
                    - Sanitation: CBD showcase, informal settlement neglect
                    - Conflict: "No incidents" in tense contexts
                    - Cohesion: High trust claims in brittle environments
                    - Housing: Forced evictions, gender-blind land data
                    - Environment: Risk maps ignoring peripheries
                    - Health: Averaged disparities hiding inequality
                    - Infrastructure: Connection ≠ reliable access
                    - Ecology: Unequal green space by income
                    - Employment: Underemployment ignored
                    - Heritage: Narrative erasure of minorities

                    4. HOLISTIC CITY ASSESSMENT REQUIRES:
                    - Cross-pillar pattern recognition
                    - Systematic vs isolated problems
                    - Evidence depth and breadth
                    - Institutional capacity across domains
                    - Equity as core metric (not afterthought)
                    - Sustainability of claimed progress

                    DATA PROVIDED:
                    Summary assessments from all 14 Veridian Urban Index pillars with scores and commentary.

                    YOUR CITY-LEVEL SYNTHESIS:
                    1. Evaluate institutional evidence quality across ALL pillars
                    2. Identify systemic patterns:
                    - Strong institutional foundations vs weak governance
                    - Equitable vs inequitable development
                    - Data transparency vs information gaps
                    - Surface improvements vs structural progress
                    3. Assess cross-pillar coherence:
                    - Do infrastructure, sanitation, health align?
                    - Is digital readiness matched by inclusion?
                    - Does economic opportunity reach all residents?
                    4. Weight evidence by TSC hierarchy - reject unsupported claims
                    5. Determine city QualitativeScore (0-4):
                    - 0: Systemic institutional failure, severe inequality
                    - 1: Weak institutions, major gaps, limited data
                    - 2: Mixed performance, inconsistent across pillars
                    - 3: Solid institutional base, some equity gaps
                    - 4: Strong institutions, verified equity, sustained performance
                    6. Calculate QualitativeProgress: (QualitativeScore / 4) × 100
                    7. Write QualitativeComment (100-150 words):
                    - Lead with institutional assessment
                    - Highlight cross-pillar patterns
                    - Flag critical data gaps
                    - Address equity explicitly
                    - Provide strategic recommendations

                    OUTPUT (valid JSON only):
                    {{
                    "QualitativeScore": <number 0-4>,
                    "QualitativeProgress": <number 0-100>,
                    "QualitativeComment": "<100-150 words>"
                    }}

                    DATA:
                    {data_context}
                    """
                ),
                ("user", "City: {cityName}\n\nProvide comprehensive city-level Veridian assessment.")
            ])

            chain = prompt | self.llm | StrOutputParser()
            analysis = await chain.ainvoke({
                "data_context": data_context,
                "cityName": city_name
            })
            
            # Clean response
            cleaned = analysis.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            if cleaned.startswith("```"):
                cleaned = cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            cleaned = cleaned.strip()
            
            return {
                "success": True,
                "city": city_name,
                "analysis": json.loads(cleaned)
            }

        except Exception as e:
            logger.error(f"Error analyzing city data: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "city": city_name
            }


# Singleton instance
llm_Execution_service = LLMExecutionService()
