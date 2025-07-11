import React, { useCallback, useState } from 'react';
import { useDropzone } from 'react-dropzone';
import { clsx } from 'clsx';
import { Upload, File, X, AlertCircle } from 'lucide-react';

interface FileUploadProps {
  label: string;
  accept?: Record<string, string[]>;
  maxSize?: number; // in bytes
  onFileSelect: (file: File) => void;
  onFileRemove?: () => void;
  selectedFile?: File;
  error?: string;
  disabled?: boolean;
  className?: string;
}

const defaultAccept = {
  'application/pdf': ['.pdf'],
  'application/msword': ['.doc'],
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
  'text/plain': ['.txt']
};

export const FileUpload: React.FC<FileUploadProps> = ({
  label,
  accept = defaultAccept,
  maxSize = 10 * 1024 * 1024, // 10MB
  onFileSelect,
  onFileRemove,
  selectedFile,
  error,
  disabled = false,
  className
}) => {
  const [dragError, setDragError] = useState<string>('');

  const onDrop = useCallback((acceptedFiles: File[], rejectedFiles: any[]) => {
    setDragError('');
    
    if (rejectedFiles.length > 0) {
      const rejection = rejectedFiles[0];
      if (rejection.errors?.some((e: any) => e.code === 'file-too-large')) {
        setDragError(`File is too large. Maximum size is ${(maxSize / 1024 / 1024).toFixed(1)}MB`);
      } else if (rejection.errors?.some((e: any) => e.code === 'file-invalid-type')) {
        setDragError('Invalid file type. Please upload PDF, DOC, DOCX, or TXT files.');
      } else {
        setDragError('Invalid file. Please try again.');
      }
      return;
    }
    
    if (acceptedFiles.length > 0) {
      onFileSelect(acceptedFiles[0]);
    }
  }, [onFileSelect, maxSize]);

  const { getRootProps, getInputProps, isDragActive, isDragReject } = useDropzone({
    onDrop,
    accept,
    maxSize,
    multiple: false,
    disabled
  });

  const displayError = error || dragError;

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
  };

  return (
    <div className={clsx('w-full', className)}>
      <label className="block text-sm font-medium text-foreground mb-2">
        {label}
      </label>
      
      {!selectedFile ? (
        <div
          {...getRootProps()}
          className={clsx(
            'border-2 border-dashed rounded-lg p-6 text-center cursor-pointer transition-colors',
            isDragActive && !isDragReject && 'border-primary-400 bg-primary-50',
            isDragReject && 'border-red-400 bg-red-50',
            !isDragActive && !displayError && 'border-border hover:border-border-hover',
            displayError && 'border-red-300 bg-red-50',
            disabled && 'opacity-50 cursor-not-allowed'
          )}
        >
          <input {...getInputProps()} />
          
          <Upload className={clsx(
            'mx-auto h-12 w-12 mb-4',
            isDragActive && !isDragReject && 'text-primary-500',
            isDragReject && 'text-red-500',
            !isDragActive && !displayError && 'text-foreground-subtle',
            displayError && 'text-red-500'
          )} />
          
          <div className="space-y-2">
            <p className="text-sm font-medium text-foreground">
              {isDragActive ? 'Drop the file here' : 'Drag & drop a file here'}
            </p>
            <p className="text-xs text-foreground-muted">
              or click to browse
            </p>
            <p className="text-xs text-foreground-subtle">
              PDF, DOC, DOCX, TXT up to {(maxSize / 1024 / 1024).toFixed(1)}MB
            </p>
          </div>
        </div>
      ) : (
        <div className="border border-border rounded-lg p-4 bg-surface-100">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <File className="h-8 w-8 text-primary-600" />
              <div>
                <p className="text-sm font-medium text-foreground">
                  {selectedFile.name}
                </p>
                <p className="text-xs text-foreground-muted">
                  {formatFileSize(selectedFile.size)}
                </p>
              </div>
            </div>
            
            {onFileRemove && (
              <button
                onClick={onFileRemove}
                className="p-1 hover:bg-surface-200 rounded-full transition-colors"
                disabled={disabled}
              >
                <X className="h-4 w-4 text-foreground-muted" />
              </button>
            )}
          </div>
        </div>
      )}
      
      {displayError && (
        <div className="mt-2 flex items-center space-x-2 text-sm text-red-600">
          <AlertCircle className="h-4 w-4" />
          <span>{displayError}</span>
        </div>
      )}
    </div>
  );
};