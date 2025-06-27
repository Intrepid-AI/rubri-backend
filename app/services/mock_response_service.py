import json
import os
from typing import Dict, Any, Optional
from pathlib import Path

from app.logger import get_logger
from app.constants import Constants

logger = get_logger(__name__)


class MockResponseService:
    """
    Service for loading and serving mock responses during development.
    
    This service provides mock responses for the question generation endpoints
    to speed up development by avoiding expensive LLM API calls.
    """
    
    def __init__(self):
        self.mock_response_cache: Optional[Dict[str, Any]] = None
    
    def load_mock_response(self, file_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Load mock response from JSON file.
        
        Args:
            file_path: Optional path to mock response file. If not provided,
                      uses the default from constants.
        
        Returns:
            Dictionary containing the mock response data
            
        Raises:
            FileNotFoundError: If the mock response file doesn't exist
            json.JSONDecodeError: If the file contains invalid JSON
        """
        if file_path is None:
            file_path = Constants.MOCK_RESPONSE_FILE.value
        
        # Use cached response if available
        if self.mock_response_cache is not None:
            logger.debug("Using cached mock response")
            return self.mock_response_cache.copy()
        
        try:
            # Convert to absolute path
            if not os.path.isabs(file_path):
                # Get the project root directory (where main.py is located)
                project_root = Path(__file__).parent.parent.parent
                file_path = project_root / file_path
            
            logger.info(f"Loading mock response from: {file_path}")
            
            with open(file_path, 'r', encoding='utf-8') as f:
                mock_response = json.load(f)
            
            # Cache the response for future use
            self.mock_response_cache = mock_response
            logger.info("Mock response loaded and cached successfully")
            
            return mock_response.copy()
            
        except FileNotFoundError:
            logger.error(f"Mock response file not found: {file_path}")
            raise FileNotFoundError(f"Mock response file not found: {file_path}")
        
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in mock response file: {e}")
            raise json.JSONDecodeError(f"Invalid JSON in mock response file: {e}")
        
        except Exception as e:
            logger.error(f"Error loading mock response: {e}")
            raise Exception(f"Error loading mock response: {e}")
    
    def get_mock_question_response(
        self, 
        position_title: str = "Mock Position", 
        input_scenario: str = "mock",
        jd_document_id: Optional[str] = None,
        resume_document_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get a mock response for question generation endpoints.
        
        Args:
            position_title: The position title for the interview
            input_scenario: The input scenario (e.g., "resume_only", "jd_only", "both")
            jd_document_id: Optional JD document ID
            resume_document_id: Optional resume document ID
        
        Returns:
            Mock response formatted for QuestionGenerationResponse
        """
        try:
            mock_response = self.load_mock_response()
            
            # Update the response with the provided parameters
            mock_response["position_title"] = position_title
            mock_response["input_scenario"] = input_scenario
            
            # Update document IDs if provided
            if jd_document_id:
                logger.debug(f"Using JD document ID: {jd_document_id}")
            if resume_document_id:
                logger.debug(f"Using resume document ID: {resume_document_id}")
            
            # Reset processing time to a low value for mock response
            mock_response["processing_time"] = 0.1
            
            # Clear rubric_id to ensure a new one is generated if needed
            mock_response["rubric_id"] = None
            
            logger.info(f"Generated mock response for position: {position_title}")
            return mock_response
            
        except Exception as e:
            logger.error(f"Error generating mock question response: {e}")
            # Return a minimal fallback response if mock file fails
            return self._get_fallback_response(position_title, input_scenario)
    
    def _get_fallback_response(self, position_title: str, input_scenario: str) -> Dict[str, Any]:
        """
        Generate a minimal fallback response if mock file loading fails.
        
        Args:
            position_title: The position title for the interview
            input_scenario: The input scenario
        
        Returns:
            Minimal mock response
        """
        logger.warning("Using fallback mock response due to file loading error")
        
        return {
            "success": True,
            "rubric_id": None,
            "processing_time": 0.1,
            "candidate_name": "Mock Candidate",
            "position_title": position_title,
            "input_scenario": input_scenario,
            "skills_identified": 5,
            "categories_covered": 3,
            "questions_generated": 10,
            "interview_duration_minutes": 60,
            "sections_created": 3,
            "key_strengths": ["Mock skill 1", "Mock skill 2"],
            "potential_concerns": [],
            "focus_areas": ["Mock focus area"],
            "overall_recommendation": "Mock recommendation - this is a development response",
            "formatted_report": "# Mock Interview Report\n\nThis is a mock response for development purposes.",
            "evaluation_object": {
                "candidate_name": "Mock Candidate",
                "position_title": position_title,
                "input_scenario": input_scenario,
                "total_skills_identified": 5,
                "skill_categories": []
            },
            "agent_performance": {},
            "messages": ["Mock response generated"],
            "workflow_success": True,
            "error": None
        }
    
    def clear_cache(self):
        """Clear the cached mock response."""
        self.mock_response_cache = None
        logger.info("Mock response cache cleared")


# Global instance for use across the application
mock_response_service = MockResponseService()