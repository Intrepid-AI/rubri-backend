import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import type { User, AuthTokens, LoginResponse } from '../types/api';
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

  // Load authentication state from localStorage on mount
  useEffect(() => {
    const loadAuthState = async () => {
      try {
        const storedTokens = localStorage.getItem(TOKEN_STORAGE_KEY);
        const storedUser = localStorage.getItem(USER_STORAGE_KEY);

        if (storedTokens && storedUser) {
          const parsedTokens = JSON.parse(storedTokens) as AuthTokens;
          const parsedUser = JSON.parse(storedUser) as User;

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
  }, []);

  const saveAuthState = (user: User, tokens: AuthTokens) => {
    localStorage.setItem(TOKEN_STORAGE_KEY, JSON.stringify(tokens));
    localStorage.setItem(USER_STORAGE_KEY, JSON.stringify(user));
    setTokens(tokens);
    setUser(user);
  };

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