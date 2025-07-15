import React, { useState } from 'react';
import type { StreamEvent } from '../../utils/WebSocketManager';

interface StreamingProgressProps {
  onStreamEvent?: (event: StreamEvent) => void;
  onStreamBatch?: (events: StreamEvent[]) => void;
}

interface SkillEvent {
  skill_name: string;
  category: string;
  experience_level: string;
  confidence_score: number;
  skill_index: number;
  total_skills: number;
}

interface QuestionEvent {
  question_id: string;
  question_text: string;
  question_type: string;
  difficulty_level: number;
  targeted_skill: string;
  category: string;
  question_number: number;
  total_questions: number;
}

interface EvaluationEvent {
  question_id: string;
  technical_depth_score: number;
  overall_quality: number;
  approved: boolean;
  question_index: number;
  total_questions: number;
}

interface ResponseEvent {
  question_id: string;
  key_concepts_count: number;
  response_index: number;
  total_responses: number;
}

interface SectionEvent {
  section_name: string;
  content: string;
}

interface StreamingProgressWithEventsProps extends StreamingProgressProps {
  latestEvent?: any;
  allEvents?: any[];
}

export const StreamingProgress: React.FC<StreamingProgressWithEventsProps> = ({
  onStreamEvent,
  onStreamBatch,
  latestEvent,
  allEvents = []
}) => {
  const [skills, setSkills] = useState<SkillEvent[]>([]);
  const [questions, setQuestions] = useState<QuestionEvent[]>([]);
  const [evaluations, setEvaluations] = useState<EvaluationEvent[]>([]);
  const [responses, setResponses] = useState<ResponseEvent[]>([]);
  const [sections, setSections] = useState<SectionEvent[]>([]);
  const [currentAgent, setCurrentAgent] = useState<string>('');
  const [agentThoughts, setAgentThoughts] = useState<string>('');

  const handleStreamEvent = (event: StreamEvent) => {
    onStreamEvent?.(event);
    setCurrentAgent(event.agent_name);

    switch (event.event_type) {
      case 'agent_start':
        setAgentThoughts(`${event.agent_name} is starting...`);
        break;

      case 'agent_thinking':
        setAgentThoughts(event.data.thought || event.data.message || '');
        break;

      case 'skill_found':
        // Handle skill found events - data might be nested under skill
        const skillData = event.data.skill || event.data;
        setSkills(prev => [...prev, skillData as SkillEvent]);
        break;

      case 'question_generated':
        // Handle question generated events - data might be nested under question
        const questionData = event.data.question || event.data;
        setQuestions(prev => [...prev, questionData as QuestionEvent]);
        break;

      case 'evaluation_result':
        // Handle evaluation result events - data might be nested under evaluation
        const evaluationData = event.data.evaluation || event.data;
        setEvaluations(prev => [...prev, evaluationData as EvaluationEvent]);
        break;

      case 'response_generated':
        // Handle response generated events - data might be nested under response
        const responseData = event.data.response || event.data;
        setResponses(prev => [...prev, responseData as ResponseEvent]);
        break;

      case 'section_assembled':
        setSections(prev => [...prev, event.data as SectionEvent]);
        break;

      case 'agent_complete':
        setAgentThoughts(`${event.agent_name} completed successfully`);
        break;

      case 'error':
        setAgentThoughts(`Error: ${event.data.error}`);
        break;
    }
  };

  const handleStreamBatch = (events: StreamEvent[]) => {
    onStreamBatch?.(events);
    events.forEach(handleStreamEvent);
  };

  // Process events when they arrive
  React.useEffect(() => {
    if (latestEvent) {
      console.log('📡 StreamingProgress received event:', latestEvent);
      handleStreamEvent(latestEvent);
    }
  }, [latestEvent, handleStreamEvent]);

  // Process all events on mount
  React.useEffect(() => {
    allEvents.forEach(event => {
      handleStreamEvent(event);
    });
  }, []);  // Only run on mount

  return (
    <div className="space-y-6">
      {/* Current Agent Status */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold text-blue-900">
            {currentAgent ? `${currentAgent}` : 'Initializing...'}
          </h3>
          <div className="flex items-center space-x-2">
            <div className="w-2 h-2 bg-blue-500 rounded-full animate-pulse"></div>
            <span className="text-sm text-blue-600">Active</span>
          </div>
        </div>
        {agentThoughts && (
          <p className="text-sm text-blue-700 mt-2 italic">
            {agentThoughts}
          </p>
        )}
      </div>

      {/* Skills Section */}
      {skills.length > 0 && (
        <div className="bg-green-50 border border-green-200 rounded-lg p-4">
          <h4 className="text-md font-semibold text-green-900 mb-3">
            Skills Extracted ({skills.length})
          </h4>
          <div className="space-y-2 max-h-32 overflow-y-auto">
            {skills.map((skill, index) => (
              <div key={index} className="flex items-center justify-between bg-white rounded p-2 shadow-sm">
                <div>
                  <span className="font-medium text-green-800">{skill.skill_name}</span>
                  <span className="text-sm text-green-600 ml-2">({skill.category})</span>
                </div>
                <div className="flex items-center space-x-2">
                  <span className="text-xs bg-green-100 text-green-700 px-2 py-1 rounded">
                    {skill.experience_level}
                  </span>
                  <span className="text-xs bg-green-200 text-green-800 px-2 py-1 rounded">
                    {skill.confidence_score}/5
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Questions Section */}
      {questions.length > 0 && (
        <div className="bg-purple-50 border border-purple-200 rounded-lg p-4">
          <h4 className="text-md font-semibold text-purple-900 mb-3">
            Questions Generated ({questions.length})
          </h4>
          <div className="space-y-2 max-h-32 overflow-y-auto">
            {questions.map((question, index) => (
              <div key={index} className="bg-white rounded p-2 shadow-sm">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <p className="text-sm text-purple-800 font-medium">
                      {question.question_text.substring(0, 100)}
                      {question.question_text.length > 100 ? '...' : ''}
                    </p>
                    <div className="flex items-center space-x-2 mt-1">
                      <span className="text-xs bg-purple-100 text-purple-700 px-2 py-1 rounded">
                        {question.targeted_skill}
                      </span>
                      <span className="text-xs bg-purple-200 text-purple-800 px-2 py-1 rounded">
                        Level {question.difficulty_level}
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Evaluations Section */}
      {evaluations.length > 0 && (
        <div className="bg-orange-50 border border-orange-200 rounded-lg p-4">
          <h4 className="text-md font-semibold text-orange-900 mb-3">
            Questions Evaluated ({evaluations.length})
          </h4>
          <div className="space-y-2 max-h-32 overflow-y-auto">
            {evaluations.map((evaluation, index) => (
              <div key={index} className="flex items-center justify-between bg-white rounded p-2 shadow-sm">
                <span className="text-sm text-orange-800 font-medium">
                  Question {evaluation.question_index}
                </span>
                <div className="flex items-center space-x-2">
                  <span className="text-xs bg-orange-100 text-orange-700 px-2 py-1 rounded">
                    Depth: {evaluation.technical_depth_score}/5
                  </span>
                  <span className="text-xs bg-orange-100 text-orange-700 px-2 py-1 rounded">
                    Quality: {evaluation.overall_quality}/5
                  </span>
                  <span className={`text-xs px-2 py-1 rounded ${
                    evaluation.approved 
                      ? 'bg-green-100 text-green-700' 
                      : 'bg-red-100 text-red-700'
                  }`}>
                    {evaluation.approved ? 'Approved' : 'Rejected'}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Responses Section */}
      {responses.length > 0 && (
        <div className="bg-indigo-50 border border-indigo-200 rounded-lg p-4">
          <h4 className="text-md font-semibold text-indigo-900 mb-3">
            Response Guidelines Created ({responses.length})
          </h4>
          <div className="space-y-2 max-h-32 overflow-y-auto">
            {responses.map((response, index) => (
              <div key={index} className="flex items-center justify-between bg-white rounded p-2 shadow-sm">
                <span className="text-sm text-indigo-800 font-medium">
                  Guidelines {response.response_index}
                </span>
                <span className="text-xs bg-indigo-100 text-indigo-700 px-2 py-1 rounded">
                  {response.key_concepts_count} key concepts
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Sections Section */}
      {sections.length > 0 && (
        <div className="bg-teal-50 border border-teal-200 rounded-lg p-4">
          <h4 className="text-md font-semibold text-teal-900 mb-3">
            Report Sections Assembled ({sections.length})
          </h4>
          <div className="space-y-2">
            {sections.map((section, index) => (
              <div key={index} className="bg-white rounded p-2 shadow-sm">
                <div className="font-medium text-teal-800">{section.section_name}</div>
                <div className="text-sm text-teal-600">{section.content}</div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};