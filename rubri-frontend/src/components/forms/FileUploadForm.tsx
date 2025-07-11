import React, { useState } from 'react';
import { FileUpload, Input, Button } from '../ui';
import { AlertCircle } from 'lucide-react';

interface FileUploadFormProps {
  onSubmit: (data: { jdFile?: File; resumeFile?: File; positionTitle: string }) => void;
  isLoading?: boolean;
  error?: string;
}

export const FileUploadForm: React.FC<FileUploadFormProps> = ({
  onSubmit,
  isLoading = false,
  error
}) => {
  const [jdFile, setJdFile] = useState<File | undefined>();
  const [resumeFile, setResumeFile] = useState<File | undefined>();
  const [positionTitle, setPositionTitle] = useState('');
  const [validationErrors, setValidationErrors] = useState<Record<string, string>>({});

  const validateForm = () => {
    const errors: Record<string, string> = {};
    
    if (!positionTitle.trim()) {
      errors.positionTitle = 'Position title is required';
    }
    
    if (!jdFile && !resumeFile) {
      errors.files = 'At least one file (Job Description or Resume) must be uploaded';
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
      jdFile,
      resumeFile,
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
      
      {/* File Uploads */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <FileUpload
          label="Job Description"
          selectedFile={jdFile}
          onFileSelect={setJdFile}
          onFileRemove={() => setJdFile(undefined)}
          disabled={isLoading}
        />
        
        <FileUpload
          label="Resume"
          selectedFile={resumeFile}
          onFileSelect={setResumeFile}
          onFileRemove={() => setResumeFile(undefined)}
          disabled={isLoading}
        />
      </div>
      
      {/* Validation Error for Files */}
      {validationErrors.files && (
        <div className="flex items-center space-x-2 text-sm text-red-600">
          <AlertCircle className="h-4 w-4" />
          <span>{validationErrors.files}</span>
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
          Upload at least one document to generate tailored interview questions
        </p>
        <p className="text-xs text-gray-400 mt-1">
          Supported formats: PDF, DOC, DOCX, TXT • Max file size: 10MB
        </p>
      </div>
    </form>
  );
};