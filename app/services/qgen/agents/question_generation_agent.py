import json
import time
from typing import List, Dict
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from app.services.qgen.agents.base_agent import BaseAgent
from app.services.qgen.models.schemas import (
    TechnicalQuestion, QuestionType, ProcessingStage,
    MultiAgentInterviewState, LLMConfig, ExtractedSkill, InputScenario,
    create_initial_state, LLMProvider, QuestionGenerationOutput
)
from app.logger import get_logger

class QuestionGenerationAgent(BaseAgent):
    """
    Agent 2: Generates deep, technical interview questions based on extracted skills.
    
    Responsibilities:
    - Create non-generic questions tailored to candidate's specific experience
    - Mix different question types (mathematical, implementation, optimization, etc.)
    - Ensure appropriate difficulty levels
    - Target specific skills with evidence-based rationale
    """
    
    def __init__(self, llm_config: LLMConfig):
        super().__init__("QuestionGenerationAgent", llm_config, structured_output_model=QuestionGenerationOutput)
    
    def execute(self, state: MultiAgentInterviewState) -> MultiAgentInterviewState:
        """Generate technical questions for all extracted skills."""
        self.logger.info("Starting question generation process")
        start_time = time.time()
        
        try:
            extracted_skills = state["extracted_skills"]
            skill_categories = state["skill_categories"]
            input_scenario = state["input_scenario"]
            
            if not extracted_skills:
                error_msg = "No extracted skills found. Run SkillExtractionAgent first."
                self.logger.error(error_msg)
                raise Exception(error_msg)
            
            # Generate questions for each skill
            all_questions = []
            
            # Group skills by category for better question generation
            skills_by_category = self._group_skills_by_category(extracted_skills)
            
            for category_name, skills in skills_by_category.items():
                category_questions = self._generate_questions_for_category(
                    category_name, skills, input_scenario
                )
                all_questions.extend(category_questions)
            
            # Update state
            state["generated_questions"] = all_questions
            state["processing_stage"] = ProcessingStage.QUESTIONS_GENERATED
            
            total_questions = len(all_questions)
            categories_covered = len(skills_by_category)
            
            # Record success
            execution_time = time.time() - start_time
            self._record_result(
                state,
                success=True,
                output_data={
                    "questions_generated": total_questions,
                    "categories_covered": categories_covered
                },
                execution_time=execution_time
            )
            
            self.logger.info(f"Question generation completed: {total_questions} questions ({execution_time:.2f}s)")
            
            # Add summary message
            state["messages"].append(AIMessage(
                content=f"✅ Question generation completed. Generated {len(all_questions)} deep technical questions "
                        f"across {len(skills_by_category)} categories. Processing time: {execution_time:.2f}s"
            ))
            
        except Exception as e:
            execution_time = time.time() - start_time
            error_msg = f"Question generation failed: {str(e)}"
            self.logger.error(f"Question generation failed ({execution_time:.2f}s): {str(e)}")
            
            state["errors"].append(error_msg)
            state["processing_stage"] = ProcessingStage.ERROR
            
            self._record_result(
                state,
                success=False,
                error_message=error_msg,
                execution_time=execution_time
            )
        
        return state
    
    def _group_skills_by_category(self, skills: List[ExtractedSkill]) -> Dict[str, List[ExtractedSkill]]:
        """Group skills by their categories."""
        skills_by_category = {}
        
        for skill in skills:
            category = skill.category
            if category not in skills_by_category:
                skills_by_category[category] = []
            skills_by_category[category].append(skill)
        
        return skills_by_category
    
    def _generate_questions_for_category(self, category_name: str, 
                                       skills: List[ExtractedSkill], 
                                       input_scenario: InputScenario) -> List[TechnicalQuestion]:
        """Generate questions for a specific category of skills."""
        
        # Prepare skills context for the LLM
        skills_context = []
        for skill in skills:
            skill_info = {
                "name": skill.skill_name,
                "experience_level": skill.experience_level,
                "confidence": skill.confidence_score,
                "evidence": skill.evidence_from_text,
                "context": skill.context,
                "technologies": skill.specific_technologies
            }
            skills_context.append(skill_info)
        
        system_prompt = f"""You are an expert technical interviewer specializing in {category_name}. 
        Your goal is to create DEEP, NON-GENERIC technical questions that test true understanding.
        
        CORE PRINCIPLES:
        1. Questions must be SPECIFIC to the candidate's experience, not generic
        2. Test mathematical foundations, implementation details, and optimization knowledge
        3. Mix different question types for comprehensive assessment
        4. Difficulty should match the candidate's demonstrated experience level
        5. Each question should have a clear rationale based on the evidence
        
        QUESTION TYPES TO MIX:
        - Mathematical foundations (derive formulas, explain algorithms)
        - Implementation details (how to build from scratch, optimize)
        - System design and scaling challenges
        - Edge cases and debugging scenarios
        - Best practices and theoretical concepts
        
        AVOID:
        - Generic questions that could apply to any candidate
        - Simple "what is X" questions
        - Questions that test only memorization
        - Basic syntax or tool usage questions"""
        
        human_prompt = f"""
        Generate deep technical interview questions for the {category_name} category.
        
        CANDIDATE'S SKILLS IN THIS CATEGORY:
        {json.dumps(skills_context, indent=2)}
        
        INPUT SCENARIO: {input_scenario.value}
        
        REQUIREMENTS:
        1. Generate 2-3 questions per skill (if skill has high confidence/importance)
        2. Questions must be tailored to the candidate's specific experience and evidence
        3. Mix question types to test different aspects of knowledge
        4. Include specific technical details from their background
        5. Ensure each question tests DEEP understanding, not surface knowledge
        
        OUTPUT FORMAT (JSON):
        {{
            "questions": [
                {{
                    "question_id": "unique_id",
                    "question_text": "detailed technical question",
                    "question_type": "mathematical_foundation|implementation_details|optimization_scaling|edge_cases_debugging|system_design|best_practices|theoretical_concepts",
                    "difficulty_level": 1-5,
                    "estimated_time_minutes": 5-15,
                    "targeted_skill": "specific skill name",
                    "rationale": "why this question for this candidate based on their evidence",
                    "tags": ["relevant", "technical", "tags"]
                }}
            ]
        }}
        
        EXAMPLES OF GOOD DEEP QUESTIONS:
        - "Given your experience with Spring Boot microservices handling 10K+ requests/second, explain how Spring's auto-configuration affects startup time and memory usage. How would you optimize the bean creation process for faster startup?"
        - "You mentioned optimizing JVM performance. Derive the mathematical relationship between heap size, GC frequency, and application throughput. How would you tune G1GC for your specific workload?"
        - "Based on your Redis caching implementation, explain the memory complexity of different Redis data structures. How would you handle cache stampede in a distributed environment?"
        
        Make each question specific to their experience and test deep technical understanding!
        """
        
        try:
            response = self.llm.invoke([
                SystemMessage(content=system_prompt),
                HumanMessage(content=human_prompt)
            ])
            
            return response.questions
        except Exception as e:
            # Fallback: generate basic questions if LLM fails
            fallback_questions = self._generate_fallback_questions(skills, category_name)
            return fallback_questions
    
    def _generate_fallback_questions(self, skills: List[ExtractedSkill], category: str) -> List[TechnicalQuestion]:
        """Generate fallback questions if LLM generation fails."""
        fallback_questions = []
        
        for i, skill in enumerate(skills[:3]):  # Max 3 skills for fallback
            question_id = f"{category}_FALLBACK_{i+1}"
            
            question = TechnicalQuestion(
                question_id=question_id,
                question_text=f"Explain the core technical principles underlying {skill.skill_name}. "
                             f"Based on your experience with {skill.context}, how would you optimize performance and handle edge cases?",
                question_type=QuestionType.IMPLEMENTATION_DETAILS,
                difficulty_level=min(skill.confidence_score, 4),
                estimated_time_minutes=10,
                targeted_skill=skill.skill_name,
                rationale=f"Fallback question to test understanding of {skill.skill_name} based on evidence: {skill.evidence_from_text[:100]}",
                tags=[skill.skill_name.lower().replace(" ", "_")]
            )
            fallback_questions.append(question)
        
        return fallback_questions

