import json
import time
from typing import List, Dict
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from app.services.qgen.agents.base_agent import BaseAgent
from app.services.qgen.models.schemas import (
    ExpectedResponse, TechnicalQuestion, ExtractedSkill, QuestionEvaluation,
    ProcessingStage, MultiAgentInterviewState, LLMConfig,
    QuestionType, create_initial_state, LLMProvider, ExpectedResponseOutput, ScoringRubric
)
from app.logger import get_logger

class ExpectedResponseAgent(BaseAgent):
    """
    Agent 4: Generates detailed expected responses for approved technical questions.
    
    Responsibilities:
    - Create comprehensive expected responses for interviewer guidance
    - Identify key concepts that must be mentioned
    - Define good answer indicators and red flags
    - Generate follow-up questions
    - Provide scoring rubrics
    - Include sample excellent answers
    """
    
    def __init__(self, llm_config: LLMConfig):
        super().__init__("ExpectedResponseAgent", llm_config, structured_output_model=ExpectedResponseOutput)
    
    def execute(self, state: MultiAgentInterviewState) -> MultiAgentInterviewState:
        """Generate expected responses for all approved questions."""
        self.logger.info("Starting expected response generation process")
        start_time = time.time()
        
        try:
            approved_questions = state["approved_questions"]
            extracted_skills = state["extracted_skills"]
            question_evaluations = state["question_evaluations"]
            
            if not approved_questions:
                error_msg = "No approved questions found. Run QuestionEvaluationAgent first."
                self.logger.error(error_msg)
                raise Exception(error_msg)
            
            # Generate expected responses for each approved question
            expected_responses = []
            
            for i, question in enumerate(approved_questions, 1):
                # Find the evaluation for this question
                evaluation = next((e for e in question_evaluations if e.question_id == question.question_id), None)
                
                # Find relevant skill
                relevant_skill = next((s for s in extracted_skills if s.skill_name == question.targeted_skill), None)
                
                expected_response = self._generate_expected_response(question, relevant_skill, evaluation)
                expected_responses.append(expected_response)
            
            # Update state
            state["expected_responses"] = expected_responses
            state["processing_stage"] = ProcessingStage.RESPONSES_GENERATED
            
            responses_count = len(expected_responses)
            questions_count = len(approved_questions)
            
            # Record success
            execution_time = time.time() - start_time
            self._record_result(
                state,
                success=True,
                output_data={
                    "responses_generated": responses_count,
                    "questions_covered": questions_count
                },
                execution_time=execution_time
            )
            
            self.logger.info(f"Expected response generation completed: {responses_count} responses ({execution_time:.2f}s)")
            
            # Add summary message
            state["messages"].append(AIMessage(
                content=f"✅ Expected response generation completed. Generated detailed interviewer guidance "
                        f"for {len(expected_responses)} approved questions. Processing time: {execution_time:.2f}s"
            ))
            
        except Exception as e:
            execution_time = time.time() - start_time
            error_msg = f"Expected response generation failed: {str(e)}"
            self.logger.error(f"Expected response generation failed ({execution_time:.2f}s): {str(e)}")
            
            state["errors"].append(error_msg)
            state["processing_stage"] = ProcessingStage.ERROR
            
            self._record_result(
                state,
                success=False,
                error_message=error_msg,
                execution_time=execution_time
            )
        
        return state
    
    def _generate_expected_response(self, question: TechnicalQuestion, 
                                  skill: ExtractedSkill, 
                                  evaluation: QuestionEvaluation) -> ExpectedResponse:
        """Generate comprehensive expected response for a single question."""
        
        system_prompt = """You are an expert technical interviewer creating detailed guidance for interviewers.
        Your job is to provide comprehensive expected responses that help interviewers:
        
        1. Identify if the candidate truly understands the technical concepts
        2. Recognize excellent vs poor answers
        3. Know what follow-up questions to ask
        4. Score responses fairly and consistently
        
        COMPONENTS TO GENERATE:
        
        1. KEY CONCEPTS REQUIRED: Core technical concepts that MUST be mentioned
        2. GOOD ANSWER INDICATORS: Signs that show deep understanding
        3. RED FLAGS: Warning signs of shallow understanding or misconceptions
        4. FOLLOW-UP QUESTIONS: 2-3 probing questions to go deeper
        5. SCORING RUBRIC: Clear criteria for different score levels
        6. COMMON MISCONCEPTIONS: Typical wrong answers to watch for
        
        Make this actionable for interviewers who may not be experts in every technical area."""
        
        skill_context = ""
        if skill:
            skill_context = f"""
            CANDIDATE'S SKILL CONTEXT:
            - Skill: {skill.skill_name}
            - Experience Level: {skill.experience_level}
            - Evidence: {skill.evidence_from_text}
            - Context: {skill.context}
            - Confidence: {skill.confidence_score}/5
            """
        
        evaluation_context = ""
        if evaluation:
            evaluation_context = f"""
            QUESTION EVALUATION:
            - Technical Depth: {evaluation.technical_depth_score}/5
            - Difficulty Level: {question.difficulty_level}/5
            - Overall Quality: {evaluation.overall_quality}/5
            """
        
        human_prompt = f"""
        Generate comprehensive interviewer guidance for this technical question:
        
        QUESTION DETAILS:
        ID: {question.question_id}
        Question: {question.question_text}
        Type: {question.question_type}
        Targeted Skill: {question.targeted_skill}
        Rationale: {question.rationale}
        Estimated Time: {question.estimated_time_minutes} minutes
        Tags: {question.tags}
        
        {skill_context}
        {evaluation_context}
        
        Provide detailed guidance in JSON format:
        
        {{
            "key_concepts_required": [
                "essential concept 1",
                "essential concept 2", 
                "essential concept 3"
            ],
            "good_answer_indicators": [
                "indicator of deep understanding 1",
                "indicator of deep understanding 2",
                "indicator of deep understanding 3"
            ],
            "red_flags": [
                "warning sign 1",
                "warning sign 2", 
                "warning sign 3"
            ],
            "follow_up_questions": [
                "probing follow-up question 1",
                "probing follow-up question 2",
                "probing follow-up question 3"
            ],
            "scoring_rubric": {{
                "excellent": "criteria for excellent (5/5)",
                "good": "criteria for good (4/5)",
                "average": "criteria for average (3/5)",
                "below_average": "criteria for below average (2/5)",
                "poor": "criteria for poor (1/5)"
            }}
        }}
        
        IMPORTANT:
        - Be specific to this exact question and technical area
        - Include technical details that interviewers should listen for
        - Make scoring criteria objective and clear
        - Provide actionable guidance for non-experts
        - Consider the candidate's demonstrated experience level
        """
        
        try:
            response = self.llm.invoke([
                SystemMessage(content=system_prompt),
                HumanMessage(content=human_prompt)
            ])
            
            # The response will be a ExpectedResponseOutput with a list of responses
            # We're generating one response at a time, so take the first response
            expected_response = response.responses[0]
            
            return expected_response
            
        except Exception as e:
            # Create fallback expected response
            fallback_response = self._create_fallback_expected_response(question, skill)
            return fallback_response
    
    def _create_fallback_expected_response(self, question: TechnicalQuestion, 
                                         skill: ExtractedSkill) -> ExpectedResponse:
        """Create fallback expected response if LLM generation fails."""
        
        fallback_response = ExpectedResponse(
            question_id=question.question_id,
            key_concepts_required=[
                f"Core {question.targeted_skill} concepts",
                "Technical implementation details",
                "Performance considerations"
            ],
            good_answer_indicators=[
                "Demonstrates deep technical understanding",
                "Provides specific examples from experience",
                "Discusses trade-offs and alternatives"
            ],
            red_flags=[
                "Vague or generic responses",
                "Incorrect technical details",
                "No awareness of limitations or edge cases"
            ],
            follow_up_questions=[
                f"Can you elaborate on the {question.targeted_skill} implementation?",
                "What challenges did you face and how did you solve them?",
                "How would you optimize this for better performance?"
            ],
            scoring_rubric=ScoringRubric(
                excellent="Complete technical accuracy with deep insights",
                good="Good technical understanding with minor gaps",
                average="Basic understanding with some inaccuracies",
                below_average="Limited understanding with major gaps",
                poor="Little to no technical understanding"
            )
        )
        
        return fallback_response

