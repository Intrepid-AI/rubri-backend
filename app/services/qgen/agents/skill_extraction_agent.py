import json
import time
from typing import List, Optional, TYPE_CHECKING
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from app.services.qgen.agents.base_agent import BaseAgent
from app.services.qgen.models.schemas import (
    ExtractedSkill, SkillCategory, ProcessingStage, 
    MultiAgentInterviewState, LLMConfig, InputScenario, create_initial_state, LLMProvider, SkillExtractionOutput
)
from app.logger import get_logger

if TYPE_CHECKING:
    from app.services.qgen.streaming.stream_manager import StreamManager

class SkillExtractionAgent(BaseAgent):
    """
    Agent 1: Extracts technical skills from resume and/or job description using LLM.
    
    Responsibilities:
    - Identify all technical skills mentioned in the text
    - Determine experience levels and confidence scores
    - Categorize skills into logical groups
    - Extract context and evidence for each skill
    """
    
    def __init__(self, llm_config: LLMConfig, stream_manager: Optional['StreamManager'] = None):
        super().__init__("SkillExtractionAgent", llm_config, 
                        structured_output_model=SkillExtractionOutput,
                        stream_manager=stream_manager)
    
    def execute(self, state: MultiAgentInterviewState) -> MultiAgentInterviewState:
        """Execute skill extraction from resume and/or job description."""
        self.logger.info("Starting skill extraction process")
        start_time = time.time()
        
        # Emit streaming start event
        self.stream_start_sync("Analyzing documents to extract technical skills...")
        
        try:
            # Extract skills based on input scenario
            scenario = state["input_scenario"]
            
            # Emit thinking event
            scenario_msg = {
                InputScenario.RESUME_ONLY: "Analyzing resume for technical skills...",
                InputScenario.JD_ONLY: "Analyzing job description for required skills...",
                InputScenario.BOTH: "Analyzing both resume and job description to identify skill matches and gaps..."
            }
            self.stream_thinking_sync(scenario_msg.get(scenario, "Processing documents..."))
            
            if scenario == InputScenario.RESUME_ONLY:
                results = self._extract_from_resume(state["resume_text"], state["position_title"])
            elif scenario == InputScenario.JD_ONLY:
                results = self._extract_from_job_description(state["job_description"], state["position_title"])
            else:  # BOTH
                results = self._extract_from_both(
                    state["resume_text"], 
                    state["job_description"], 
                    state["position_title"]
                )
            
            # Update state with extracted skills
            skills_count = len(results["skills"])
            categories_count = len(results["categories"])
            
            # Stream extracted skills
            if self.stream_manager:
                self.stream_thinking_sync(f"Found {skills_count} skills across {categories_count} categories")
                
                # Emit skill found events for each skill
                for i, skill in enumerate(results["skills"]):
                    # Use synchronous streaming
                    self.stream_manager.emit_skill_found_sync({
                        "skill_name": skill.skill_name,
                        "category": skill.category,
                        "experience_level": skill.experience_level,
                        "confidence_score": skill.confidence_score,
                        "skill_index": i + 1,
                        "total_skills": skills_count
                    })
            
            state["extracted_skills"] = results["skills"]
            state["skill_categories"] = results["categories"]
            state["processing_stage"] = ProcessingStage.SKILLS_EXTRACTED
            
            # Record success
            execution_time = time.time() - start_time
            self._record_result(
                state, 
                success=True, 
                output_data={
                    "skills_count": skills_count,
                    "categories_count": categories_count
                },
                execution_time=execution_time
            )
            
            self.logger.info(f"Skill extraction completed: {skills_count} skills, {categories_count} categories ({execution_time:.2f}s)")
            
            # Add summary message
            state["messages"].append(AIMessage(
                content=f"✅ Skill extraction completed. Found {skills_count} technical skills "
                        f"across {categories_count} categories. Processing time: {execution_time:.2f}s"
            ))
            
        except Exception as e:
            execution_time = time.time() - start_time
            error_msg = f"Skill extraction failed: {str(e)}"
            self.logger.error(f"Skill extraction failed ({execution_time:.2f}s): {str(e)}")
            
            state["errors"].append(error_msg)
            state["processing_stage"] = ProcessingStage.ERROR
            
            self._record_result(
                state, 
                success=False, 
                error_message=error_msg,
                execution_time=execution_time
            )
        
        return state
    
    def _extract_from_resume(self, resume_text: str, position_title: str) -> dict:
        """Extract skills from resume only."""
        
        system_prompt = """You are an expert technical recruiter and skill extraction specialist. 
        Your task is to analyze a resume and extract ALL technical skills with high accuracy.
        
        Focus on:
        - Programming languages, frameworks, libraries
        - Databases, cloud platforms, tools
        - Methodologies, algorithms, technical concepts
        - Specific technologies and versions mentioned
        
        For each skill, determine:
        - Experience level based on context clues
        - Confidence in the assessment
        - Specific evidence from the text
        - Work/project context where it was used"""
        
        human_prompt = f"""
        Analyze this resume for the position of "{position_title}" and extract ALL technical skills.
        
        RESUME:
        {resume_text}
        
        Provide a comprehensive analysis in the following JSON format:
        
        {{
            "skills": [
                {{
                    "skill_name": "exact skill name",
                    "category": "logical category (e.g., Programming Languages, Backend Frameworks, Databases, Cloud Platforms, etc.)",
                    "evidence_from_text": "exact text snippet where mentioned",
                    "experience_level": "Beginner/Intermediate/Advanced/Expert",
                    "confidence_score": 1-5,
                    "context": "work/project context where used",
                    "years_of_experience": "if mentioned explicitly",
                    "specific_technologies": ["related tools/versions"]
                }}
            ],
            "categories": [
                {{
                    "name": "category name",
                    "description": "what this category covers",
                    "priority": 1-5
                }}
            ]
        }}
        
        IMPORTANT:
        - Extract EVERY technical skill mentioned, even if briefly
        - Infer experience levels from context (project complexity, role seniority, achievements)
        - High confidence (4-5) only for skills with clear evidence
        - Categories should be comprehensive and logical
        - Priority 1 = most important for the role
        """
        
        response = self.llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=human_prompt)
        ])
        
        return {"skills": response.skills, "categories": response.categories}
    
    def _extract_from_job_description(self, jd_text: str, position_title: str) -> dict:
        """Extract required skills from job description."""
        
        system_prompt = """You are an expert at analyzing job descriptions to identify required technical skills.
        Extract both explicit requirements and implicit skills needed for the role.
        
        Focus on:
        - Must-have vs nice-to-have skills
        - Technical depth required
        - Experience levels expected
        - Related technologies in the ecosystem"""
        
        human_prompt = f"""
        Analyze this job description for "{position_title}" and extract ALL required/preferred technical skills.
        
        JOB DESCRIPTION:
        {jd_text}
        
        Extract skills that candidates would need to have or learn for this role.
        
        Provide analysis in this JSON format:
        
        {{
            "skills": [
                {{
                    "skill_name": "exact skill name",
                    "category": "logical category",
                    "evidence_from_text": "where mentioned in JD",
                    "experience_level": "what level seems required",
                    "confidence_score": 1-5,
                    "context": "role context where needed",
                    "years_of_experience": "if specified",
                    "specific_technologies": ["related tools mentioned"]
                }}
            ],
            "categories": [
                {{
                    "name": "category name", 
                    "description": "what this category covers",
                    "priority": 1-5
                }}
            ]
        }}
        
        IMPORTANT:
        - Include both explicit and implicit skill requirements
        - Consider ecosystem technologies (e.g., if React mentioned, also consider JavaScript, CSS, etc.)
        - Confidence based on how explicitly the skill is mentioned
        - Experience level based on role seniority and requirements
        """
        
        response = self.llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=human_prompt)
        ])
        
        return {"skills": response.skills, "categories": response.categories}
    
    def _extract_from_both(self, resume_text: str, jd_text: str, position_title: str) -> dict:
        """Extract skills from both resume and job description, finding matches and gaps."""
        
        system_prompt = """You are analyzing both a candidate's resume and a job description to create 
        a comprehensive skill assessment. Identify:
        
        1. Skills the candidate HAS (from resume)
        2. Skills the role NEEDS (from JD)  
        3. MATCHES where candidate skills align with requirements
        4. GAPS where role needs skills not evidenced in resume
        5. ADDITIONAL skills candidate has beyond role requirements
        
        This analysis will drive targeted interview questions."""
        
        human_prompt = f"""
        Analyze this resume against the job requirements for "{position_title}".
        
        RESUME:
        {resume_text}
        
        JOB DESCRIPTION:
        {jd_text}
        
        Provide comprehensive skill extraction and analysis:
        
        {{
            "skills": [
                {{
                    "skill_name": "exact skill name",
                    "category": "logical category",
                    "evidence_from_text": "where found (resume/JD/both)",
                    "experience_level": "candidate's level OR required level",
                    "confidence_score": 1-5,
                    "context": "context from resume/JD",
                    "years_of_experience": "if mentioned",
                    "specific_technologies": ["related tools"],
                    "skill_status": "MATCH/GAP/ADDITIONAL",
                    "priority_for_interview": 1-5
                }}
            ],
            "categories": [
                {{
                    "name": "category name",
                    "description": "what this covers", 
                    "priority": 1-5
                }}
            ]
        }}
        
        SKILL_STATUS definitions:
        - MATCH: Candidate has skill that role requires
        - GAP: Role requires skill not evidenced in resume  
        - ADDITIONAL: Candidate has skill beyond role requirements
        
        PRIORITY_FOR_INTERVIEW:
        - 5: Critical skill, must assess deeply
        - 4: Important skill, good to assess
        - 3: Relevant skill, assess if time permits
        - 2: Nice to know
        - 1: Not essential for this role
        
        Focus on skills that need deep technical assessment during interview.
        """
        
        response = self.llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=human_prompt)
        ])
        
        return {"skills": response.skills, "categories": response.categories}
    
    def _parse_extraction_response(self, response_content: str) -> dict:
        # This method is no longer needed with structured output, so it can be removed or left as a stub.
        return {}

