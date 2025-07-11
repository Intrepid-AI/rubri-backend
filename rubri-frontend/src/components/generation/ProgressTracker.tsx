import React from 'react';
import { Progress, Card, CardContent } from '../ui';
import { Brain, CheckCircle, Clock, Zap } from 'lucide-react';
import type { GenerationState } from '../../types/api';

interface ProgressTrackerProps {
  state: GenerationState;
  startTime?: number;
}

export const ProgressTracker: React.FC<ProgressTrackerProps> = ({
  state,
  startTime
}) => {
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
    { name: 'Extracting Skills', icon: Zap, threshold: 20 },
    { name: 'Generating Questions', icon: Brain, threshold: 40 },
    { name: 'Evaluating Questions', icon: CheckCircle, threshold: 60 },
    { name: 'Creating Guidance', icon: CheckCircle, threshold: 80 },
    { name: 'Finalizing Report', icon: CheckCircle, threshold: 100 }
  ];

  return (
    <Card className="max-w-2xl mx-auto">
      <CardContent className="p-8">
        <div className="text-center mb-8">
          <div className="bg-primary-100 p-4 rounded-full w-16 h-16 mx-auto mb-4 flex items-center justify-center">
            <Brain className="h-8 w-8 text-primary-600 animate-pulse" />
          </div>
          <h2 className="text-xl font-semibold text-gray-900 mb-2">
            Generating Your Interview Questions
          </h2>
          <p className="text-gray-600">
            Our AI agents are analyzing your documents and creating tailored questions
          </p>
        </div>

        {/* Progress Bar */}
        <div className="mb-8">
          <Progress 
            value={state.progress} 
            label={state.stage}
            color="primary"
            size="lg"
          />
        </div>

        {/* Stage Indicators */}
        <div className="space-y-3 mb-8">
          {stages.map((stage, index) => {
            const StageIcon = stage.icon;
            const isCompleted = state.progress >= stage.threshold;
            const isCurrent = state.progress >= (stages[index - 1]?.threshold || 0) && state.progress < stage.threshold;
            
            return (
              <div 
                key={stage.name}
                className="flex items-center space-x-3"
              >
                <div className={`
                  w-6 h-6 rounded-full flex items-center justify-center
                  ${isCompleted 
                    ? 'bg-green-100 text-green-600' 
                    : isCurrent 
                      ? 'bg-primary-100 text-primary-600 animate-pulse' 
                      : 'bg-gray-100 text-gray-400'
                  }
                `}>
                  <StageIcon className="h-3 w-3" />
                </div>
                <span className={`text-sm ${
                  isCompleted 
                    ? 'text-green-700 font-medium' 
                    : isCurrent 
                      ? 'text-primary-700 font-medium' 
                      : 'text-gray-500'
                }`}>
                  {stage.name}
                </span>
                {isCompleted && (
                  <CheckCircle className="h-4 w-4 text-green-500 ml-auto" />
                )}
              </div>
            );
          })}
        </div>

        {/* Time Information */}
        <div className="flex justify-between items-center text-sm text-gray-500 bg-gray-50 p-4 rounded-lg">
          <div className="flex items-center space-x-2">
            <Clock className="h-4 w-4" />
            <span>Elapsed: {getElapsedTime()}</span>
          </div>
          <div>
            Estimated: {getEstimatedTotal()}
          </div>
        </div>

        {/* Current Activity */}
        <div className="mt-6 text-center">
          <p className="text-sm text-gray-600">
            <span className="font-medium">Current activity:</span> {state.stage}
          </p>
        </div>
      </CardContent>
    </Card>
  );
};