import React, { useState } from 'react';
import { Card, CardHeader, CardContent, Button } from '../components/ui';
import { InputToggle, FileUploadForm, TextInputForm } from '../components/forms';
import { ProgressTracker } from '../components/generation';
import { ReportViewer } from '../components/report';
import { Brain, ArrowLeft } from 'lucide-react';
import { uploadFile, asyncQuestionAPI } from '../services/api';
import { useWebSocket } from '../hooks/useWebSocket';
import { useAuth } from '../contexts/AuthContext';
import type { 
  GenerationState, 
  QuestionGenerationResponse,
  DocumentResponse,
  ProgressUpdate
} from '../types/api';

interface GeneratorPageProps {
  onBack: () => void;
}

type PageState = 'input' | 'generating' | 'results';

export const GeneratorPage: React.FC<GeneratorPageProps> = ({ onBack }) => {
  const { tokens, isAuthenticated, isLoading } = useAuth();
  const [inputMode, setInputMode] = useState<'upload' | 'text'>('upload');


  // Show loading while auth state is being determined
  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <h2 className="text-xl font-semibold mb-4">Loading...</h2>
          <p className="text-foreground-muted">Checking authentication status...</p>
        </div>
      </div>
    );
  }

  // Redirect to login if not authenticated
  if (!isAuthenticated) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <h2 className="text-xl font-semibold mb-4">Authentication Required</h2>
          <p className="text-foreground-muted mb-6">Please sign in to access the interview generator.</p>
          <Button onClick={onBack}>Back to Home</Button>
        </div>
      </div>
    );
  }
  const [pageState, setPageState] = useState<PageState>('input');
  const [generationState, setGenerationState] = useState<GenerationState>({
    isLoading: false,
    progress: 0,
    stage: 'Initializing...'
  });
  const [generationStartTime, setGenerationStartTime] = useState<number>();
  const [result, setResult] = useState<QuestionGenerationResponse | null>(null);
  const [error, setError] = useState<string>('');
  const [currentTaskId, setCurrentTaskId] = useState<string | null>(null);

  // WebSocket integration for real-time progress updates
  useWebSocket({
    taskId: currentTaskId || undefined,
    enabled: !!currentTaskId && pageState === 'generating',
    onProgressUpdate: (progress: ProgressUpdate) => {
      setGenerationState(prev => ({
        ...prev,
        progress: progress.progress,
        stage: progress.current_step,
        estimatedTimeRemaining: progress.estimated_remaining_minutes
      }));
    },
    onTaskCompleted: async (data: any) => {
      if (data.status === 'completed' && data.rubric_id) {
        // Fetch the final result using the rubric_id
        try {
          const taskStatus = await asyncQuestionAPI.getTaskStatus(currentTaskId!);
          if (taskStatus.result_data) {
            setResult(taskStatus.result_data);
            setPageState('results');
          }
        } catch (err) {
          console.error('Failed to fetch task result:', err);
          setError('Failed to retrieve generation results');
          setPageState('input');
        }
      } else if (data.status === 'failed') {
        setError(data.error_message || 'Question generation failed');
        setPageState('input');
      }
      setCurrentTaskId(null);
    },
    onError: (error: string) => {
      console.error('WebSocket error:', error);
      setError(`Connection error: ${error}`);
    }
  });

  const handleFileUploadSubmit = async (data: { 
    jdFile?: File; 
    resumeFile?: File; 
    positionTitle: string;
  }) => {
    setError('');
    setPageState('generating');
    setGenerationStartTime(Date.now());
    setGenerationState({
      isLoading: true,
      progress: 5,
      stage: 'Uploading documents...'
    });

    try {
      // Upload files
      let jdDocId: string | undefined;
      let resumeDocId: string | undefined;

      if (data.jdFile) {
        setGenerationState(prev => ({ ...prev, progress: 10, stage: 'Processing job description...' }));
        const jdResponse: DocumentResponse = await uploadFile(data.jdFile, 'jd', tokens?.access_token);
        jdDocId = jdResponse.doc_id;
      }

      if (data.resumeFile) {
        setGenerationState(prev => ({ ...prev, progress: 15, stage: 'Processing resume...' }));
        const resumeResponse: DocumentResponse = await uploadFile(data.resumeFile, 'resume', tokens?.access_token);
        resumeDocId = resumeResponse.doc_id;
      }

      setGenerationState(prev => ({ ...prev, progress: 20, stage: 'Starting AI agents...' }));

      // Start async question generation
      const taskResponse = await asyncQuestionAPI.startAsyncGeneration({
        jd_document_id: jdDocId,
        resume_document_id: resumeDocId,
        position_title: data.positionTitle,
        llm_provider: 'openai'
      }, tokens?.access_token);

      // Set task ID to start WebSocket connection
      setCurrentTaskId(taskResponse.task_id);
      setGenerationState(prev => ({ 
        ...prev, 
        progress: 25, 
        stage: 'Connected to AI agents - starting analysis...' 
      }));

    } catch (err) {
      setError(err instanceof Error ? err.message : 'An unexpected error occurred');
      setPageState('input');
      setCurrentTaskId(null);
    }
  };

  const handleTextInputSubmit = async (data: { 
    jobDescription?: string; 
    resumeText?: string; 
    positionTitle: string;
  }) => {
    setError('');
    setPageState('generating');
    setGenerationStartTime(Date.now());
    setGenerationState({
      isLoading: true,
      progress: 10,
      stage: 'Processing text input...'
    });

    try {
      // Start async quick question generation
      const taskResponse = await asyncQuestionAPI.startAsyncQuickGeneration({
        resume_text: data.resumeText,
        job_description: data.jobDescription,
        position_title: data.positionTitle,
        llm_provider: 'openai'
      }, tokens?.access_token);

      // Set task ID to start WebSocket connection
      setCurrentTaskId(taskResponse.task_id);
      setGenerationState(prev => ({ 
        ...prev, 
        progress: 20, 
        stage: 'Connected to AI agents - starting analysis...' 
      }));

    } catch (err) {
      setError(err instanceof Error ? err.message : 'An unexpected error occurred');
      setPageState('input');
      setCurrentTaskId(null);
    }
  };

  const handleExport = (format: 'pdf' | 'link') => {
    // TODO: Implement export functionality
    console.log(`Exporting as ${format}`, result);
    
    if (format === 'pdf') {
      // Would integrate with a PDF generation service
      alert('PDF export would be implemented here');
    } else {
      // Would generate a shareable link
      alert('Share link would be generated here');
    }
  };

  const handleStartOver = () => {
    setPageState('input');
    setResult(null);
    setError('');
    setCurrentTaskId(null);
    setGenerationState({
      isLoading: false,
      progress: 0,
      stage: 'Initializing...'
    });
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-background via-background-muted to-surface-100 py-8">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="mb-8">
          <Button
            onClick={pageState === 'results' ? handleStartOver : onBack}
            variant="ghost"
            leftIcon={ArrowLeft}
            className="mb-4 -ml-3"
          >
            {pageState === 'results' ? 'Generate New Questions' : 'Back to Home'}
          </Button>
          
          <div className="flex items-center space-x-3">
            <div className="bg-primary-600 p-3 rounded-lg">
              <Brain className="h-6 w-6 text-white" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-foreground">
                {pageState === 'results' ? 'Interview Questions Generated' : 'AI Interview Question Generator'}
              </h1>
              <p className="text-foreground-muted">
                {pageState === 'results' 
                  ? 'Your comprehensive interview plan is ready'
                  : 'Upload documents or paste text to generate tailored interview questions'
                }
              </p>
            </div>
          </div>
        </div>

        {/* Content */}
        {pageState === 'input' && (
          <Card className="max-w-4xl mx-auto">
            <CardHeader>
              <div className="flex justify-between items-center">
                <div>
                  <h2 className="text-xl font-semibold text-foreground">
                    Create Interview Questions
                  </h2>
                  <p className="text-foreground-muted mt-1">
                    Choose your input method and provide the necessary information
                  </p>
                </div>
                
                <InputToggle 
                  mode={inputMode} 
                  onModeChange={setInputMode}
                />
              </div>
            </CardHeader>
            
            <CardContent>
              {inputMode === 'upload' ? (
                <FileUploadForm
                  onSubmit={handleFileUploadSubmit}
                  isLoading={false}
                  error={error}
                />
              ) : (
                <TextInputForm
                  onSubmit={handleTextInputSubmit}
                  isLoading={false}
                  error={error}
                />
              )}
            </CardContent>
          </Card>
        )}

        {pageState === 'generating' && (
          <ProgressTracker 
            state={generationState}
            startTime={generationStartTime}
          />
        )}

        {pageState === 'results' && result && (
          <ReportViewer 
            result={result}
            onExport={handleExport}
          />
        )}
      </div>
    </div>
  );
};