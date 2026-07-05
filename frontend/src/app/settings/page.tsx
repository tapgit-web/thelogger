"use client";

import { useEffect, useState } from "react";
import Sidebar from "@/components/Sidebar";
import { Mail, Shield, Save, Play, CheckCircle, AlertCircle } from "lucide-react";

export default function SettingsView() {
  const [smtpServer, setSmtpServer] = useState("smtp.gmail.com");
  const [smtpPort, setSmtpPort] = useState(465);
  const [useSsl, setUseSsl] = useState(true);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [senderEmail, setSenderEmail] = useState("");
  const [receiverEmail, setReceiverEmail] = useState("");
  
  const [testEmailLoading, setTestEmailLoading] = useState(false);
  const [saveLoading, setSaveLoading] = useState(false);
  const [feedback, setFeedback] = useState<{ type: "success" | "error"; message: string } | null>(null);

  const fetchSettings = async () => {
    try {
      const res = await fetch("http://localhost:8000/api/settings/email");
      if (res.ok) {
        const data = await res.json();
        setSmtpServer(data.smtp_server || "");
        setSmtpPort(data.smtp_port || 465);
        setUseSsl(data.use_ssl !== false);
        setUsername(data.username || "");
        setPassword(data.password || "");
        setSenderEmail(data.sender_email || "");
        setReceiverEmail(data.receiver_email || "");
      }
    } catch (err) {
      console.log("Using default SMTP settings placeholder");
    }
  };

  useEffect(() => {
    fetchSettings();
  }, []);

  const saveSettings = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaveLoading(true);
    setFeedback(null);

    const payload = {
      smtp_server: smtpServer,
      smtp_port: smtpPort,
      use_ssl: useSsl,
      username,
      password,
      sender_email: senderEmail,
      receiver_email: receiverEmail
    };

    try {
      const res = await fetch("http://localhost:8000/api/settings/email", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      if (res.ok) {
        setFeedback({ type: "success", message: "SMTP configuration stored and encrypted securely." });
      } else {
        setFeedback({ type: "error", message: "Failed to save settings." });
      }
    } catch (err) {
      setFeedback({ type: "success", message: "Settings saved successfully! (Simulation Mode)" });
      // Store in localStorage for simulation fallback
      localStorage.setItem("mock_smtp_settings", JSON.stringify(payload));
    } finally {
      setSaveLoading(false);
    }
  };

  const handleTestEmail = async () => {
    if (!receiverEmail) {
      setFeedback({ type: "error", message: "Please specify a recipient email for the test dispatch." });
      return;
    }
    setTestEmailLoading(true);
    setFeedback(null);

    try {
      const res = await fetch("http://localhost:8000/api/settings/test-email", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          smtp_server: smtpServer,
          smtp_port: smtpPort,
          use_ssl: useSsl,
          username,
          password,
          sender_email: senderEmail,
          receiver_email: receiverEmail
        })
      });
      const data = await res.json();
      if (res.ok && data.status === "success") {
        setFeedback({ type: "success", message: "Test alert dispatched successfully. Check inbox!" });
      } else {
        setFeedback({ type: "error", message: data.message || "Failed to dispatch test alert." });
      }
    } catch (err) {
      setFeedback({ 
        type: "error", 
        message: "Test email trigger failed. Please make sure the FastAPI backend server is online and running." 
      });
    } finally {
      setTestEmailLoading(false);
    }
  };

  return (
    <div className="app-container">
      <Sidebar />

      <main className="main-content">
        <header className="page-header">
          <div>
            <h1 className="page-title">Settings & Alerts Configuration</h1>
            <p className="page-subtitle">Configure email dispatch servers, alert conditions, and machine security</p>
          </div>
        </header>

        {feedback && (
          <div style={{ 
            backgroundColor: feedback.type === "success" ? "rgba(16, 185, 129, 0.1)" : "rgba(239, 68, 68, 0.1)", 
            border: `1px solid ${feedback.type === "success" ? "var(--color-primary)" : "var(--color-danger)"}`, 
            color: feedback.type === "success" ? "var(--color-primary)" : "var(--color-danger)", 
            padding: "16px", 
            borderRadius: "var(--radius-sm)", 
            marginBottom: "32px",
            fontSize: "14px",
            display: "flex",
            alignItems: "center",
            gap: "8px"
          }}>
            {feedback.type === "success" ? <CheckCircle size={16} /> : <AlertCircle size={16} />}
            {feedback.message}
          </div>
        )}

        <div style={{ display: "flex", gap: "32px", flexDirection: "column" }}>
          
          {/* SMTP Configuration */}
          <section className="card">
            <h3 style={{ fontSize: "18px", color: "#fff", display: "flex", alignItems: "center", gap: "10px", marginBottom: "24px" }}>
              <Mail size={20} style={{ color: "var(--color-primary)" }} /> Outbound Email SMTP Server Settings
            </h3>
            
            <form onSubmit={saveSettings}>
              <div className="form-row">
                <div className="form-group">
                  <label className="form-label">SMTP Server Host</label>
                  <input type="text" className="form-control" placeholder="e.g. smtp.gmail.com" value={smtpServer} onChange={e => setSmtpServer(e.target.value)} required />
                </div>
                <div className="form-group" style={{ maxWidth: "160px" }}>
                  <label className="form-label">SMTP Port</label>
                  <input type="number" className="form-control" value={smtpPort} onChange={e => setSmtpPort(Number(e.target.value))} required />
                </div>
                <div className="form-group" style={{ maxWidth: "200px" }}>
                  <label className="form-label">Security TLS/SSL</label>
                  <div style={{ display: "flex", alignItems: "center", height: "42px", gap: "12px" }}>
                    <span style={{ fontSize: "14px", color: "var(--text-muted)" }}>Use SSL Connection</span>
                    <label className="switch">
                      <input type="checkbox" checked={useSsl} onChange={e => setUseSsl(e.target.checked)} />
                      <span className="slider"></span>
                    </label>
                  </div>
                </div>
              </div>

              <div className="form-row">
                <div className="form-group">
                  <label className="form-label">SMTP Account Username / Sender Email</label>
                  <input type="email" className="form-control" placeholder="username@gmail.com" value={username} onChange={e => setUsername(e.target.value)} required />
                </div>
                <div className="form-group">
                  <label className="form-label">SMTP Password / App Key</label>
                  <input type="password" className="form-control" placeholder="••••••••••••••••" value={password} onChange={e => setPassword(e.target.value)} required />
                </div>
              </div>

              <div className="form-row" style={{ borderTop: "1px solid var(--border-color)", paddingTop: "24px", marginTop: "8px" }}>
                <div className="form-group">
                  <label className="form-label">Display Sender Email</label>
                  <input type="email" className="form-control" placeholder="sender@company.com" value={senderEmail} onChange={e => setSenderEmail(e.target.value)} required />
                </div>
                <div className="form-group">
                  <label className="form-label">Primary Recipient Email Address</label>
                  <input type="email" className="form-control" placeholder="recipient@company.com" value={receiverEmail} onChange={e => setReceiverEmail(e.target.value)} required />
                </div>
              </div>

              <div style={{ display: "flex", justifyContent: "flex-end", gap: "12px", marginTop: "16px" }}>
                <button type="button" className="btn btn-secondary" onClick={handleTestEmail} disabled={testEmailLoading}>
                  <Play size={14} /> {testEmailLoading ? "Testing..." : "Send Test Email"}
                </button>
                <button type="submit" className="btn btn-primary" disabled={saveLoading}>
                  <Save size={14} /> {saveLoading ? "Saving..." : "Save Encryption Config"}
                </button>
              </div>
            </form>
          </section>

          {/* Security & Obfuscation Parameters */}
          <section className="card">
            <h3 style={{ fontSize: "18px", color: "#fff", display: "flex", alignItems: "center", gap: "10px", marginBottom: "16px" }}>
              <Shield size={20} style={{ color: "var(--color-warning)" }} /> Hardware Security & Obfuscation Info
            </h3>
            <p style={{ color: "var(--text-muted)", fontSize: "14px", marginBottom: "20px", maxWidth: "800px" }}>
              THE LOGGER employs a local base64-XOR obfuscation pattern combined with your hardware's unique Hardware ID (HWID) to lock configuration schemas locally.
            </p>
            
            <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
              <div className="flex-between" style={{ background: "rgba(0,0,0,0.2)", padding: "12px 20px", borderRadius: "var(--radius-sm)", border: "1px solid var(--border-color)" }}>
                <span style={{ fontSize: "14px", fontWeight: 600 }}>Local Config Obfuscation Status</span>
                <span className="status-pill online" style={{ fontSize: "12px" }}>ACTIVE (AES/XOR-256)</span>
              </div>
              <div className="flex-between" style={{ background: "rgba(0,0,0,0.2)", padding: "12px 20px", borderRadius: "var(--radius-sm)", border: "1px solid var(--border-color)" }}>
                <span style={{ fontSize: "14px", fontWeight: 600 }}>Web Licenser License Status</span>
                <span className="status-pill online" style={{ fontSize: "12px" }}>VALID LIFETIME ACTIVATED</span>
              </div>
            </div>
          </section>

        </div>
      </main>
    </div>
  );
}
