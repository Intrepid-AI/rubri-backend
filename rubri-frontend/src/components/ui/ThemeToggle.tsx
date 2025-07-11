import React from 'react';
import { Sun, Moon } from 'lucide-react';
import { clsx } from 'clsx';

interface ThemeToggleProps {
  isDark: boolean;
  onToggle: () => void;
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

export const ThemeToggle: React.FC<ThemeToggleProps> = ({
  isDark,
  onToggle,
  size = 'md',
  className
}) => {
  const sizes = {
    sm: 'w-10 h-6',
    md: 'w-12 h-7',
    lg: 'w-14 h-8'
  };

  const toggleSizes = {
    sm: 'w-4 h-4',
    md: 'w-5 h-5',
    lg: 'w-6 h-6'
  };

  const iconSizes = {
    sm: 'w-3 h-3',
    md: 'w-3.5 h-3.5',
    lg: 'w-4 h-4'
  };

  return (
    <button
      onClick={onToggle}
      className={clsx(
        'relative inline-flex items-center rounded-full transition-colors duration-200 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 focus:ring-offset-background',
        isDark ? 'bg-primary-600' : 'bg-gray-300',
        sizes[size],
        className
      )}
      aria-label={`Switch to ${isDark ? 'light' : 'dark'} mode`}
    >
      {/* Toggle Circle */}
      <span
        className={clsx(
          'inline-block rounded-full bg-white shadow-lg transform transition-transform duration-200 flex items-center justify-center',
          isDark ? 'translate-x-6' : 'translate-x-1',
          toggleSizes[size]
        )}
      >
        {isDark ? (
          <Moon className={clsx('text-primary-600', iconSizes[size])} />
        ) : (
          <Sun className={clsx('text-yellow-500', iconSizes[size])} />
        )}
      </span>

      {/* Background Icons */}
      <div className="absolute inset-0 flex items-center justify-between px-1">
        <Sun 
          className={clsx(
            'text-white transition-opacity duration-200',
            isDark ? 'opacity-0' : 'opacity-100',
            iconSizes[size]
          )} 
        />
        <Moon 
          className={clsx(
            'text-white transition-opacity duration-200',
            isDark ? 'opacity-100' : 'opacity-0',
            iconSizes[size]
          )} 
        />
      </div>
    </button>
  );
};