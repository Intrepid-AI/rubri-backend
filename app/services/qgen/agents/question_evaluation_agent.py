import json
import time
from typing import List, Dict, Optional, TYPE_CHECKING
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from app.services.qgen.agents.base_agent import BaseAgent
from app.services.qgen.models.schemas import (
    QuestionEvaluation, TechnicalQuestion, ExtractedSkill,
    ProcessingStage, MultiAgentInterviewState, LLMConfig,
    QuestionType, create_initial_state, LLMProvider, QuestionEvaluationOutput
)
from app.logger import get_logger

if TYPE_CHECKING:
    from app.services.qgen.streaming.stream_manager import StreamManager

class QuestionEvaluationAgent(BaseAgent):
    """
    Agent 3: Evaluates the quality and depth of generated technical questions.
    
    Responsibilities:
    - Assess technical depth vs surface level
    - Evaluate relevance to candidate's experience  
    - Check difficulty appropriateness
    - Ensure questions are non-generic
    - Approve/reject questions based on quality criteria
    """
    
    def __init__(self, llm_config: LLMConfig, stream_manager: Optional['StreamManager'] = None):
        super().__init__("QuestionEvaluationAgent", llm_config, 
                        structured_output_model=QuestionEvaluationOutput,
                        stream_manager=stream_manager)
    
    def execute(self, state: MultiAgentInterviewState) -> MultiAgentInterviewState:
        """Evaluate all generated questions for quality and appropriateness."""
        self.logger.info("Starting question evaluation process")
        start_time = time.time()
        
        # Emit streaming start event
        self.stream_start_sync("Evaluating question quality and relevance...")
        
        try:
            generated_questions = state["generated_questions"]
            extracted_skills = state["extracted_skills"]
            
            if not generated_questions:
                error_msg = "No generated questions found. Run QuestionGenerationAgent first."
                self.logger.error(error_msg)
                raise Exception(error_msg)
            
            # Stream thinking about evaluation strategy
            self.stream_thinking_sync(f"Analyzing {len(generated_questions)} questions for technical depth and relevance...")
            
            # Evaluate each question
            evaluations = []
            approved_questions = []
            total_questions = len(generated_questions)
            
            for i, question in enumerate(generated_questions, 1):
                self.stream_thinking_sync(f"Evaluating question {i}/{total_questions}: {question.question_text[:80]}...")
                
                evaluation = self._evaluate_question(question, extracted_skills, i, total_questions)
                evaluations.append(evaluation)
                
                # Approve question if it meets quality criteria
                if evaluation.approved:
                    approved_questions.append(question)
            
            # Update state
            state["question_evaluations"] = evaluations
            state["approved_questions"] = approved_questions
            state["processing_stage"] = ProcessingStage.QUESTIONS_EVALUATED
            
            # Calculate evaluation statistics
            total_questions = len(generated_questions)
            approved_count = len(approved_questions)
            avg_quality = sum(e.overall_quality for e in evaluations) / len(evaluations) if evaluations else 0
            
            # Record success
            execution_time = time.time() - start_time
            self._record_result(
                state,
                success=True,
                output_data={
                    "total_questions": total_questions,
                    "approved_questions": approved_count,
                    "approval_rate": approved_count / total_questions if total_questions > 0 else 0,
                    "average_quality_score": round(avg_quality, 2)
                },
                execution_time=execution_time
            )
            
            self.logger.info(f"Question evaluation completed: {approved_count}/{total_questions} approved ({execution_time:.2f}s)")
            
            # Add summary message
            state["messages"].append(AIMessage(
                content=f"✅ Question evaluation completed. Approved {approved_count}/{total_questions} questions "
                        f"(approval rate: {approved_count/total_questions*100:.1f}%). "
                        f"Average quality score: {avg_quality:.1f}/5. Processing time: {execution_time:.2f}s"
            ))
            
        except Exception as e:
            execution_time = time.time() - start_time
            error_msg = f"Question evaluation failed: {str(e)}"
            self.logger.error(f"Question evaluation failed ({execution_time:.2f}s): {str(e)}")
            
            state["errors"].append(error_msg)
            state["processing_stage"] = ProcessingStage.ERROR
            
            self._record_result(
                state,
                success=False,
                error_message=error_msg,
                execution_time=execution_time
            )
        
        return state
    
    def _evaluate_question(self, question: TechnicalQuestion, 
                          extracted_skills: List[ExtractedSkill],
                          question_index: int = 1,
                          total_questions: int = 1) -> QuestionEvaluation:
        """Evaluate a single question for quality and appropriateness."""
        
        # Find the relevant skill for this question
        relevant_skill = None
        for skill in extracted_skills:
            if skill.skill_name == question.targeted_skill:
                relevant_skill = skill
                break
        
        if not relevant_skill:
            # If we can't find the skill, create a basic evaluation
            return QuestionEvaluation(
                question_id=question.question_id,
                technical_depth_score=2,
                relevance_score=2,
                difficulty_appropriateness=2,
                non_generic_score=2,
                overall_quality=2,
                feedback="Could not find matching skill for evaluation",
                approved=False
            )
        
        system_prompt = """You are an expert technical interview evaluator. Your job is to assess 
        the quality of technical interview questions against strict criteria.
        
        EVALUATION CRITERIA:
        
        1. TECHNICAL DEPTH (1-5):
           - 1: Surface level, tests only basic knowledge
           - 2: Shallow technical understanding
           - 3: Moderate technical depth
           - 4: Deep technical concepts
           - 5: Very deep, tests mathematical foundations and internals
        
        2. RELEVANCE (1-5):
           - 1: Not relevant to candidate's experience
           - 2: Loosely related
           - 3: Somewhat relevant
           - 4: Highly relevant to their background
           - 5: Perfectly tailored to their specific experience
        
        3. DIFFICULTY APPROPRIATENESS (1-5):
           - 1: Too easy/hard for candidate's level
           - 2: Somewhat inappropriate difficulty
           - 3: Acceptable difficulty level
           - 4: Well-matched to experience level
           - 5: Perfect difficulty calibration
        
        4. NON-GENERIC SCORE (1-5):
           - 1: Very generic, could ask any candidate
           - 2: Mostly generic with some specifics
           - 3: Moderately specific
           - 4: Highly specific to candidate
           - 5: Completely tailored, couldn't ask others
        
        APPROVAL CRITERIA:
        - Technical depth >= 3
        - Relevance >= 3
        - Difficulty appropriateness >= 3
        - Non-generic score >= 3
        - Overall quality >= 3"""
        
        human_prompt = f"""
        Evaluate this technical interview question:
        
        QUESTION:
        ID: {question.question_id}
        Text: {question.question_text}
        Type: {question.question_type}
        Difficulty Level: {question.difficulty_level}
        Targeted Skill: {question.targeted_skill}
        Rationale: {question.rationale}
        Tags: {question.tags}
        
        CANDIDATE'S SKILL CONTEXT:
        Skill: {relevant_skill.skill_name}
        Experience Level: {relevant_skill.experience_level}
        Confidence Score: {relevant_skill.confidence_score}/5
        Evidence: {relevant_skill.evidence_from_text}
        Context: {relevant_skill.context}
        Technologies: {relevant_skill.specific_technologies}
        
        Provide detailed evaluation in JSON format:
        
        {{
            "technical_depth_score": 1-5,
            "technical_depth_reasoning": "why this score",
            "relevance_score": 1-5,
            "relevance_reasoning": "why this score",
            "difficulty_appropriateness": 1-5,
            "difficulty_reasoning": "why this score", 
            "non_generic_score": 1-5,
            "non_generic_reasoning": "why this score",
            "overall_quality": 1-5,
            "strengths": ["what's good about this question"],
            "weaknesses": ["what could be improved"],
            "improvement_suggestions": ["specific suggestions"],
            "approved": true/false,
            "detailed_feedback": "comprehensive feedback"
        }}
        
        Be strict in your evaluation. Only approve questions that truly test deep technical understanding
        and are specifically tailored to the candidate's experience.
        """
        
        try:
            response = self.llm.invoke([
                SystemMessage(content=system_prompt),
                HumanMessage(content=human_prompt)
            ])
            
            evaluation = response.evaluations[0]
            
            # Stream evaluation result
            if self.stream_manager:
                self._ensure_async_context(self.stream_manager.emit_evaluation_result(
                    question.question_id,
                    {
                        "question_id": question.question_id,
                        "technical_depth_score": evaluation.technical_depth_score,
                        "relevance_score": evaluation.relevance_score,
                        "difficulty_appropriateness": evaluation.difficulty_appropriateness,
                        "non_generic_score": evaluation.non_generic_score,
                        "overall_quality": evaluation.overall_quality,
                        "approved": evaluation.approved,
                        "feedback": evaluation.feedback,
                        "question_index": question_index,
                        "total_questions": total_questions
                    }
                ))
            
            return evaluation
        except Exception as e:
            # Fallback evaluation if LLM fails
            fallback_eval = self._create_fallback_evaluation(question, relevant_skill)
            
            # Stream fallback evaluation result
            if self.stream_manager:
                self._ensure_async_context(self.stream_manager.emit_evaluation_result(
                    question.question_id,
                    {
                        "question_id": question.question_id,
                        "technical_depth_score": fallback_eval.technical_depth_score,
                        "relevance_score": fallback_eval.relevance_score,
                        "difficulty_appropriateness": fallback_eval.difficulty_appropriateness,
                        "non_generic_score": fallback_eval.non_generic_score,
                        "overall_quality": fallback_eval.overall_quality,
                        "approved": fallback_eval.approved,
                        "feedback": fallback_eval.feedback,
                        "question_index": question_index,
                        "total_questions": total_questions,
                        "is_fallback": True
                    }
                ))
            
            return fallback_eval
    
    def _create_fallback_evaluation(self, question: TechnicalQuestion, 
                                  skill: ExtractedSkill) -> QuestionEvaluation:
        """Create fallback evaluation if LLM evaluation fails."""
        
        self.logger.info(f"Creating fallback evaluation for question {question.question_id}")
        
        # Simple heuristic-based evaluation
        technical_depth = 3  # Default moderate
        if any(word in question.question_text.lower() for word in 
               ['derive', 'mathematical', 'algorithm', 'complexity', 'optimize']):
            technical_depth = 4
            self.logger.info("Increased technical depth score due to advanced keywords")
        
        relevance = 3  # Default moderate
        if skill.skill_name.lower() in question.question_text.lower():
            relevance = 4
            self.logger.info("Increased relevance score due to skill name match")
        
        difficulty_appropriateness = 3  # Default appropriate
        if question.difficulty_level <= skill.confidence_score:
            difficulty_appropriateness = 4
            self.logger.info("Increased difficulty appropriateness due to good level match")
        
        non_generic = 3  # Default moderate
        if any(context_word in question.question_text.lower() for context_word in 
               skill.context.lower().split() if len(context_word) > 3):
            non_generic = 4
            self.logger.info("Increased non-generic score due to context match")
        
        overall = (technical_depth + relevance + difficulty_appropriateness + non_generic) // 4
        approved = overall >= 3
        
        self.logger.info(f"Fallback evaluation scores: Depth={technical_depth}, Relevance={relevance}, Difficulty={difficulty_appropriateness}, NonGeneric={non_generic}, Overall={overall}")
        self.logger.info(f"Question {question.question_id} {'APPROVED' if approved else 'REJECTED'} by fallback evaluation")
        
        return QuestionEvaluation(
            question_id=question.question_id,
            technical_depth_score=technical_depth,
            relevance_score=relevance,
            difficulty_appropriateness=difficulty_appropriateness,
            non_generic_score=non_generic,
            overall_quality=overall,
            feedback="Fallback evaluation - LLM evaluation failed",
            approved=approved
        )

