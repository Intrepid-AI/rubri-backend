import React, { createContext, useContext, useState, useEffect } from 'react';
import type { ReactNode } from 'react';
import type { User, AuthTokens } from '../types/api';
import { authAPI } from '../services/api';

interface AuthContextType {
  user: User | null;
  tokens: AuthTokens | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (code: string, state?: string) => Promise<void>;
  logout: () => Promise<void>;
  updatePreferences: (preferences: Partial<Pick<User, 'email_notifications_enabled' | 'preferred_llm_provider'>>) => Promise<void>;
  refreshToken: () => Promise<boolean>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

const TOKEN_STORAGE_KEY = 'rubri_auth_tokens';
const USER_STORAGE_KEY = 'rubri_user';

interface AuthProviderProps {
  children: ReactNode;
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [tokens, setTokens] = useState<AuthTokens | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const isAuthenticated = !!(user && tokens);

  // Helper function to save auth state
  const saveAuthState = React.useCallback((user: User, tokens: AuthTokens) => {
    localStorage.setItem(TOKEN_STORAGE_KEY, JSON.stringify(tokens));
    localStorage.setItem(USER_STORAGE_KEY, JSON.stringify(user));
    setTokens(tokens);
    setUser(user);
  }, []);

  // Load authentication state from localStorage on mount
  useEffect(() => {
    const loadAuthState = async () => {
      try {
        // Check for tokens in URL parameters first (OAuth callback)
        const urlParams = new URLSearchParams(window.location.search);
        const accessToken = urlParams.get('access_token');
        const refreshToken = urlParams.get('refresh_token');

        if (accessToken && refreshToken) {
          try {
            // Get user profile with the new token
            const currentUser = await authAPI.getCurrentUser(accessToken);
            const tokens: AuthTokens = { 
              access_token: accessToken, 
              refresh_token: refreshToken,
              token_type: 'bearer',
              expires_in: 3600
            };
            
            // Save auth state
            saveAuthState(currentUser, tokens);
            
            // Check if we're on the generator page (OAuth redirect)
            if (window.location.pathname === '/generator') {
              // Trigger navigation to generator in the app
              window.dispatchEvent(new CustomEvent('navigate-to-generator'));
              // Clean up URL and redirect to root
              window.history.replaceState({}, document.title, '/');
            } else {
              // Clean up URL parameters
              window.history.replaceState({}, document.title, window.location.pathname);
            }
            
            setIsLoading(false);
            return;
          } catch (error) {
            console.error('Error handling OAuth callback:', error);
          }
        }

        // Check existing stored tokens
        const storedTokens = localStorage.getItem(TOKEN_STORAGE_KEY);
        const storedUser = localStorage.getItem(USER_STORAGE_KEY);

        if (storedTokens && storedUser) {
          const parsedTokens = JSON.parse(storedTokens) as AuthTokens;
          JSON.parse(storedUser) as User;

          // Check if tokens are still valid by fetching user profile
          try {
            const currentUser = await authAPI.getCurrentUser(parsedTokens.access_token);
            setTokens(parsedTokens);
            setUser(currentUser);
          } catch (error) {
            // Tokens might be expired, try to refresh
            try {
              const refreshed = await refreshTokenInternal(parsedTokens.refresh_token);
              if (!refreshed) {
                // Refresh failed, clear stored data
                clearAuthState();
              }
            } catch (refreshError) {
              clearAuthState();
            }
          }
        }
      } catch (error) {
        console.error('Error loading auth state:', error);
        clearAuthState();
      } finally {
        setIsLoading(false);
      }
    };

    loadAuthState();
  }, [saveAuthState]);

  const clearAuthState = () => {
    localStorage.removeItem(TOKEN_STORAGE_KEY);
    localStorage.removeItem(USER_STORAGE_KEY);
    setTokens(null);
    setUser(null);
  };

  const login = async (code: string, state?: string): Promise<void> => {
    try {
      setIsLoading(true);
      const response = await authAPI.googleCallback(code, state);
      saveAuthState(response.user, response.tokens);
      console.log('✅ Login successful:', response.user.email);
    } catch (error) {
      console.error('❌ Login failed:', error);
      throw error;
    } finally {
      setIsLoading(false);
    }
  };

  const logout = async (): Promise<void> => {
    try {
      if (tokens) {
        await authAPI.logout(tokens.access_token);
      }
    } catch (error) {
      console.error('Error during logout:', error);
    } finally {
      clearAuthState();
      console.log('✅ Logout successful');
    }
  };

  const updatePreferences = async (
    preferences: Partial<Pick<User, 'email_notifications_enabled' | 'preferred_llm_provider'>>
  ): Promise<void> => {
    if (!tokens || !user) {
      throw new Error('Not authenticated');
    }

    try {
      const updatedPrefs = await authAPI.updatePreferences(preferences, tokens.access_token);
      
      // Update user state with new preferences
      setUser(prev => prev ? {
        ...prev,
        email_notifications_enabled: updatedPrefs.user.email_notifications_enabled,
        preferred_llm_provider: updatedPrefs.user.preferred_llm_provider
      } : null);

      // Update localStorage
      if (user) {
        const updatedUser = {
          ...user,
          email_notifications_enabled: updatedPrefs.user.email_notifications_enabled,
          preferred_llm_provider: updatedPrefs.user.preferred_llm_provider
        };
        localStorage.setItem(USER_STORAGE_KEY, JSON.stringify(updatedUser));
      }

      console.log('✅ Preferences updated successfully');
    } catch (error) {
      console.error('❌ Failed to update preferences:', error);
      throw error;
    }
  };

  const refreshTokenInternal = async (refreshToken: string): Promise<boolean> => {
    try {
      const newTokens = await authAPI.refreshToken(refreshToken);
      
      if (user) {
        saveAuthState(user, newTokens);
        return true;
      }
      return false;
    } catch (error) {
      console.error('Token refresh failed:', error);
      return false;
    }
  };

  const refreshToken = async (): Promise<boolean> => {
    if (!tokens?.refresh_token) {
      return false;
    }
    return refreshTokenInternal(tokens.refresh_token);
  };

  // Set up automatic token refresh
  useEffect(() => {
    if (!tokens) return;

    const tokenExpiry = tokens.expires_in * 1000; // Convert to milliseconds
    const refreshTime = tokenExpiry - (5 * 60 * 1000); // Refresh 5 minutes before expiry

    const refreshTimeout = setTimeout(async () => {
      console.log('🔄 Auto-refreshing token...');
      const success = await refreshToken();
      if (!success) {
        console.log('❌ Auto-refresh failed, logging out...');
        await logout();
      }
    }, refreshTime);

    return () => clearTimeout(refreshTimeout);
  }, [tokens]);

  const contextValue: AuthContextType = {
    user,
    tokens,
    isAuthenticated,
    isLoading,
    login,
    logout,
    updatePreferences,
    refreshToken
  };

  return (
    <AuthContext.Provider value={contextValue}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};