# Enhanced response generation with specialized templates
class SpecializedResponseGenerators:
    """Specialized expected response generators for different question types."""
    
    @staticmethod
    def generate_mathematical_response_template(question: TechnicalQuestion) -> Dict:
        """Template for mathematical foundation questions."""
        return {
            "key_concepts_focus": "Mathematical derivations, formulas, complexity analysis",
            "good_indicators": [
                "Shows mathematical working step by step",
                "Explains the intuition behind formulas",
                "Discusses computational complexity"
            ],
            "red_flags": [
                "Cannot derive or explain formulas", 
                "Makes mathematical errors",
                "No understanding of complexity implications"
            ]
        }
    
    @staticmethod
    def generate_implementation_response_template(question: TechnicalQuestion) -> Dict:
        """Template for implementation detail questions."""
        return {
            "key_concepts_focus": "Architecture, design patterns, optimization techniques",
            "good_indicators": [
                "Describes implementation architecture clearly",
                "Discusses design pattern choices",
                "Addresses performance optimization"
            ],
            "red_flags": [
                "Cannot explain implementation details",
                "No consideration of edge cases",
                "Ignores performance implications"
            ]
        }
    
    @staticmethod
    def generate_system_design_response_template(question: TechnicalQuestion) -> Dict:
        """Template for system design questions."""
        return {
            "key_concepts_focus": "Scalability, reliability, trade-offs",
            "good_indicators": [
                "Considers scalability requirements",
                "Discusses reliability and fault tolerance",
                "Analyzes trade-offs between solutions"
            ],
            "red_flags": [
                "No consideration of scale",
                "Ignores reliability concerns",
                "Cannot explain design trade-offs"
            ]
        }