# Testing the Skill Extraction Agent
def test_skill_extraction_agent():
    """Test the skill extraction agent with sample data."""
    
    print("🧪 Testing Skill Extraction Agent")
    print("=" * 40)
    
    # Sample Java developer resume
    java_resume = """
    Rajesh Kumar
    Senior Java Developer
    
    Experience:
    • 5+ years developing microservices with Spring Boot and Spring Cloud
    • Built high-performance REST APIs handling 10K+ requests/second
    • Implemented caching solutions using Redis and optimized JVM performance
    • Experience with PostgreSQL, MongoDB, and Elasticsearch
    • Deployed applications on AWS using Docker and Kubernetes
    • Proficient in Maven, Gradle, Jenkins CI/CD pipelines
    
    Technical Skills:
    Java 8/11/17, Spring Framework, Hibernate, Apache Kafka, 
    PostgreSQL, Redis, Docker, Kubernetes, AWS (EC2, S3, RDS)
    """
    
    # Create LLM config (you can test with different providers)
    llm_config = LLMConfig(
        provider=LLMProvider.OPENAI,  # or LLMProvider.ANTHROPIC
        model="gpt-4",  # or "claude-3-sonnet"
        temperature=0.1
    )
    
    # Create initial state
    state = create_initial_state(
        resume_text=java_resume,
        position_title="Senior Java Developer",
        llm_provider=llm_config.provider,
        llm_model=llm_config.model
    )
    
    # Create and execute agent (without streaming for test)
    agent = SkillExtractionAgent(llm_config, stream_manager=None)
    
    try:
        result_state = agent.execute(state)
        
        if result_state["processing_stage"] == ProcessingStage.SKILLS_EXTRACTED:
            print("✅ Skill extraction successful!")
            
            skills = result_state["extracted_skills"]
            categories = result_state["skill_categories"]
            
            print(f"📊 Extracted {len(skills)} skills across {len(categories)} categories")
            
            print("\n🏷️ Categories:")
            for cat in categories:
                print(f"  • {cat.name} (Priority: {cat.priority}) - {cat.description}")
            
            print("\n🔧 Sample Skills:")
            for skill in skills[:5]:  # Show first 5 skills
                print(f"  • {skill.skill_name} ({skill.category})")
                print(f"    Level: {skill.experience_level}, Confidence: {skill.confidence_score}/5")
                print(f"    Evidence: {skill.evidence_from_text[:60]}...")
                print()
            
            print(f"💬 Agent Message: {result_state['messages'][-1].content}")
            
        else:
            print("❌ Skill extraction failed")
            for error in result_state["errors"]:
                print(f"  Error: {error}")
    
    except Exception as e:
        print(f"❌ Test failed: {e}")

if __name__ == "__main__":
    test_skill_extraction_agent()