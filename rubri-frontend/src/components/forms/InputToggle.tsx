import React from 'react';
import { clsx } from 'clsx';
import { Upload, Type } from 'lucide-react';

interface InputToggleProps {
  mode: 'upload' | 'text';
  onModeChange: (mode: 'upload' | 'text') => void;
  className?: string;
}

export const InputToggle: React.FC<InputToggleProps> = ({
  mode,
  onModeChange,
  className
}) => {
  return (
    <div className={clsx('flex bg-gray-100 rounded-lg p-1', className)}>
      <button
        type="button"
        onClick={() => onModeChange('upload')}
        className={clsx(
          'flex items-center justify-center px-4 py-2 rounded-md text-sm font-medium transition-all',
          'focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 focus:ring-offset-gray-100',
          mode === 'upload'
            ? 'bg-white text-primary-700 shadow-sm'
            : 'text-gray-600 hover:text-gray-900'
        )}
      >
        <Upload className="h-4 w-4 mr-2" />
        Upload Files
      </button>
      
      <button
        type="button"
        onClick={() => onModeChange('text')}
        className={clsx(
          'flex items-center justify-center px-4 py-2 rounded-md text-sm font-medium transition-all',
          'focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 focus:ring-offset-gray-100',
          mode === 'text'
            ? 'bg-white text-primary-700 shadow-sm'
            : 'text-gray-600 hover:text-gray-900'
        )}
      >
        <Type className="h-4 w-4 mr-2" />
        Paste Text
      </button>
    </div>
  );
};