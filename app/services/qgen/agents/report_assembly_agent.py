import time
from typing import List, Dict, Optional
from datetime import datetime
from langchain_core.messages import AIMessage
from app.services.qgen.agents.base_agent import BaseAgent
from app.services.qgen.models.schemas import (
    SkillAssessment, InterviewSection, CandidateEvaluation,
    TechnicalQuestion, ExpectedResponse, ExtractedSkill, SkillCategory,
    QuestionEvaluation, ProcessingStage, MultiAgentInterviewState, LLMConfig,
    InputScenario, LLMProvider, QuestionType, create_initial_state, ScoringRubric
)
from app.logger import get_logger


class ReportAssemblyAgent(BaseAgent):
    """
    Agent 5: Assembles all components into the final comprehensive interview evaluation report.
    
    Responsibilities:
    - Group approved questions and responses by skill categories
    - Create structured interview sections
    - Generate overall candidate evaluation
    - Format everything into the final report structure
    - Provide executive summary and recommendations
    """
    
    def __init__(self, llm_config: LLMConfig):
        super().__init__("ReportAssemblyAgent", llm_config)
    
    def execute(self, state: MultiAgentInterviewState) -> MultiAgentInterviewState:
        """Assemble final comprehensive interview evaluation report."""
        self.logger.info("Starting report assembly process")
        start_time = time.time()
        
        try:
            approved_questions = state["approved_questions"]
            expected_responses = state["expected_responses"]
            extracted_skills = state["extracted_skills"]
            skill_categories = state["skill_categories"]
            question_evaluations = state["question_evaluations"]
            
            if not approved_questions or not expected_responses:
                error_msg = "Missing approved questions or expected responses. Run previous agents first."
                self.logger.error(error_msg)
                raise Exception(error_msg)
            
            # Create skill assessments
            skill_assessments = self._create_skill_assessments(
                approved_questions, expected_responses, extracted_skills, question_evaluations
            )
            
            # Create interview sections
            interview_sections = self._create_interview_sections(skill_assessments, skill_categories)
            
            # Generate overall candidate evaluation
            candidate_evaluation = self._generate_candidate_evaluation(
                interview_sections, extracted_skills, state
            )
            # Update state
            state["skill_assessments"] = skill_assessments
            state["interview_sections"] = interview_sections
            state["final_evaluation"] = candidate_evaluation
            state["processing_stage"] = ProcessingStage.REPORT_ASSEMBLED
            
            # Record success
            execution_time = time.time() - start_time
            self._record_result(
                state,
                success=True,
                output_data={
                    "skill_assessments": len(skill_assessments),
                    "interview_sections": len(interview_sections),
                    "total_questions": candidate_evaluation.total_questions,
                    "estimated_duration": candidate_evaluation.estimated_interview_duration
                },
                execution_time=execution_time
            )
            
            self.logger.info(f"Report assembly completed: {candidate_evaluation.total_questions} questions, {candidate_evaluation.estimated_interview_duration} min ({execution_time:.2f}s)")
            
            # Add completion message
            state["messages"].append(AIMessage(
                content=f"✅ Report assembly completed! Generated comprehensive interview evaluation with "
                        f"{len(interview_sections)} sections, {candidate_evaluation.total_questions} questions, "
                        f"estimated duration: {candidate_evaluation.estimated_interview_duration} minutes. "
                        f"Processing time: {execution_time:.2f}s"
            ))
            
            # Set final processing stage
            state["processing_stage"] = ProcessingStage.COMPLETED
            
        except Exception as e:
            execution_time = time.time() - start_time
            error_msg = f"Report assembly failed: {str(e)}"
            self.logger.error(f"Report assembly failed ({execution_time:.2f}s): {str(e)}")
            
            state["errors"].append(error_msg)
            state["processing_stage"] = ProcessingStage.ERROR
            
            self._record_result(
                state,
                success=False,
                error_message=error_msg,
                execution_time=execution_time
            )
        
        return state
    
    def _create_skill_assessments(self, approved_questions: List[TechnicalQuestion],
                                expected_responses: List[ExpectedResponse],
                                extracted_skills: List[ExtractedSkill],
                                question_evaluations: List[QuestionEvaluation]) -> List[SkillAssessment]:
        """Create skill assessments by combining questions, responses, and evaluations."""
        
        skill_assessments = []
        
        # Group by targeted skill
        skills_data = {}
        
        for question in approved_questions:
            skill_name = question.targeted_skill
            if skill_name not in skills_data:
                skills_data[skill_name] = {
                    "questions": [],
                    "responses": [],
                    "evaluations": [],
                    "extracted_skill": None
                }
            
            skills_data[skill_name]["questions"].append(question)
            
            # Find corresponding response and evaluation
            response = next((r for r in expected_responses if r.question_id == question.question_id), None)
            if response:
                skills_data[skill_name]["responses"].append(response)
            
            evaluation = next((e for e in question_evaluations if e.question_id == question.question_id), None)
            if evaluation:
                skills_data[skill_name]["evaluations"].append(evaluation)
            
            # Find extracted skill
            if not skills_data[skill_name]["extracted_skill"]:
                extracted_skill = next((s for s in extracted_skills if s.skill_name == skill_name), None)
                skills_data[skill_name]["extracted_skill"] = extracted_skill
        
        # Create SkillAssessment objects
        for skill_name, data in skills_data.items():
            if data["extracted_skill"]:  # Only create assessment if we have the extracted skill
                assessment = SkillAssessment(
                    skill_name=skill_name,
                    category=data["extracted_skill"].category,
                    extracted_skill=data["extracted_skill"],
                    questions=data["questions"],
                    question_evaluations=data["evaluations"],
                    expected_responses=data["responses"],
                    overall_assessment=self._generate_skill_assessment_summary(data)
                )
                skill_assessments.append(assessment)
        
        return skill_assessments
    
    def _generate_skill_assessment_summary(self, skill_data: Dict) -> str:
        """Generate summary for a skill assessment."""
        skill = skill_data["extracted_skill"]
        questions = skill_data["questions"]
        evaluations = skill_data["evaluations"]
        
        avg_quality = sum(e.overall_quality for e in evaluations) / len(evaluations) if evaluations else 0
        question_types = list(set(q.question_type for q in questions))
        
        summary = f"Assessment covers {len(questions)} deep technical questions targeting {skill.skill_name} "
        summary += f"({skill.experience_level} level, confidence: {skill.confidence_score}/5). "
        summary += f"Questions focus on: {', '.join([qt.value.replace('_', ' ') for qt in question_types])}. "
        summary += f"Average question quality: {avg_quality:.1f}/5."
        
        return summary
    
    def _create_interview_sections(self, skill_assessments: List[SkillAssessment],
                                 skill_categories: List[SkillCategory]) -> List[InterviewSection]:
        """Create interview sections by grouping skill assessments by category."""
        
        # Group assessments by category
        category_groups = {}
        for assessment in skill_assessments:
            category = assessment.category
            if category not in category_groups:
                category_groups[category] = []
            category_groups[category].append(assessment)
        
        # Create interview sections
        sections = []
        section_id = 1
        
        # Sort categories by priority
        sorted_categories = sorted(skill_categories, key=lambda c: c.priority)
        
        for category in sorted_categories:
            if category.name in category_groups:
                assessments = category_groups[category.name]
                
                # Calculate total time for this section
                total_time = sum(
                    sum(q.estimated_time_minutes for q in assessment.questions)
                    for assessment in assessments
                )
                
                section = InterviewSection(
                    section_id=f"section_{section_id}",
                    section_name=category.name,
                    description=category.description,
                    skill_assessments=assessments,
                    estimated_total_time=total_time,
                    priority=category.priority
                )
                sections.append(section)
                section_id += 1
        
        return sections
    
    def _generate_candidate_evaluation(self, interview_sections: List[InterviewSection],
                                     extracted_skills: List[ExtractedSkill],
                                     state: MultiAgentInterviewState) -> CandidateEvaluation:
        """Generate overall candidate evaluation."""
        
        # Extract candidate name from resume if available
        candidate_name = self._extract_candidate_name(state.get("resume_text", ""))
        
        # Calculate totals
        total_questions = sum(
            len(assessment.questions) 
            for section in interview_sections 
            for assessment in section.skill_assessments
        )
        
        total_duration = sum(section.estimated_total_time for section in interview_sections)
        
        # Generate insights
        key_strengths = self._identify_key_strengths(extracted_skills, interview_sections)
        potential_concerns = self._identify_potential_concerns(extracted_skills, interview_sections)
        focus_areas = self._recommend_focus_areas(interview_sections)
        overall_recommendation = self._generate_overall_recommendation(
            extracted_skills, interview_sections, state["input_scenario"]
        )
        
        # Create skill categories summary
        categories_summary = []
        for section in interview_sections:
            category = SkillCategory(
                name=section.section_name,
                description=section.description,
                priority=section.priority
            )
            categories_summary.append(category)
        
        evaluation = CandidateEvaluation(
            candidate_name=candidate_name,
            position_title=state["position_title"],
            evaluation_date=datetime.now(),
            input_scenario=state["input_scenario"],
            total_skills_identified=len(extracted_skills),
            skill_categories=categories_summary,
            interview_sections=interview_sections,
            total_questions=total_questions,
            estimated_interview_duration=total_duration,
            key_strengths=key_strengths,
            potential_concerns=potential_concerns,
            recommended_focus_areas=focus_areas,
            overall_recommendation=overall_recommendation
        )
        
        return evaluation
    
    def _extract_candidate_name(self, resume_text: str) -> Optional[str]:
        """Extract candidate name from resume text."""
        if not resume_text:
            return None
        
        lines = resume_text.split('\n')[:5]  # Check first 5 lines
        
        for line in lines:
            line = line.strip()
            if not line or len(line) < 3:
                continue
            
            # Simple heuristic: if line has 2-3 words and looks like a name
            words = line.split()
            if 2 <= len(words) <= 3 and all(word.isalpha() for word in words):
                # Check if it's likely a name (title case, reasonable length)
                if all(word[0].isupper() for word in words) and len(line) <= 50:
                    return line
        
        return None
    
    def _identify_key_strengths(self, extracted_skills: List[ExtractedSkill],
                              interview_sections: List[InterviewSection]) -> List[str]:
        """Identify candidate's key technical strengths."""
        strengths = []
        
        # High confidence skills
        high_confidence_skills = [s for s in extracted_skills if s.confidence_score >= 4]
        if high_confidence_skills:
            top_skills = sorted(high_confidence_skills, key=lambda s: s.confidence_score, reverse=True)[:3]
            for skill in top_skills:
                strengths.append(f"Strong evidence of {skill.skill_name} expertise ({skill.experience_level} level)")
        
        # Breadth of skills
        total_categories = len(set(s.category for s in extracted_skills))
        if total_categories >= 3:
            strengths.append(f"Broad technical expertise across {total_categories} different categories")
        
        # Advanced experience levels
        advanced_skills = [s for s in extracted_skills if s.experience_level in ["Advanced", "Expert"]]
        if len(advanced_skills) >= 2:
            strengths.append(f"Advanced proficiency in multiple areas: {', '.join(s.skill_name for s in advanced_skills[:3])}")
        
        # High-quality questions generated
        high_quality_sections = [s for s in interview_sections if s.priority <= 2]
        if high_quality_sections:
            strengths.append("Sufficient experience depth to warrant comprehensive technical assessment")
        
        return strengths[:4]  # Limit to top 4 strengths
    
    def _identify_potential_concerns(self, extracted_skills: List[ExtractedSkill],
                                   interview_sections: List[InterviewSection]) -> List[str]:
        """Identify potential areas of concern."""
        concerns = []
        
        # Low confidence skills
        low_confidence_skills = [s for s in extracted_skills if s.confidence_score <= 2]
        if low_confidence_skills:
            concerns.append(f"Limited evidence for {len(low_confidence_skills)} mentioned skills")
        
        # Skills with beginner level
        beginner_skills = [s for s in extracted_skills if s.experience_level == "Beginner"]
        if len(beginner_skills) >= 2:
            concerns.append(f"Several skills at beginner level: {', '.join(s.skill_name for s in beginner_skills[:3])}")
        
        # Missing high-priority categories (this would be role-specific)
        if len(interview_sections) < 2:
            concerns.append("Limited technical breadth - few skill categories identified")
        
        # Few questions generated (indicates shallow experience)
        total_questions = sum(len(assessment.questions) for section in interview_sections for assessment in section.skill_assessments)
        if total_questions < 5:
            concerns.append("Limited depth of experience may result in fewer technical questions")
        
        return concerns[:4]  # Limit to top 4 concerns
    
    def _recommend_focus_areas(self, interview_sections: List[InterviewSection]) -> List[str]:
        """Recommend which areas to focus on during the interview."""
        focus_areas = []
        
        # High priority sections - FIX: Convert to list explicitly
        high_priority = sorted(list(interview_sections), key=lambda s: s.priority)[:2]
        for section in high_priority:
            focus_areas.append(f"Prioritize {section.section_name} assessment - {len(sum([a.questions for a in section.skill_assessments], []))} targeted questions available")
        
        # Sections with most questions - FIX: Ensure proper sorting
        question_counts = [(len(sum([a.questions for a in section.skill_assessments], [])), section) for section in interview_sections]
        # Sort by count (first element of tuple) only, not by section - this prevents comparison of InterviewSection objects
        top_question_sections = sorted(question_counts, key=lambda x: x[0], reverse=True)[:2]
        
        for count, section in top_question_sections:
            if count >= 3:  # Only mention if substantial
                focus_areas.append(f"Deep dive into {section.section_name} - candidate shows strong evidence")
        
        # Time management
        total_time = sum(section.estimated_total_time for section in interview_sections)
        if total_time > 60:
            focus_areas.append(f"Consider time management - full assessment estimated at {total_time} minutes")
        
        return list(set(focus_areas))[:4]  # Remove duplicates and limit
    
    def _generate_overall_recommendation(self, extracted_skills: List[ExtractedSkill],
                                       interview_sections: List[InterviewSection],
                                       input_scenario: InputScenario) -> str:
        """Generate overall hiring recommendation."""
        
        # Calculate strength metrics
        high_confidence_count = len([s for s in extracted_skills if s.confidence_score >= 4])
        advanced_skills_count = len([s for s in extracted_skills if s.experience_level in ["Advanced", "Expert"]])
        total_categories = len(set(s.category for s in extracted_skills))
        total_questions = sum(len(assessment.questions) for section in interview_sections for assessment in section.skill_assessments)
        
        # Scoring logic
        strength_score = 0
        if high_confidence_count >= 3:
            strength_score += 2
        elif high_confidence_count >= 1:
            strength_score += 1
        
        if advanced_skills_count >= 2:
            strength_score += 2
        elif advanced_skills_count >= 1:
            strength_score += 1
        
        if total_categories >= 4:
            strength_score += 2
        elif total_categories >= 2:
            strength_score += 1
        
        if total_questions >= 8:
            strength_score += 1
        
        # Generate recommendation based on scenario and strength
        if input_scenario == InputScenario.BOTH:
            scenario_context = "Strong alignment between candidate skills and role requirements. "
        elif input_scenario == InputScenario.RESUME_ONLY:
            scenario_context = "Assessment based on candidate's demonstrated experience. "
        else:  # JD_ONLY
            scenario_context = "Assessment covers all role requirements. "
        
        if strength_score >= 6:
            recommendation = scenario_context + "Highly recommended - demonstrates deep technical expertise across multiple areas. Proceed with confidence to technical interview."
        elif strength_score >= 4:
            recommendation = scenario_context + "Recommended - shows solid technical foundation. Good candidate for technical interview with focus on identified strength areas."
        elif strength_score >= 2:
            recommendation = scenario_context + "Conditionally recommended - adequate technical background but may need focused assessment in key areas."
        else:
            recommendation = scenario_context + "Requires careful evaluation - limited evidence of deep technical expertise. Consider preliminary screening."
        
        return recommendation