# Enhanced question generation with specific strategies for common categories
class SpecializedQuestionGenerators:
    """Specialized question generation strategies for specific technical categories."""
    
    @staticmethod
    def generate_programming_language_questions(skills: List[ExtractedSkill], llm) -> List[TechnicalQuestion]:
        """Generate deep questions for programming languages."""
        
        # Get the most confident programming language skill
        lang_skill = max(skills, key=lambda s: s.confidence_score)
        
        system_prompt = f"""Generate deep technical questions for {lang_skill.skill_name} programming.
        Focus on language internals, memory management, performance optimization, and advanced concepts."""
        
        human_prompt = f"""
        The candidate has {lang_skill.experience_level} level experience with {lang_skill.skill_name}.
        Evidence: {lang_skill.evidence_from_text}
        Context: {lang_skill.context}
        
        Generate 2-3 DEEP technical questions that test:
        1. Language internals and memory model
        2. Performance optimization and concurrency
        3. Advanced language features and edge cases
        
        Make questions specific to their experience level and context.
        """
        
        # Implementation would follow similar pattern to main agent
        pass
    
    @staticmethod
    def generate_database_questions(skills: List[ExtractedSkill], llm) -> List[TechnicalQuestion]:
        """Generate deep database-specific questions."""
        pass
    
    @staticmethod 
    def generate_ml_ai_questions(skills: List[ExtractedSkill], llm) -> List[TechnicalQuestion]:
        """Generate deep ML/AI specific questions."""
        pass

