import React, { useState } from 'react';
import { Progress, Card, CardContent } from '../ui';
import { Brain, CheckCircle, Clock, Zap, ChevronDown, ChevronUp, Target, FileText, AlertCircle, TrendingUp, Sparkles } from 'lucide-react';
import type { GenerationState } from '../../types/api';
import { StreamingProgress } from './StreamingProgress';
import type { StreamEvent } from '../../utils/WebSocketManager';

interface ProgressTrackerProps {
  state: GenerationState;
  startTime?: number;
  streamingEnabled?: boolean;
  onStreamEvent?: (event: StreamEvent) => void;
  onStreamBatch?: (events: StreamEvent[]) => void;
  latestStreamEvent?: any;
  allStreamEvents?: any[];
}

export const ProgressTracker: React.FC<ProgressTrackerProps> = ({
  state,
  startTime,
  streamingEnabled = false,
  onStreamEvent,
  onStreamBatch,
  latestStreamEvent,
  allStreamEvents = []
}) => {
  const [showStreamingDetails, setShowStreamingDetails] = useState(false);
  const getElapsedTime = () => {
    if (!startTime) return '0s';
    const elapsed = Math.floor((Date.now() - startTime) / 1000);
    const minutes = Math.floor(elapsed / 60);
    const seconds = elapsed % 60;
    return minutes > 0 ? `${minutes}m ${seconds}s` : `${seconds}s`;
  };

  const getEstimatedTotal = () => {
    if (state.progress < 10) return '2-3 minutes';
    if (state.progress < 50) return '1-2 minutes';
    return 'Almost done';
  };

  const stages = [
    { name: 'Extracting Skills', icon: Target, threshold: 20, color: 'text-blue-600 bg-blue-50' },
    { name: 'Generating Questions', icon: Brain, threshold: 40, color: 'text-purple-600 bg-purple-50' },
    { name: 'Evaluating Questions', icon: CheckCircle, threshold: 60, color: 'text-orange-600 bg-orange-50' },
    { name: 'Creating Guidance', icon: FileText, threshold: 80, color: 'text-indigo-600 bg-indigo-50' },
    { name: 'Finalizing Report', icon: Sparkles, threshold: 100, color: 'text-teal-600 bg-teal-50' }
  ];

  const getCurrentStage = () => {
    return stages.find(stage => state.progress < stage.threshold) || stages[stages.length - 1];
  };

  const getCompletedStages = () => {
    return stages.filter(stage => state.progress >= stage.threshold);
  };

  const currentStage = getCurrentStage();
  const completedStages = getCompletedStages();

  return (
    <Card className="max-w-2xl mx-auto overflow-hidden">
      <CardContent className="p-8">
        <div className="text-center mb-8">
          <div className={`relative p-4 rounded-full w-16 h-16 mx-auto mb-4 flex items-center justify-center ${currentStage.color} transition-all duration-500`}>
            {React.createElement(currentStage.icon, { className: "h-8 w-8 animate-pulse" })}
            <div className="absolute inset-0 rounded-full bg-gradient-to-r from-transparent via-white/20 to-transparent animate-shimmer" />
          </div>
          <h2 className="text-xl font-semibold text-gray-900 mb-2">
            Generating Your Interview Questions
          </h2>
          <p className="text-gray-600">
            Our AI agents are analyzing your documents and creating tailored questions
          </p>
          <div className="mt-4 flex items-center justify-center gap-2">
            <div className="flex items-center gap-1 text-sm text-gray-500">
              <TrendingUp className="h-4 w-4" />
              <span>{state.progress}% Complete</span>
            </div>
            <div className="w-1 h-1 bg-gray-400 rounded-full" />
            <div className="text-sm text-gray-500">
              {currentStage.name}
            </div>
          </div>
        </div>

        {/* Enhanced Progress Bar */}
        <div className="mb-8">
          <div className="relative mb-4">
            <Progress 
              value={state.progress} 
              label={state.stage}
              color="primary"
              size="lg"
            />
            <div className="absolute top-0 left-0 h-full bg-gradient-to-r from-transparent via-white/30 to-transparent rounded-lg animate-pulse" style={{ width: `${state.progress}%` }} />
          </div>
          <div className="flex justify-between text-sm text-gray-500">
            <span>Started</span>
            <span className="font-medium">{state.progress}%</span>
            <span>Complete</span>
          </div>
        </div>

        {/* Enhanced Stage Indicators */}
        <div className="space-y-4 mb-8">
          {stages.map((stage, index) => {
            const StageIcon = stage.icon;
            const isCompleted = state.progress >= stage.threshold;
            const isCurrent = state.progress >= (stages[index - 1]?.threshold || 0) && state.progress < stage.threshold;
            const isUpcoming = state.progress < (stages[index - 1]?.threshold || 0);
            
            return (
              <div 
                key={stage.name}
                className={`relative p-4 rounded-lg border transition-all duration-300 ${
                  isCompleted
                    ? 'bg-green-50 border-green-200 transform scale-[1.02]'
                    : isCurrent
                      ? `${stage.color} border-current transform scale-105 shadow-md`
                      : 'bg-gray-50 border-gray-200 hover:bg-gray-100'
                }`}
              >
                <div className="flex items-center space-x-4">
                  <div className={`
                    w-10 h-10 rounded-full flex items-center justify-center transition-all duration-300
                    ${isCompleted 
                      ? 'bg-green-100 text-green-600 shadow-lg' 
                      : isCurrent 
                        ? `${stage.color} animate-pulse shadow-md` 
                        : 'bg-gray-100 text-gray-400'
                    }
                  `}>
                    <StageIcon className="h-5 w-5" />
                  </div>
                  <div className="flex-1">
                    <div className="flex items-center justify-between">
                      <span className={`text-sm font-medium ${
                        isCompleted 
                          ? 'text-green-700' 
                          : isCurrent 
                            ? 'text-gray-900' 
                            : 'text-gray-500'
                      }`}>
                        {stage.name}
                      </span>
                      <div className="flex items-center gap-2">
                        {isCompleted && (
                          <div className="flex items-center gap-1 text-green-600">
                            <CheckCircle className="h-4 w-4" />
                            <span className="text-xs font-medium">Complete</span>
                          </div>
                        )}
                        {isCurrent && (
                          <div className="flex items-center gap-1 text-gray-600">
                            <div className="w-2 h-2 bg-current rounded-full animate-pulse" />
                            <span className="text-xs font-medium">In Progress</span>
                          </div>
                        )}
                        {isUpcoming && (
                          <div className="flex items-center gap-1 text-gray-400">
                            <Clock className="h-4 w-4" />
                            <span className="text-xs font-medium">Pending</span>
                          </div>
                        )}
                      </div>
                    </div>
                    {isCurrent && (
                      <div className="mt-2">
                        <div className="w-full bg-gray-200 rounded-full h-1.5">
                          <div 
                            className="bg-current h-1.5 rounded-full transition-all duration-500"
                            style={{ width: `${((state.progress - (stages[index - 1]?.threshold || 0)) / (stage.threshold - (stages[index - 1]?.threshold || 0))) * 100}%` }}
                          />
                        </div>
                      </div>
                    )}
                  </div>
                </div>
                {isCurrent && (
                  <div className="absolute inset-0 rounded-lg bg-gradient-to-r from-transparent via-white/10 to-transparent animate-shimmer" />
                )}
              </div>
            );
          })}
        </div>

        {/* Enhanced Time Information */}
        <div className="bg-gradient-to-r from-gray-50 to-blue-50 p-4 rounded-lg border border-gray-200">
          <div className="flex justify-between items-center">
            <div className="flex items-center space-x-4">
              <div className="flex items-center space-x-2 text-sm text-gray-600">
                <Clock className="h-4 w-4" />
                <span className="font-medium">Elapsed: {getElapsedTime()}</span>
              </div>
              <div className="w-1 h-1 bg-gray-400 rounded-full" />
              <div className="text-sm text-gray-600">
                <span className="font-medium">Estimated: {getEstimatedTotal()}</span>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <div className="text-sm text-gray-500">
                {completedStages.length} of {stages.length} stages
              </div>
              <div className="flex gap-1">
                {stages.map((stage, index) => (
                  <div
                    key={index}
                    className={`w-2 h-2 rounded-full transition-all duration-300 ${
                      state.progress >= stage.threshold ? 'bg-green-500' : 'bg-gray-300'
                    }`}
                  />
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* Enhanced Current Activity */}
        <div className="mt-6 text-center bg-white border border-gray-200 rounded-lg p-4">
          <div className="flex items-center justify-center gap-2 mb-2">
            <div className="w-2 h-2 bg-blue-500 rounded-full animate-pulse" />
            <span className="text-sm font-medium text-gray-700">Current Activity</span>
          </div>
          <p className="text-sm text-gray-600">
            {state.stage}
          </p>
          <div className="mt-2 text-xs text-gray-500">
            Stage {stages.findIndex(s => s.name === currentStage.name) + 1} of {stages.length}
          </div>
        </div>

        {/* Enhanced Streaming Details Toggle */}
        {streamingEnabled && (
          <div className="mt-6">
            <button
              onClick={() => setShowStreamingDetails(!showStreamingDetails)}
              className="w-full flex items-center justify-center space-x-2 text-sm text-gray-600 hover:text-gray-800 transition-all duration-200 p-3 rounded-lg hover:bg-gray-50 border border-gray-200 hover:border-gray-300"
            >
              <div className="flex items-center gap-2">
                <div className="w-2 h-2 bg-blue-500 rounded-full animate-pulse" />
                <span className="font-medium">View Real-time AI Processing</span>
              </div>
              {showStreamingDetails ? (
                <ChevronUp className="h-4 w-4" />
              ) : (
                <ChevronDown className="h-4 w-4" />
              )}
            </button>
          </div>
        )}
      </CardContent>

      {/* Enhanced Streaming Details Section */}
      {streamingEnabled && showStreamingDetails && (
        <div className="border-t border-gray-200 bg-gradient-to-b from-white to-gray-50">
          <div className="p-6">
            <div className="flex items-center gap-2 mb-4">
              <div className="w-2 h-2 bg-blue-500 rounded-full animate-pulse" />
              <h3 className="text-lg font-semibold text-gray-900">
                Real-time AI Processing
              </h3>
              <div className="ml-auto text-sm text-gray-500">
                Live updates from our AI agents
              </div>
            </div>
            <StreamingProgress 
              onStreamEvent={onStreamEvent}
              onStreamBatch={onStreamBatch}
              latestEvent={latestStreamEvent}
              allEvents={allStreamEvents}
            />
          </div>
        </div>
      )}
    </Card>
  );
};

// Add CSS for shimmer animation
const styles = `
  @keyframes shimmer {
    0% { transform: translateX(-100%); }
    100% { transform: translateX(100%); }
  }
  .animate-shimmer {
    animation: shimmer 2s infinite;
  }
`;

// Inject styles
if (typeof document !== 'undefined') {
  const styleElement = document.getElementById('progress-tracker-styles');
  if (!styleElement) {
    const newStyleElement = document.createElement('style');
    newStyleElement.id = 'progress-tracker-styles';
    newStyleElement.textContent = styles;
    document.head.appendChild(newStyleElement);
  }
}