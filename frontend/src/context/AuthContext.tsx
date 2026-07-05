"use client";

import React, { createContext, useContext, useState, useEffect } from "react";
import { useRouter, usePathname } from "next/navigation";

interface User {
  username: string;
  role: "admin" | "user";
}

interface AuthContextType {
  user: User | null;
  isAuthenticated: boolean;
  isActivated: boolean;
  activationKey: string | null;
  login: (username: string, role: "admin" | "user") => void;
  logout: () => void;
  activate: (key: string) => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isActivated, setIsActivated] = useState<boolean>(false);
  const [activationKey, setActivationKey] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    // Load auth status from localStorage on startup
    const storedUser = localStorage.getItem("logger_user");
    const storedRole = localStorage.getItem("logger_role");
    const storedActivated = localStorage.getItem("logger_activated");
    const storedKey = localStorage.getItem("logger_activation_key");

    if (storedUser && storedRole) {
      setUser({ username: storedUser, role: storedRole as "admin" | "user" });
    }
    
    if (storedActivated === "true") {
      setIsActivated(true);
    }
    
    if (storedKey) {
      setActivationKey(storedKey);
    }
    
    setIsLoading(false);
  }, []);

  useEffect(() => {
    if (isLoading) return;

    const authenticated = !!user;
    
    if (!authenticated && pathname !== "/login") {
      router.push("/login");
    } else if (authenticated && pathname === "/login") {
      router.push("/dashboard");
    }
  }, [user, pathname, isLoading, router]);

  const login = (username: string, role: "admin" | "user") => {
    localStorage.setItem("logger_user", username);
    localStorage.setItem("logger_role", role);
    setUser({ username, role });
    router.push("/dashboard");
  };

  const logout = () => {
    localStorage.removeItem("logger_user");
    localStorage.removeItem("logger_role");
    setUser(null);
    router.push("/login");
  };

  const activate = (key: string) => {
    localStorage.setItem("logger_activated", "true");
    localStorage.setItem("logger_activation_key", key);
    setIsActivated(true);
    setActivationKey(key);
  };

  const isAuthenticated = !!user;

  return (
    <AuthContext.Provider value={{ user, isAuthenticated, isActivated, activationKey, login, logout, activate }}>
      {!isLoading && children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
