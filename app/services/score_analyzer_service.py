"""
Score analyzer service - LLM-powered analysis with database exception logging
"""
import math
import logging
from typing import Any, Optional
from app.services.common.database_service import db_service
from app.services.common.db_logger_service import db_logger_service
from app.services.common.veridian_ai_research_service import veridian_ai_research_service

logger = logging.getLogger(__name__)


class ScoreAnalyzerService:
    """Service for analyzing SQL Server data using LLM"""

    __slots__ = ('db_service',)  # Memory optimization

    def __init__(self):
        self.db_service = db_service

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

    def _get_city_data(self, city_id: Optional[int] = None):
        """Fetch city data with optional filtering"""
        where_clause = f"where IsDeleted=0 and CityID={city_id}" if city_id else "where IsDeleted=0"
        return db_service.read_with_query(
            f"Select CityID, CityName, State, Country from Cities {where_clause}"
        )

    async def analyze_all_cities_questions(self, city_id: Optional[int] = None) -> bool:
        """Analyze City Questions data for all cities or specific city"""
        try:
            df = self._get_city_data(city_id)

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
            df = self._get_city_data(cityId)
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
            df = self._get_city_data(cityId)
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
            "Year": self.to_int_safe(ai_data["year"]),
            "AIScore": self.to_float_safe(ai_data["ai_score"]),
            "AIProgress": self.to_float_safe(ai_data["ai_progress"]),
            "EvaluatorProgress": self.to_float_safe(normalized_value * 100),
            "Discrepancy": self.to_float_safe(ai_data["discrepancy"]),
            "ConfidenceLevel": ai_data["confidence_level"],
            "DataSourcesUsed": self.to_int_safe(ai_data["data_sources_count"]),
            "EvidenceSummary": ai_data["evidence_summary"],
            "RedFlags": ai_data["red_flag"],
            "GeographicEquityNote": ai_data["geographic_equity_note"],
            "SourceType": ai_data["source_type"],
            "SourceName": ai_data["source_name"],
            "SourceURL": ai_data["source_url"],
            "SourceDataYear": self.to_int_safe(ai_data["source_data_year"]),
            "SourceDataExtract": ai_data["source_data_extract"],
            "SourceTrustLevel": self.to_int_safe(ai_data["source_trust_level"])
        }

    async def analyze_PillarQuestions(self, city: Any, pillar_id: Optional[int] = None) -> bool:
        """Analyze Pillar Questions data for a city"""
        try:
            where = f"cityId = {city.CityID}"
            if pillar_id is not None:
                where = f"cityId = {city.CityID} and PillarID={pillar_id}"


            df = db_service.get_view_data("vw_AiCityPillarQuestionEvaluations", where,5)
            
            if not len(df):
                db_logger_service.log_message("INFO", f"No pillar questions found for city {city.CityID} ({city.CityName})")
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
                            ai_data = await veridian_ai_research_service.research_and_score_question(
                                city.CityName,
                                f"State :{city.State}, Country :{city.Country}",
                                row.PillarID,
                                row.PillarName,
                                row.QuestionText,
                                row.ScoreProgress,
                                round(normalized_value * 4.0),
                                None
                            )

                            if ai_data["success"]:
                                questionList.append(self._build_question_record(row, ai_data, normalized_value))
                                
                                if len(questionList) == 10:
                                    db_service.bulk_upsert_question_evaluations(questionList)
                                    questionList = []
                            else:
                                db_logger_service.log_message("WARNING", 
                                    f"AI analysis failed for QuestionID {row.QuestionID} in City {city.CityID}")
                                
                        except Exception as e:
                            logger.error(f"Error processing question {row.QuestionID} for city {city.CityID}: {e}")
                            continue
                    
                    if questionList:
                        db_service.bulk_upsert_question_evaluations(questionList)

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
            df = db_service.get_view_data("vw_AiCityPillarEvaluation", where)
            
            if not len(df):
                db_logger_service.log_message("INFO", f"No pillar evaluations found for city {city.CityID} ({city.CityName})")
                return False
                
            pillarList: list[dict[str, Any]] = []
            pillarSourceList: list[dict[str, Any]] = []
            
            for row in df.itertuples(index=False):
                try:
                    ai_data = await veridian_ai_research_service.research_and_score_pillar(
                        city.CityName,
                        f"State :{city.State}, Country :{city.Country}",
                        row.PillarID,
                        row.PillarName,
                        row.QuestionWithScores,
                        row.EvaluatorProgress,
                        row.AIScore,
                    )

                    if ai_data["success"]:
                        for src in ai_data["sources"]:
                            pillarSourceList.append({
                                "CityID": row.CityID,
                                "DataYear": self.to_int_safe(ai_data['year']),
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
                            "Year": self.to_int_safe(ai_data['year']),
                            "AIScore": self.to_float_safe(ai_data["ai_score"]),
                            "AIProgress": self.to_float_safe(ai_data["ai_progress"]),
                            "EvaluatorProgress": self.to_float_safe(row.EvaluatorProgress),
                            "Discrepancy": self.to_float_safe(ai_data["discrepancy"]),
                            "ConfidenceLevel": ai_data["confidence_level"],
                            "EvidenceSummary": ai_data['evidence_summary'],
                            "RedFlags": ai_data.get('red_flag', ''),
                            "GeographicEquityNote": ai_data['geographic_equity_note'],
                            "InstitutionalAssessment": ai_data['institutional_assessment'],
                            "DataGapAnalysis": ai_data['data_gap_analysis']
                        })

                        if len(pillarList) == 5:
                            db_service.bulk_upsert_pillar_evaluations(pillarList, pillarSourceList)
                            pillarList = []
                            pillarSourceList = []
                    else:
                        db_logger_service.log_message("WARNING", 
                            f"AI analysis failed for PillarID {row.PillarID} in City {city.CityID}")

                except Exception as e:
                    logger.error(f"Error processing pillar {row.PillarID} for city {city.CityID}: {e}")
                    continue

            if pillarList:
                db_service.bulk_upsert_pillar_evaluations(pillarList, pillarSourceList)
                return True
                
            return False
            
        except Exception as e:
            logger.error(f"Error in analyze_cityPillar for city {city.CityID}: {e}")
            raise

    async def analyze_city(self, city: Any) -> bool:
        """Analyze overall city data and generate comprehensive evaluation"""
        try:
            df = db_service.get_view_data("vw_AiCityEvaluations", f"cityId = {city.CityID}")
            
            if not len(df):
                db_logger_service.log_message("INFO", f"No city evaluations found for city {city.CityID} ({city.CityName})")
                return False

            cityList: list[dict[str, Any]] = []
            
            for row in df.itertuples(index=False):
                try:
                    ai_data = await veridian_ai_research_service.research_and_score_city(
                        city.CityName,
                        f"State :{city.State}, Country :{city.Country}",
                        row.EvaluatorProgress,
                        row.AIScore,
                        row.PillarWithScores
                    )

                    if ai_data["success"]:
                        cityList.append({
                            "CityID": row.CityID,
                            "Year": self.to_int_safe(ai_data['year']),
                            "AIScore": self.to_float_safe(ai_data["ai_score"]),
                            "AIProgress": self.to_float_safe(ai_data["ai_progress"]),
                            "EvaluatorProgress": self.to_float_safe(row.EvaluatorProgress),
                            "Discrepancy": self.to_float_safe(ai_data["discrepancy"]),
                            "ConfidenceLevel": ai_data['confidence_level'],
                            "EvidenceSummary": ai_data['evidence_summary'],
                            "CrossPillarPatterns": ai_data.get('cross_pillar_patterns', ''),
                            "InstitutionalCapacity": ai_data['institutional_capacity'],
                            "EquityAssessment": ai_data['equity_assessment'],
                            "SustainabilityOutlook": ai_data['sustainability_outlook'],
                            "StrategicRecommendations": ai_data['strategic_recommendation'],
                            "DataTransparencyNote": ai_data['data_transparency_note'],
                        })

                        if len(cityList) == 10:
                            db_service.bulk_upsert_city_evaluations(cityList)
                            cityList = []
                    else:
                        db_logger_service.log_message("WARNING", f"AI analysis failed for City {city.CityID}")

                except Exception as e:
                    logger.error(f"Error processing city evaluation for {city.CityID}: {e}")
                    continue

            if cityList:
                db_service.bulk_upsert_city_evaluations(cityList)
                return True

            return False
            
        except Exception as e:
            logger.error(f"Error in analyze_city for city {city.CityID}: {e}")
            raise


# Singleton instance
score_analyzer_service = ScoreAnalyzerService()