# Testing the Expected Response Agent
def test_expected_response_agent():
    """Test the expected response agent."""
    
    print("🧪 Testing Expected Response Agent")
    print("=" * 45)
    
    # Create sample approved questions
    approved_questions = [
        TechnicalQuestion(
            question_id="SPRING_Q1",
            question_text="Given your experience with Spring Boot microservices handling 10K+ requests/second, explain how Spring's auto-configuration affects startup time and memory usage. How would you optimize the bean creation process for faster startup?",
            question_type=QuestionType.OPTIMIZATION_SCALING,
            difficulty_level=4,
            estimated_time_minutes=12,
            targeted_skill="Java Spring Boot",
            rationale="Tests deep understanding of Spring internals based on high-performance experience",
            tags=["spring", "performance", "optimization"]
        ),
        TechnicalQuestion(
            question_id="POSTGRES_Q1",
            question_text="Based on your PostgreSQL optimization experience, derive the cost estimation formula used by the query planner. How do statistics influence join order decisions in complex queries?",
            question_type=QuestionType.MATHEMATICAL_FOUNDATION,
            difficulty_level=5,
            estimated_time_minutes=15,
            targeted_skill="PostgreSQL", 
            rationale="Tests deep database internals knowledge specific to their optimization work",
            tags=["postgresql", "optimization", "query-planning"]
        )
    ]
    
    # Create sample skills and evaluations
    sample_skills = [
        ExtractedSkill(
            skill_name="Java Spring Boot",
            category="Backend Development",
            evidence_from_text="5+ years developing microservices with Spring Boot handling 10K+ requests/second",
            experience_level="Advanced",
            confidence_score=5,
            context="High-performance microservices",
            specific_technologies=["Spring Boot", "Spring Cloud"]
        ),
        ExtractedSkill(
            skill_name="PostgreSQL",
            category="Database Systems",
            evidence_from_text="Experience with PostgreSQL optimization and query tuning",
            experience_level="Intermediate",
            confidence_score=4,
            context="Database optimization for high-traffic applications",
            specific_technologies=["PostgreSQL", "SQL"]
        )
    ]
    
    sample_evaluations = [
        QuestionEvaluation(
            question_id="SPRING_Q1",
            technical_depth_score=4,
            relevance_score=5,
            difficulty_appropriateness=4,
            non_generic_score=5,
            overall_quality=4,
            feedback="Excellent question that tests Spring internals with specific context",
            approved=True
        ),
        QuestionEvaluation(
            question_id="POSTGRES_Q1", 
            technical_depth_score=5,
            relevance_score=4,
            difficulty_appropriateness=4,
            non_generic_score=4,
            overall_quality=4,
            feedback="Deep technical question testing database internals",
            approved=True
        )
    ]
    
    # Create LLM config
    llm_config = LLMConfig(
        provider=LLMProvider.OPENAI,
        model="gpt-4",
        temperature=0.1
    )
    
    # Create state
    state = create_initial_state(
        resume_text="Sample resume",
        position_title="Senior Java Developer", 
        llm_provider=llm_config.provider,
        llm_model=llm_config.model
    )
    
    # Set up state
    state["approved_questions"] = approved_questions
    state["extracted_skills"] = sample_skills
    state["question_evaluations"] = sample_evaluations
    state["processing_stage"] = ProcessingStage.QUESTIONS_EVALUATED
    
    # Create and execute agent
    agent = ExpectedResponseAgent(llm_config)
    
    try:
        result_state = agent.execute(state)
        
        if result_state["processing_stage"] == ProcessingStage.RESPONSES_GENERATED:
            print("✅ Expected response generation successful!")
            
            expected_responses = result_state["expected_responses"]
            print(f"📊 Generated guidance for {len(expected_responses)} questions")
            
            print("\n📋 SAMPLE INTERVIEWER GUIDANCE:")
            for response in expected_responses[:1]:  # Show first response in detail
                print(f"\n🎯 Question ID: {response.question_id}")
                print(f"📚 Key Concepts Required:")
                for concept in response.key_concepts_required:
                    print(f"   • {concept}")
                
                print(f"\n✅ Good Answer Indicators:")
                for indicator in response.good_answer_indicators:
                    print(f"   • {indicator}")
                
                print(f"\n🚩 Red Flags:")
                for flag in response.red_flags:
                    print(f"   • {flag}")
                
                print(f"\n❓ Follow-up Questions:")
                for follow_up in response.follow_up_questions:
                    print(f"   • {follow_up}")
                
                print(f"\n📊 Scoring Rubric:")
                print(f"   excellent: {response.scoring_rubric.excellent}")
                print(f"   good: {response.scoring_rubric.good}")
                print(f"   average: {response.scoring_rubric.average}")
                print(f"   below_average: {response.scoring_rubric.below_average}")
                print(f"   poor: {response.scoring_rubric.poor}")
            
            print(f"\n💬 Agent Message: {result_state['messages'][-1].content}")
            
        else:
            print("❌ Expected response generation failed")
            for error in result_state["errors"]:
                print(f"  Error: {error}")
    
    except Exception as e:
        print(f"❌ Test failed: {e}")

if __name__ == "__main__":
    test_expected_response_agent()