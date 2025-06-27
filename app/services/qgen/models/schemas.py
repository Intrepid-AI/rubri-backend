from typing import Dict, List, Optional, TypedDict, Literal, Annotated, Union
from langchain_core.messages import BaseMessage
import operator
from pydantic import BaseModel, Field
from enum import Enum
from datetime import datetime

# LLM Model Configuration
class LLMProvider(str, Enum):
    OPENAI = "openai"
    GEMINI = "gemini"
    GROQ = "groq"
    AZURE_OPENAI = "azure_openai"
    PORTKEY = "portkey"

class LLMConfig(BaseModel):
    provider: LLMProvider
    model: str  # e.g., "gpt-4o-mini", "gemini-2.0-flash-001"
    temperature: float = 0.1
    max_tokens: Optional[int] = None

# Input scenarios
class InputScenario(str, Enum):
    RESUME_ONLY = "resume_only"
    JD_ONLY = "jd_only"
    BOTH = "both"

# Agent processing stages
class ProcessingStage(str, Enum):
    INITIALIZED = "initialized"
    SKILLS_EXTRACTED = "skills_extracted"
    QUESTIONS_GENERATED = "questions_generated"
    QUESTIONS_EVALUATED = "questions_evaluated"
    RESPONSES_GENERATED = "responses_generated"
    REPORT_ASSEMBLED = "report_assembled"
    COMPLETED = "completed"
    ERROR = "error"

# Skill categories (dynamically determined by LLM)
class SkillCategory(BaseModel):
    name: str  # e.g., "Backend Development", "Machine Learning"
    description: str
    priority: Literal[1, 2, 3, 4, 5]  # 1 = highest priority

# Technical skill extracted by LLM
class ExtractedSkill(BaseModel):
    skill_name: str
    category: str  # Will be mapped to SkillCategory later
    evidence_from_text: str  # Where this skill was mentioned
    experience_level: Literal["Beginner", "Intermediate", "Advanced", "Expert"]
    confidence_score: Literal[1, 2, 3, 4, 5]  # How confident we are about this skill
    context: str  # Project/work context where skill was used
    years_of_experience: Optional[str] = None
    specific_technologies: List[str] = []  # Related tools/frameworks

# Question types that can be generated
class QuestionType(str, Enum):
    MATHEMATICAL_FOUNDATION = "mathematical_foundation"
    IMPLEMENTATION_DETAILS = "implementation_details"
    OPTIMIZATION_SCALING = "optimization_scaling"
    EDGE_CASES_DEBUGGING = "edge_cases_debugging"
    SYSTEM_DESIGN = "system_design"
    BEST_PRACTICES = "best_practices"
    THEORETICAL_CONCEPTS = "theoretical_concepts"

# Generated technical question
class TechnicalQuestion(BaseModel):
    question_id: str
    question_text: str
    question_type: QuestionType
    difficulty_level: Literal[1, 2, 3, 4, 5]
    estimated_time_minutes: int
    targeted_skill: str
    rationale: str  # Why this question for this candidate
    tags: List[str] = []  # e.g., ["algorithms", "concurrency", "performance"]

# Question quality evaluation
class QuestionEvaluation(BaseModel):
    question_id: str
    technical_depth_score: Literal[1, 2, 3, 4, 5]  # 1=surface level, 5=very deep
    relevance_score: Literal[1, 2, 3, 4, 5]  # How relevant to candidate's experience
    difficulty_appropriateness: Literal[1, 2, 3, 4, 5]  # Appropriate for skill level
    non_generic_score: Literal[1, 2, 3, 4, 5]  # How specific vs generic
    overall_quality: Literal[1, 2, 3, 4, 5]
    feedback: str  # What could be improved
    approved: bool

class ScoringRubric(BaseModel):
    excellent: str = Field(description="Criteria for excellent score")
    good: str = Field(description="Criteria for good score") 
    average: str = Field(description="Criteria for average score")
    below_average: str = Field(description="Criteria for below average score")
    poor: str = Field(description="Criteria for poor score")

# Expected response for interviewer guidance
class ExpectedResponse(BaseModel):
    question_id: str
    key_concepts_required: List[str]  # Must mention these concepts
    good_answer_indicators: List[str]  # Signs of a strong answer
    red_flags: List[str]  # Warning signs in answers
    follow_up_questions: List[str]  # Suggested follow-ups
    scoring_rubric: ScoringRubric  # Score levels and what they mean