# Enhanced evaluation with batch processing
class BatchQuestionEvaluator:
    """Evaluates multiple questions in a single LLM call for efficiency."""
    
    def __init__(self, llm):
        self.llm = llm
    
    def evaluate_batch(self, questions: List[TechnicalQuestion], 
                      skills: List[ExtractedSkill]) -> List[QuestionEvaluation]:
        """Evaluate multiple questions in a single LLM call."""
        
        # Prepare batch evaluation prompt
        questions_data = []
        for q in questions:
            # Find relevant skill
            relevant_skill = next((s for s in skills if s.skill_name == q.targeted_skill), None)
            
            question_data = {
                "id": q.question_id,
                "text": q.question_text,
                "type": q.question_type,
                "difficulty": q.difficulty_level,
                "skill": q.targeted_skill,
                "rationale": q.rationale,
                "skill_context": {
                    "experience_level": relevant_skill.experience_level if relevant_skill else "Unknown",
                    "evidence": relevant_skill.evidence_from_text if relevant_skill else "",
                    "confidence": relevant_skill.confidence_score if relevant_skill else 1
                }
            }
            questions_data.append(question_data)
        
        system_prompt = """You are evaluating multiple technical interview questions for quality.
        For each question, provide scores (1-5) for:
        - Technical depth
        - Relevance to candidate 
        - Difficulty appropriateness
        - Non-generic specificity
        - Overall quality
        
        Be strict - only approve questions that truly test deep understanding."""
        
        human_prompt = f"""
        Evaluate these {len(questions_data)} questions:
        
        {json.dumps(questions_data, indent=2)}
        
        Return evaluations in JSON format:
        {{
            "evaluations": [
                {{
                    "question_id": "...",
                    "technical_depth_score": 1-5,
                    "relevance_score": 1-5,
                    "difficulty_appropriateness": 1-5,
                    "non_generic_score": 1-5,
                    "overall_quality": 1-5,
                    "approved": true/false,
                    "feedback": "brief feedback"
                }}
            ]
        }}
        """
        
        # This would implement the actual batch evaluation
        # For now, return individual evaluations
        return []

