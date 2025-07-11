import React, { useState } from 'react';
import { Input, Textarea, Button } from '../ui';
import { AlertCircle } from 'lucide-react';

interface TextInputFormProps {
  onSubmit: (data: { jobDescription?: string; resumeText?: string; positionTitle: string }) => void;
  isLoading?: boolean;
  error?: string;
}

export const TextInputForm: React.FC<TextInputFormProps> = ({
  onSubmit,
  isLoading = false,
  error
}) => {
  const [jobDescription, setJobDescription] = useState('');
  const [resumeText, setResumeText] = useState('');
  const [positionTitle, setPositionTitle] = useState('');
  const [validationErrors, setValidationErrors] = useState<Record<string, string>>({});

  const validateForm = () => {
    const errors: Record<string, string> = {};
    
    if (!positionTitle.trim()) {
      errors.positionTitle = 'Position title is required';
    }
    
    if (!jobDescription.trim() && !resumeText.trim()) {
      errors.content = 'At least one text field (Job Description or Resume) must be filled';
    }
    
    setValidationErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!validateForm()) {
      return;
    }
    
    onSubmit({
      jobDescription: jobDescription.trim() || undefined,
      resumeText: resumeText.trim() || undefined,
      positionTitle: positionTitle.trim()
    });
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      {/* Position Title */}
      <Input
        label="Position Title"
        placeholder="e.g., Senior Software Engineer, Data Scientist"
        value={positionTitle}
        onChange={(e) => setPositionTitle(e.target.value)}
        error={validationErrors.positionTitle}
        required
      />
      
      {/* Text Inputs */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Textarea
          label="Job Description"
          placeholder="Paste the job description here..."
          value={jobDescription}
          onChange={(e) => setJobDescription(e.target.value)}
          rows={12}
          maxLength={10000}
          showCharCount
          helper="Include requirements, responsibilities, and preferred qualifications"
        />
        
        <Textarea
          label="Resume"
          placeholder="Paste the candidate's resume here..."
          value={resumeText}
          onChange={(e) => setResumeText(e.target.value)}
          rows={12}
          maxLength={10000}
          showCharCount
          helper="Include work experience, skills, and education"
        />
      </div>
      
      {/* Validation Error for Content */}
      {validationErrors.content && (
        <div className="flex items-center space-x-2 text-sm text-red-600">
          <AlertCircle className="h-4 w-4" />
          <span>{validationErrors.content}</span>
        </div>
      )}
      
      {/* API Error */}
      {error && (
        <div className="flex items-center space-x-2 text-sm text-red-600 bg-red-50 p-3 rounded-md">
          <AlertCircle className="h-4 w-4" />
          <span>{error}</span>
        </div>
      )}
      
      {/* Submit Button */}
      <div className="flex justify-center">
        <Button
          type="submit"
          size="lg"
          loading={isLoading}
          disabled={isLoading}
          className="px-8 py-3"
        >
          Generate Interview Questions
        </Button>
      </div>
      
      {/* Helper Text */}
      <div className="text-center">
        <p className="text-sm text-gray-500">
          Fill in at least one text field to generate tailored interview questions
        </p>
        <p className="text-xs text-gray-400 mt-1">
          Maximum 10,000 characters per field
        </p>
      </div>
    </form>
  );
};