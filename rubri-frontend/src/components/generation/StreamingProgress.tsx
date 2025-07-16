import React, { useState } from 'react';
import type { StreamEvent } from '../../utils/WebSocketManager';
import { 
  Brain, 
  Sparkles, 
  CheckCircle, 
  AlertCircle, 
  Clock, 
  Target, 
  FileText, 
  Users, 
  TrendingUp, 
  ArrowRight,
  ChevronDown,
  ChevronRight,
  Search,
  Filter,
  Play,
  Pause
} from 'lucide-react';

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
  const [expandedSections, setExpandedSections] = useState<Set<string>>(new Set(['current-agent']));
  const [eventFilter, setEventFilter] = useState<string>('');
  const [isPlaying, setIsPlaying] = useState(true);
  const [animationQueue, setAnimationQueue] = useState<string[]>([]);

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
    
    // Add animation effect for new events
    if (isPlaying) {
      const eventId = `event-${Date.now()}-${Math.random()}`;
      setAnimationQueue(prev => [...prev, eventId]);
      setTimeout(() => {
        setAnimationQueue(prev => prev.filter(id => id !== eventId));
      }, 1000);
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

  const toggleSection = (sectionId: string) => {
    const newExpanded = new Set(expandedSections);
    if (newExpanded.has(sectionId)) {
      newExpanded.delete(sectionId);
    } else {
      newExpanded.add(sectionId);
    }
    setExpandedSections(newExpanded);
  };

  const getAgentIcon = (agentName: string) => {
    switch (agentName.toLowerCase()) {
      case 'skillextractionagent':
        return Target;
      case 'questiongenerationagent':
        return Brain;
      case 'questionevaluationagent':
        return CheckCircle;
      case 'expectedresponseagent':
        return FileText;
      case 'reportassemblyagent':
        return Users;
      default:
        return Sparkles;
    }
  };

  const getAgentColor = (agentName: string) => {
    switch (agentName.toLowerCase()) {
      case 'skillextractionagent':
        return 'text-blue-600 bg-blue-50 border-blue-200';
      case 'questiongenerationagent':
        return 'text-purple-600 bg-purple-50 border-purple-200';
      case 'questionevaluationagent':
        return 'text-orange-600 bg-orange-50 border-orange-200';
      case 'expectedresponseagent':
        return 'text-indigo-600 bg-indigo-50 border-indigo-200';
      case 'reportassemblyagent':
        return 'text-teal-600 bg-teal-50 border-teal-200';
      default:
        return 'text-gray-600 bg-gray-50 border-gray-200';
    }
  };

  const formatAgentName = (agentName: string) => {
    return agentName.replace('Agent', '').replace(/([A-Z])/g, ' $1').trim();
  };

  const filteredSkills = skills.filter(skill => 
    eventFilter === '' || skill.skill_name.toLowerCase().includes(eventFilter.toLowerCase())
  );
  const filteredQuestions = questions.filter(question => 
    eventFilter === '' || question.question_text.toLowerCase().includes(eventFilter.toLowerCase())
  );
  const filteredEvaluations = evaluations.filter(evaluation => 
    eventFilter === '' || evaluation.question_id.toLowerCase().includes(eventFilter.toLowerCase())
  );
  const filteredResponses = responses.filter(response => 
    eventFilter === '' || response.question_id.toLowerCase().includes(eventFilter.toLowerCase())
  );
  const filteredSections = sections.filter(section => 
    eventFilter === '' || section.section_name.toLowerCase().includes(eventFilter.toLowerCase())
  );

  return (
    <div className="space-y-6">
      {/* Controls */}
      <div className="flex flex-col sm:flex-row gap-4 items-center justify-between bg-white border border-gray-200 rounded-lg p-4">
        <div className="flex items-center gap-3">
          <button
            onClick={() => setIsPlaying(!isPlaying)}
            className="flex items-center gap-2 px-3 py-1.5 bg-blue-100 text-blue-700 rounded-lg hover:bg-blue-200 transition-colors"
          >
            {isPlaying ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4" />}
            {isPlaying ? 'Pause' : 'Play'}
          </button>
          <div className="text-sm text-gray-600">
            {skills.length + questions.length + evaluations.length + responses.length + sections.length} events
          </div>
        </div>
        <div className="flex items-center gap-2">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
            <input
              type="text"
              placeholder="Filter events..."
              value={eventFilter}
              onChange={(e) => setEventFilter(e.target.value)}
              className="pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm"
            />
          </div>
        </div>
      </div>

      {/* Current Agent Status */}
      <div className={`border rounded-lg p-4 transition-all duration-300 ${getAgentColor(currentAgent)}`}>
        <div className="flex items-center justify-between">
          <button
            onClick={() => toggleSection('current-agent')}
            className="flex items-center gap-3 text-left flex-1"
          >
            <div className="flex items-center gap-2">
              {expandedSections.has('current-agent') ? (
                <ChevronDown className="h-4 w-4" />
              ) : (
                <ChevronRight className="h-4 w-4" />
              )}
              {React.createElement(getAgentIcon(currentAgent), { className: "h-5 w-5" })}
            </div>
            <div>
              <h3 className="text-lg font-semibold">
                {currentAgent ? formatAgentName(currentAgent) : 'Initializing...'}
              </h3>
              {agentThoughts && (
                <p className="text-sm opacity-80 mt-1">
                  {agentThoughts}
                </p>
              )}
            </div>
          </button>
          <div className="flex items-center space-x-2">
            <div className="w-2 h-2 bg-current rounded-full animate-pulse"></div>
            <span className="text-sm font-medium">Active</span>
          </div>
        </div>
      </div>

      {/* Skills Section */}
      {filteredSkills.length > 0 && (
        <div className="bg-gradient-to-r from-green-50 to-emerald-50 border border-green-200 rounded-lg p-4 transition-all duration-300">
          <button
            onClick={() => toggleSection('skills')}
            className="flex items-center justify-between w-full mb-3"
          >
            <div className="flex items-center gap-2">
              {expandedSections.has('skills') ? (
                <ChevronDown className="h-4 w-4 text-green-600" />
              ) : (
                <ChevronRight className="h-4 w-4 text-green-600" />
              )}
              <Target className="h-5 w-5 text-green-600" />
              <h4 className="text-md font-semibold text-green-900">
                Skills Extracted ({filteredSkills.length})
              </h4>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-sm text-green-600">
                Avg Confidence: {(filteredSkills.reduce((acc, skill) => acc + skill.confidence_score, 0) / filteredSkills.length).toFixed(1)}/5
              </span>
            </div>
          </button>
          {expandedSections.has('skills') && (
            <div className="space-y-3 max-h-64 overflow-y-auto">
              {filteredSkills.map((skill, index) => (
                <div key={index} className="flex items-center justify-between bg-white rounded-lg p-3 shadow-sm hover:shadow-md transition-all duration-200 transform hover:scale-[1.02]">
                  <div className="flex items-center gap-3">
                    <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" style={{ animationDelay: `${index * 100}ms` }} />
                    <div>
                      <span className="font-medium text-green-800">{skill.skill_name}</span>
                      <span className="text-sm text-green-600 ml-2">({skill.category})</span>
                    </div>
                  </div>
                  <div className="flex items-center space-x-2">
                    <span className="text-xs bg-green-100 text-green-700 px-2 py-1 rounded-full font-medium">
                      {skill.experience_level}
                    </span>
                    <div className="flex items-center gap-1">
                      <div className="flex">
                        {[...Array(5)].map((_, i) => (
                          <div
                            key={i}
                            className={`w-2 h-2 rounded-full mx-0.5 ${
                              i < skill.confidence_score ? 'bg-green-500' : 'bg-gray-200'
                            }`}
                          />
                        ))}
                      </div>
                      <span className="text-xs text-green-800 font-medium ml-1">
                        {skill.confidence_score}/5
                      </span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Questions Section */}
      {filteredQuestions.length > 0 && (
        <div className="bg-gradient-to-r from-purple-50 to-indigo-50 border border-purple-200 rounded-lg p-4 transition-all duration-300">
          <button
            onClick={() => toggleSection('questions')}
            className="flex items-center justify-between w-full mb-3"
          >
            <div className="flex items-center gap-2">
              {expandedSections.has('questions') ? (
                <ChevronDown className="h-4 w-4 text-purple-600" />
              ) : (
                <ChevronRight className="h-4 w-4 text-purple-600" />
              )}
              <Brain className="h-5 w-5 text-purple-600" />
              <h4 className="text-md font-semibold text-purple-900">
                Questions Generated ({filteredQuestions.length})
              </h4>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-sm text-purple-600">
                Avg Difficulty: {(filteredQuestions.reduce((acc, q) => acc + q.difficulty_level, 0) / filteredQuestions.length).toFixed(1)}/5
              </span>
            </div>
          </button>
          {expandedSections.has('questions') && (
            <div className="space-y-3 max-h-64 overflow-y-auto">
              {filteredQuestions.map((question, index) => (
                <div key={index} className="bg-white rounded-lg p-3 shadow-sm hover:shadow-md transition-all duration-200 transform hover:scale-[1.01]">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-2">
                        <div className="w-2 h-2 bg-purple-500 rounded-full animate-pulse" style={{ animationDelay: `${index * 100}ms` }} />
                        <span className="text-xs text-purple-600 font-medium">Q{question.question_number}</span>
                      </div>
                      <p className="text-sm text-purple-800 font-medium leading-relaxed">
                        {question.question_text.length > 120 ? (
                          <>
                            {question.question_text.substring(0, 120)}...
                            <button className="text-purple-600 hover:text-purple-800 ml-1 underline text-xs">
                              Read more
                            </button>
                          </>
                        ) : (
                          question.question_text
                        )}
                      </p>
                      <div className="flex items-center space-x-2 mt-2">
                        <span className="text-xs bg-purple-100 text-purple-700 px-2 py-1 rounded-full font-medium">
                          {question.targeted_skill}
                        </span>
                        <span className="text-xs bg-purple-200 text-purple-800 px-2 py-1 rounded-full font-medium">
                          {question.question_type}
                        </span>
                        <div className="flex items-center gap-1">
                          <div className="flex">
                            {[...Array(5)].map((_, i) => (
                              <div
                                key={i}
                                className={`w-2 h-2 rounded-full mx-0.5 ${
                                  i < question.difficulty_level ? 'bg-purple-500' : 'bg-gray-200'
                                }`}
                              />
                            ))}
                          </div>
                          <span className="text-xs text-purple-800 font-medium ml-1">
                            Level {question.difficulty_level}
                          </span>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Evaluations Section */}
      {filteredEvaluations.length > 0 && (
        <div className="bg-gradient-to-r from-orange-50 to-yellow-50 border border-orange-200 rounded-lg p-4 transition-all duration-300">
          <button
            onClick={() => toggleSection('evaluations')}
            className="flex items-center justify-between w-full mb-3"
          >
            <div className="flex items-center gap-2">
              {expandedSections.has('evaluations') ? (
                <ChevronDown className="h-4 w-4 text-orange-600" />
              ) : (
                <ChevronRight className="h-4 w-4 text-orange-600" />
              )}
              <CheckCircle className="h-5 w-5 text-orange-600" />
              <h4 className="text-md font-semibold text-orange-900">
                Questions Evaluated ({filteredEvaluations.length})
              </h4>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-sm text-orange-600">
                {filteredEvaluations.filter(e => e.approved).length} approved
              </span>
            </div>
          </button>
          {expandedSections.has('evaluations') && (
            <div className="space-y-3 max-h-64 overflow-y-auto">
              {filteredEvaluations.map((evaluation, index) => (
                <div key={index} className="flex items-center justify-between bg-white rounded-lg p-3 shadow-sm hover:shadow-md transition-all duration-200">
                  <div className="flex items-center gap-3">
                    <div className="w-2 h-2 bg-orange-500 rounded-full animate-pulse" style={{ animationDelay: `${index * 100}ms` }} />
                    <span className="text-sm text-orange-800 font-medium">
                      Question {evaluation.question_index + 1}
                    </span>
                  </div>
                  <div className="flex items-center space-x-2">
                    <div className="flex items-center gap-1">
                      <span className="text-xs text-orange-700 font-medium">Depth:</span>
                      <div className="flex">
                        {[...Array(5)].map((_, i) => (
                          <div
                            key={i}
                            className={`w-2 h-2 rounded-full mx-0.5 ${
                              i < evaluation.technical_depth_score ? 'bg-orange-500' : 'bg-gray-200'
                            }`}
                          />
                        ))}
                      </div>
                    </div>
                    <div className="flex items-center gap-1">
                      <span className="text-xs text-orange-700 font-medium">Quality:</span>
                      <div className="flex">
                        {[...Array(5)].map((_, i) => (
                          <div
                            key={i}
                            className={`w-2 h-2 rounded-full mx-0.5 ${
                              i < evaluation.overall_quality ? 'bg-orange-500' : 'bg-gray-200'
                            }`}
                          />
                        ))}
                      </div>
                    </div>
                    <span className={`text-xs px-3 py-1 rounded-full font-medium ${
                      evaluation.approved 
                        ? 'bg-green-100 text-green-700 border border-green-300' 
                        : 'bg-red-100 text-red-700 border border-red-300'
                    }`}>
                      {evaluation.approved ? '✓ Approved' : '✗ Rejected'}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Responses Section */}
      {filteredResponses.length > 0 && (
        <div className="bg-gradient-to-r from-indigo-50 to-blue-50 border border-indigo-200 rounded-lg p-4 transition-all duration-300">
          <button
            onClick={() => toggleSection('responses')}
            className="flex items-center justify-between w-full mb-3"
          >
            <div className="flex items-center gap-2">
              {expandedSections.has('responses') ? (
                <ChevronDown className="h-4 w-4 text-indigo-600" />
              ) : (
                <ChevronRight className="h-4 w-4 text-indigo-600" />
              )}
              <FileText className="h-5 w-5 text-indigo-600" />
              <h4 className="text-md font-semibold text-indigo-900">
                Response Guidelines Created ({filteredResponses.length})
              </h4>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-sm text-indigo-600">
                {filteredResponses.reduce((acc, r) => acc + r.key_concepts_count, 0)} concepts
              </span>
            </div>
          </button>
          {expandedSections.has('responses') && (
            <div className="space-y-3 max-h-64 overflow-y-auto">
              {filteredResponses.map((response, index) => (
                <div key={index} className="flex items-center justify-between bg-white rounded-lg p-3 shadow-sm hover:shadow-md transition-all duration-200">
                  <div className="flex items-center gap-3">
                    <div className="w-2 h-2 bg-indigo-500 rounded-full animate-pulse" style={{ animationDelay: `${index * 100}ms` }} />
                    <span className="text-sm text-indigo-800 font-medium">
                      Guidelines {response.response_index + 1}
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs bg-indigo-100 text-indigo-700 px-3 py-1 rounded-full font-medium">
                      {response.key_concepts_count} key concepts
                    </span>
                    <div className="flex items-center gap-1">
                      <Sparkles className="h-3 w-3 text-indigo-500" />
                      <span className="text-xs text-indigo-600">Complete</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Sections Section */}
      {filteredSections.length > 0 && (
        <div className="bg-gradient-to-r from-teal-50 to-cyan-50 border border-teal-200 rounded-lg p-4 transition-all duration-300">
          <button
            onClick={() => toggleSection('sections')}
            className="flex items-center justify-between w-full mb-3"
          >
            <div className="flex items-center gap-2">
              {expandedSections.has('sections') ? (
                <ChevronDown className="h-4 w-4 text-teal-600" />
              ) : (
                <ChevronRight className="h-4 w-4 text-teal-600" />
              )}
              <Users className="h-5 w-5 text-teal-600" />
              <h4 className="text-md font-semibold text-teal-900">
                Report Sections Assembled ({filteredSections.length})
              </h4>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-sm text-teal-600">
                Final assembly complete
              </span>
            </div>
          </button>
          {expandedSections.has('sections') && (
            <div className="space-y-3 max-h-64 overflow-y-auto">
              {filteredSections.map((section, index) => (
                <div key={index} className="bg-white rounded-lg p-3 shadow-sm hover:shadow-md transition-all duration-200">
                  <div className="flex items-center gap-3 mb-2">
                    <div className="w-2 h-2 bg-teal-500 rounded-full animate-pulse" style={{ animationDelay: `${index * 100}ms` }} />
                    <div className="font-medium text-teal-800">{section.section_name}</div>
                  </div>
                  <div className="text-sm text-teal-600 leading-relaxed pl-5">
                    {section.content.length > 100 ? (
                      <>
                        {section.content.substring(0, 100)}...
                        <button className="text-teal-700 hover:text-teal-900 ml-1 underline text-xs">
                          Read more
                        </button>
                      </>
                    ) : (
                      section.content
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
      {/* Summary Stats */}
      <div className="bg-gradient-to-r from-gray-50 to-gray-100 border border-gray-200 rounded-lg p-4">
        <h4 className="text-md font-semibold text-gray-900 mb-3 flex items-center gap-2">
          <TrendingUp className="h-5 w-5 text-gray-600" />
          Processing Summary
        </h4>
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4 text-center">
          <div className="bg-white rounded-lg p-3 shadow-sm">
            <div className="text-2xl font-bold text-green-600">{filteredSkills.length}</div>
            <div className="text-sm text-gray-600">Skills</div>
          </div>
          <div className="bg-white rounded-lg p-3 shadow-sm">
            <div className="text-2xl font-bold text-purple-600">{filteredQuestions.length}</div>
            <div className="text-sm text-gray-600">Questions</div>
          </div>
          <div className="bg-white rounded-lg p-3 shadow-sm">
            <div className="text-2xl font-bold text-orange-600">{filteredEvaluations.filter(e => e.approved).length}</div>
            <div className="text-sm text-gray-600">Approved</div>
          </div>
          <div className="bg-white rounded-lg p-3 shadow-sm">
            <div className="text-2xl font-bold text-indigo-600">{filteredResponses.length}</div>
            <div className="text-sm text-gray-600">Responses</div>
          </div>
          <div className="bg-white rounded-lg p-3 shadow-sm">
            <div className="text-2xl font-bold text-teal-600">{filteredSections.length}</div>
            <div className="text-sm text-gray-600">Sections</div>
          </div>
        </div>
      </div>
    </div>
  );
};