# Testing the Question Evaluation Agent
def test_question_evaluation_agent():
    """Test the question evaluation agent."""
    
    print("🧪 Testing Question Evaluation Agent")
    print("=" * 45)
    
    # Create sample questions (as if from QuestionGenerationAgent)
    sample_questions = [
        TechnicalQuestion(
            question_id="JAVA_Q1",
            question_text="Given your experience with Spring Boot microservices handling 10K+ requests/second, explain how Spring's auto-configuration affects startup time and memory usage. How would you optimize the bean creation process for faster startup?",
            question_type=QuestionType.OPTIMIZATION_SCALING,
            difficulty_level=4,
            estimated_time_minutes=12,
            targeted_skill="Java Spring Boot",
            rationale="Tests deep understanding of Spring internals based on high-performance experience",
            tags=["spring", "performance", "optimization"]
        ),
        TechnicalQuestion(
            question_id="GENERIC_Q1", 
            question_text="What is Spring Boot?",
            question_type=QuestionType.THEORETICAL_CONCEPTS,
            difficulty_level=1,
            estimated_time_minutes=3,
            targeted_skill="Java Spring Boot",
            rationale="Basic question about Spring Boot",
            tags=["spring", "basic"]
        ),
        TechnicalQuestion(
            question_id="POSTGRES_Q1",
            question_text="Based on your PostgreSQL optimization experience, derive the cost estimation formula used by the query planner. How do statistics influence join order decisions in complex queries with your specific workload patterns?",
            question_type=QuestionType.MATHEMATICAL_FOUNDATION,
            difficulty_level=5,
            estimated_time_minutes=15,
            targeted_skill="PostgreSQL",
            rationale="Tests deep database internals knowledge specific to their optimization work",
            tags=["postgresql", "optimization", "query-planning"]
        )
    ]
    
    # Create sample skills
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
    
    # Set up state with questions and skills
    state["generated_questions"] = sample_questions
    state["extracted_skills"] = sample_skills
    state["processing_stage"] = ProcessingStage.QUESTIONS_GENERATED
    
    # Create and execute agent
    agent = QuestionEvaluationAgent(llm_config)
    
    try:
        result_state = agent.execute(state)
        
        if result_state["processing_stage"] == ProcessingStage.QUESTIONS_EVALUATED:
            print("✅ Question evaluation successful!")
            
            evaluations = result_state["question_evaluations"]
            approved_questions = result_state["approved_questions"]
            
            print(f"📊 Evaluated {len(evaluations)} questions")
            print(f"✅ Approved {len(approved_questions)} questions")
            print(f"📈 Approval rate: {len(approved_questions)/len(evaluations)*100:.1f}%")
            
            print("\n🔍 DETAILED EVALUATION RESULTS:")
            for eval_result in evaluations:
                print(f"\n📋 Question ID: {eval_result.question_id}")
                print(f"   Technical Depth: {eval_result.technical_depth_score}/5")
                print(f"   Relevance: {eval_result.relevance_score}/5") 
                print(f"   Difficulty Match: {eval_result.difficulty_appropriateness}/5")
                print(f"   Non-Generic: {eval_result.non_generic_score}/5")
                print(f"   Overall Quality: {eval_result.overall_quality}/5")
                print(f"   APPROVED: {'✅ YES' if eval_result.approved else '❌ NO'}")
                print(f"   Feedback: {eval_result.feedback[:150]}...")
            
            print(f"\n💬 Agent Message: {result_state['messages'][-1].content}")
            
        else:
            print("❌ Question evaluation failed")
            for error in result_state["errors"]:
                print(f"  Error: {error}")
    
    except Exception as e:
        print(f"❌ Test failed: {e}")

if __name__ == "__main__":
    test_question_evaluation_agent()