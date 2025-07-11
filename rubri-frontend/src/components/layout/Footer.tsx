import React from 'react';
import { Github, Mail } from 'lucide-react';

export const Footer: React.FC = () => {
  return (
    <footer className="bg-background-muted border-t border-border">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
          {/* Brand */}
          <div className="col-span-1 md:col-span-2">
            <div className="flex items-center space-x-3 mb-4">
              <img 
                src="/logo.png" 
                alt="Interview Valley" 
                className="h-8 w-8 object-contain"
              />
              <span className="text-lg font-bold text-foreground">Interview Valley</span>
            </div>
            <p className="text-foreground-muted text-sm max-w-md mb-2">
              Your path to better Hires
            </p>
            <p className="text-foreground-muted text-sm max-w-md mb-4">
              AI-powered interview question generation platform that creates comprehensive, 
              tailored technical assessments based on job descriptions and candidate resumes.
            </p>
            <div className="flex items-center space-x-4">
              <a
                href="https://github.com/your-repo"
                target="_blank"
                rel="noopener noreferrer"
                className="text-foreground-subtle hover:text-foreground transition-colors"
              >
                <Github className="h-5 w-5" />
              </a>
              <a
                href="mailto:contact@interviewvalley.ai"
                className="text-foreground-subtle hover:text-foreground transition-colors"
              >
                <Mail className="h-5 w-5" />
              </a>
            </div>
          </div>
          
          {/* Product */}
          <div>
            <h3 className="text-sm font-semibold text-foreground mb-4">Product</h3>
            <ul className="space-y-2">
              <li>
                <a href="#features" className="text-sm text-foreground-muted hover:text-foreground transition-colors">
                  Features
                </a>
              </li>
              <li>
                <a href="#pricing" className="text-sm text-foreground-muted hover:text-foreground transition-colors">
                  Pricing
                </a>
              </li>
              <li>
                <a href="#api" className="text-sm text-foreground-muted hover:text-foreground transition-colors">
                  API
                </a>
              </li>
              <li>
                <a href="#integrations" className="text-sm text-foreground-muted hover:text-foreground transition-colors">
                  Integrations
                </a>
              </li>
            </ul>
          </div>
          
          {/* Support */}
          <div>
            <h3 className="text-sm font-semibold text-foreground mb-4">Support</h3>
            <ul className="space-y-2">
              <li>
                <a href="#docs" className="text-sm text-foreground-muted hover:text-foreground transition-colors">
                  Documentation
                </a>
              </li>
              <li>
                <a href="#help" className="text-sm text-foreground-muted hover:text-foreground transition-colors">
                  Help Center
                </a>
              </li>
              <li>
                <a href="#contact" className="text-sm text-foreground-muted hover:text-foreground transition-colors">
                  Contact Us
                </a>
              </li>
              <li>
                <a href="#status" className="text-sm text-foreground-muted hover:text-foreground transition-colors">
                  Status
                </a>
              </li>
            </ul>
          </div>
        </div>
        
        <div className="border-t border-border mt-8 pt-8 flex flex-col md:flex-row justify-between items-center">
          <p className="text-xs text-foreground-subtle">
            © 2024 Interview Valley. All rights reserved.
          </p>
          <div className="flex items-center space-x-6 mt-4 md:mt-0">
            <a href="#privacy" className="text-xs text-foreground-subtle hover:text-foreground-muted transition-colors">
              Privacy Policy
            </a>
            <a href="#terms" className="text-xs text-foreground-subtle hover:text-foreground-muted transition-colors">
              Terms of Service
            </a>
          </div>
        </div>
      </div>
    </footer>
  );
};