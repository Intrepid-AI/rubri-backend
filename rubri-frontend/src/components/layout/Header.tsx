import React from 'react';
import { Github, ExternalLink } from 'lucide-react';
import { Button, ThemeToggle } from '../ui';
import { useTheme } from '../../contexts/ThemeContext';

export const Header: React.FC = () => {
  const { isDark, toggleTheme } = useTheme();
  
  return (
    <header className="bg-background border-b border-border sticky top-0 z-50 backdrop-blur-sm">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          {/* Logo and Brand */}
          <div className="flex items-center space-x-4">
            <div className="flex items-center space-x-3">
              <img 
                src="/logo.png" 
                alt="Interview Valley" 
                className="h-10 w-10 object-contain"
              />
              <div>
                <h1 className="text-xl font-bold text-foreground">
                  Interview Valley
                </h1>
                <p className="text-xs text-foreground-muted -mt-1">
                  Your path to better Hires
                </p>
              </div>
            </div>
          </div>
          
          {/* Navigation */}
          <nav className="hidden md:flex items-center space-x-6">
            <a 
              href="#features" 
              className="text-foreground-muted hover:text-foreground text-sm font-medium transition-colors"
            >
              Features
            </a>
            <a 
              href="#how-it-works" 
              className="text-foreground-muted hover:text-foreground text-sm font-medium transition-colors"
            >
              How it Works
            </a>
            <a 
              href="#pricing" 
              className="text-foreground-muted hover:text-foreground text-sm font-medium transition-colors"
            >
              Pricing
            </a>
          </nav>
          
          {/* Action Buttons */}
          <div className="flex items-center space-x-3">
            <ThemeToggle
              isDark={isDark}
              onToggle={toggleTheme}
              size="sm"
            />
            
            <a
              href="https://github.com/your-repo"
              target="_blank"
              rel="noopener noreferrer"
              className="text-foreground-subtle hover:text-foreground transition-colors"
            >
              <Github className="h-5 w-5" />
            </a>
            
            <Button variant="outline" size="sm" leftIcon={ExternalLink}>
              API Docs
            </Button>
            
            <Button size="sm">
              Get Started
            </Button>
          </div>
        </div>
      </div>
    </header>
  );
};