"use client";

import { useEffect, useState, useRef } from "react";
import Sidebar from "@/components/Sidebar";
import { Play, Square, Activity, Database, AlertCircle, RefreshCw } from "lucide-react";

interface RegisterReading {
  id: number;
  name: string;
  device_name: string;
  value: number | string;
  unit: string;
  register_type: string;
  address: number;
  status: "success" | "error";
  timestamp: string;
}

export default function Dashboard() {
  const [readings, setReadings] = useState<RegisterReading[]>([]);
  const [wsStatus, setWsStatus] = useState<"connecting" | "connected" | "disconnected">("disconnected");
  const [isPolling, setIsPolling] = useState(false);
  const [deviceStatuses, setDeviceStatuses] = useState<{[key: string]: boolean}>({});
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    let active = true;
    let ws: WebSocket | null = null;

    const connect = () => {
      if (!active) return;
      setWsStatus("connecting");
      ws = new WebSocket("ws://localhost:8000/api/ws/live");
      wsRef.current = ws;

      ws.onopen = () => {
        if (!active) {
          ws?.close();
          return;
        }
        setWsStatus("connected");
        console.log("WebSocket connected");
      };

      ws.onmessage = (event) => {
        if (!active) return;
        try {
          const message = JSON.parse(event.data);
          if (message.type === "telemetry") {
            setReadings(message.data);
            setIsPolling(message.is_polling);
            
            // Compute device statuses based on register errors
            const statuses: {[key: string]: boolean} = {};
            message.data.forEach((r: RegisterReading) => {
              if (statuses[r.device_name] === undefined) {
                statuses[r.device_name] = true;
              }
              if (r.status === "error") {
                statuses[r.device_name] = false;
              }
            });
            setDeviceStatuses(statuses);
          }
        } catch (err) {
          console.error("Error parsing WS message:", err);
        }
      };

      ws.onclose = () => {
        if (active) {
          setWsStatus("disconnected");
          console.log("WebSocket disconnected, reconnecting...");
          setTimeout(connect, 3000);
        }
      };

      ws.onerror = (err) => {
        if (active) {
          console.error("WebSocket error:", err);
          ws?.close();
        }
      };
    };

    connect();

    return () => {
      active = false;
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []);

  const togglePolling = async () => {
    try {
      const response = await fetch("http://localhost:8000/api/polling/toggle", {
        method: "POST",
        headers: { "Content-Type": "application/json" }
      });
      const data = await response.json();
      setIsPolling(data.is_polling);
    } catch (err) {
      console.error("Failed to toggle polling:", err);
      // Toggle client-side for simulation/demo fallback
      setIsPolling(!isPolling);
    }
  };

  // Generate simulated readings if backend isn't available
  useEffect(() => {
    let interval: NodeJS.Timeout;
    if (wsStatus === "disconnected" && isPolling) {
      // Simulate real-time data
      const mockRegisters: RegisterReading[] = [
        { id: 1, name: "Chiller Temperature", device_name: "PLC_Chiller", value: 18.5, unit: "°C", register_type: "Holding Register (FC03)", address: 40001, status: "success", timestamp: new Date().toISOString() },
        { id: 2, name: "Flow Rate", device_name: "Flowmeter_RTU", value: 125.4, unit: "m³/h", register_type: "Input Register (FC04)", address: 30005, status: "success", timestamp: new Date().toISOString() },
        { id: 3, name: "Chiller State", device_name: "PLC_Chiller", value: 1, unit: "ON/OFF", register_type: "Discrete Input (FC02)", address: 10001, status: "success", timestamp: new Date().toISOString() },
        { id: 4, name: "Pressure Limit Alarm", device_name: "PLC_Chiller", value: 0, unit: "Alarm", register_type: "Coil (FC01)", address: 1, status: "success", timestamp: new Date().toISOString() },
        { id: 5, name: "Main Supply Voltage", device_name: "Energy_Meter", value: 415.2, unit: "V", register_type: "Holding Register (FC03)", address: 40020, status: "success", timestamp: new Date().toISOString() },
        { id: 6, name: "Current Draw", device_name: "Energy_Meter", value: 34.8, unit: "A", register_type: "Holding Register (FC03)", address: 40022, status: "success", timestamp: new Date().toISOString() }
      ];

      setReadings(mockRegisters);

      setDeviceStatuses({
        "PLC_Chiller": true,
        "Flowmeter_RTU": true,
        "Energy_Meter": true
      });

      interval = setInterval(() => {
        setReadings(prev => 
          prev.map(r => {
            if (typeof r.value === "number") {
              const variance = (Math.random() - 0.5) * (r.unit === "°C" ? 0.4 : 2.0);
              const newValue = parseFloat((r.value + variance).toFixed(2));
              return { ...r, value: r.unit === "ON/OFF" ? (Math.random() > 0.95 ? (r.value === 1 ? 0 : 1) : r.value) : newValue, timestamp: new Date().toISOString() };
            }
            return r;
          })
        );
      }, 1000);
    }
    return () => clearInterval(interval);
  }, [wsStatus, isPolling]);

  return (
    <div className="app-container">
      <Sidebar />
      
      <main className="main-content">
        <header className="page-header">
          <div>
            <h1 className="page-title">Live Telemetry Dashboard</h1>
            <p className="page-subtitle">Real-time status updates of active Modbus nodes</p>
          </div>
          
          <div style={{ display: "flex", gap: "12px", alignItems: "center" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
              <span className={`status-pill ${wsStatus === "connected" ? "online" : "offline"}`}>
                <Activity size={12} className={wsStatus === "connected" ? "animate-pulse" : ""} />
                WS Status: {wsStatus.toUpperCase()}
              </span>
            </div>

            <button 
              onClick={togglePolling} 
              className={`btn ${isPolling ? "btn-danger" : "btn-primary"}`}
              style={{ minWidth: "160px" }}
            >
              {isPolling ? (
                <>
                  <Square size={16} fill="white" />
                  Stop Polling
                </>
              ) : (
                <>
                  <Play size={16} fill="var(--text-inverse)" />
                  Start Polling
                </>
              )}
            </button>
          </div>
        </header>

        {/* Device Status Banner */}
        <section className="card" style={{ marginBottom: "32px", padding: "16px 24px" }}>
          <h3 style={{ fontSize: "16px", marginBottom: "12px", color: "var(--text-muted)", display: "flex", alignItems: "center", gap: "8px" }}>
            <Database size={18} /> Modbus Device States
          </h3>
          <div style={{ display: "flex", gap: "24px", flexWrap: "wrap" }}>
            {Object.keys(deviceStatuses).length === 0 ? (
              <span style={{ fontSize: "14px", color: "var(--text-muted)" }}>No devices configured</span>
            ) : (
              Object.entries(deviceStatuses).map(([name, isOnline]) => (
                <div key={name} style={{ display: "flex", alignItems: "center", gap: "8px", background: "rgba(255,255,255,0.03)", padding: "8px 16px", borderRadius: "var(--radius-sm)" }}>
                  <div style={{ width: "8px", height: "8px", borderRadius: "50%", backgroundColor: isOnline ? "var(--color-success)" : "var(--color-danger)" }}></div>
                  <span style={{ fontSize: "14px", fontWeight: 600 }}>{name}</span>
                  <span style={{ fontSize: "12px", color: "var(--text-muted)" }}>{isOnline ? "Online" : "Connection Error"}</span>
                </div>
              ))
            )}
          </div>
        </section>

        {/* Telemetry Grid */}
        <section className="dashboard-grid">
          {readings.map((reading) => (
            <div key={reading.id} className="card telemetry-card" style={{
              borderLeft: reading.status === "error" ? "4px solid var(--color-danger)" : "1px solid var(--border-color)"
            }}>
              <div className="telemetry-header">
                <div>
                  <span className="register-title">{reading.name}</span>
                  <div style={{ fontSize: "11px", color: "var(--text-muted)", marginTop: "2px" }}>
                    Addr: {reading.address} | {reading.register_type.split(" ")[0]}
                  </div>
                </div>
                <span className="device-badge">{reading.device_name}</span>
              </div>

              <div className="register-value-container">
                {reading.status === "error" ? (
                  <div style={{ display: "flex", alignItems: "center", gap: "8px", color: "var(--color-danger)" }}>
                    <AlertCircle size={24} />
                    <span style={{ fontSize: "16px", fontWeight: 600 }}>Read Error</span>
                  </div>
                ) : (
                  <div>
                    <span className="register-value">{reading.value}</span>
                    <span className="register-unit">{reading.unit}</span>
                  </div>
                )}
              </div>

              <div className="telemetry-footer">
                <span>Updated: {new Date(reading.timestamp).toLocaleTimeString()}</span>
                <span style={{ 
                  color: reading.status === "success" ? "var(--color-success)" : "var(--color-danger)",
                  fontWeight: 600
                }}>
                  {reading.status.toUpperCase()}
                </span>
              </div>
            </div>
          ))}
        </section>

        {readings.length === 0 && (
          <div className="card" style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", minHeight: "250px", textAlign: "center" }}>
            <Activity size={48} style={{ color: "var(--text-muted)", marginBottom: "16px", opacity: 0.5 }} />
            <h3 style={{ fontSize: "18px", marginBottom: "8px" }}>No Telemetry Active</h3>
            <p style={{ color: "var(--text-muted)", maxWidth: "450px", fontSize: "14px" }}>
              Configure devices and registers in the Device Manager, then toggle the "Start Polling" switch to monitor telemetry.
            </p>
          </div>
        )}
      </main>
    </div>
  );
}
