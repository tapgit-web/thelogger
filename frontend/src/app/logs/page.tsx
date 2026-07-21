"use client";

import { useEffect, useState } from "react";
import Navbar from "@/components/Navbar";
import { 
  BellRing, 
  Mail, 
  Search, 
  RefreshCw, 
  AlertTriangle, 
  CheckCircle, 
  Activity, 
  History 
} from "lucide-react";
import { API_URL } from "@/config";

interface AlarmLog {
  timestamp: string;
  device_name: string;
  field_name: string;
  address: number;
  value: number;
  condition: string;
  threshold: number;
}

interface EmailLog {
  timestamp: string;
  device_name: string;
  field_name: string;
  recipient: string;
  status: string;
}

const getAuthHeaders = (): Record<string, string> => {
  if (typeof window === "undefined") return {};
  const token = localStorage.getItem("logger_token");
  return token ? { "Authorization": `Bearer ${token}` } : {};
};

export default function LogsView() {
  const [activeTab, setActiveTab] = useState<"alarms" | "emails">("alarms");
  const [alarmLogs, setAlarmLogs] = useState<AlarmLog[]>([]);
  const [emailLogs, setEmailLogs] = useState<EmailLog[]>([]);
  const [searchTerm, setSearchTerm] = useState("");
  const [loading, setLoading] = useState(false);

  const fetchLogs = async () => {
    setLoading(true);
    try {
      if (activeTab === "alarms") {
        const res = await fetch(`${API_URL}/api/logs/alarms`, { headers: getAuthHeaders() });
        if (res.ok) {
          const data = await res.json();
          setAlarmLogs(data);
        }
      } else {
        const res = await fetch(`${API_URL}/api/logs/emails`, { headers: getAuthHeaders() });
        if (res.ok) {
          const data = await res.json();
          setEmailLogs(data);
        }
      }
    } catch (err) {
      console.error("Error loading logs from API:", err);
      // Mock Fallbacks
      if (activeTab === "alarms") {
        setAlarmLogs([
          {
            timestamp: new Date().toISOString().replace("T", " ").substring(0, 19),
            device_name: "PLC_Chiller",
            field_name: "Chiller Temperature",
            address: 40001,
            value: 36.4,
            condition: "Reading (36.4) exceeds max limit (35.0)",
            threshold: 35.0
          },
          {
            timestamp: new Date(Date.now() - 3600000).toISOString().replace("T", " ").substring(0, 19),
            device_name: "Flow_Meter",
            field_name: "Flow Rate",
            address: 30005,
            value: 205.1,
            condition: "Reading (205.1) exceeds max limit (200.0)",
            threshold: 200.0
          }
        ]);
      } else {
        setEmailLogs([
          {
            timestamp: new Date().toISOString().replace("T", " ").substring(0, 19),
            device_name: "PLC_Chiller",
            field_name: "Chiller Temperature",
            recipient: "admin@company.com",
            status: "SUCCESS"
          },
          {
            timestamp: new Date(Date.now() - 3600000).toISOString().replace("T", " ").substring(0, 19),
            device_name: "Flow_Meter",
            field_name: "Flow Rate",
            recipient: "operator@company.com",
            status: "FAILED (SMTP Timeout)"
          }
        ]);
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchLogs();
  }, [activeTab]);

  const filteredAlarms = alarmLogs.filter(
    (log) =>
      log.device_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      log.field_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      log.condition.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const filteredEmails = emailLogs.filter(
    (log) =>
      log.device_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      log.field_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      log.recipient.toLowerCase().includes(searchTerm.toLowerCase()) ||
      log.status.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="app-container">
      <Navbar />

      <main className="main-content">
        <header className="page-header">
          <div>
            <h1 className="page-title">Alarms & System Audit Logs</h1>
            <p className="page-subtitle">Inspect historical limit breaches, warnings, and email alerts</p>
          </div>
          <button 
            id="btn-refresh-logs"
            onClick={fetchLogs} 
            className="btn btn-secondary" 
            disabled={loading}
            style={{ height: "42px", gap: "8px" }}
          >
            <RefreshCw size={16} className={loading ? "spin" : ""} /> 
            {loading ? "Syncing..." : "Refresh Logs"}
          </button>
        </header>

        {/* Filters and Navigation Tab bar */}
        <section className="card" style={{ marginBottom: "32px", padding: "16px 24px" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "20px" }}>
            
            {/* Tabs */}
            <div style={{ display: "flex", gap: "8px", background: "rgba(0,0,0,0.2)", padding: "4px", borderRadius: "var(--radius-sm)", border: "1px solid var(--border-color)" }}>
              <button
                id="tab-alarms"
                onClick={() => { setActiveTab("alarms"); setSearchTerm(""); }}
                className={`btn ${activeTab === "alarms" ? "btn-primary" : "btn-secondary"}`}
                style={{ border: "none", background: activeTab === "alarms" ? "" : "transparent" }}
              >
                <AlertTriangle size={14} style={{ marginRight: "6px" }} />
                Alarms History
              </button>
              <button
                id="tab-emails"
                onClick={() => { setActiveTab("emails"); setSearchTerm(""); }}
                className={`btn ${activeTab === "emails" ? "btn-primary" : "btn-secondary"}`}
                style={{ border: "none", background: activeTab === "emails" ? "" : "transparent" }}
              >
                <Mail size={14} style={{ marginRight: "6px" }} />
                Email Dispatches
              </button>
            </div>

            {/* Search */}
            <div className="form-group" style={{ margin: 0, minWidth: "300px", position: "relative" }}>
              <Search size={16} style={{ position: "absolute", left: "14px", top: "13px", color: "var(--text-muted)" }} />
              <input
                id="input-log-search"
                type="text"
                placeholder={`Search ${activeTab === "alarms" ? "alarms by device, name..." : "emails by recipient, status..."}`}
                className="form-control"
                style={{ paddingLeft: "40px" }}
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
              />
            </div>
          </div>
        </section>

        {/* Display list based on active tab */}
        {activeTab === "alarms" ? (
          filteredAlarms.length > 0 ? (
            <section className="table-container">
              <table className="table">
                <thead>
                  <tr>
                    <th>Timestamp</th>
                    <th>Device Name</th>
                    <th>Field Name</th>
                    <th>Register Address</th>
                    <th>Reading Value</th>
                    <th>Threshold</th>
                    <th>Condition / Cause</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredAlarms.map((log, idx) => (
                    <tr key={idx}>
                      <td style={{ color: "var(--text-muted)", fontSize: "13px", fontFamily: "var(--font-mono)" }}>
                        {log.timestamp}
                      </td>
                      <td style={{ fontWeight: 600, color: "var(--text-primary)" }}>
                        {log.device_name}
                      </td>
                      <td>
                        {log.field_name}
                      </td>
                      <td style={{ fontFamily: "var(--font-mono)", fontSize: "13px" }}>
                        {log.address}
                      </td>
                      <td style={{ color: "var(--color-danger)", fontWeight: 700 }}>
                        {log.value}
                      </td>
                      <td style={{ color: "var(--text-muted)", fontWeight: 600 }}>
                        {log.threshold}
                      </td>
                      <td>
                        <span className="status-pill offline" style={{ backgroundColor: "rgba(239, 68, 68, 0.1)", color: "var(--color-danger)", fontSize: "12px" }}>
                          {log.condition}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </section>
          ) : (
            <div className="card" style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", minHeight: "350px", textAlign: "center" }}>
              <History size={48} style={{ color: "var(--text-muted)", marginBottom: "16px", opacity: 0.5 }} />
              <h3 style={{ fontSize: "18px", marginBottom: "8px" }}>No Threshold Breaches</h3>
              <p style={{ color: "var(--text-muted)", maxWidth: "450px", fontSize: "14px" }}>
                All registered Modbus nodes are currently operating within their specified safety limits.
              </p>
            </div>
          )
        ) : (
          filteredEmails.length > 0 ? (
            <section className="table-container">
              <table className="table">
                <thead>
                  <tr>
                    <th>Timestamp</th>
                    <th>Target Device</th>
                    <th>Failed Field</th>
                    <th>Recipient Address</th>
                    <th>Transmission Status</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredEmails.map((log, idx) => (
                    <tr key={idx}>
                      <td style={{ color: "var(--text-muted)", fontSize: "13px", fontFamily: "var(--font-mono)" }}>
                        {log.timestamp}
                      </td>
                      <td style={{ fontWeight: 600, color: "var(--text-primary)" }}>
                        {log.device_name}
                      </td>
                      <td>
                        {log.field_name}
                      </td>
                      <td style={{ fontWeight: 600 }}>
                        {log.recipient}
                      </td>
                      <td>
                        <span className={`status-pill ${log.status.toUpperCase().includes("SUCCESS") ? "online" : "offline"}`} style={{ fontSize: "12px" }}>
                          {log.status}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </section>
          ) : (
            <div className="card" style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", minHeight: "350px", textAlign: "center" }}>
              <Mail size={48} style={{ color: "var(--text-muted)", marginBottom: "16px", opacity: 0.5 }} />
              <h3 style={{ fontSize: "18px", marginBottom: "8px" }}>No Email Logs Found</h3>
              <p style={{ color: "var(--text-muted)", maxWidth: "450px", fontSize: "14px" }}>
                No SMTP dispatch alerts have been sent. Set up test emails in "Settings & Alerts".
              </p>
            </div>
          )
        )}
      </main>
    </div>
  );
}
