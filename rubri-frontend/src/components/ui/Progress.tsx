import React from 'react';
import { clsx } from 'clsx';

interface ProgressProps {
  value: number; // 0-100
  size?: 'sm' | 'md' | 'lg';
  color?: 'primary' | 'success' | 'warning' | 'error';
  showLabel?: boolean;
  label?: string;
  className?: string;
}

export const Progress: React.FC<ProgressProps> = ({
  value,
  size = 'md',
  color = 'primary',
  showLabel = true,
  label,
  className
}) => {
  const clampedValue = Math.min(100, Math.max(0, value));
  
  const sizes = {
    sm: 'h-2',
    md: 'h-3',
    lg: 'h-4'
  };
  
  const colors = {
    primary: 'bg-primary-600',
    success: 'bg-green-600',
    warning: 'bg-yellow-600',
    error: 'bg-red-600'
  };
  
  return (
    <div className={clsx('w-full', className)}>
      {(showLabel || label) && (
        <div className="flex justify-between items-center mb-2">
          <span className="text-sm font-medium text-foreground">
            {label || 'Progress'}
          </span>
          {showLabel && (
            <span className="text-sm text-foreground-muted">
              {Math.round(clampedValue)}%
            </span>
          )}
        </div>
      )}
      
      <div className={clsx(
        'w-full bg-surface-100 rounded-full overflow-hidden',
        sizes[size]
      )}>
        <div
          className={clsx(
            'transition-all duration-300 ease-out',
            colors[color],
            sizes[size]
          )}
          style={{ width: `${clampedValue}%` }}
        />
      </div>
    </div>
  );
};