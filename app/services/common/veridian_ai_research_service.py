"""
    Veridian Urban Index AI Research Service
    Independent research-based scoring with evidence tracking
"""
import re
import json
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from app.config import settings
from app.services.common.llm_factory import llm_factory
from app.services.common.pillar_prompts import PillarPrompts

logger = logging.getLogger(__name__)

class VerdianAIResearchService:
    """AI service that conducts independent research and evidence-based scoring"""

    def __init__(self):
        self.llm = None
        self._initialized = False
        self.max_retries = 3
        self.retry_delay = 1  # seconds

    async def initialize(self):
        """Initialize the LLM with retry logic"""
        if self._initialized:
            return

        for attempt in range(self.max_retries):
            try:
                self.llm = llm_factory.create_llm()
                self._initialized = True
                logger.info(f"✅ Veridian AI Research Service initialized with {settings.LLM_PROVIDER}")
                return
            except Exception as e:
                logger.error(f"Initialization attempt {attempt + 1} failed: {e}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay)
                    continue
                else:
                    raise RuntimeError(f"Failed to initialize after {self.max_retries} attempts: {e}")

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
            scoreProgress: Optional[float] = None,
            evaluator_score: Optional[float] = None,
            year: int = None
        ) -> Dict[str, Any]:
            """
            Conduct independent research for a single question with enhanced validation
            
            Returns comprehensive evidence-based scoring with detailed source tracking
            """
            try:
                await self._ensure_initialized()
                
                if year is None:
                    year = datetime.now().year
                
                pillar_context = PillarPrompts.get_pillar_context(pillarID)

                prompt = ChatPromptTemplate.from_messages([
                    ("system", self._get_question_system_prompt()),
                    ("user", """Conduct independent research and provide evidence-based scoring.
                     
                    City: {city_name}
                    Address: {city_address}
                    Question: {question_text}
                    Pillar: {pillar_name}
                    Year: {year}
                    {evaluator_context}

                    SEARCH THE WEB for verifiable evidence and provide your assessment.
                    
                    Remember: Return ONLY a single JSON object with the EXACT structure specified. Report details for only the MOST TRUSTWORTHY source.""")
                ])

                evaluator_context = ""
                if evaluator_score is not None:
                    evaluator_context = f"Evaluator Score: {evaluator_score}/4, Progress: {scoreProgress}%" if evaluator_score else "No evaluator score provided"

                     # Execute with retry logic
                for attempt in range(self.max_retries):
                    try:

                        chain = prompt | self.llm | StrOutputParser()
                        
                        result = await chain.ainvoke({
                            "city_name": city_name,
                            "city_address": city_address,
                            "question_text": question_text,
                            "pillar_name": pillar_name,
                            "pillar_context": pillar_context,
                            "year": year,
                            "evaluator_score": evaluator_score if evaluator_score is not None else "Not provided",
                            "scoreProgress": scoreProgress if scoreProgress is not None else 0,
                            "evaluator_context": evaluator_context
                        })
                        
                        # Parse and validate response
                        cleaned = self._clean_json_response(result)
                        analysis = self._validate_question_response(json.loads(cleaned))
                        
                        # Calculate discrepancy
                        discrepancy = None
                        if evaluator_score is not None:
                            discrepancy = abs(analysis['ai_progress'] - ((evaluator_score/4)*100))
                        else:
                            discrepancy = analysis['ai_progress']
                
                        
                        return {
                            "success": True,
                            "question": question_text,
                            "year": year,
                            "ai_score": analysis['ai_score'],
                            "ai_progress": analysis['ai_progress'],
                            "discrepancy": discrepancy,
                            "confidence_level": analysis['confidence_level'],
                            "data_sources_count": analysis['data_sources_count'],
                            "evidence_summary": analysis['evidence_summary'],
                            "red_flag": analysis.get('red_flag', ''),
                            "geographic_equity_note": analysis.get('geographic_equity_note', ''),
                            "source_type": analysis['source_type'],
                            "source_name": analysis['source_name'],
                            "source_url": analysis['source_url'],
                            "source_data_year": analysis['source_data_year'],
                            "source_data_extract": analysis['source_data_extract'],
                            "source_trust_level": analysis['source_trust_level']
                        }

                    except (json.JSONDecodeError, ValueError) as e:
                        logger.error(f"JSON parse error on attempt {attempt + 1}: {e}")
                        if attempt < self.max_retries - 1:
                            await asyncio.sleep(self.retry_delay)
                            continue
                        else:
                            raise

            except Exception as e:
                logger.error(f"Error in question research: {e}", exc_info=True)
                return {
                    "success": False,
                    "error": str(e)
                }
            
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
                f"Human Evaluator Score: {evaluator_score}/100"
                if evaluator_score is not None
                else "No evaluator score"
            )
            
            # Build AI context
            ai_input_context = (
                f"Previous AI Score: {aIScore}/4"
                if aIScore is not None
                else "No previous AI score available."
            )
            
            # Create the prompt
            prompt = ChatPromptTemplate.from_messages([
                ("system",self._get_pillar_system_prompt()),
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
            
                       # Execute with retry logic
            for attempt in range(self.max_retries):
                try:
                    chain = prompt | self.llm | StrOutputParser()
                    
                    result = await chain.ainvoke({
                        "city_name": city_name,
                        "city_address": city_address,
                        "pillar_name": pillar_name,
                        "year": year,
                        "pillar_context": pillar_context,
                        "ai_input_context": ai_input_context,
                        "evaluator_context": evaluator_context
                    })
                    
                    # Parse and validate
                    cleaned = self._clean_json_response(result)
                    analysis = self._validate_pillar_response(json.loads(cleaned))
                    
                    discrepancy = self._calculate_discrepancy(
                        analysis['ai_progress'],
                        evaluator_score
                    )
                    
                    return {
                        "success": True,
                        "pillar": pillar_name,
                        "pillar_id": pillarId,
                        "ai_score": analysis['ai_score'],
                        "ai_progress": analysis['ai_progress'],
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
                    
                except (json.JSONDecodeError, ValueError) as e:
                    logger.error(f"JSON parse error on attempt {attempt + 1}: {e}")
                    if attempt < self.max_retries - 1:
                        await asyncio.sleep(self.retry_delay)
                        continue
                    else:
                        raise
        except Exception as e:
            logger.error(f"Error in pillar research for {pillar_name}: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "pillar": pillar_name
            }

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
                ("system",self._get_city_system_prompt()),
                ("user", """Conduct comprehensive city-wide assessment:

                City: {city_name}
                Address: {city_address}
                Year: {year}
                aIScore:{aIScore}
                {evaluator_context}

                SEARCH THE WEB comprehensively for city-level data. Synthesize findings across all 14 pillars. Provide holistic Veridian Urban Index evaluation with clear evidence.""")
            ])

            evaluator_context = ""
            if evaluator_score is not None:
                evaluator_context = f"Evaluator's City Score: {evaluator_score}/100"

            for attempt in range(self.max_retries):
                try:
                    chain = prompt | self.llm | StrOutputParser()
                    
                    result = await chain.ainvoke({
                        "city_name": city_name,
                        "city_address": city_address,
                        "pillars_context": pillars_context,
                        "year": year,
                        "aIScore":aIScore if aIScore else "Not provided",
                        "evaluator_context": evaluator_context
                    })
                    
                     # Parse and validate
                    cleaned = self._clean_json_response(result)
                    analysis = self._validate_city_response(json.loads(cleaned))
                    
                    discrepancy = self._calculate_discrepancy(
                        analysis['ai_progress'],
                        evaluator_score
                    )
                    
                    return {
                        "success": True,
                        "city": city_name,
                        "ai_score": analysis['ai_score'],
                        "ai_progress": analysis['ai_progress'],
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
                except (json.JSONDecodeError, ValueError) as e:
                    logger.error(f"JSON parse error on attempt {attempt + 1}: {e}")
                    if attempt < self.max_retries - 1:
                        await asyncio.sleep(self.retry_delay)
                        continue
                    else:
                        raise
        except Exception as e:
            logger.error(f"Error in city research: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    # ==================== VALIDATION METHODS ====================

    def _validate_question_response(self, data: Dict) -> Dict:
        """Validate and sanitize question response data"""
        required_fields = [
            'ai_score', 'ai_progress', 'confidence_level', 'evidence_summary',
            'data_sources_count', 'source_type', 'source_name', 'source_url',
            'source_data_year', 'source_trust_level', 'source_data_extract'
        ]
        
        for field in required_fields:
            if field not in data:
                raise ValueError(f"Missing required field: {field}")
        
        # Validate score ranges
        if not (0 <= data['ai_score'] <= 4):
            raise ValueError(f"ai_score must be 0-4, got {data['ai_score']}")
        
        if not (0 <= data['ai_progress'] <= 100):
            raise ValueError(f"ai_progress must be 0-100, got {data['ai_progress']}")
        
        if not (1 <= data['source_trust_level'] <= 7):
            raise ValueError(f"source_trust_level must be 1-7, got {data['source_trust_level']}")
        
        # Validate confidence level
        if data['confidence_level'] not in ['High', 'Medium', 'Low']:
            logger.warning(f"Invalid confidence level: {data['confidence_level']}, defaulting to 'Medium'")
            data['confidence_level'] = 'Medium'
        
        return data

    def _validate_pillar_response(self, data: Dict) -> Dict:
        """Validate and sanitize pillar response data"""
        required_fields = [
            'ai_score', 'ai_progress', 'confidence_level', 
            'evidence_summary', 'sources'
        ]
        
        for field in required_fields:
            if field not in data:
                raise ValueError(f"Missing required field: {field}")
        
        # Validate score ranges
        if not (0 <= data['ai_score'] <= 4):
            raise ValueError(f"ai_score must be 0-4, got {data['ai_score']}")
        
        if not (0 <= data['ai_progress'] <= 100):
            raise ValueError(f"ai_progress must be 0-100, got {data['ai_progress']}")
        
        # Validate sources array
        if not isinstance(data['sources'], list) or len(data['sources']) < 1:
            logger.warning("Invalid sources array, creating placeholder")
            data['sources'] = [{
                "source_type": "Unknown",
                "source_name": "Data not available",
                "source_url": "Not available",
                "data_year": datetime.now().year,
                "trust_level": 1,
                "data_extract": "Insufficient data available"
            }]
        
        return data

    def _validate_city_response(self, data: Dict) -> Dict:
        """Validate and sanitize city response data"""
        required_fields = [
            'ai_score', 'ai_progress', 'confidence_level', 'evidence_summary'
        ]
        
        for field in required_fields:
            if field not in data:
                raise ValueError(f"Missing required field: {field}")
        
        # Validate score ranges
        if not (0 <= data['ai_score'] <= 4):
            raise ValueError(f"ai_score must be 0-4, got {data['ai_score']}")
        
        if not (0 <= data['ai_progress'] <= 100):
            raise ValueError(f"ai_progress must be 0-100, got {data['ai_progress']}")
        
        return data

    # ==================== UTILITY METHODS ====================

    def _calculate_discrepancy(
        self, 
        ai_progress: float, 
        evaluator_score: Optional[float]
    ) -> float:
        """Calculate discrepancy between AI and evaluator scores"""
        if evaluator_score is not None:

            return abs(ai_progress - evaluator_score)
        return ai_progress
    
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
        
        # Replace smart quotes and special characters
        json_str = json_str.replace('"', '"').replace('"', '"')
        json_str = json_str.replace(''', "'").replace(''', "'")
        json_str = json_str.replace('–', '-').replace('—', '-')
        json_str = json_str.replace('…', '...')
        
        # Remove control characters (but keep newlines for now)
        json_str = re.sub(r'[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f]', '', json_str)
        
        # Try to parse to validate
        try:
            json.loads(json_str)
            return json_str
        except json.JSONDecodeError as e:
            logger.warning(f"JSON parse error at position {e.pos}: {e.msg}")
            
            # Show error context
            start = max(0, e.pos - 100)
            end = min(len(json_str), e.pos + 100)
            logger.warning(f"Context: ...{json_str[start:end]}...")
            
            # Try to fix common issues
            json_str_fixed = self._fix_json_escaping(json_str)
            
            try:
                json.loads(json_str_fixed)
                logger.info("Successfully fixed JSON")
                return json_str_fixed
            except json.JSONDecodeError as e2:
                logger.error(f"Failed to fix JSON: {e2.msg} at position {e2.pos}")
                logger.error(f"Problematic JSON (first 500 chars):\n{json_str[:500]}")
                raise ValueError(f"Could not parse JSON: {e2.msg} at position {e2.pos}")

    def _fix_json_escaping(self, json_str: str) -> str:
        """
        Fix escaping issues in JSON string values.
        
        Args:
            json_str: JSON string that may have escaping issues
            
        Returns:
            Fixed JSON string
        """
        result = []
        i = 0
        in_string = False
        
        while i < len(json_str):
            char = json_str[i]
            
            # Detect string boundaries (unescaped quotes)
            if char == '"' and (i == 0 or json_str[i-1] != '\\'):
                in_string = not in_string
                result.append(char)
                i += 1
                continue
            
            # Inside a string value
            if in_string:
                # Handle backslash sequences
                if char == '\\' and i + 1 < len(json_str):
                    next_char = json_str[i + 1]
                    
                    # Valid escape sequences
                    if next_char in ['"', '\\', '/', 'b', 'f', 'n', 'r', 't', 'u']:
                        result.append(char)
                        result.append(next_char)
                        i += 2
                        continue
                    # Escaped single quote - not needed in JSON, remove backslash
                    elif next_char == "'":
                        result.append("'")
                        i += 2
                        continue
                    # Invalid escape - keep the backslash and char
                    else:
                        result.append('\\')
                        result.append('\\')
                        i += 1
                        continue
                # Handle unescaped special characters
                elif char == '\n':
                    result.append('\\n')
                    i += 1
                elif char == '\r':
                    result.append('\\r')
                    i += 1
                elif char == '\t':
                    result.append('\\t')
                    i += 1
                else:
                    result.append(char)
                    i += 1
            else:
                # Outside strings, keep as is
                result.append(char)
                i += 1
        
        return ''.join(result)
    
    # ==================== PROMPT TEMPLATES ====================

    def _get_question_system_prompt(self) -> str:
        """Get optimized system prompt for question-level research"""
        return """
                You are an expert urban analyst conducting independent research for the Veridian Urban Index.

                **CRITICAL MISSION**: Research real evidence and provide verifiable, source-backed scoring for a specific urban question.
            

                **YOUR RESEARCH PROCESS**:

                1. **MANDATORY WEB SEARCH FOR EVIDENCE ** You MUST search for:
                -  "{city_name}" + specific question topic (official data)
                - "{city_name}" government reports on this issue
                - Search for: "{city_name}" + relevant pillar keywords
                - Search international databases: World Bank, UN-Habitat, WHO data for this city
                - Search academic research on this city's performance in this area

                2. **APPLY TRUSTWORTHY SOURCE CHAIN (TSC)** - Priority Order:
                **TIER 7** (Strongest): City government portals, municipal databases, official statistics
                **TIER 6**: Auditor reports, ombudsman data, regulatory oversight
                **TIER 5**: UN agencies (UN-Habitat, WHO, UNESCO), World Bank, OECD
                **TIER 4**: Peer-reviewed academic journals, university research
                **TIER 3**: Credible NGOs (Transparency International, etc.)
                **TIER 2**: Private sector data (telecom, utilities, satellites)
                **TIER 1**: News media, social media (context only, not primary evidence)

                3. **VERIFICATION REQUIREMENTS**:
                • Find AT LEAST 2 independent sources (Tiers 5-7 preferred)
                • Structural data > perception surveys
                • City-specific data > national averages
                • Recent data (≤2 years) > outdated information
                • Report ONLY the MOST TRUSTWORTHY source in response

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

                **OUTPUT AUDIENCE**: Responses must be readable by a general audience and avoid technical or internal scoring terminology.

                **CRITICAL OUTPUT REQUIREMENTS**:
                You MUST return ONLY a single valid JSON object with this EXACT structure (no additional fields, no field suffixes like _2, _3, etc.):
                
                {{
                    "ai_score": <0-4>,
                    "ai_progress": <0.00-100>,
                    "confidence_level": "<High|Medium|Low>",
                    "evidence_summary": "<100-150 words summarizing key findings and rationale>",
                    "red_flag": "<10-150 words: any concerns found, or empty string if none>",
                    "geographic_equity_note": "<10-60 words: comment on inequality if detected, or empty string if none>",
                    "data_sources_count": <number of sources consulted (1-5)>,
                    "source_type": "<Government|International|Academic|NGO|Private|Media>",
                    "source_name": "<10-60 words: organization name of the MOST TRUSTWORTHY source>",
                    "source_url": "<URL if available, or 'Not available'>",
                    "source_data_year": <year of data>,
                    "source_trust_level": <1-7>,
                    "source_data_extract": "<10-150 words: specific finding/data point from this source>"
                }}

                **JSON OUTPUT FORMAT REQUIREMENTS**:
                CRITICAL: You MUST return valid, fully parseable JSON only. Failure to follow any rule below is unacceptable.

                1. Use ONLY straight double quotes (") for all JSON keys and string values
                2. Do NOT use smart quotes (" "), curly quotes, or any Unicode quote variants
                3. Escape all special characters in string values:
                - Newlines: \\n
                - Tabs: \\t
                - Quotes within strings: \\"
                - Backslashes: \\\\
                4. Do NOT include actual line breaks inside string values
                5. Use regular hyphens (-) not em-dashes (—) or en-dashes (–)
                6. Keep string values concise - aim for single paragraphs without line breaks
                7. Test that your JSON is valid before responding
                8. Use ASCII characters only (no Unicode characters such as \u2019, smart apostrophes, or typographic symbols).
                9. Before responding, verify that:
                    - All string values are closed
                    - The JSON object ends with a closing brace }}
                        
                    Failure Handling:
                        If the response risks being truncated, exceeds length limits, or violates any rule, return {{}} only.

                **RESEARCH NOW for**: {city_name} {city_address}
                Question: {question_text}
                Pillar: {pillar_name}
                """

    def _get_pillar_system_prompt(self) -> str:
        """Get optimized system prompt for pillar-level research"""
        return """You are an expert urban analyst for the Veridian Urban Index. Your task is to conduct independent research and provide evidence-based scoring for a city pillar.

                        **YOUR MISSION:**
                        Research and synthesize evidence across all aspects of this urban pillar and provide a verifiable score (0-4) with clear justification.

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

                        3. **VERIFICATION STANDARDS**:
                        - Find AT LEAST 2 independent sources (preferably Tier 5-7)
                        - Prioritize: City-specific data > National averages
                        - Prioritize: Recent data (within 1 years) > Old data
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

                        **Reference Scores (for context only - DO NOT copy these):**
                        {evaluator_context}
                        {ai_input_context}

                        **OUTPUT FORMAT:**

                        You MUST return ONLY valid JSON in this exact structure (no markdown, no explanations):

                        {{
                        "ai_score": <Scoring Rubric (0-4 scale)> ,
                        "ai_progress": <ai estimated progress for current year (0-100)>,
                        "confidence_level": "<High|Medium|Low>",
                        "evidence_summary": "Concise MAX 250 words, patterns discovered, and critical gaps identified based on your research, written for a general audience with no technical or internal scoring terminology",
                        "sources": [
                            {{
                            "source_type": "Government",
                            "source_name": "City Department of X",
                            "source_url": "https://example.com/report",
                            "data_year": 2025,
                            "trust_level": 7,
                            "data_extract": "Concise 10-200 words : Specific finding or data point from this source"
                            }},
                            {{
                            "source_type": "International",
                            "source_name": "World Bank",
                            "source_url": "https://worldbank.org/data",
                            "data_year": 2025,
                            "trust_level": 5,
                            "data_extract": "Concise 10-200 words : Another specific data point"
                            }}
                        ],
                        "red_flag": "Concise 150-200 words Description of any systemic concerns, contradictions, or warning signs identified ",
                        "geographic_equity_note": "Concise 150-200 words Assessment of whether services/outcomes are equitably distributed across the city",
                        "institutional_assessment": " Concise 150-200 words Evaluation of government capacity, governance quality, and institutional effectiveness",
                        "data_gap_analysis": "Concise 150-200 words Critical information that was missing or unavailable during research"
                        }}

                        **CRITICAL RULES:**
                        - ai_score must be between 0 and 4
                        - ai_progress = <pillar progress or can say ai_score for pillar between 0.00-100> 
                        - Include AT LEAST 2 sources in the sources array
                        - Each source must have all required fields
                        
                        **OUTPUT AUDIENCE**: Responses must be readable by a general audience and avoid technical or internal scoring terminology.

  
                        **JSON OUTPUT FORMAT REQUIREMENTS**:
                        CRITICAL: The response MUST be valid, parseable JSON. Follow these rules STRICTLY:

                        1. Use ONLY straight double quotes (") for all JSON keys and string values
                        2. Do NOT use smart quotes (" "), curly quotes, or any Unicode quote variants
                        3. Escape all special characters in string values:
                        - Newlines: \\n
                        - Tabs: \\t
                        - Quotes within strings: \\"
                        - Backslashes: \\\\
                        4. Do NOT include actual line breaks inside string values
                        5. Use regular hyphens (-) not em-dashes (—) or en-dashes (–)
                        6. Keep string values concise - aim for single paragraphs without line breaks
                        7. Test that your JSON is valid before responding
                        8. Use ASCII characters only (no Unicode characters such as \u2019, smart apostrophes, or typographic symbols).
                        9. Before responding, verify that:
                        - All string values are closed
                        - The JSON object ends with a closing brace }}
                        
                    Failure Handling:
                        If the response risks being truncated, exceeds length limits, or violates any rule, return {{}} only.

                        """

    def _get_city_system_prompt(self) -> str:
        """Get optimized system prompt for city-level research"""
        return """You are conducting comprehensive city-wide Veridian Urban Index assessment.

            **MISSION**: Synthesize evidence across all 14 pillars to evaluate overall urban performance.

            **CITY-LEVEL SYNTHESIS STRATEGY**:

            1. **HOLISTIC WEB SEARCH** - Search for:
            - "{city_name} urban development plan"
            - "{city_name} city master plan progress"
            - "{city_name} governance indicators"
            - "World Bank {city_name}" OR "UN-Habitat {city_name}"
            - "{city_name} peer city comparison"
            - "{city_name} urban resilience {year}"

            2. **CROSS-PILLAR INTEGRATION**:
            - Are institutional strengths/weaknesses consistent?
            - Do infrastructure and service delivery align?
            - Is economic growth reaching all residents?
            - Are environmental and social pillars balanced?

            3. **EVIDENCE HIERARCHY**:
            **TIER 7**: City master plans, municipal comprehensive reports
            **TIER 5**: UN-Habitat city profiles, World Bank urban assessments
            **TIER 4**: Academic urban studies, research institutions
            **TIER 3**: Think tank city evaluations (Brookings, C40, etc.)

            4. **CRITICAL CITY-LEVEL QUESTIONS**:
            - Institutional capacity: Strong or fragmented?
            - Equity: Inclusive or deeply divided?
            - Sustainability: Short-term gains or structural progress?
            - Data transparency: Open or opaque governance?
            - Trajectory: Improving, stable, or declining?

            5. **RED FLAGS**:
            • Contradictions between pillars
            • High performance in some areas masking severe neglect elsewhere
            • Lack of comprehensive urban planning
            • Missing equity data
            • Governance weaknesses affecting multiple pillars

            **PILLAR SYNTHESIS CONTEXT**:
            {pillars_context}

            **REFERENCE SCORES** (for context only):
            {evaluator_context}
            Previous AI Assessment: {aIScore}

            **SCORING FRAMEWORK (0-4)**:

            **4.0 (Excellent)**: Strong across all pillars
            - Verified equity, robust institutions
            - Consistent high performance
            - Transparent governance
            - Sustainable trajectory

            **3.0 (Good)**: Solid overall performance
            - Some weak areas
            - Generally inclusive
            - Room for improvement in specific pillars

            **2.0 (Basic)**: Mixed results
            - Significant gaps in multiple pillars
            - Inequality concerns
            - Inconsistent institutional capacity

            **1.0 (Poor)**: Weak institutions
            - Major deficiencies across pillars
            - Limited data availability
            - Serious equity issues

            **0.0 (Critical)**: Systemic failure
            - Severe inequality
            - Institutional collapse
            - Multiple pillars in crisis

            **CONFIDENCE LEVELS**:
            - **High**: Comprehensive data, multiple Tier 5-7 sources, consistent patterns
            - **Medium**: Mixed data quality, some gaps, moderate verification
            - **Low**: Limited data, significant gaps, national proxies only

           **OUTPUT AUDIENCE**: Responses must be readable by a general audience and avoid technical or internal scoring terminology.

            **OUTPUT** (JSON):
            {{
                "ai_score": <0-4>,
                "ai_progress": <0.00-100 : overall progress accross all 14 pillars like SCORING FRAMEWORK>,
                "confidence_level": "<High|Medium|Low>",
                "evidence_summary": "<MAX 250 words, single paragraph, written for a general audience with no technical or internal scoring terminology>"
                "source": "<Tier 5-7 sources prioritized>",
                "cross_pillar_patterns": "<MAX 200 words, ASCII only : systemic observations>",
                "institutional_capacity": "<MAX 200 words, ASCII only : governance quality assessment>",
                "equity_assessment": "<MAX 200 words, ASCII only : geographic and social inclusion>",
                "sustainability_outlook": "<MAX 200 words, ASCII only :trajectory and resilience>",
                "strategic_recommendation": "<MAX 200 words, ASCII only : priority actions>",
                "data_transparency_note": "<MAX 200 words, ASCII only : information availability>"
            }}

            **JSON OUTPUT FORMAT REQUIREMENTS**:
            CRITICAL: The response MUST be valid, parseable JSON. Follow these rules STRICTLY:

            1. Use ONLY straight double quotes (") for all JSON keys and string values
            2. Do NOT use smart quotes (" "), curly quotes, or any Unicode quote variants
            3. Escape all special characters in string values:
            - Newlines: \\n
            - Tabs: \\t
            - Quotes within strings: \\"
            - Backslashes: \\\\
            4. Do NOT include actual line breaks inside string values
            5. Use regular hyphens (-) not em-dashes (—) or en-dashes (–)
            6. Keep string values concise - aim for single paragraphs without line breaks
            7. Test that your JSON is valid before responding
            8. Use ASCII characters only (no Unicode characters such as \u2019, smart apostrophes, or typographic symbols).
            9. Before responding, verify that:
            - All string values are closed
            - The JSON object ends with a closing brace }}
            
           Failure Handling:
            If the response risks being truncated, exceeds length limits, or violates any rule, return {{}} only.
         
            **RESEARCH NOW for**: {city_name} {city_address} """
    
# Singleton instance
veridian_ai_research_service = VerdianAIResearchService()