# Final report formatting
def format_final_report(evaluation: CandidateEvaluation) -> str:
    """Format the complete evaluation into a comprehensive report."""
    
    report_lines = []
    
    # Header
    report_lines.append(f"# Technical Interview Evaluation: {evaluation.candidate_name or 'Candidate'}")
    report_lines.append(f"**Position:** {evaluation.position_title}")
    report_lines.append(f"**Evaluation Date:** {evaluation.evaluation_date.strftime('%Y-%m-%d')}")
    report_lines.append(f"**Input Scenario:** {evaluation.input_scenario.value}")
    report_lines.append("")
    
    # Executive Summary
    report_lines.append("## Executive Summary")
    report_lines.append("")
    report_lines.append(f"**Skills Identified:** {evaluation.total_skills_identified}")
    report_lines.append(f"**Categories Covered:** {len(evaluation.skill_categories)}")
    report_lines.append(f"**Technical Questions Generated:** {evaluation.total_questions}")
    report_lines.append(f"**Estimated Interview Duration:** {evaluation.estimated_interview_duration} minutes")
    report_lines.append("")
    report_lines.append(f"**Overall Recommendation:** {evaluation.overall_recommendation}")
    report_lines.append("")
    
    # Key Insights
    report_lines.append("## Key Insights")
    report_lines.append("")
    
    report_lines.append("### Strengths")
    for strength in evaluation.key_strengths:
        report_lines.append(f"- {strength}")
    report_lines.append("")
    
    if evaluation.potential_concerns:
        report_lines.append("### Areas for Assessment")
        for concern in evaluation.potential_concerns:
            report_lines.append(f"- {concern}")
        report_lines.append("")
    
    report_lines.append("### Recommended Focus Areas")
    for focus in evaluation.recommended_focus_areas:
        report_lines.append(f"- {focus}")
    report_lines.append("")
    
    # Detailed Technical Sections
    for i, section in enumerate(evaluation.interview_sections, 1):
        report_lines.append(f"## Section {i}: {section.section_name}")
        report_lines.append(f"*{section.description}*")
        report_lines.append(f"**Estimated Time:** {section.estimated_total_time} minutes")
        report_lines.append("")
        
        # Skills in this section
        for j, assessment in enumerate(section.skill_assessments, 1):
            report_lines.append(f"### {i}.{j} {assessment.skill_name}")
            report_lines.append("")
            
            # Skill context
            skill = assessment.extracted_skill
            report_lines.append(f"**Experience Level:** {skill.experience_level} (Confidence: {skill.confidence_score}/5)")
            report_lines.append(f"**Evidence:** {skill.evidence_from_text}")
            if skill.context:
                report_lines.append(f"**Context:** {skill.context}")
            report_lines.append("")
            
            # Questions
            report_lines.append("**Technical Questions:**")
            report_lines.append("")
            
            for k, question in enumerate(assessment.questions, 1):
                question_num = f"{i}.{j}.{k}"
                report_lines.append(f"**{question_num}. {question.question_text}**")
                
                # Find corresponding expected response
                expected_response = next((r for r in assessment.expected_responses if r.question_id == question.question_id), None)
                
                if expected_response:
                    report_lines.append(f"- **Question Type:** {question.question_type.value.replace('_', ' ').title()}")
                    report_lines.append(f"- **Difficulty Level:** {question.difficulty_level}/5")
                    report_lines.append(f"- **Estimated Time:** {question.estimated_time_minutes} minutes")
                    report_lines.append(f"- **Rationale:** {question.rationale}")
                    report_lines.append("")
                    
                    report_lines.append("**Expected Response Guidance:**")
                    report_lines.append("*Key Concepts Required:*")
                    for concept in expected_response.key_concepts_required:
                        report_lines.append(f"  - {concept}")
                    
                    report_lines.append("*Good Answer Indicators:*")
                    for indicator in expected_response.good_answer_indicators:
                        report_lines.append(f"  - {indicator}")
                    
                    report_lines.append("*Red Flags:*")
                    for flag in expected_response.red_flags:
                        report_lines.append(f"  - {flag}")
                    
                    report_lines.append("*Follow-up Questions:*")
                    for follow_up in expected_response.follow_up_questions:
                        report_lines.append(f"  - {follow_up}")
                    
                    report_lines.append("*Scoring Rubric:*")
                    for level, criteria in expected_response.scoring_rubric.model_dump().items():
                        clean_level = level.replace('_', ' ').title()
                        report_lines.append(f"  - {clean_level}: {criteria}")
                    
                    report_lines.append("")
                
                else:
                    report_lines.append(f"- **Rationale:** {question.rationale}")
                    report_lines.append("")
    
    return "\n".join(report_lines)

