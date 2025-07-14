import axios, { AxiosError } from 'axios';
import type { 
  DocumentResponse, 
  QuestionGenerationResponse, 
  QuestionGenerationRequest,
  QuickQuestionRequest,
  TextUploadRequest,
  ErrorResponse,
  User,
  AuthTokens,
  LoginResponse,
  GoogleAuthResponse,
  TaskInitiationResponse,
  TaskStatusResponse,
  AsyncQuestionGenerationRequest,
  AsyncQuickQuestionRequest
} from '../types/api';

// Configure axios instance
const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000',
  timeout: 1200000, // 20 minutes for long-running operations (question generation can take 15-20 minutes)
  headers: {
    'Content-Type': 'application/json',
  },
});

// Function to add auth headers
const addAuthHeaders = (token?: string) => {
  if (token) {
    return { Authorization: `Bearer ${token}` };
  }
  return {};
};

// Request interceptor for logging
api.interceptors.request.use(
  (config) => {
    console.log(`🚀 API Request: ${config.method?.toUpperCase()} ${config.url}`);
    return config;
  },
  (error) => {
    console.error('❌ API Request Error:', error);
    return Promise.reject(error);
  }
);

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => {
    console.log(`✅ API Response: ${response.status} ${response.config.url}`);
    return response;
  },
  (error: AxiosError<ErrorResponse>) => {
    console.error('❌ API Response Error:', error.response?.data || error.message);
    
    // Transform backend validation errors to user-friendly messages
    if (error.response?.data?.detail) {
      const detail = error.response.data.detail;
      if (Array.isArray(detail)) {
        // Validation errors
        const messages = detail.map(err => `${err.loc.join('.')}: ${err.msg}`);
        throw new Error(`Validation Error: ${messages.join(', ')}`);
      } else {
        // String error
        throw new Error(detail);
      }
    }
    
    throw new Error(error.message || 'An unexpected error occurred');
  }
);

// File Upload APIs
export const uploadFile = async (file: File, type: 'jd' | 'resume', token?: string): Promise<DocumentResponse> => {
  const formData = new FormData();
  formData.append('file', file);
  
  const response = await api.post<DocumentResponse>(`/api/v1/upload/file/${type}`, formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
      ...addAuthHeaders(token)
    },
  });
  
  return response.data;
};

export const uploadText = async (text: string, type: 'jd' | 'resume', token?: string): Promise<DocumentResponse> => {
  const payload: TextUploadRequest = { text, document_type: type };
  const response = await api.post<DocumentResponse>(`/api/v1/upload/text/${type}`, payload, {
    headers: addAuthHeaders(token)
  });
  return response.data;
};

// Question Generation APIs
export const generateQuestions = async (
  request: QuestionGenerationRequest,
  onProgress?: (progress: number, stage: string) => void
): Promise<QuestionGenerationResponse> => {
  // Simulate progress updates during the request
  const progressInterval = setInterval(() => {
    if (onProgress) {
      const stages = [
        'Extracting skills from documents...',
        'Generating technical questions...',
        'Evaluating question quality...',
        'Creating interviewer guidance...',
        'Assembling final report...'
      ];
      const randomStage = stages[Math.floor(Math.random() * stages.length)];
      const randomProgress = Math.min(95, Math.floor(Math.random() * 80) + 10);
      onProgress(randomProgress, randomStage);
    }
  }, 2000);

  try {
    const response = await api.post<QuestionGenerationResponse>(
      '/api/v1/questions/generate',
      request
    );
    
    clearInterval(progressInterval);
    if (onProgress) {
      onProgress(100, 'Complete!');
    }
    
    return response.data;
  } catch (error) {
    clearInterval(progressInterval);
    throw error;
  }
};

