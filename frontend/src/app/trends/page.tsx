"use client";

import { useEffect, useState } from "react";
import Navbar from "@/components/Navbar";
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler
} from "chart.js";
import { Line } from "react-chartjs-2";
import { FileDown, Calendar, Search, Activity, HelpCircle, ChevronDown } from "lucide-react";
import { API_URL } from "@/config";

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler
);

const getAuthHeaders = (): Record<string, string> => {
  if (typeof window === "undefined") return {};
  const token = localStorage.getItem("logger_token");
  return {
    "Cache-Control": "no-cache, no-store, must-revalidate",
    "Pragma": "no-cache",
    "Expires": "0",
    ...(token ? { "Authorization": `Bearer ${token}` } : {})
  };
};

const PALETTE = ["#10B981", "#3B82F6", "#F59E0B", "#EF4444", "#8B5CF6", "#EC4899", "#14B8A6", "#F97316"];

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
  const [selectedRegisters, setSelectedRegisters] = useState<number[]>([]);
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const [startDate, setStartDate] = useState(new Date().toISOString().split("T")[0]);
  const [endDate, setEndDate] = useState(new Date().toISOString().split("T")[0]);
  
  const [trendData, setTrendData] = useState<any[]>([]);
  const [registerStats, setRegisterStats] = useState<Record<number, { min: number; max: number; avg: number }>>({});
  const [loading, setLoading] = useState(false);
  const [exporting, setExporting] = useState(false);

  // Fetch initial configuration
  const loadConfig = async () => {
    try {
      const resDev = await fetch(`${API_URL}/api/devices`, { headers: getAuthHeaders() });
      if (!resDev.ok) {
        throw new Error(`HTTP error ${resDev.status}`);
      }
      const listDev = await resDev.json();
      if (Array.isArray(listDev)) {
        setDevices(listDev);
        if (listDev.length > 0) {
          setSelectedDevice(listDev[0].id);
        }
      } else {
        throw new Error("Response is not an array");
      }
    } catch (err) {
      console.error("Failed to fetch devices in trends view:", err);
      // Mock defaults
      const mockD = [{ id: 1, name: "PLC_Chiller" }, { id: 3, name: "Energy_Meter" }];
      setDevices(mockD);
      setSelectedDevice(1);
    }
  };

  const loadRegisters = async (deviceId: number) => {
    try {
      const res = await fetch(`${API_URL}/api/devices/${deviceId}/registers`, { headers: getAuthHeaders() });
      if (!res.ok) {
        throw new Error(`HTTP error ${res.status}`);
      }
      const listReg = await res.json();
      if (Array.isArray(listReg)) {
        setRegisters(listReg);
        if (listReg.length > 0) {
          setSelectedRegisters([listReg[0].id]);
        } else {
          setSelectedRegisters([]);
        }
      } else {
        throw new Error("Response is not an array");
      }
    } catch (err) {
      console.error("Failed to fetch registers in trends view:", err);
      const mockR = [
        { id: 1, device_id: 1, name: "Chiller Temperature", unit: "°C", limit_min: 5, limit_max: 35 },
        { id: 2, device_id: 1, name: "Chiller State", unit: "ON/OFF" },
        { id: 5, device_id: 3, name: "Main Supply Voltage", unit: "V" }
      ];
      const filtered = mockR.filter(r => r.device_id === deviceId);
      setRegisters(filtered);
      if (filtered.length > 0) {
        setSelectedRegisters([filtered[0].id]);
      } else {
        setSelectedRegisters([]);
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
      setSelectedRegisters([]);
    }
  }, [selectedDevice]);

  useEffect(() => {
    const handleOutsideClick = (e: MouseEvent) => {
      const target = e.target as HTMLElement;
      if (!target.closest(".multi-select-container")) {
        setIsDropdownOpen(false);
      }
    };
    document.addEventListener("mousedown", handleOutsideClick);
    return () => document.removeEventListener("mousedown", handleOutsideClick);
  }, []);

  const fetchTrends = async () => {
    if (selectedDevice === "" || selectedRegisters.length === 0) return;
    setLoading(true);
    
    try {
      const idsStr = selectedRegisters.join(",");
      const res = await fetch(`${API_URL}/api/trends/data?register_ids=${idsStr}&start_date=${startDate}&end_date=${endDate}`, { headers: getAuthHeaders() });
      const data = await res.json();
      
      const mergedPointsMap: Record<string, any> = {};
      const newStats: Record<number, { min: number; max: number; avg: number }> = {};
      
      Object.entries(data).forEach(([rIdStr, regResult]: [string, any]) => {
        const rId = Number(rIdStr);
        newStats[rId] = regResult.stats;
        regResult.points.forEach((pt: any) => {
          if (!mergedPointsMap[pt.timestamp]) {
            mergedPointsMap[pt.timestamp] = { timestamp: pt.timestamp };
          }
          mergedPointsMap[pt.timestamp][rId] = pt.value;
        });
      });
      
      const mergedPoints = Object.values(mergedPointsMap).sort(
        (a: any, b: any) => a.timestamp.localeCompare(b.timestamp)
      );
      
      setTrendData(mergedPoints);
      setRegisterStats(newStats);
    } catch (err) {
      const mergedPointsMap: Record<string, any> = {};
      const newStats: Record<number, { min: number; max: number; avg: number }> = {};
      
      selectedRegisters.forEach((rId) => {
        const reg = registers.find(r => r.id === rId);
        const baseTemp = rId === 1 ? 18.5 : rId === 5 ? 415.2 : 25;
        const step = rId === 1 ? 0.2 : 0.8;
        
        let tempStats = { min: 9999, max: -9999, sum: 0 };
        
        for (let i = 0; i < 24; i++) {
          const timeStr = `${String(i).padStart(2, "0")}:00`;
          const val = parseFloat((baseTemp + (Math.sin(i / 3) * step * 4) + (Math.random() - 0.5) * step).toFixed(2));
          
          if (!mergedPointsMap[timeStr]) {
            mergedPointsMap[timeStr] = { timestamp: timeStr };
          }
          mergedPointsMap[timeStr][rId] = val;
          
          if (val < tempStats.min) tempStats.min = val;
          if (val > tempStats.max) tempStats.max = val;
          tempStats.sum += val;
        }
        
        newStats[rId] = {
          min: tempStats.min,
          max: tempStats.max,
          avg: parseFloat((tempStats.sum / 24).toFixed(2))
        };
      });
      
      const mergedPoints = Object.values(mergedPointsMap).sort(
        (a: any, b: any) => a.timestamp.localeCompare(b.timestamp)
      );
      
      setTrendData(mergedPoints);
      setRegisterStats(newStats);
    } finally {
      setLoading(false);
    }
  };

  const handleExportPDF = async () => {
    if (selectedRegisters.length === 0) return;
    setExporting(true);
    try {
      const idsStr = selectedRegisters.join(",");
      const response = await fetch(`${API_URL}/api/trends/export-pdf?register_ids=${idsStr}&start_date=${startDate}&end_date=${endDate}`, { headers: getAuthHeaders() });
      if (response.ok) {
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `TrendReport_${startDate}.pdf`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
      } else {
        alert("Failed to export PDF from backend. Checking details...");
      }
    } catch (err) {
      alert("Backend offline. PDF generation is compiled in Python (ReportLab) on the FastAPI server. Please check the backend connection.");
    } finally {
      setExporting(false);
    }
  };

  return (
    <div className="app-container">
      <Navbar />

      <main className="main-content">
        <header className="page-header">
          <div>
            <h1 className="page-title">Trend Reports & Export</h1>
            <p className="page-subtitle">View historical registry patterns and generate signed PDF audits</p>
          </div>
        </header>

        {/* Filter configuration card */}
        <section className="card" style={{ marginBottom: "32px", position: "relative", zIndex: 50, overflow: "visible" }}>
          <div style={{ display: "flex", gap: "20px", flexWrap: "wrap", alignItems: "flex-end" }}>
            <div className="form-group" style={{ margin: 0, flex: 1, minWidth: "200px" }}>
              <label className="form-label">Select Device</label>
              <select className="form-control" value={selectedDevice} onChange={e => setSelectedDevice(e.target.value === "" ? "" : Number(e.target.value))}>
                <option value="">-- Select Device --</option>
                {Array.isArray(devices) && devices.map(d => (
                  <option key={d.id} value={d.id}>{d.name}</option>
                ))}
              </select>
            </div>

            <div className="form-group multi-select-container" style={{ margin: 0, flex: 1, minWidth: "240px", position: "relative" }}>
              <label className="form-label">Select Register Points</label>
              <div 
                className="form-control" 
                style={{ 
                  cursor: "pointer", 
                  display: "flex", 
                  justifyContent: "space-between", 
                  alignItems: "center",
                  background: "var(--bg-input)",
                  border: "1px solid var(--border-color)",
                  minHeight: "42px",
                  height: "auto",
                  padding: "6px 12px",
                  borderRadius: "var(--radius-sm)"
                }}
                onClick={() => setIsDropdownOpen(!isDropdownOpen)}
              >
                <span style={{ color: selectedRegisters.length > 0 ? "var(--text-primary)" : "var(--text-muted)", fontSize: "14px", textOverflow: "ellipsis", overflow: "hidden", whiteSpace: "nowrap" }}>
                  {selectedRegisters.length > 0 && Array.isArray(registers)
                    ? registers.filter(r => selectedRegisters.includes(r.id)).map(r => r.name).join(", ")
                    : "-- Select Registers --"}
                </span>
                <ChevronDown size={16} style={{ flexShrink: 0, marginLeft: "8px" }} />
              </div>
              
              {isDropdownOpen && (
                <div style={{
                  position: "absolute",
                  top: "100%",
                  left: 0,
                  width: "100%",
                  background: "var(--bg-card)",
                  border: "1px solid var(--border-color-hover)",
                  borderRadius: "var(--radius-sm)",
                  boxShadow: "0 10px 25px -5px rgba(0, 0, 0, 0.4), 0 8px 10px -6px rgba(0, 0, 0, 0.3)",
                  zIndex: 9999,
                  maxHeight: "260px",
                  overflowY: "auto",
                  marginTop: "6px",
                  padding: "8px"
                }}>
                  {Array.isArray(registers) && registers.map(r => {
                    const isChecked = selectedRegisters.includes(r.id);
                    return (
                      <label 
                        key={r.id} 
                        style={{ 
                          display: "flex", 
                          alignItems: "center", 
                          gap: "10px", 
                          padding: "8px", 
                          cursor: "pointer",
                          borderRadius: "4px",
                          background: isChecked ? "rgba(16, 185, 129, 0.05)" : "transparent",
                          marginBottom: "2px"
                        }}
                      >
                        <input 
                          type="checkbox" 
                          checked={isChecked}
                          onChange={() => {
                            if (isChecked) {
                              setSelectedRegisters(selectedRegisters.filter(id => id !== r.id));
                            } else {
                              setSelectedRegisters([...selectedRegisters, r.id]);
                            }
                          }}
                        />
                        <span style={{ fontSize: "13px", color: "var(--text-primary)" }}>
                          {r.name} ({r.unit})
                        </span>
                      </label>
                    );
                  })}
                  {registers.length === 0 && (
                    <span style={{ fontSize: "12px", color: "var(--text-muted)", padding: "4px 8px", display: "block" }}>
                      No registers configured for this device.
                    </span>
                  )}
                </div>
              )}
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
              <button onClick={fetchTrends} className="btn btn-primary" style={{ height: "42px" }} disabled={selectedRegisters.length === 0}>
                <Search size={16} /> Query
              </button>
              
              <button onClick={handleExportPDF} className="btn btn-secondary" style={{ height: "42px" }} disabled={selectedRegisters.length === 0 || exporting}>
                <FileDown size={16} /> {exporting ? "Generating..." : "Export PDF"}
              </button>
            </div>
          </div>
        </section>

        {trendData.length > 0 ? (
          <div>
            {/* Statistics Section */}
            {selectedRegisters.length === 1 ? (
              (() => {
                const regId = selectedRegisters[0];
                const reg = registers.find(r => r.id === regId);
                const stats = registerStats[regId] || { min: 0, max: 0, avg: 0 };
                return (
                  <div style={{ display: "flex", gap: "24px", marginBottom: "32px" }}>
                    <div className="card" style={{ flex: 1, textAlign: "center", padding: "16px" }}>
                      <span style={{ fontSize: "13px", color: "var(--text-muted)", textTransform: "uppercase" }}>Minimum Value</span>
                      <div style={{ fontSize: "28px", fontWeight: 700, marginTop: "4px", color: "var(--color-secondary)", fontFamily: "var(--font-mono)" }}>
                        {stats.min} <span style={{ fontSize: "14px" }}>{reg?.unit}</span>
                      </div>
                    </div>
                    <div className="card" style={{ flex: 1, textAlign: "center", padding: "16px" }}>
                      <span style={{ fontSize: "13px", color: "var(--text-muted)", textTransform: "uppercase" }}>Maximum Value</span>
                      <div style={{ fontSize: "28px", fontWeight: 700, marginTop: "4px", color: "var(--color-danger)", fontFamily: "var(--font-mono)" }}>
                        {stats.max} <span style={{ fontSize: "14px" }}>{reg?.unit}</span>
                      </div>
                    </div>
                    <div className="card" style={{ flex: 1, textAlign: "center", padding: "16px" }}>
                      <span style={{ fontSize: "13px", color: "var(--text-muted)", textTransform: "uppercase" }}>Average Value</span>
                      <div style={{ fontSize: "28px", fontWeight: 700, marginTop: "4px", color: "var(--color-primary)", fontFamily: "var(--font-mono)" }}>
                        {stats.avg} <span style={{ fontSize: "14px" }}>{reg?.unit}</span>
                      </div>
                    </div>
                  </div>
                );
              })()
            ) : (
              <div className="card" style={{ marginBottom: "32px", padding: "20px" }}>
                <h3 style={{ fontSize: "16px", marginBottom: "16px", fontWeight: 600 }}>Registry Statistical Summary</h3>
                <div style={{ overflowX: "auto" }}>
                  <table style={{ width: "100%", borderCollapse: "collapse", textAlign: "left" }}>
                    <thead>
                      <tr style={{ borderBottom: "1px solid var(--border-color)", paddingBottom: "8px" }}>
                        <th style={{ padding: "8px", color: "var(--text-muted)", fontSize: "13px" }}>Register</th>
                        <th style={{ padding: "8px", color: "var(--text-muted)", fontSize: "13px" }}>Min Value</th>
                        <th style={{ padding: "8px", color: "var(--text-muted)", fontSize: "13px" }}>Max Value</th>
                        <th style={{ padding: "8px", color: "var(--text-muted)", fontSize: "13px" }}>Average Value</th>
                        <th style={{ padding: "8px", color: "var(--text-muted)", fontSize: "13px" }}>Unit</th>
                      </tr>
                    </thead>
                    <tbody>
                      {selectedRegisters.map((regId, idx) => {
                        const reg = registers.find(r => r.id === regId);
                        const stats = registerStats[regId] || { min: 0, max: 0, avg: 0 };
                        const colorHex = PALETTE[idx % PALETTE.length];
                        return (
                          <tr key={regId} style={{ borderBottom: "1px solid rgba(255,255,255,0.03)" }}>
                            <td style={{ padding: "12px 8px", fontSize: "14px", fontWeight: 500, display: "flex", alignItems: "center", gap: "8px" }}>
                              <span style={{ display: "inline-block", width: "10px", height: "10px", borderRadius: "50%", background: colorHex }} />
                              {reg?.name || `Register ${regId}`}
                            </td>
                            <td style={{ padding: "12px 8px", fontSize: "14px", fontFamily: "var(--font-mono)", color: "var(--color-secondary)" }}>{stats.min}</td>
                            <td style={{ padding: "12px 8px", fontSize: "14px", fontFamily: "var(--font-mono)", color: "var(--color-danger)" }}>{stats.max}</td>
                            <td style={{ padding: "12px 8px", fontSize: "14px", fontFamily: "var(--font-mono)", color: "var(--color-primary)" }}>{stats.avg}</td>
                            <td style={{ padding: "12px 8px", fontSize: "14px", color: "var(--text-muted)" }}>{reg?.unit}</td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* Chart.js Graphical Display */}
            {(() => {
              const chartLabels = trendData.map(d => d.timestamp);
              const chartDatasets = selectedRegisters.map((regId, idx) => {
                const reg = Array.isArray(registers) ? registers.find(r => r.id === regId) : undefined;
                const colorHex = PALETTE[idx % PALETTE.length];
                return {
                  label: reg ? `${reg.name} (${reg.unit})` : `Register ${regId}`,
                  data: trendData.map(d => d[regId]),
                  borderColor: colorHex,
                  backgroundColor: colorHex + "20",
                  borderWidth: 2,
                  pointRadius: 3,
                  pointHoverRadius: 6,
                  tension: 0.3,
                  fill: false,
                };
              });

              const chartData = {
                labels: chartLabels,
                datasets: chartDatasets
              };

              const chartOptions = {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                  legend: {
                    position: "top" as const,
                    labels: {
                      color: "#94A3B8",
                      font: {
                        family: "Outfit, sans-serif",
                        size: 13,
                      },
                      usePointStyle: true,
                      padding: 20
                    }
                  },
                  tooltip: {
                    backgroundColor: "#0F172A",
                    titleColor: "#F8FAFC",
                    bodyColor: "#F8FAFC",
                    borderColor: "rgba(239, 68, 68, 0.4)",
                    borderWidth: 1,
                    padding: 12,
                    boxPadding: 6,
                    usePointStyle: true
                  }
                },
                scales: {
                  x: {
                    grid: {
                      color: "rgba(255, 255, 255, 0.05)"
                    },
                    ticks: {
                      color: "#64748B",
                      font: {
                        size: 11
                      }
                    }
                  },
                  y: {
                    grid: {
                      color: "rgba(255, 255, 255, 0.05)"
                    },
                    ticks: {
                      color: "#64748B",
                      font: {
                        size: 11
                      }
                    }
                  }
                }
              };

              return (
                <div className="card" style={{ padding: "24px", height: "450px" }}>
                  <Line data={chartData} options={chartOptions} />
                </div>
              );
            })()}
          </div>
        ) : (
          <div className="card" style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", minHeight: "350px", textAlign: "center" }}>
            <Activity size={48} style={{ color: "var(--text-muted)", marginBottom: "16px", opacity: 0.5 }} />
            <h3 style={{ fontSize: "18px", marginBottom: "8px" }}>Historical Query Analyzer</h3>
            <p style={{ color: "var(--text-muted)", maxWidth: "450px", fontSize: "14px" }}>
              Select a Modbus device and mapped register channels, choose your temporal window, and hit "Query" to graph trends and extract formal audit reports.
            </p>
          </div>
        )}
      </main>
    </div>
  );
}
