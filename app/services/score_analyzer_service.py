"""
Score analyzer service - LLM-powered analysis of SQL Server data
"""

import logging
from typing import Any, Optional
import math
from app.services.common.database_service import db_service
from app.services.common.llm_Execution_service import llm_Execution_service
from app.services.common.veridian_ai_research_service import veridian_ai_research_service
from app.config import settings

logger = logging.getLogger(__name__)


class ScoreAnalyzerService:
    """Service for analyzing SQL Server data using LLM"""

    def __init__(self):
        self.db_service = db_service

    async def analyze_all_cities_questions(self,cityId:Optional[int] =None) -> bool:
        """
        Analyze City Questions data for a city.

        Args:
            cityId: ID of the city, if you want to process only one city.
        """
        df = db_service.read_with_query(f"Select CityID, CityName,State, Country from Cities where IsDeleted=0 and cityId={cityId}")

        for city in df.itertuples(index=False):
            #res = await self.analyze_PillarQuestions(city)
            #res = await self.analyze_cityPillar(city)
            res = await self.analyze_city(city)

        return res

    async def analyze_PillarQuestions(self, city: Any) -> bool:
        """
        Analyze Pillar Questions data for a city.

        Args:
            cityId: ID of the city, if you want to process only one city.
        """
        df = db_service.get_view_data(
            "vw_CityPillarQuestionEvaluations", f"cityId = {city.CityID}",10
        )
        if(len(df)):
            pillarIds = df["PillarID"].unique().tolist()
            for pillarId in pillarIds:
                pillar_df = df[df["PillarID"] == pillarId]
                questionList: list[dict[str, Any]] = []
                try:
                    for row in pillar_df.itertuples(index=False):
                        # Run the AI analysis
                        ai_data = await veridian_ai_research_service.research_and_score_question (
                            city.CityName,
                            f"State :{city.State}, Country :{city.Country}",
                            row.PillarID,
                            row.PillarName,
                            row.QuestionText,
                            row.ScoreProgress,
                            row.NormalizedValue * 4.0,
                            None
                        )

                        if ai_data["success"]:
                            #dont changed the order of below parameter
                            r = {
                                "CityID": row.CityID,
                                "PillarID": row.PillarID,
                                "QuestionID": row.QuestionID,
                                "Year": ai_data["year"],
                                "AIScore": ai_data["ai_score"],
                                "AIProgress": ai_data["ai_progress"],
                                "EvaluatorScore": ai_data["evaluator_score"],
                                "Discrepancy": ai_data["discrepancy"],
                                "ConfidenceLevel": ai_data["confidence_level"],
                                "DataSourcesUsed": ai_data["data_sources_count"],
                                "EvidenceSummary": ai_data["evidence_summary"],
                                "RedFlags": ai_data["red_flag"],
                                "GeographicEquityNote": ai_data["geographic_equity_note"],
                                "SourceType": ai_data["source_type"],
                                "SourceName": ai_data["source_name"],
                                "SourceURL": ai_data["source_url"],
                                "SourceDataYear": ai_data["source_data_year"],
                                "SourceDataExtract": ai_data["source_data_extract"],
                                "SourceTrustLevel": ai_data["source_trust_level"]
                            }
                            questionList.append(r)
                        else:
                            logger.error(
                                f"Not get record for {row.QuestionID}", exc_info=True
                            )
                    if len(questionList) > 0 :
                        db_service.bulk_upsert_question_evaluations(questionList)

                except Exception as e:
                    logger.error(
                        f"Error analyzing pillar {pillarId} data: {e}", exc_info=True
                    )
            return True
        return False

    async def analyze_cityPillar(self, city: Any)-> bool:
        """
            Docstring for analyze_cityPillar
            
            :param cityId: cityid of city which going to be process
            :type cityId: int
            :return: Description
            :rtype: bool
        """

        df = db_service.get_view_data("vw_CityPillarEvaluations", f"cityId = {city.CityID}",2)
        if(len(df)):
            pillarList: list[dict[str, Any]] = []
            pillarSourceList: list[dict[str, Any]] = []
            for row in df.itertuples(index=False):
                # Run the AI analysis
                ai_data = await veridian_ai_research_service.research_and_score_pillar(
                    city.CityName,
                    f"State :{city.State}, Country :{city.Country}",
                    row.PillarID,
                    row.PillarName,
                    row.QuestionWithScores,
                    row.EvaluatorScore,
                    row.AIScore,
                )

                if ai_data["success"]:
                    #dont changed the order of below parameter

                    for src in ai_data["sources"]:
                        subRes = {
                            "CityID": row.CityID,
                            "DataYear": ai_data['year'],
                            "PillarID": row.PillarID,
                            "SourceType": src["source_type"],
                            "SourceName": src["source_name"],
                            "SourceURL": src["source_url"],
                            "DataExtract": src["data_extract"],
                            "TrustLevel": src["trust_level"]
                        }
                        pillarSourceList.append(subRes)

                    r = {
                        "CityID": row.CityID,
                        "PillarID": row.PillarID,
                        "Year": ai_data['year'],
                        "AIScore": ai_data['ai_score'],
                        "AIProgress": ai_data['ai_progress'],
                        "EvaluatorScore": ai_data['evaluator_score'],
                        "Discrepancy": ai_data['discrepancy'],
                        "ConfidenceLevel": ai_data['confidence_level'],
                        "EvidenceSummary": ai_data['evidence_summary'],
                        "RedFlags": ai_data.get('red_flag',''),
                        "GeographicEquityNote": ai_data['geographic_equity_note'],
                        "InstitutionalAssessment": ai_data['institutional_assessment'],
                        "DataGapAnalysis": ai_data['data_gap_analysis']
                    }
                    pillarList.append(r)

                else:
                    logger.error(
                        f"Not get record for {row.PillarID}", exc_info=True
                    )
            if len(pillarList) > 0 :
                db_service.bulk_upsert_pillar_evaluations(pillarList, pillarSourceList)
                return True
        return False

    async def analyze_city(self,city:Any)->bool:
        """
            Docstring for analyze_city
            
            :param cityId: id of the city to get combine description of all pillars
            :type cityId: int
            :return: Description
            :rtype: bool
        """
        where = f"cityId = {city.CityID}";
        df = db_service.get_view_data("vw_CityEvaluations", where)
        cityList : list[dict[str, Any]] = []
        if(len(df)):
            for row in df.itertuples(index = False):
                 # Run the AI analysis
                ai_data = await veridian_ai_research_service.research_and_score_city(
                    city.CityName,
                    f"State :{city.State}, Country :{city.Country}",
                    row.EvaluatorScore,
                    row.AIScore,
                    row.PillarWithScores
                )

                if ai_data["success"]:
                    #dont changed the order of below parameter
                    r = {
                        "CityID": row.CityID,
                        "Year": ai_data['year'],
                        "AIScore": ai_data['ai_score'],
                        "AIProgress": ai_data['ai_progress'],
                        "EvaluatorScore": ai_data['evaluator_score'],
                        "Discrepancy": ai_data['discrepancy'],
                        "ConfidenceLevel": ai_data['confidence_level'],
                        "EvidenceSummary": ai_data['evidence_summary'],
                        "CrossPillarPatterns": ai_data.get('cross_pillar_patterns',''),
                        "InstitutionalCapacity": ai_data['institutional_capacity'],
                        "EquityAssessment": ai_data['equity_assessment'],
                        "SustainabilityOutlook": ai_data['sustainability_outlook'],
                        "StrategicRecommendations": ai_data['strategic_recommendation'],
                        "DataTransparencyNote": ai_data['data_transparency_note'],
                    }
                    cityList.append(r)
                else:
                    logger.error(
                        f"Not get record for {row.CityID}", exc_info=True
                    )
            if(len(cityList)):
                db_service.bulk_upsert_city_evaluations(cityList)
                return True

        return False


# Singleton instance
score_analyzer_service = ScoreAnalyzerService()
