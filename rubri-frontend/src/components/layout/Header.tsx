import React, { useState } from 'react';
import { Button, ThemeToggle } from '../ui';
import { useTheme } from '../../contexts/ThemeContext';
import { useAuth } from '../../contexts/AuthContext';
import { LogIn, LogOut, User } from 'lucide-react';

export const Header: React.FC = () => {
  const { isDark, toggleTheme } = useTheme();
  const { user, isAuthenticated, logout } = useAuth();
  const [activeItem, setActiveItem] = useState('home');
  
  const navItems = [
    { id: 'home', label: 'Home', href: '#' },
    { id: 'features', label: 'Features', href: '#features' },
    { id: 'how-it-works', label: 'How it Works', href: '#how-it-works' },
    { id: 'pricing', label: 'Pricing', href: '#pricing' }
  ];
  
  const handleNavClick = (item: typeof navItems[0]) => {
    setActiveItem(item.id);
    
    if (item.id === 'home') {
      // Scroll to top of page
      window.scrollTo({
        top: 0,
        behavior: 'smooth'
      });
    }
  };

  const handleLogin = async () => {
    try {
      // Call the backend to get the Google OAuth URL
      const response = await fetch(`${import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'}/api/v1/auth/google/login`);
      const data = await response.json();
      
      if (data.authorization_url) {
        // Redirect to Google OAuth page
        window.location.href = data.authorization_url;
      } else {
        console.error('No authorization URL received');
      }
    } catch (error) {
      console.error('Failed to initiate Google OAuth:', error);
    }
  };

  const handleLogout = async () => {
    try {
      await logout();
    } catch (error) {
      console.error('Logout failed:', error);
    }
  };
  
  return (
    <header className="bg-background border-b border-border sticky top-0 z-50 backdrop-blur-sm">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          {/* Logo and Brand */}
          <div className="flex items-center space-x-4">
            <div 
              className="flex items-center space-x-3 cursor-pointer hover:opacity-80 transition-opacity duration-200"
              onClick={() => {
                setActiveItem('home');
                window.scrollTo({
                  top: 0,
                  behavior: 'smooth'
                });
              }}
            >
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
            {navItems.map((item) => (
              <a 
                key={item.id}
                href={item.href} 
                onClick={(e) => {
                  if (item.id === 'home') {
                    e.preventDefault();
                  }
                  handleNavClick(item);
                }}
                className={`relative text-sm font-medium transition-colors duration-200 ${
                  activeItem === item.id 
                    ? 'text-foreground' 
                    : 'text-foreground-muted hover:text-foreground'
                }`}
              >
                {item.label}
                {activeItem === item.id && (
                  <div className="absolute -bottom-1 left-0 right-0 h-0.5 bg-primary-500 rounded-full"></div>
                )}
              </a>
            ))}
          </nav>
          
          {/* Action Buttons */}
          <div className="flex items-center space-x-3">
            <ThemeToggle
              isDark={isDark}
              onToggle={toggleTheme}
              size="sm"
            />
            
            {isAuthenticated ? (
              <>
                {/* User Info */}
                <div className="flex items-center space-x-2 text-sm text-foreground-subtle">
                  <User className="h-4 w-4" />
                  <span>{user?.name}</span>
                </div>
                
                {/* Logout Button */}
                <Button 
                  size="sm" 
                  variant="outline"
                  onClick={handleLogout}
                  leftIcon={LogOut}
                >
                  Logout
                </Button>
              </>
            ) : (
              <Button 
                size="sm"
                onClick={handleLogin}
                leftIcon={LogIn}
              >
                Sign in with Google
              </Button>
            )}
          </div>
        </div>
      </div>
    </header>
  );
};