export const generateQuickQuestions = async (
  request: QuickQuestionRequest,
  onProgress?: (progress: number, stage: string) => void
): Promise<QuestionGenerationResponse> => {
  // Simulate progress updates
  const progressInterval = setInterval(() => {
    if (onProgress) {
      const stages = [
        'Analyzing input text...',
        'Extracting technical skills...',
        'Generating targeted questions...',
        'Creating evaluation criteria...',
        'Finalizing interview plan...'
      ];
      const randomStage = stages[Math.floor(Math.random() * stages.length)];
      const randomProgress = Math.min(95, Math.floor(Math.random() * 80) + 10);
      onProgress(randomProgress, randomStage);
    }
  }, 1500);

  try {
    const response = await api.post<QuestionGenerationResponse>(
      '/api/v1/questions/generate/quick',
      request
    );
    
    clearInterval(progressInterval);
    if (onProgress) {
      onProgress(100, 'Complete!');
    }
    
    return response.data;
  } catch (error) {
    clearInterval(progressInterval);
    throw error;
  }
};

// Authentication APIs
export const authAPI = {
  // Get Google OAuth login URL
  getGoogleLoginUrl: async (): Promise<GoogleAuthResponse> => {
    const response = await api.get<GoogleAuthResponse>('/api/v1/auth/google/login');
    return response.data;
  },

  // Handle Google OAuth callback
  googleCallback: async (code: string, state?: string): Promise<LoginResponse> => {
    const params = new URLSearchParams({ code });
    if (state) params.append('state', state);
    
    const response = await api.get<LoginResponse>(`/api/v1/auth/google/callback?${params}`);
    return response.data;
  },

  // Get current user profile
  getCurrentUser: async (token: string): Promise<User> => {
    const response = await api.get<User>('/api/v1/auth/me', {
      headers: addAuthHeaders(token)
    });
    return response.data;
  },

  // Update user preferences
  updatePreferences: async (
    preferences: Partial<Pick<User, 'email_notifications_enabled' | 'preferred_llm_provider'>>,
    token: string
  ): Promise<{ message: string; user: Pick<User, 'email_notifications_enabled' | 'preferred_llm_provider'> }> => {
    const response = await api.put('/api/v1/auth/me/preferences', preferences, {
      headers: addAuthHeaders(token)
    });
    return response.data;
  },

  // Logout
  logout: async (token: string): Promise<{ message: string }> => {
    const response = await api.post('/api/v1/auth/logout', {}, {
      headers: addAuthHeaders(token)
    });
    return response.data;
  },

  // Refresh access token
  refreshToken: async (refreshToken: string): Promise<AuthTokens> => {
    const response = await api.post<AuthTokens>('/api/v1/auth/refresh', { 
      refresh_token: refreshToken 
    });
    return response.data;
  }
};

// Async Question Generation APIs
export const asyncQuestionAPI = {
  // Start async question generation from uploaded documents
  startAsyncGeneration: async (
    request: AsyncQuestionGenerationRequest,
    token?: string
  ): Promise<TaskInitiationResponse> => {
    const response = await api.post<TaskInitiationResponse>(
      '/api/v1/questions/generate/async',
      request,
      { headers: addAuthHeaders(token) }
    );
    return response.data;
  },

  // Start async quick question generation from text
  startAsyncQuickGeneration: async (
    request: AsyncQuickQuestionRequest,
    token?: string
  ): Promise<TaskInitiationResponse> => {
    const response = await api.post<TaskInitiationResponse>(
      '/api/v1/questions/generate/quick/async',
      request,
      { headers: addAuthHeaders(token) }
    );
    return response.data;
  },

  // Get task status
  getTaskStatus: async (taskId: string, token?: string): Promise<TaskStatusResponse> => {
    const response = await api.get<TaskStatusResponse>(
      `/api/v1/tasks/${taskId}/status`,
      { headers: addAuthHeaders(token) }
    );
    return response.data;
  },

  // List user's tasks
  listTasks: async (
    params: {
      status?: string;
      task_type?: string;
      skip?: number;
      limit?: number;
    } = {},
    token?: string
  ): Promise<{ items: TaskStatusResponse[]; total: number; skip: number; limit: number }> => {
    const response = await api.get('/api/v1/tasks', {
      params,
      headers: addAuthHeaders(token)
    });
    return response.data;
  }
};

// Health check
export const healthCheck = async (): Promise<{ status: string }> => {
  const response = await api.get<{ status: string }>('/health');
  return response.data;
};

export default api;