# Complete skill assessment
class SkillAssessment(BaseModel):
    skill_name: str
    category: str
    extracted_skill: ExtractedSkill
    questions: List[TechnicalQuestion]
    question_evaluations: List[QuestionEvaluation]
    expected_responses: List[ExpectedResponse]
    overall_assessment: str  # Summary of what this skill assessment covers

# Interview section (groups related skills)
class InterviewSection(BaseModel):
    section_id: str
    section_name: str  # e.g., "Machine Learning and AI"
    description: str
    skill_assessments: List[SkillAssessment]
    estimated_total_time: int  # minutes
    priority: Literal[1, 2, 3, 4, 5]

# Overall candidate evaluation
class CandidateEvaluation(BaseModel):
    candidate_name: Optional[str]
    position_title: str
    evaluation_date: datetime
    input_scenario: InputScenario
    
    # Extracted information
    total_skills_identified: int
    skill_categories: List[SkillCategory]
    
    # Generated content
    interview_sections: List[InterviewSection]
    total_questions: int
    estimated_interview_duration: int  # minutes
    
    # Overall insights
    key_strengths: List[str]
    potential_concerns: List[str]
    recommended_focus_areas: List[str]
    overall_recommendation: str

# Agent execution results
class AgentResult(BaseModel):
    agent_name: str
    execution_time: float  # seconds
    success: bool
    output_data: Optional[Dict] = None
    error_message: Optional[str] = None
    metadata: Dict = {}

# Main state for the multi-agent system
class MultiAgentInterviewState(TypedDict):
    # Configuration
    llm_config: LLMConfig
    
    # Input data
    resume_text: Optional[str]
    job_description: Optional[str]
    position_title: str
    
    # Processing metadata
    input_scenario: Optional[InputScenario]
    processing_stage: ProcessingStage
    current_agent: Optional[str]
    
    # Agent 1: Skill Extraction Results
    extracted_skills: List[ExtractedSkill]
    skill_categories: List[SkillCategory]
    
    # Agent 2: Question Generation Results
    generated_questions: List[TechnicalQuestion]
    
    # Agent 3: Question Evaluation Results
    question_evaluations: List[QuestionEvaluation]
    approved_questions: List[TechnicalQuestion]
    
    # Agent 4: Expected Response Generation Results
    expected_responses: List[ExpectedResponse]
    
    # Agent 5: Report Assembly Results
    skill_assessments: List[SkillAssessment]
    interview_sections: List[InterviewSection]
    final_evaluation: Optional[CandidateEvaluation]
    
    # System tracking
    agent_results: List[AgentResult]
    messages: List[BaseMessage]
    errors: Annotated[List[str], operator.add]

# SkillExtractionOutput Pydantic model
class SkillExtractionOutput(BaseModel):
    skills: List[ExtractedSkill]
    categories: List[SkillCategory]

# QuestionGenerationOutput Pydantic model
class QuestionGenerationOutput(BaseModel):
    questions: List[TechnicalQuestion]

# QuestionEvaluationOutput Pydantic model
class QuestionEvaluationOutput(BaseModel):
    evaluations: List[QuestionEvaluation]

# ExpectedResponseOutput Pydantic model
class ExpectedResponseOutput(BaseModel):
    responses: List[ExpectedResponse]

# Utility functions for state management
def create_initial_state(
    resume_text: str = "",
    job_description: str = "",
    position_title: str = "Technical Position",
    llm_provider: LLMProvider = LLMProvider.OPENAI,
    llm_model: str = "gpt-4o-mini"
) -> MultiAgentInterviewState:
    """Create initial state for the multi-agent system."""
    
    # Determine input scenario
    has_resume = bool(resume_text.strip())
    has_jd = bool(job_description.strip())
    
    if has_resume and has_jd:
        scenario = InputScenario.BOTH
    elif has_resume:
        scenario = InputScenario.RESUME_ONLY
    elif has_jd:
        scenario = InputScenario.JD_ONLY
    else:
        raise ValueError("Must provide either resume, job description, or both")
    
    return {
        "llm_config": LLMConfig(
            provider=llm_provider,
            model=llm_model
        ),
        "resume_text": resume_text.strip(),
        "job_description": job_description.strip(),
        "position_title": position_title.strip(),
        "input_scenario": scenario,
        "processing_stage": ProcessingStage.INITIALIZED,
        "current_agent": None,
        "extracted_skills": [],
        "skill_categories": [],
        "generated_questions": [],
        "question_evaluations": [],
        "approved_questions": [],
        "expected_responses": [],
        "skill_assessments": [],
        "interview_sections": [],
        "final_evaluation": None,
        "agent_results": [],
        "messages": [],
        "errors": []
    }