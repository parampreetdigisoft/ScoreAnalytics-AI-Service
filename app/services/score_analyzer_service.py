"""
Score analyzer service - LLM-powered analysis with database exception logging
"""

from datetime import datetime
import math
import logging
from typing import Any, Optional
from app.services.core.repository import DatabaseRepository
from app.services.common.veridian_ai_research_service import VerdianAIResearchService
from app.services.rag_query_service import rag_query_service

logger = logging.getLogger(__name__)


class ScoreAnalyzerService:
    """Service for analyzing SQL Server data using LLM"""

    __slots__ = ('db_service', '_ai')  # Memory optimization

    def __init__(self):
        self.db_service = DatabaseRepository()
        self._ai = VerdianAIResearchService()

    @staticmethod
    def to_float_safe(value) -> float:
        """Convert value to float safely, returning 0.0 for invalid values"""
        if value is None:
            return 0.0

        if isinstance(value, float):
            return 0.0 if (math.isnan(value) or math.isinf(value)) else round(value, 2)

        if isinstance(value, int):
            return float(value)

        if isinstance(value, str):
            s = value.strip().lower()
            if s in {"", "null", "none", "nan", "inf", "-inf", "infinity", "-infinity"}:
                return 0.0
            
            try:
                val = float(s.replace(",", ""))
                return 0.0 if (math.isnan(val) or math.isinf(val)) else round(val, 2)
            except (ValueError, TypeError):
                return 0.0

        return 0.0

    @staticmethod
    def to_float_none(value) -> float | None:
        """Convert value to float safely. Returns None for invalid values."""

        if value is None:
            return None

        try:
            if isinstance(value, str):
                s = value.strip().lower()

                if s in {"", "null", "none", "nan", "inf", "-inf", "infinity", "-infinity"}:
                    return None

                value = float(s.replace(",", ""))

            val = float(value)

            if math.isnan(val) or math.isinf(val):
                return None

            return round(val, 2)

        except (ValueError, TypeError):
            return None
    
    @staticmethod
    def to_int_safe(value) -> int:
        """Convert value to int safely, returning 0 for invalid values"""
        if value is None:
            return 0

        if isinstance(value, int):
            return value

        if isinstance(value, float):
            return 0 if (math.isnan(value) or math.isinf(value)) else int(value)

        if isinstance(value, str):
            s = value.strip().lower()
            if s in {"", "null", "none", "nan", "inf", "-inf", "infinity", "-infinity"}:
                return 0
            
            try:
                return int(float(s.replace(",", "")))
            except (ValueError, TypeError):
                return 0

        return 0
    
    async def _get_city_data(self, city_id: Optional[int] = None):
        where = (
            f"WHERE IsDeleted = 0 AND CityID = {city_id}"
            if city_id
            else "WHERE IsDeleted = 0"
        )
        return await self.db_service.engine.fetch_df_async(
            f"Select CityID, CityName, State, Country from Cities {where}"
        )


    async def analyze_all_cities_questions(self, city_id: Optional[int] = None) -> bool:
        """Analyze City Questions data for all cities or specific city"""
        try:
            df = await self._get_city_data(city_id)

            if df.empty:
                logger.error("No cities found for analysis analyze_all_cities_questions endpoint")
                return False

            for city in df.itertuples(index=False):
                try:
                    await self.analyze_PillarQuestions(city)
                    await self.analyze_cityPillar(city)
                    await self.analyze_city(city)
                except Exception as e:
                    logger.error(f"Failed to analyze city {city.CityID} ({city.CityName}): {e}")
                    continue

            return True
            
        except Exception as e:
            logger.error(f"Error in analyze_all_cities_questions: {e}")
            raise

    async def analyze_single_City(self, cityId: int) -> bool:
        """Analyze City Questions data for a specific city"""
        try:
            df = await self._get_city_data(cityId)
            if df.empty:
                return False

            for city in df.itertuples(index=False):
                await self.analyze_city(city)

            return True
            
        except Exception as e:
            logger.error(f"Error in analyze_single_City (CityID: {cityId}): {e}")
            raise

    async def analyze_city_pillars(self, cityId: int) -> bool:
        """Analyze City pillar data for a specific city"""
        try:
            df = await self._get_city_data(cityId)
            if df.empty:
                return False

            for city in df.itertuples(index=False):
                await self.analyze_cityPillar(city)

            return True
            
        except Exception as e:
            logger.error(f"Error in analyze_city_pillars (CityID: {cityId}): {e}")
            raise

    async def analyze_Single_Pillar(self, cityId: int, pillar_id: Optional[int] = None) -> bool:
        """Analyze specific pillar for a city"""
        try:
            df = self._get_city_data(cityId)
            if df.empty:
                return False

            for city in df.itertuples(index=False):
                await self.analyze_cityPillar(city, pillar_id)

            return True
            
        except Exception as e:
            logger.error(f"Error in analyze_Single_Pillar (CityID: {cityId}, PillarID: {pillar_id}): {e}")
            raise

    async def analyze_questions_of_city_pillar(self, cityId: int, pillar_id: Optional[int] = None) -> bool:
        """Analyze questions for city pillar"""
        try:
            df = self._get_city_data(cityId)
            if df.empty:
                return False

            for city in df.itertuples(index=False):
                await self.analyze_PillarQuestions(city, pillar_id)

            return True
            
        except Exception as e:
            logger.error(f"Error in analyze_questions_of_city_pillar (CityID: {cityId}): {e}")
            raise

    def _build_question_record(self, row, ai_data, normalized_value: float) -> dict[str, Any]:
        """Build question evaluation record from AI data"""

        return {
            "CityID": row.CityID,
            "PillarID": row.PillarID,
            "QuestionID": row.QuestionID,
            "Year": self.to_int_safe(ai_data["Year"]),
            "AIScore": self.to_float_none(ai_data["AIScore"]),
            "AIProgress": self.to_float_safe(ai_data["AIProgress"]),
            "EvaluatorProgress": self.to_float_safe(normalized_value * 100),
            "Discrepancy": self.to_float_safe(ai_data["Discrepancy"]),
            "ConfidenceLevel": ai_data["ConfidenceLevel"],
            "DataSourcesUsed": self.to_int_safe(ai_data["DataSourcesCount"]),
            "EvidenceSummary": ai_data["EvidenceSummary"],
            "RedFlags": ai_data["RedFlag"],
            "GeographicEquityNote": ai_data["GeographicEquityNote"],
            "SourceType": ai_data["SourceType"],
            "SourceName": ai_data["SourceName"],
            "SourceURL": ai_data["SourceURL"],
            "SourceDataYear": self.to_int_safe(ai_data["SourceDataYear"]),
            "SourceDataExtract": ai_data["SourceDataExtract"],
            "SourceTrustLevel": self.to_int_safe(ai_data["SourceHierarchyLevel"])
        }

    async def analyze_PillarQuestions(self, city: Any, pillar_id: Optional[int] = None) -> bool:
        """Analyze Pillar Questions data for a city"""
        try:
            where = f"cityId = {city.CityID}"
            if pillar_id is not None:
                where = f"cityId = {city.CityID} and PillarID={pillar_id}"

            df = await self.db_service.get_view_data("vw_AiCityPillarQuestionEvaluations", where)
            
            if not len(df):
                logger.info(f"No pillar questions found for city {city.CityID} ({city.CityName})")
                return False
            
            pillarIds = [pillar_id] if pillar_id is not None else df["PillarID"].unique().tolist()
            
            for pillarId in pillarIds:
                pillar_df = df[df["PillarID"] == pillarId]
                questionList: list[dict[str, Any]] = []
                
                try:
                    for row in pillar_df.itertuples(index=False):
                        normalized_value = 0 if (row.NormalizedValue is None or 
                                                  (isinstance(row.NormalizedValue, float) and 
                                                   math.isnan(row.NormalizedValue))) else row.NormalizedValue
                            
                        try:
                            ai_data = await self._ai.research_and_score_question(
                                city.CityName,
                                f"State :{city.State}, Country :{city.Country}",
                                row.PillarID,
                                row.PillarName,
                                f" Question :{row.QuestionText}, Options :{row.Options}",
                                row.ScoreProgress,
                                round(normalized_value * 4.0),
                                None
                            )

                            if ai_data["success"]:
                                questionList.append(self._build_question_record(row, ai_data, normalized_value))
                                
                                if len(questionList) == 10:
                                    await self.db_service.bulk_upsert_question_evaluations(questionList)
                                    questionList = []
                            else:
                                logger.warning(f"AI analysis failed for QuestionID {row.QuestionID} in City {city.CityID}")
                                
                        except Exception as e:
                            logger.error(f"Error processing question {row.QuestionID} for city {city.CityID}: {e}")
                            continue
                    
                    if questionList:
                        await self.db_service.bulk_upsert_question_evaluations(questionList)

                except Exception as e:
                    logger.error(f"Error analyzing pillar {pillarId} for city {city.CityID}: {e}")
                    continue
                    
            return True
            
        except Exception as e:
            logger.error(f"Error in analyze_PillarQuestions for city {city.CityID}: {e}")
            raise

    async def analyze_cityPillar(self, city: Any, pillar_id: Optional[int] = None) -> bool:
        """Analyze city pillar data and generate evaluations"""
        try:
            where = f"cityId = {city.CityID} and PillarID = {pillar_id}" if pillar_id else f"cityId = {city.CityID}"
            df = await self.db_service.get_view_data("vw_AiCityPillarEvaluation", where)
            
            if not len(df):
                logger.info(f"No pillar evaluations found for city {city.CityID} ({city.CityName})")
                return False
                
            pillarList: list[dict[str, Any]] = []
            pillarSourceList: list[dict[str, Any]] = []
            
            for row in df.itertuples(index=False):
                try:
                    ai_data = await self._ai.research_and_score_pillar(
                        city.CityName,
                        f"State :{city.State}, Country :{city.Country}",
                        row.PillarID,
                        row.PillarName,
                        row.QuestionWithScores,
                        row.EvaluatorProgress,
                        row.AIScore,
                    )

                    if ai_data["success"]:
                        for src in ai_data["Sources"]:
                            pillarSourceList.append({
                                "CityID": row.CityID,
                                "DataYear": self.to_int_safe(ai_data['Year']),
                                "PillarID": row.PillarID,
                                "SourceType": src["source_type"],
                                "SourceName": src["source_name"],
                                "SourceURL": src["source_url"],
                                "DataExtract": src["data_extract"],
                                "TrustLevel": self.to_int_safe(src["trust_level"])
                            })

                        pillarList.append({
                            "CityID": row.CityID,
                            "PillarID": row.PillarID,
                            "Year": self.to_int_safe(ai_data["Year"]),
                            "AIScore": self.to_float_safe(ai_data["AIScore"]),
                            "AIProgress": self.to_float_safe(ai_data["AIProgress"]),
                            "EvaluatorProgress": self.to_float_safe(row.EvaluatorProgress),
                            "Discrepancy": self.to_float_safe(ai_data["Discrepancy"]),
                            "ConfidenceLevel": ai_data["ConfidenceLevel"],
                            "EvidenceSummary": ai_data["EvidenceSummary"],
                            "RedFlags": ai_data.get("RedFlag", ""),
                            "GeographicEquityNote": ai_data["GeographicEquityNote"],
                            "InstitutionalAssessment": ai_data["InstitutionalAssessment"],
                            "DataGapAnalysis": ai_data["DataGapAnalysis"],
                            "AnalystDataGapAnalysis": ai_data["AnalystDataGapAnalysis"]
                        })

                        if len(pillarList) == 5:
                            await self.db_service.bulk_upsert_pillar_evaluations(pillarList, pillarSourceList)
                            pillarList = []
                            pillarSourceList = []
                    else:
                        logger.warning(f"AI analysis failed for PillarID {row.PillarID} in City {city.CityID}")

                except Exception as e:
                    logger.error(f"Error processing pillar {row.PillarID} for city {city.CityID}: {e}")
                    continue

            if pillarList:
                await self.db_service.bulk_upsert_pillar_evaluations(pillarList, pillarSourceList)
                return True
                
            return False
            
        except Exception as e:
            logger.error(f"Error in analyze_cityPillar for city {city.CityID}: {e}")
            raise

    async def analyze_city(self, city: Any) -> bool:
        """Analyze overall city data and generate comprehensive evaluation"""
        try:
            df = await self.db_service.get_view_data("vw_AiCityEvaluations", f"cityId = {city.CityID}")
            
            if not len(df):
                logger.info(f"No city evaluations found for city {city.CityID} ({city.CityName})")
                return False

            cityList: list[dict[str, Any]] = []
            
            for row in df.itertuples(index=False):
                try:
                    ai_data = await self._ai.research_and_score_city(
                        city.CityName,
                        f"State :{city.State}, Country :{city.Country}",
                        row.EvaluatorProgress,
                        row.AIScore,
                        row.PillarWithScores
                    )

                    if ai_data["success"]:
                        cityList.append({
                            "CityID": row.CityID,
                            "Year": self.to_int_safe(ai_data['Year']),
                            "AIScore": self.to_float_safe(ai_data["AIScore"]),
                            "AIProgress": self.to_float_safe(ai_data["AIProgress"]),
                            "EvaluatorProgress": self.to_float_safe(row.EvaluatorProgress),
                            "Discrepancy": self.to_float_safe(ai_data["Discrepancy"]),
                            "ConfidenceLevel": ai_data['ConfidenceLevel'],
                            "EvidenceSummary": ai_data['EvidenceSummary'],
                            "CrossPillarPatterns": ai_data.get('CrossPillarPatterns', ''),
                            "InstitutionalCapacity": ai_data['InstitutionalCapacity'],
                            "EquityAssessment": ai_data['EquityAssessment'],
                            "SustainabilityOutlook": ai_data['SustainabilityOutlook'],
                            "StrategicRecommendations": ai_data['StrategicRecommendation'],
                            "DataTransparencyNote": ai_data['DataTransparencyNote'],
                        })

                        if len(cityList) == 10:
                            await self.db_service.bulk_upsert_city_evaluations(cityList)
                            cityList = []
                    else:
                        logger.warning(f"AI analysis failed for City {city.CityID}")

                except Exception as e:
                    logger.error(f"Error processing city evaluation for {city.CityID}: {e}")
                    continue

            if cityList:
                await self.db_service.bulk_upsert_city_evaluations(cityList)
                return True

            return False
            
        except Exception as e:
            logger.error(f"Error in analyze_city for city {city.CityID}: {e}")
            raise

    async def immediateSituation(self, city_id: int, **_) -> bool:
            """Score the overall city-level peace assessment."""
            year = datetime.now().year        

            ai_city= await self.db_service.get_ai_city_context(city_id, year)
            city_Name = ai_city["CityName"]
            country = ai_city["Country"]

            question = f"""
            What are the most critical recent developments, emerging risks, structural weaknesses, and key strengths across all major sectors in {city_Name}? Include insights on governance, security, economy, social cohesion, infrastructure, and institutional effectiveness. Focus on cross-pillar patterns and high-impact information relevant for executive-level city assessment and situational awareness.
            """

            document_context = await rag_query_service.get_city_document_context(city_id, question)

            if ai_city:
                ai_city_context = "\n".join(f"{key}: {value}" for key, value in ai_city.items())
            else:
                ai_city_context = ""

            ai_data = await self._ai.immediate_situation(
                        city_name=city_Name,
                        country=country,
                        ai_city_context=ai_city_context,
                        documentContext=document_context,
                        year=year
                    )

            result = self._build_immediateSituation_record(city_id, ai_data)
            
            await self.db_service.save_immediate_situation_summary(city_id,year,result)
            
            
            return True

    def _build_immediateSituation_record(self, cityId: int, ai: dict) -> dict:
            summary = ai.get("executive_summary", "")

            return {
                "CityID": cityId,
                "immediateSituationSummary": ai.get("immediateSituationSummary", "Unknown"),
                "key_developments": ai.get("key_developments", "Unknown"),
                "critical_risks": ai.get("critical_risks"),
                "gaps": ai.get("gaps"),
                "executive_summary": summary if isinstance(summary, str) and len(summary) > 50 else ""
            }

# Singleton instance
score_analyzer_service = ScoreAnalyzerService()