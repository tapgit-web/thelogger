"use client";

import { useState, useEffect } from "react";
import { useAuth } from "@/context/AuthContext";
import { Terminal, Key, Shield, AlertTriangle } from "lucide-react";

export default function Login() {
  const { login, isActivated, activate } = useAuth();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [activationKey, setActivationKey] = useState("");
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);
  const [needsActivation, setNeedsActivation] = useState(false);

  useEffect(() => {
    // If not activated, ask for activation key first
    setNeedsActivation(!isActivated);
  }, [isActivated]);

  const handleActivation = async (e: React.FormEvent) => {
    e.preventDefault();
    const cleanKey = activationKey.trim().toUpperCase();
    if (!cleanKey) {
      setError("Please enter a valid activation key");
      return;
    }
    
    setLoading(true);
    setError("");

    // Instant local bypass for Developer/Demo Key
    if (cleanKey === "DEV-LOGGER-LIFETIME") {
      activate(cleanKey);
      setNeedsActivation(false);
      setMessage("Developer mode activated successfully!");
      setLoading(false);
      return;
    }
    
    try {
      // Direct call to TAP sentinel API (replicating core desktop app backend logic)
      const res = await fetch("https://tap-server-v2.onrender.com/activate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          key: cleanKey,
          hwid: "WEB_LICENSE_" + Math.random().toString(36).substring(2, 10).toUpperCase()
        })
      });

      const data = await res.json();
      
      if (res.ok && data.status === "success") {
        activate(cleanKey);
        setNeedsActivation(false);
        setMessage("Activation successful! Please log in.");
      } else {
        setError(data.message || "Invalid activation key. Use 'DEV-LOGGER-LIFETIME' for demo mode.");
      }
    } catch (err) {
      // Fallback if activation server is offline but key is a known desktop license pattern
      if (cleanKey.startsWith("SO24-") || cleanKey.startsWith("ORAJ-")) {
        activate(cleanKey);
        setNeedsActivation(false);
        setMessage("Offline/Development Activation successful!");
      } else {
        setError("Activation server connection failed. Use 'DEV-LOGGER-LIFETIME' to bypass offline.");
      }
    } finally {
      setLoading(false);
    }
  };

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!username || !password) {
      setError("Please enter both username and password");
      return;
    }

    setLoading(true);
    setError("");

    try {
      const response = await fetch("http://localhost:8000/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password })
      });

      const data = await response.json();
      if (response.ok) {
        login(data.username, data.role);
      } else {
        setError(data.detail || "Invalid credentials");
      }
    } catch (err) {
      // Frontend-only demo login fallback if backend isn't running yet
      if (username === "admin" && password === "admin123") {
        login("admin", "admin");
      } else if (username === "user" && password === "user123") {
        login("user", "user");
      } else {
        setError("Could not connect to backend server. Try default credentials: admin/admin123");
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="auth-wrapper">
      <div className="card auth-card">
        <div className="auth-header">
          <div className="auth-logo" style={{ display: "flex", justifyContent: "center", alignItems: "center", gap: "8px" }}>
            <Terminal size={32} style={{ color: "var(--color-primary)" }} />
            THE <span>LOGGER</span>
          </div>
          <p className="page-subtitle">
            {needsActivation 
              ? "System Activation Required" 
              : "Industrial Modbus Monitoring & Logging System"
            }
          </p>
        </div>

        {error && (
          <div style={{ 
            backgroundColor: "rgba(239, 68, 68, 0.1)", 
            border: "1px solid var(--color-danger)", 
            color: "var(--color-danger)", 
            padding: "12px", 
            borderRadius: "var(--radius-sm)", 
            marginBottom: "20px",
            fontSize: "14px",
            display: "flex",
            alignItems: "center",
            gap: "8px"
          }}>
            <AlertTriangle size={16} />
            {error}
          </div>
        )}

        {message && (
          <div style={{ 
            backgroundColor: "rgba(16, 185, 129, 0.1)", 
            border: "1px solid var(--color-primary)", 
            color: "var(--color-primary)", 
            padding: "12px", 
            borderRadius: "var(--radius-sm)", 
            marginBottom: "20px",
            fontSize: "14px"
          }}>
            {message}
          </div>
        )}

        {needsActivation ? (
          <form onSubmit={handleActivation}>
            <div className="form-group">
              <label className="form-label" htmlFor="activationKey">
                Product Activation Key
              </label>
              <div style={{ position: "relative" }}>
                <Key size={16} style={{ position: "absolute", left: "14px", top: "14px", color: "var(--text-muted)" }} />
                <input
                  id="activationKey"
                  type="text"
                  placeholder="XXXX-XXXX-XXXX-XXXX"
                  className="form-control"
                  style={{ paddingLeft: "42px" }}
                  value={activationKey}
                  onChange={(e) => setActivationKey(e.target.value)}
                  disabled={loading}
                />
              </div>
            </div>
            <button 
              type="submit" 
              className="btn btn-primary" 
              style={{ width: "100%", height: "45px" }}
              disabled={loading}
            >
              {loading ? "Activating..." : "Activate Software"}
            </button>
            
            <p style={{ marginTop: "16px", color: "var(--text-muted)", fontSize: "12px", textAlign: "center" }}>
              Enter your standard TAP Sentinel activation key.
              <br />
              For demo/testing, use: <code>DEV-LOGGER-LIFETIME</code>
            </p>
          </form>
        ) : (
          <form onSubmit={handleLogin}>
            <div className="form-group">
              <label className="form-label" htmlFor="username">
                Username
              </label>
              <div style={{ position: "relative" }}>
                <Shield size={16} style={{ position: "absolute", left: "14px", top: "14px", color: "var(--text-muted)" }} />
                <input
                  id="username"
                  type="text"
                  placeholder="Enter username"
                  className="form-control"
                  style={{ paddingLeft: "42px" }}
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  disabled={loading}
                />
              </div>
            </div>

            <div className="form-group" style={{ marginBottom: "24px" }}>
              <label className="form-label" htmlFor="password">
                Password
              </label>
              <input
                id="password"
                type="password"
                placeholder="Enter password"
                className="form-control"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                disabled={loading}
              />
            </div>

            <button 
              type="submit" 
              className="btn btn-primary" 
              style={{ width: "100%", height: "45px" }}
              disabled={loading}
            >
              {loading ? "Logging In..." : "Sign In"}
            </button>

            <p style={{ marginTop: "16px", color: "var(--text-muted)", fontSize: "12px", textAlign: "center" }}>
              Log in to access live dashboards and polling telemetry.
              <br />
              Admin: <code>admin</code> / <code>admin123</code>
            </p>
          </form>
        )}
      </div>
    </main>
  );
}
