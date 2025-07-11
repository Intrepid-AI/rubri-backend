// API Response Types based on backend data models

export interface DocumentResponse {
  document_type: 'jd' | 'resume';
  doc_id: string;
  original_filename: string;
}

export interface QuestionGenerationResponse {
  success: boolean;
  rubric_id?: string | null;
  processing_time: number;
  candidate_name?: string | null;
  position_title: string;
  input_scenario: string;
  skills_identified?: number | null;
  categories_covered?: number | null;
  questions_generated?: number | null;
  interview_duration_minutes?: number | null;
  sections_created?: number | null;
  key_strengths?: string[] | null;
  potential_concerns?: string[] | null;
  focus_areas?: string[] | null;
  overall_recommendation?: string | null;
  formatted_report?: string | null;
  evaluation_object?: Record<string, any> | null;
  agent_performance?: Record<string, any> | null;
  messages?: string[] | null;
  workflow_success?: boolean | null;
  error?: string | null;
}

export interface ErrorResponse {
  detail: string | Array<{
    loc: (string | number)[];
    msg: string;
    type: string;
  }>;
  status_code?: number;
}

// Request Types
export interface TextUploadRequest {
  text: string;
  document_type: 'jd' | 'resume';
}

export interface QuestionGenerationRequest {
  jd_document_id?: string | null;
  resume_document_id?: string | null;
  position_title: string;
  llm_provider?: string | null;
}

export interface QuickQuestionRequest {
  resume_text?: string | null;
  job_description?: string | null;
  position_title: string;
  llm_provider?: string | null;
}

// UI State Types
export interface GenerationState {
  isLoading: boolean;
  progress: number;
  stage: string;
  estimatedTimeRemaining?: number;
}

export interface UploadedFile {
  file: File;
  type: 'jd' | 'resume';
  preview?: string;
}

export interface GenerationResult extends QuestionGenerationResponse {
  timestamp: number;
}

// Authentication Types
export interface User {
  user_id: string;
  email: string;
  name: string;
  given_name?: string;
  family_name?: string;
  picture_url?: string;
  email_notifications_enabled: boolean;
  preferred_llm_provider: string;
  created_at: string;
  last_login_at?: string;
}

export interface AuthTokens {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface LoginResponse {
  message: string;
  user: User;
  tokens: AuthTokens;
}

export interface GoogleAuthResponse {
  authorization_url: string;
  state: string;
}

// Async Task Types
export interface TaskStatusResponse {
  task_id: string;
  task_type: string;
  status: 'pending' | 'in_progress' | 'completed' | 'failed';
  progress: number; // 0-100
  current_step?: string;
  total_steps: number;
  position_title?: string;
  started_at?: string;
  completed_at?: string;
  created_at: string;
  result_data?: any;
  error_message?: string;
  rubric_id?: string;
}

export interface TaskInitiationResponse {
  task_id: string;
  status: 'pending' | 'in_progress' | 'completed' | 'failed';
  message: string;
  estimated_duration_minutes: number;
  websocket_endpoint?: string;
}

export interface ProgressUpdate {
  task_id: string;
  progress: number; // 0-100
  current_step: string;
  step_number?: number;
  total_steps: number;
  estimated_remaining_minutes?: number;
}

export interface WebSocketMessage {
  type: 'progress_update' | 'task_completed' | 'error';
  task_id: string;
  data: any;
}

// Updated request types with auth support
export interface AsyncQuestionGenerationRequest {
  jd_document_id?: string;
  resume_document_id?: string;
  position_title: string;
  llm_provider?: string;
  user_email?: string; // Optional fallback if not authenticated
}

export interface AsyncQuickQuestionRequest {
  resume_text?: string;
  job_description?: string;
  position_title: string;
  llm_provider?: string;
  user_email?: string; // Optional fallback if not authenticated
}