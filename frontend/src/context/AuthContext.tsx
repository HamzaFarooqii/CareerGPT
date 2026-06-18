import { createContext, useContext, useState, useEffect, ReactNode } from 'react';

interface User {
  id: string;
  name: string;
  email: string;
  profile: {
    phone?: string;
    location?: string;
    skills?: string[];
    preferred_job_titles?: string[];
    preferred_locations?: string[];
    bio?: string;
    linkedin?: string;
    github?: string;
    portfolio?: string;
  };
  saved_jobs: string[];
  applications: any[];
  created_at: string;
}

interface AuthContextType {
  user: User | null;
  token: string | null;
  login: (token: string, user: User) => void;
  logout: () => void;
  updateUser: (user: User) => void;
  isAuthenticated: boolean;
}

const AuthContext = createContext<AuthContextType>({
  user: null,
  token: null,
  login: () => {},
  logout: () => {},
  updateUser: () => {},
  isAuthenticated: false,
});

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(() => localStorage.getItem('jm_token'));
  const [user, setUser] = useState<User | null>(() => {
    const stored = localStorage.getItem('jm_user');
    return stored ? JSON.parse(stored) : null;
  });

  const login = (newToken: string, newUser: User) => {
    localStorage.setItem('jm_token', newToken);
    localStorage.setItem('jm_user', JSON.stringify(newUser));
    setToken(newToken);
    setUser(newUser);
  };

  const logout = () => {
    localStorage.removeItem('jm_token');
    localStorage.removeItem('jm_user');
    setToken(null);
    setUser(null);
  };

  const updateUser = (newUser: User) => {
    localStorage.setItem('jm_user', JSON.stringify(newUser));
    setUser(newUser);
  };

  return (
    <AuthContext.Provider value={{
      user, token, login, logout, updateUser,
      isAuthenticated: !!token && !!user,
    }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);
