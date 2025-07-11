import React from 'react';
import { clsx } from 'clsx';

interface TextareaProps extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  label?: string;
  error?: string;
  helper?: string;
  showCharCount?: boolean;
  maxLength?: number;
}

export const Textarea: React.FC<TextareaProps> = ({
  label,
  error,
  helper,
  showCharCount = false,
  maxLength,
  className,
  id,
  value,
  ...props
}) => {
  const textareaId = id || label?.toLowerCase().replace(/\s+/g, '-');
  const currentLength = String(value || '').length;
  
  return (
    <div className="w-full">
      {label && (
        <label 
          htmlFor={textareaId}
          className="block text-sm font-medium text-foreground mb-1"
        >
          {label}
          {props.required && <span className="text-red-500 ml-1">*</span>}
        </label>
      )}
      
      <textarea
        id={textareaId}
        value={value}
        maxLength={maxLength}
        className={clsx(
          'input min-h-[120px] resize-y',
          error && 'border-red-300 focus:border-red-500 focus:ring-red-500',
          className
        )}
        {...props}
      />
      
      <div className="flex justify-between items-start mt-1">
        <div className="flex-1">
          {error && (
            <p className="text-sm text-red-600">
              {error}
            </p>
          )}
          
          {helper && !error && (
            <p className="text-sm text-foreground-muted">
              {helper}
            </p>
          )}
        </div>
        
        {(showCharCount || maxLength) && (
          <p className={clsx(
            'text-xs ml-2 flex-shrink-0',
            maxLength && currentLength > maxLength * 0.9 
              ? 'text-orange-400' 
              : 'text-foreground-subtle'
          )}>
            {maxLength ? `${currentLength}/${maxLength}` : currentLength}
          </p>
        )}
      </div>
    </div>
  );
};