# Testing the Report Assembly Agent
def test_report_assembly_agent():
    """Test the complete report assembly agent."""
    
    print("🧪 Testing Report Assembly Agent")
    print("=" * 45)
    
    # This would typically use data from all previous agents
    # For testing, we'll create comprehensive sample data
    
    # Create LLM config
    llm_config = LLMConfig(
        provider=LLMProvider.OPENAI,
        model="gpt-4",
        temperature=0.1
    )
    
    # Create complete test state with all components
    state = create_initial_state(
        resume_text="John Smith - Senior Java Developer with Spring Boot and PostgreSQL experience",
        position_title="Senior Java Developer",
        llm_provider=llm_config.provider,
        llm_model=llm_config.model
    )
    
    # Add sample data (as if from previous agents)
    state["extracted_skills"] = [
        ExtractedSkill(
            skill_name="Java Spring Boot",
            category="Backend Development",
            evidence_from_text="Senior Java Developer with Spring Boot experience",
            experience_level="Advanced",
            confidence_score=5,
            context="Enterprise applications",
            specific_technologies=["Spring Boot", "Spring Cloud"]
        )
    ]
    
    state["skill_categories"] = [
        SkillCategory(name="Backend Development", description="Server-side development", priority=1)
    ]
    
    state["approved_questions"] = [
        TechnicalQuestion(
            question_id="JAVA_Q1",
            question_text="Explain Spring Boot auto-configuration mechanism and optimize startup time",
            question_type=QuestionType.OPTIMIZATION_SCALING,
            difficulty_level=4,
            estimated_time_minutes=12,
            targeted_skill="Java Spring Boot",
            rationale="Tests Spring internals",
            tags=["spring", "optimization"]
        )
    ]
    
    state["expected_responses"] = [
        ExpectedResponse(
            question_id="JAVA_Q1",
            key_concepts_required=["Auto-configuration", "Classpath scanning", "Conditional beans"],
            good_answer_indicators=["Mentions startup optimization", "Discusses lazy initialization"],
            red_flags=["Cannot explain auto-configuration", "No optimization strategies"],
            follow_up_questions=["How would you profile startup time?"],
            scoring_rubric=ScoringRubric(
                excellent="Complete understanding with optimization strategies",
                good="Good understanding with minor gaps",
                average="Basic understanding",
                below_average="Limited understanding",
                poor="Poor understanding"
            )
        )
    ]
    
    state["question_evaluations"] = [
        QuestionEvaluation(
            question_id="JAVA_Q1",
            technical_depth_score=4,
            relevance_score=5,
            difficulty_appropriateness=4,
            non_generic_score=4,
            overall_quality=4,
            feedback="Excellent technical question",
            approved=True
        )
    ]
    
    state["processing_stage"] = ProcessingStage.RESPONSES_GENERATED
    
    # Create and execute agent
    agent = ReportAssemblyAgent(llm_config)
    
    try:
        result_state = agent.execute(state)
        
        if result_state["processing_stage"] == ProcessingStage.COMPLETED:
            print("✅ Report assembly successful!")
            
            evaluation = result_state["final_evaluation"]
            
            print(f"📊 FINAL EVALUATION SUMMARY:")
            print(f"   Candidate: {evaluation.candidate_name}")
            print(f"   Position: {evaluation.position_title}")
            print(f"   Skills Identified: {evaluation.total_skills_identified}")
            print(f"   Questions Generated: {evaluation.total_questions}")
            print(f"   Interview Duration: {evaluation.estimated_interview_duration} minutes")
            print(f"   Sections: {len(evaluation.interview_sections)}")
            
            print(f"\n🎯 RECOMMENDATION:")
            print(f"   {evaluation.overall_recommendation}")
            
            print(f"\n💪 KEY STRENGTHS:")
            for strength in evaluation.key_strengths:
                print(f"   • {strength}")
            
            if evaluation.potential_concerns:
                print(f"\n⚠️ AREAS FOR ASSESSMENT:")
                for concern in evaluation.potential_concerns:
                    print(f"   • {concern}")
            
            # Generate and show sample of formatted report
            formatted_report = format_final_report(evaluation)
            print(f"\n📄 FORMATTED REPORT PREVIEW:")
            print("=" * 50)
            print(formatted_report[:1000] + "...")
            
            print(f"\n💬 Agent Message: {result_state['messages'][-1].content}")
            
        else:
            print("❌ Report assembly failed")
            for error in result_state["errors"]:
                print(f"  Error: {error}")
    
    except Exception as e:
        print(f"❌ Test failed: {e}")

if __name__ == "__main__":
    test_report_assembly_agent()