# Testing the Question Generation Agent
def test_question_generation_agent():
    """Test the question generation agent."""
    
    print("🧪 Testing Question Generation Agent")
    print("=" * 45)
    
    # Create sample extracted skills (as if from SkillExtractionAgent)
    sample_skills = [
        ExtractedSkill(
            skill_name="Java Spring Boot",
            category="Backend Development",
            evidence_from_text="5+ years developing microservices with Spring Boot handling 10K+ requests/second",
            experience_level="Advanced",
            confidence_score=5,
            context="High-performance microservices development",
            specific_technologies=["Spring Boot", "Spring Cloud", "Maven"]
        ),
        ExtractedSkill(
            skill_name="PostgreSQL",
            category="Database Systems",
            evidence_from_text="Experience with PostgreSQL optimization and query tuning",
            experience_level="Intermediate",
            confidence_score=4,
            context="Database optimization for high-traffic applications",
            specific_technologies=["PostgreSQL", "SQL", "Database Tuning"]
        ),
        ExtractedSkill(
            skill_name="Redis",
            category="Caching & Performance",
            evidence_from_text="Implemented caching solutions using Redis",
            experience_level="Intermediate", 
            confidence_score=3,
            context="Performance optimization through caching",
            specific_technologies=["Redis", "Caching", "Performance"]
        )
    ]
    
    # Create LLM config
    llm_config = LLMConfig(
        provider=LLMProvider.OPENAI,
        model="gpt-4",
        temperature=0.1
    )
    
    # Create state with extracted skills
    state = create_initial_state(
        resume_text="Sample resume",
        position_title="Senior Java Developer",
        llm_provider=llm_config.provider,
        llm_model=llm_config.model
    )
    
    # Simulate skills extraction results
    state["extracted_skills"] = sample_skills
    state["processing_stage"] = ProcessingStage.SKILLS_EXTRACTED
    
    # Create and execute agent
    agent = QuestionGenerationAgent(llm_config)
    
    try:
        result_state = agent.execute(state)
        
        if result_state["processing_stage"] == ProcessingStage.QUESTIONS_GENERATED:
            print("✅ Question generation successful!")
            
            questions = result_state["generated_questions"]
            print(f"📊 Generated {len(questions)} technical questions")
            
            print("\n🔥 Sample Deep Technical Questions:")
            for i, question in enumerate(questions[:3], 1):  # Show first 3
                print(f"\n{i}. QUESTION ID: {question.question_id}")
                print(f"   TARGET SKILL: {question.targeted_skill}")
                print(f"   TYPE: {question.question_type}")
                print(f"   DIFFICULTY: {question.difficulty_level}/5")
                print(f"   TIME: {question.estimated_time_minutes} minutes")
                print(f"   QUESTION: {question.question_text}")
                print(f"   RATIONALE: {question.rationale}")
                print(f"   TAGS: {', '.join(question.tags)}")
            
            print(f"\n💬 Agent Message: {result_state['messages'][-1].content}")
            
        else:
            print("❌ Question generation failed")
            for error in result_state["errors"]:
                print(f"  Error: {error}")
    
    except Exception as e:
        print(f"❌ Test failed: {e}")

if __name__ == "__main__":
    test_question_generation_agent()