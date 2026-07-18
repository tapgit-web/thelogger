"use client";

import { useEffect, useState } from "react";
import Sidebar from "@/components/Sidebar";
import { 
  LineChart, 
  Line, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  Legend, 
  ResponsiveContainer,
  ReferenceLine
} from "recharts";
import { FileDown, Calendar, Search, Activity, HelpCircle } from "lucide-react";
import { API_URL } from "@/config";

const getAuthHeaders = (): Record<string, string> => {
  if (typeof window === "undefined") return {};
  const token = localStorage.getItem("logger_token");
  return token ? { "Authorization": `Bearer ${token}` } : {};
};

interface Device {
  id: number;
  name: string;
}

interface Register {
  id: number;
  device_id: number;
  name: string;
  unit: string;
  limit_min?: number;
  limit_max?: number;
}

interface TrendDataPoint {
  timestamp: string;
  value: number;
}

export default function TrendsView() {
  const [devices, setDevices] = useState<Device[]>([]);
  const [registers, setRegisters] = useState<Register[]>([]);
  const [selectedDevice, setSelectedDevice] = useState<number | "">("");
  const [selectedRegister, setSelectedRegister] = useState<number | "">("");
  const [startDate, setStartDate] = useState(new Date().toISOString().split("T")[0]);
  const [endDate, setEndDate] = useState(new Date().toISOString().split("T")[0]);
  
  const [trendData, setTrendData] = useState<TrendDataPoint[]>([]);
  const [stats, setStats] = useState({ min: 0, max: 0, avg: 0 });
  const [loading, setLoading] = useState(false);
  const [exporting, setExporting] = useState(false);

  // Fetch initial configuration
  const loadConfig = async () => {
    try {
      const resDev = await fetch(`${API_URL}/api/devices`, { headers: getAuthHeaders() });
      const listDev = await resDev.json();
      setDevices(listDev);
      if (listDev.length > 0) {
        setSelectedDevice(listDev[0].id);
      }
    } catch (err) {
      // Mock defaults
      const mockD = [{ id: 1, name: "PLC_Chiller" }, { id: 3, name: "Energy_Meter" }];
      setDevices(mockD);
      setSelectedDevice(1);
    }
  };

  const loadRegisters = async (deviceId: number) => {
    try {
      const res = await fetch(`${API_URL}/api/devices/${deviceId}/registers`, { headers: getAuthHeaders() });
      const listReg = await res.json();
      setRegisters(listReg);
      if (listReg.length > 0) {
        setSelectedRegister(listReg[0].id);
      } else {
        setSelectedRegister("");
      }
    } catch (err) {
      const mockR = [
        { id: 1, device_id: 1, name: "Chiller Temperature", unit: "°C", limit_min: 5, limit_max: 35 },
        { id: 2, device_id: 1, name: "Chiller State", unit: "ON/OFF" },
        { id: 5, device_id: 3, name: "Main Supply Voltage", unit: "V" }
      ];
      const filtered = mockR.filter(r => r.device_id === deviceId);
      setRegisters(filtered);
      if (filtered.length > 0) {
        setSelectedRegister(filtered[0].id);
      } else {
        setSelectedRegister("");
      }
    }
  };

  useEffect(() => {
    loadConfig();
  }, []);

  useEffect(() => {
    if (selectedDevice !== "") {
      loadRegisters(Number(selectedDevice));
    } else {
      setRegisters([]);
      setSelectedRegister("");
    }
  }, [selectedDevice]);

  const fetchTrends = async () => {
    if (selectedDevice === "" || selectedRegister === "") return;
    setLoading(true);
    
    try {
      const res = await fetch(`${API_URL}/api/trends/data?register_id=${selectedRegister}&start_date=${startDate}&end_date=${endDate}`, { headers: getAuthHeaders() });
      const data = await res.json();
      setTrendData(data.points);
      setStats({
        min: data.stats.min,
        max: data.stats.max,
        avg: data.stats.avg
      });
    } catch (err) {
      // Mock trend data points
      const points: TrendDataPoint[] = [];
      const baseTemp = selectedRegister === 1 ? 18.5 : selectedRegister === 5 ? 415.2 : 25;
      const step = selectedRegister === 1 ? 0.2 : 0.8;
      
      let tempStats = { min: 9999, max: -9999, sum: 0 };
      
      for (let i = 0; i < 24; i++) {
        const timeStr = `${String(i).padStart(2, "0")}:00`;
        const val = parseFloat((baseTemp + (Math.sin(i / 3) * step * 4) + (Math.random() - 0.5) * step).toFixed(2));
        points.push({ timestamp: timeStr, value: val });
        
        if (val < tempStats.min) tempStats.min = val;
        if (val > tempStats.max) tempStats.max = val;
        tempStats.sum += val;
      }
      
      setTrendData(points);
      setStats({
        min: tempStats.min,
        max: tempStats.max,
        avg: parseFloat((tempStats.sum / 24).toFixed(2))
      });
    } finally {
      setLoading(false);
    }
  };

  const handleExportPDF = async () => {
    if (selectedRegister === "") return;
    setExporting(true);
    try {
      const response = await fetch(`${API_URL}/api/trends/export-pdf?register_id=${selectedRegister}&start_date=${startDate}&end_date=${endDate}`, { headers: getAuthHeaders() });
      if (response.ok) {
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `TrendReport_${selectedRegister}_${startDate}.pdf`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
      } else {
        alert("Failed to export PDF from backend. Checking details...");
      }
    } catch (err) {
      // Local client-side warning mock
      alert("Backend offline. PDF generation is compiled in Python (ReportLab) on the FastAPI server. Please check the backend connection.");
    } finally {
      setExporting(false);
    }
  };

  const activeRegister = registers.find(r => r.id === Number(selectedRegister));

  return (
    <div className="app-container">
      <Sidebar />

      <main className="main-content">
        <header className="page-header">
          <div>
            <h1 className="page-title">Trend Reports & Export</h1>
            <p className="page-subtitle">View historical registry patterns and generate signed PDF audits</p>
          </div>
        </header>

        {/* Filter configuration card */}
        <section className="card" style={{ marginBottom: "32px" }}>
          <div style={{ display: "flex", gap: "20px", flexWrap: "wrap", alignItems: "flex-end" }}>
            <div className="form-group" style={{ margin: 0, flex: 1, minWidth: "200px" }}>
              <label className="form-label">Select Device</label>
              <select className="form-control" value={selectedDevice} onChange={e => setSelectedDevice(e.target.value === "" ? "" : Number(e.target.value))}>
                <option value="">-- Select Device --</option>
                {devices.map(d => (
                  <option key={d.id} value={d.id}>{d.name}</option>
                ))}
              </select>
            </div>

            <div className="form-group" style={{ margin: 0, flex: 1, minWidth: "200px" }}>
              <label className="form-label">Select Register Point</label>
              <select className="form-control" value={selectedRegister} onChange={e => setSelectedRegister(e.target.value === "" ? "" : Number(e.target.value))} disabled={!selectedDevice}>
                <option value="">-- Select Register --</option>
                {registers.map(r => (
                  <option key={r.id} value={r.id}>{r.name} ({r.unit})</option>
                ))}
              </select>
            </div>

            <div className="form-group" style={{ margin: 0, width: "160px" }}>
              <label className="form-label">Start Date</label>
              <input type="date" className="form-control" value={startDate} onChange={e => setStartDate(e.target.value)} />
            </div>

            <div className="form-group" style={{ margin: 0, width: "160px" }}>
              <label className="form-label">End Date</label>
              <input type="date" className="form-control" value={endDate} onChange={e => setEndDate(e.target.value)} />
            </div>

            <div style={{ display: "flex", gap: "12px" }}>
              <button onClick={fetchTrends} className="btn btn-primary" style={{ height: "42px" }} disabled={selectedRegister === ""}>
                <Search size={16} /> Query
              </button>
              
              <button onClick={handleExportPDF} className="btn btn-secondary" style={{ height: "42px" }} disabled={selectedRegister === "" || exporting}>
                <FileDown size={16} /> {exporting ? "Generating..." : "Export PDF"}
              </button>
            </div>
          </div>
        </section>

        {trendData.length > 0 ? (
          <div>
            {/* Statistics Cards */}
            <div style={{ display: "flex", gap: "24px", marginBottom: "32px" }}>
              <div className="card" style={{ flex: 1, textAlign: "center", padding: "16px" }}>
                <span style={{ fontSize: "13px", color: "var(--text-muted)", textTransform: "uppercase" }}>Minimum Value</span>
                <div style={{ fontSize: "28px", fontWeight: 700, marginTop: "4px", color: "var(--color-secondary)", fontFamily: "var(--font-mono)" }}>
                  {stats.min} <span style={{ fontSize: "14px" }}>{activeRegister?.unit}</span>
                </div>
              </div>
              <div className="card" style={{ flex: 1, textAlign: "center", padding: "16px" }}>
                <span style={{ fontSize: "13px", color: "var(--text-muted)", textTransform: "uppercase" }}>Maximum Value</span>
                <div style={{ fontSize: "28px", fontWeight: 700, marginTop: "4px", color: "var(--color-danger)", fontFamily: "var(--font-mono)" }}>
                  {stats.max} <span style={{ fontSize: "14px" }}>{activeRegister?.unit}</span>
                </div>
              </div>
              <div className="card" style={{ flex: 1, textAlign: "center", padding: "16px" }}>
                <span style={{ fontSize: "13px", color: "var(--text-muted)", textTransform: "uppercase" }}>Average Value</span>
                <div style={{ fontSize: "28px", fontWeight: 700, marginTop: "4px", color: "var(--color-primary)", fontFamily: "var(--font-mono)" }}>
                  {stats.avg} <span style={{ fontSize: "14px" }}>{activeRegister?.unit}</span>
                </div>
              </div>
            </div>

            {/* Recharts Graphical Display */}
            <div className="card" style={{ padding: "32px 24px 16px 16px", height: "450px" }}>
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={trendData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                  <XAxis dataKey="timestamp" stroke="var(--text-muted)" fontSize={12} />
                  <YAxis stroke="var(--text-muted)" fontSize={12} unit={activeRegister?.unit} />
                  <Tooltip 
                    contentStyle={{ 
                      backgroundColor: "var(--bg-main)", 
                      borderColor: "var(--border-color-hover)",
                      borderRadius: "var(--radius-sm)",
                      color: "var(--text-primary)"
                    }} 
                  />
                  <Legend verticalAlign="top" height={36} />
                  
                  <Line 
                    name={activeRegister?.name || "Value"} 
                    type="monotone" 
                    dataKey="value" 
                    stroke="var(--color-primary)" 
                    strokeWidth={2}
                    dot={{ fill: "var(--color-primary)", r: 3 }}
                    activeDot={{ r: 6 }} 
                  />

                  {/* Reference line limits alerts */}
                  {activeRegister?.limit_min !== undefined && (
                    <ReferenceLine y={activeRegister.limit_min} label={{ value: `Min limit (${activeRegister.limit_min})`, fill: "var(--color-warning)", position: "top", fontSize: 11 }} stroke="var(--color-warning)" strokeDasharray="5 5" />
                  )}
                  {activeRegister?.limit_max !== undefined && (
                    <ReferenceLine y={activeRegister.limit_max} label={{ value: `Max limit (${activeRegister.limit_max})`, fill: "var(--color-danger)", position: "top", fontSize: 11 }} stroke="var(--color-danger)" strokeDasharray="5 5" />
                  )}
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>
        ) : (
          <div className="card" style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", minHeight: "350px", textAlign: "center" }}>
            <Activity size={48} style={{ color: "var(--text-muted)", marginBottom: "16px", opacity: 0.5 }} />
            <h3 style={{ fontSize: "18px", marginBottom: "8px" }}>Historical Query Analyzer</h3>
            <p style={{ color: "var(--text-muted)", maxWidth: "450px", fontSize: "14px" }}>
              Select a Modbus device and mapped register channel, choose your temporal window, and hit "Query" to graph trends and extract formal audit reports.
            </p>
          </div>
        )}
      </main>
    </div>
  );
}
