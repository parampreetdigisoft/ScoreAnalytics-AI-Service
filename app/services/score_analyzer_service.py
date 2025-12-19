"""
Score analyzer service - LLM-powered analysis with database exception logging
"""
import math
import logging
from typing import Any, Optional
from app.services.common.database_service import db_service
from app.services.common.veridian_ai_research_service import veridian_ai_research_service
from app.services.common.db_logger_service import db_logger_service
from app.config import settings

logger = logging.getLogger(__name__)


class ScoreAnalyzerService:
    """Service for analyzing SQL Server data using LLM"""

    def __init__(self):
        self.db_service = db_service

    def to_float_safe(self, value):
        if value is None:
            return float(0.0)

        if isinstance(value, float):
            # Convert NaN/inf to None
            if math.isnan(value) or math.isinf(value):
                return float(0.0)
            return round(value, 2)

        if isinstance(value, int):
            return float(value)

        if isinstance(value, str):
            s = value.strip().lower()

            # Empty or null-like
            if s in ("", "null", "none", "nan", "inf", "-inf", "infinity", "-infinity"):
                return float(0.0)

            # Remove commas like "1,234.56"
            s = s.replace(",", "")
            try:
                val = float(s)
                if math.isnan(val) or math.isinf(val):
                    return float(0.0)
                return round(val, 2)
            except:
                return float(0.0)

        # Other types not supported
        return float(0.0)

    def to_int_safe(self, value):
        if value is None:
            return int(0.0)

        if isinstance(value, int):
            return value

        if isinstance(value, float):
            if math.isnan(value) or math.isinf(value):
                return int(0.0)
            return int(value)

        if isinstance(value, str):
            s = value.strip().lower()

            if s in ("", "null", "none", "nan", "inf", "-inf", "infinity", "-infinity"):
                return int(0.0)

            # Remove commas
            s = s.replace(",", "")

            try:
                return int(float(s))  # Convert "5.0" → 5 safely
            except:
                return int(0.0)

        return int(0.0)

    async def analyze_all_cities_questions(self,city_id:Optional[int]=None) -> bool:
        """
        Analyze City Questions data for all cities 
        
        """
        try:
            where_clause = f"where IsDeleted=0 and CityID={city_id}" if city_id is not None else f"where IsDeleted=0" 
            df = db_service.read_with_query(
                f"Select CityID, CityName, State, Country from Cities {where_clause}"
            )

            if df.empty:
                db_logger_service.log_message(
                    "WARNING",
                    f"No cities found for analysis analyze_all_cities_questions endpoint"
                )
                return False

            for city in df.itertuples(index=False):
                try:
                    await self.analyze_PillarQuestions(city)
                    await self.analyze_cityPillar(city)
                    await self.analyze_city(city)
                except Exception as e:
                    db_logger_service.log_exception(
                        "ERROR",
                        f"Failed to analyze city {city.CityID} ({city.CityName})",
                        e
                    )
                    # Continue with next city instead of stopping
                    continue

            return True
            
        except Exception as e:
            db_logger_service.log_exception(
                "ERROR",
                f"Error in analyze_all_cities_questions ",
                e
            )
            raise

    async def analyze_single_City(self, cityId: int) -> bool:
        """
        Analyze City Questions data for a specific city.

        Args:
            cityId: ID of the city to process.
        """
        try:
            df = db_service.read_with_query(
                f"Select CityID, CityName, State, Country from Cities where IsDeleted=0 and CityID={cityId}"
            )

            if df.empty:
                return False

            for city in df.itertuples(index=False):
                await self.analyze_city(city)

            return True
            
        except Exception as e:
            db_logger_service.log_exception(
                "ERROR",
                f"Error in analyze_single_City (CityID: {cityId})",
                e
            )
            raise

    async def analyze_city_pillars(self, cityId: int) -> bool:
        """
        Analyze City Questions data for a specific city.

        Args:
            cityId: ID of the city to process.
        """
        try:
            df = db_service.read_with_query(
                f"Select CityID, CityName, State, Country from Cities where IsDeleted=0 and CityID={cityId}"
            )

            if df.empty:
                return False

            for city in df.itertuples(index=False):
                await self.analyze_cityPillar(city)

            return True
            
        except Exception as e:
            db_logger_service.log_exception(
                "ERROR",
                f"Error in analyze_single_City (CityID: {cityId})",
                e
            )
            raise

    async def analyze_questions_of_city_pillar(self, cityId: int,pillar_id:Optional[int]=None) -> bool:
            """
            Analyze City Questions data for a specific city.

            Args:
                cityId: ID of the city to process.
            """
            try:
                df = db_service.read_with_query(
                    f"Select CityID, CityName, State, Country from Cities where IsDeleted=0 and CityID={cityId}"
                )

                if df.empty:
                    return False

                for city in df.itertuples(index=False):
                    await self.analyze_PillarQuestions(city,pillar_id)

                return True
                
            except Exception as e:
                db_logger_service.log_exception(
                    "ERROR",
                    f"Error in analyze_single_City (CityID: {cityId})",
                    e
                )
                raise

    async def analyze_PillarQuestions(self, city: Any, pillar_id:Optional[int]=None) -> bool:
        """
        Analyze Pillar Questions data for a city.

        Args:
            city: City record with CityID, CityName, State, Country
        """
        try:
            df = db_service.get_view_data(
                "vw_CityPillarQuestionEvaluations", f"cityId = {city.CityID}"
            )
            
            if not len(df):
                db_logger_service.log_message(
                    "INFO",
                    f"No pillar questions found for city {city.CityID} ({city.CityName})"
                )
                return False
            
            pillarIds = df["PillarID"].unique().tolist() if pillar_id is None else [pillar_id]
            
            for pillarId in pillarIds:
                pillar_df = df[df["PillarID"] == pillarId]  
                questionList: list[dict[str, Any]] = []
                
                try:
                    for row in pillar_df.itertuples(index=False):
                        normalizedValue = row.NormalizedValue
                        if normalizedValue is None or (isinstance(normalizedValue, float) and math.isnan(normalizedValue)):
                            normalizedValue = 0
                            
                        try:
                            # Run the AI analysis
                            ai_data = await veridian_ai_research_service.research_and_score_question(
                                city.CityName,
                                f"State :{city.State}, Country :{city.Country}",
                                row.PillarID,
                                row.PillarName,
                                row.QuestionText,
                                row.ScoreProgress,
                                round(normalizedValue * 4.0),
                                None
                            )

                            if ai_data["success"]:
                                r = {
                                    "CityID": row.CityID,
                                    "PillarID": row.PillarID,
                                    "QuestionID": row.QuestionID,
                                    "Year": self.to_int_safe(ai_data["year"]),
                                    "AIScore": self.to_float_safe(ai_data["ai_score"]),
                                    "AIProgress": self.to_float_safe(ai_data["ai_progress"]),
                                    "EvaluatorProgress": self.to_float_safe(normalizedValue * 100),
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
                                questionList.append(r)
                            else:
                                db_logger_service.log_message(
                                    "WARNING",
                                    f"AI analysis failed for QuestionID {row.QuestionID} in City {city.CityID}"
                                )
                                
                        except Exception as e:
                            db_logger_service.log_exception(
                                "ERROR",
                                f"Error processing question {row.QuestionID} for city {city.CityID}",
                                e
                            )
                            # Continue with next question
                            continue
                    
                    if len(questionList) > 0:
                        db_service.bulk_upsert_question_evaluations(questionList)

                except Exception as e:
                    db_logger_service.log_exception(
                        "ERROR",
                        f"Error analyzing pillar {pillarId} for city {city.CityID}",
                        e
                    )
                    # Continue with next pillar
                    continue
                    
            return True
            
        except Exception as e:
            db_logger_service.log_exception(
                "ERROR",
                f"Error in analyze_PillarQuestions for city {city.CityID}",
                e
            )
            raise

    async def analyze_cityPillar(self, city: Any) -> bool:
        """
        Analyze city pillar data and generate evaluations
        
        Args:
            city: City record with CityID, CityName, State, Country
        """
        try:
            df = db_service.get_view_data(
                "vw_AiCityPillarEvaluation", f"cityId = {city.CityID}"
            )
            
            if not len(df):
                db_logger_service.log_message(
                    "INFO",
                    f"No pillar evaluations found for city {city.CityID} ({city.CityName})"
                )
                return False

            pillarList: list[dict[str, Any]] = []
            pillarSourceList: list[dict[str, Any]] = []
            
            for row in df.itertuples(index=False):
                try:
                    # Run the AI analysis
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
                            subRes = {
                                "CityID": row.CityID,
                                "DataYear": self.to_int_safe(ai_data['year']),
                                "PillarID": row.PillarID,
                                "SourceType": src["source_type"],
                                "SourceName": src["source_name"],
                                "SourceURL": src["source_url"],
                                "DataExtract": src["data_extract"],
                                "TrustLevel": self.to_int_safe(src["trust_level"])
                            }
                            pillarSourceList.append(subRes)

                        r = {
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
                        }

                        pillarList.append(r)
                    else:
                        db_logger_service.log_message(
                            "WARNING",
                            f"AI analysis failed for PillarID {row.PillarID} in City {city.CityID}"
                        )

                except Exception as e:
                    db_logger_service.log_exception(
                        "ERROR",
                        f"Error processing pillar {row.PillarID} for city {city.CityID}",
                        e
                    )
                    continue

            if len(pillarList) > 0:
                db_service.bulk_upsert_pillar_evaluations(pillarList, pillarSourceList)
                return True
                
            return False
            
        except Exception as e:
            db_logger_service.log_exception(
                "ERROR",
                f"Error in analyze_cityPillar for city {city.CityID}",
                e
            )
            raise

    async def analyze_city(self, city: Any) -> bool:
        """
        Analyze overall city data and generate comprehensive evaluation
        
        Args:
            city: City record with CityID, CityName, State, Country
        """
        try:
            where = f"cityId = {city.CityID}"
            df = db_service.get_view_data("vw_CityEvaluations", where)
            
            if not len(df):
                db_logger_service.log_message(
                    "INFO",
                    f"No city evaluations found for city {city.CityID} ({city.CityName})"
                )
                return False

            cityList: list[dict[str, Any]] = []
            
            for row in df.itertuples(index=False):
                try:
                    # Run the AI analysis
                    ai_data = await veridian_ai_research_service.research_and_score_city(
                        city.CityName,
                        f"State :{city.State}, Country :{city.Country}",
                        row.EvaluatorProgress,
                        row.AIScore,
                        row.PillarWithScores
                    )

                    if ai_data["success"]:
                        r = {
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
                        }
                        cityList.append(r)
                    else:
                        db_logger_service.log_message(
                            "WARNING",
                            f"AI analysis failed for City {city.CityID}"
                        )

                except Exception as e:  
                    db_logger_service.log_exception(
                        "ERROR",
                        f"Error processing city evaluation for {city.CityID}",
                        e
                    )
                    continue

            if len(cityList):
                db_service.bulk_upsert_city_evaluations(cityList)
                return True

            return False
            
        except Exception as e:
            db_logger_service.log_exception(
                "ERROR",
                f"Error in analyze_city for city {city.CityID}",
                e
            )
            raise


# Singleton instance
score_analyzer_service = ScoreAnalyzerService()