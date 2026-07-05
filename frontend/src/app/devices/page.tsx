"use client";

import { useEffect, useState } from "react";
import Sidebar from "@/components/Sidebar";
import { Plus, Edit, Trash2, Cpu, FileText, ChevronRight, X, AlertTriangle } from "lucide-react";

interface Device {
  id: number;
  name: string;
  connection_type: "TCP" | "RTU";
  host?: string;
  port?: number;
  com_port?: string;
  baudrate?: number;
  parity?: "N" | "E" | "O";
  bytesize?: number;
  stopbits?: number;
}

interface Register {
  id: number;
  device_id: number;
  name: string;
  address: number;
  register_type: "Coil (FC01)" | "Discrete Input (FC02)" | "Holding Register (FC03)" | "Input Register (FC04)";
  data_type: "INT16" | "UINT16" | "INT32" | "UINT32" | "FLOAT32" | "BCD";
  multiplier: number;
  divisor: number;
  unit: string;
  limit_min?: number;
  limit_max?: number;
}

export default function DeviceManager() {
  const [devices, setDevices] = useState<Device[]>([]);
  const [selectedDevice, setSelectedDevice] = useState<Device | null>(null);
  const [registers, setRegisters] = useState<Register[]>([]);
  const [loading, setLoading] = useState(false);

  // Modals status
  const [showDeviceModal, setShowDeviceModal] = useState(false);
  const [showRegisterModal, setShowRegisterModal] = useState(false);
  const [editingDevice, setEditingDevice] = useState<Device | null>(null);
  const [editingRegister, setEditingRegister] = useState<Register | null>(null);

  // Form Fields for Device
  const [deviceName, setDeviceName] = useState("");
  const [connectionType, setConnectionType] = useState<"TCP" | "RTU">("TCP");
  const [tcpHost, setTcpHost] = useState("127.0.0.1");
  const [tcpPort, setTcpPort] = useState(502);
  const [rtuComPort, setRtuComPort] = useState("COM1");
  const [rtuBaud, setRtuBaud] = useState(9600);
  const [rtuParity, setRtuParity] = useState<"N" | "E" | "O">("N");
  const [rtuBytesize, setRtuBytesize] = useState(8);
  const [rtuStopbits, setRtuStopbits] = useState(1);

  // Form Fields for Register
  const [regName, setRegName] = useState("");
  const [regAddress, setRegAddress] = useState(0);
  const [regType, setRegType] = useState<Register["register_type"]>("Holding Register (FC03)");
  const [regDataType, setRegDataType] = useState<Register["data_type"]>("FLOAT32");
  const [regMultiplier, setRegMultiplier] = useState(1.0);
  const [regDivisor, setRegDivisor] = useState(1.0);
  const [regUnit, setRegUnit] = useState("");
  const [regMin, setRegMin] = useState<number | "">("");
  const [regMax, setRegMax] = useState<number | "">("");

  const fetchData = async () => {
    setLoading(true);
    try {
      const res = await fetch("http://localhost:8000/api/devices");
      const data = await res.json();
      setDevices(data);
      if (data.length > 0 && !selectedDevice) {
        setSelectedDevice(data[0]);
      }
    } catch (err) {
      console.error("Error fetching devices:", err);
      // Mock data for static verification/fallback
      const mockD: Device[] = [
        { id: 1, name: "PLC_Chiller", connection_type: "TCP", host: "192.168.1.50", port: 502 },
        { id: 2, name: "Flowmeter_RTU", connection_type: "RTU", com_port: "COM3", baudrate: 9600, parity: "N", bytesize: 8, stopbits: 1 },
        { id: 3, name: "Energy_Meter", connection_type: "TCP", host: "192.168.1.55", port: 502 }
      ];
      setDevices(mockD);
      if (mockD.length > 0 && !selectedDevice) {
        setSelectedDevice(mockD[0]);
      }
    } finally {
      setLoading(false);
    }
  };

  const fetchRegisters = async (deviceId: number) => {
    try {
      const res = await fetch(`http://localhost:8000/api/devices/${deviceId}/registers`);
      const data = await res.json();
      setRegisters(data);
    } catch (err) {
      console.error("Error fetching registers:", err);
      // Mock registers
      const mockR: Register[] = [
        { id: 1, device_id: 1, name: "Chiller Temperature", address: 40001, register_type: "Holding Register (FC03)", data_type: "FLOAT32", multiplier: 1.0, divisor: 10.0, unit: "°C", limit_min: 5, limit_max: 35 },
        { id: 2, device_id: 1, name: "Chiller State", address: 10001, register_type: "Discrete Input (FC02)", data_type: "INT16", multiplier: 1, divisor: 1, unit: "ON/OFF" },
        { id: 3, device_id: 1, name: "Pressure Limit Alarm", address: 1, register_type: "Coil (FC01)", data_type: "INT16", multiplier: 1, divisor: 1, unit: "Alarm" },
        { id: 4, device_id: 2, name: "Flow Rate", address: 30005, register_type: "Input Register (FC04)", data_type: "FLOAT32", multiplier: 1.0, divisor: 1.0, unit: "m³/h", limit_max: 200 },
        { id: 5, device_id: 3, name: "Main Supply Voltage", address: 40020, register_type: "Holding Register (FC03)", data_type: "FLOAT32", multiplier: 1.0, divisor: 10.0, unit: "V" },
        { id: 6, device_id: 3, name: "Current Draw", address: 40022, register_type: "Holding Register (FC03)", data_type: "FLOAT32", multiplier: 1.0, divisor: 100.0, unit: "A" }
      ];
      setRegisters(mockR.filter(r => r.device_id === deviceId));
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  useEffect(() => {
    if (selectedDevice) {
      fetchRegisters(selectedDevice.id);
    } else {
      setRegisters([]);
    }
  }, [selectedDevice]);

  const openAddDevice = () => {
    setEditingDevice(null);
    setDeviceName("");
    setConnectionType("TCP");
    setTcpHost("127.0.0.1");
    setTcpPort(502);
    setRtuComPort("COM1");
    setRtuBaud(9600);
    setRtuParity("N");
    setRtuBytesize(8);
    setRtuStopbits(1);
    setShowDeviceModal(true);
  };

  const openEditDevice = (dev: Device) => {
    setEditingDevice(dev);
    setDeviceName(dev.name);
    setConnectionType(dev.connection_type);
    if (dev.connection_type === "TCP") {
      setTcpHost(dev.host || "127.0.0.1");
      setTcpPort(dev.port || 502);
    } else {
      setRtuComPort(dev.com_port || "COM1");
      setRtuBaud(dev.baudrate || 9600);
      setRtuParity(dev.parity || "N");
      setRtuBytesize(dev.bytesize || 8);
      setRtuStopbits(dev.stopbits || 1);
    }
    setShowDeviceModal(true);
  };

  const saveDevice = async (e: React.FormEvent) => {
    e.preventDefault();
    const payload = connectionType === "TCP" ? {
      name: deviceName,
      connection_type: "TCP",
      host: tcpHost,
      port: tcpPort
    } : {
      name: deviceName,
      connection_type: "RTU",
      com_port: rtuComPort,
      baudrate: rtuBaud,
      parity: rtuParity,
      bytesize: rtuBytesize,
      stopbits: rtuStopbits
    };

    try {
      const url = editingDevice 
        ? `http://localhost:8000/api/devices/${editingDevice.id}`
        : "http://localhost:8000/api/devices";
      
      const method = editingDevice ? "PUT" : "POST";
      
      const res = await fetch(url, {
        method,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      const saved = await res.json();
      
      if (editingDevice) {
        setDevices(devices.map(d => d.id === editingDevice.id ? saved : d));
        setSelectedDevice(saved);
      } else {
        setDevices([...devices, saved]);
        setSelectedDevice(saved);
      }
      setShowDeviceModal(false);
    } catch (err) {
      // Mock save
      const mockSaved = {
        id: editingDevice ? editingDevice.id : Date.now(),
        ...payload
      } as Device;
      if (editingDevice) {
        setDevices(devices.map(d => d.id === editingDevice.id ? mockSaved : d));
        setSelectedDevice(mockSaved);
      } else {
        setDevices([...devices, mockSaved]);
        setSelectedDevice(mockSaved);
      }
      setShowDeviceModal(false);
    }
  };

  const deleteDevice = async (id: number) => {
    if (!confirm("Are you sure you want to delete this device and all its registers?")) return;
    try {
      await fetch(`http://localhost:8000/api/devices/${id}`, { method: "DELETE" });
      const nextDevices = devices.filter(d => d.id !== id);
      setDevices(nextDevices);
      setSelectedDevice(nextDevices.length > 0 ? nextDevices[0] : null);
    } catch (err) {
      const nextDevices = devices.filter(d => d.id !== id);
      setDevices(nextDevices);
      setSelectedDevice(nextDevices.length > 0 ? nextDevices[0] : null);
    }
  };

  const openAddRegister = () => {
    if (!selectedDevice) return;
    setEditingRegister(null);
    setRegName("");
    setRegAddress(40001);
    setRegType("Holding Register (FC03)");
    setRegDataType("FLOAT32");
    setRegMultiplier(1.0);
    setRegDivisor(1.0);
    setRegUnit("");
    setRegMin("");
    setRegMax("");
    setShowRegisterModal(true);
  };

  const openEditRegister = (reg: Register) => {
    setEditingRegister(reg);
    setRegName(reg.name);
    setRegAddress(reg.address);
    setRegType(reg.register_type);
    setRegDataType(reg.data_type);
    setRegMultiplier(reg.multiplier);
    setRegDivisor(reg.divisor);
    setRegUnit(reg.unit);
    setRegMin(reg.limit_min !== undefined && reg.limit_min !== null ? reg.limit_min : "");
    setRegMax(reg.limit_max !== undefined && reg.limit_max !== null ? reg.limit_max : "");
    setShowRegisterModal(true);
  };

  const saveRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedDevice) return;

    const payload = {
      device_id: selectedDevice.id,
      name: regName,
      address: Number(regAddress),
      register_type: regType,
      data_type: regDataType,
      multiplier: Number(regMultiplier),
      divisor: Number(regDivisor),
      unit: regUnit,
      limit_min: regMin === "" ? undefined : Number(regMin),
      limit_max: regMax === "" ? undefined : Number(regMax)
    };

    try {
      const url = editingRegister
        ? `http://localhost:8000/api/registers/${editingRegister.id}`
        : "http://localhost:8000/api/registers";
      
      const method = editingRegister ? "PUT" : "POST";
      
      const res = await fetch(url, {
        method,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      const saved = await res.json();
      
      if (editingRegister) {
        setRegisters(registers.map(r => r.id === editingRegister.id ? saved : r));
      } else {
        setRegisters([...registers, saved]);
      }
      setShowRegisterModal(false);
    } catch (err) {
      // Mock save
      const mockSaved = {
        id: editingRegister ? editingRegister.id : Date.now(),
        ...payload
      } as Register;
      if (editingRegister) {
        setRegisters(registers.map(r => r.id === editingRegister.id ? mockSaved : r));
      } else {
        setRegisters([...registers, mockSaved]);
      }
      setShowRegisterModal(false);
    }
  };

  const deleteRegister = async (id: number) => {
    if (!confirm("Are you sure you want to delete this register?")) return;
    try {
      await fetch(`http://localhost:8000/api/registers/${id}`, { method: "DELETE" });
      setRegisters(registers.filter(r => r.id !== id));
    } catch (err) {
      setRegisters(registers.filter(r => r.id !== id));
    }
  };

  return (
    <div className="app-container">
      <Sidebar />

      <main className="main-content">
        <header className="page-header">
          <div>
            <h1 className="page-title">Device & Register Manager</h1>
            <p className="page-subtitle">Configure Modbus TCP server maps and Serial RTU COM configurations</p>
          </div>
          <button onClick={openAddDevice} className="btn btn-primary">
            <Plus size={16} /> Add Device
          </button>
        </header>

        <div style={{ display: "flex", gap: "32px", alignItems: "flex-start" }}>
          
          {/* Devices List Left Sidebar */}
          <div style={{ width: "320px", display: "flex", flexDirection: "column", gap: "16px" }}>
            <h3 style={{ fontSize: "14px", color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.05em" }}>Modbus Nodes</h3>
            
            {devices.map((d) => (
              <div 
                key={d.id} 
                className={`card ${selectedDevice?.id === d.id ? "active" : ""}`}
                style={{ 
                  padding: "16px", 
                  cursor: "pointer", 
                  borderColor: selectedDevice?.id === d.id ? "var(--color-primary)" : "var(--border-color)",
                  background: selectedDevice?.id === d.id ? "rgba(16, 185, 129, 0.04)" : "var(--bg-card)",
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center"
                }}
                onClick={() => setSelectedDevice(d)}
              >
                <div style={{ display: "flex", gap: "12px", alignItems: "center" }}>
                  <Cpu size={20} style={{ color: d.connection_type === "TCP" ? "var(--color-secondary)" : "var(--color-warning)" }} />
                  <div>
                    <h4 style={{ fontSize: "15px", fontWeight: 600, color: "#fff" }}>{d.name}</h4>
                    <span style={{ fontSize: "12px", color: "var(--text-muted)" }}>
                      {d.connection_type === "TCP" ? `TCP: ${d.host}:${d.port}` : `RTU: ${d.com_port} @ ${d.baudrate}`}
                    </span>
                  </div>
                </div>
                <div style={{ display: "flex", gap: "4px" }} onClick={(e) => e.stopPropagation()}>
                  <button onClick={() => openEditDevice(d)} style={{ background: "transparent", border: "none", color: "var(--text-muted)", cursor: "pointer", padding: "4px" }}>
                    <Edit size={14} />
                  </button>
                  <button onClick={() => deleteDevice(d.id)} style={{ background: "transparent", border: "none", color: "var(--color-danger)", cursor: "pointer", padding: "4px" }}>
                    <Trash2 size={14} />
                  </button>
                </div>
              </div>
            ))}

            {devices.length === 0 && (
              <p style={{ color: "var(--text-muted)", fontSize: "14px", padding: "16px" }}>No devices added yet.</p>
            )}
          </div>

          {/* Registers Table Right Content Area */}
          <div style={{ flexGrow: 1 }}>
            {selectedDevice ? (
              <div>
                <div className="flex-between" style={{ marginBottom: "16px" }}>
                  <h3 style={{ fontSize: "18px", color: "#fff", display: "flex", alignItems: "center", gap: "8px" }}>
                    <FileText size={18} style={{ color: "var(--color-primary)" }} /> Configured Registers for <span style={{ color: "var(--color-primary)" }}>{selectedDevice.name}</span>
                  </h3>
                  <button onClick={openAddRegister} className="btn btn-secondary">
                    <Plus size={16} /> Add Register
                  </button>
                </div>

                <div className="table-container">
                  <table className="table">
                    <thead>
                      <tr>
                        <th>Register Name</th>
                        <th>Address</th>
                        <th>Type (FC)</th>
                        <th>Data Type</th>
                        <th>Scale</th>
                        <th>Unit</th>
                        <th>Alarm Range</th>
                        <th>Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {registers.map((r) => (
                        <tr key={r.id}>
                          <td style={{ fontWeight: 600, color: "#fff" }}>{r.name}</td>
                          <td style={{ fontFamily: "var(--font-mono)", fontSize: "13px" }}>{r.address}</td>
                          <td>{r.register_type.split(" ")[0]}</td>
                          <td style={{ fontSize: "13px" }}>{r.data_type}</td>
                          <td>
                            {r.multiplier !== 1 || r.divisor !== 1 ? `x${r.multiplier} /${r.divisor}` : "1:1"}
                          </td>
                          <td style={{ fontWeight: 500 }}>{r.unit}</td>
                          <td>
                            {r.limit_min !== undefined || r.limit_max !== undefined ? (
                              <span style={{ color: "var(--color-warning)", display: "flex", gap: "4px", alignItems: "center", fontSize: "12px" }}>
                                <AlertTriangle size={12} />
                                {r.limit_min !== undefined ? `>=${r.limit_min}` : ""}
                                {r.limit_min !== undefined && r.limit_max !== undefined ? " & " : ""}
                                {r.limit_max !== undefined ? `<=${r.limit_max}` : ""}
                              </span>
                            ) : (
                              <span style={{ color: "var(--text-muted)", fontSize: "12px" }}>Disabled</span>
                            )}
                          </td>
                          <td>
                            <div style={{ display: "flex", gap: "8px" }}>
                              <button onClick={() => openEditRegister(r)} className="btn btn-secondary" style={{ padding: "6px 10px", fontSize: "12px" }}>
                                <Edit size={12} />
                              </button>
                              <button onClick={() => deleteRegister(r.id)} className="btn btn-secondary" style={{ padding: "6px 10px", fontSize: "12px", color: "var(--color-danger)" }}>
                                <Trash2 size={12} />
                              </button>
                            </div>
                          </td>
                        </tr>
                      ))}

                      {registers.length === 0 && (
                        <tr>
                          <td colSpan={8} style={{ textAlign: "center", color: "var(--text-muted)", padding: "32px" }}>
                            No registers configured for this device. Click "Add Register" to configure points.
                          </td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
            ) : (
              <div className="card" style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", height: "300px", textAlign: "center" }}>
                <Cpu size={48} style={{ color: "var(--text-muted)", marginBottom: "16px", opacity: 0.5 }} />
                <h3 style={{ fontSize: "18px", marginBottom: "8px" }}>No Device Selected</h3>
                <p style={{ color: "var(--text-muted)", fontSize: "14px" }}>Select an existing device from the sidebar, or create a new node to see registers.</p>
              </div>
            )}
          </div>
        </div>

        {/* DEVICE FORM MODAL */}
        {showDeviceModal && (
          <div className="modal-overlay">
            <div className="modal-content">
              <div className="modal-header">
                <h2 className="page-title" style={{ fontSize: "20px" }}>{editingDevice ? "Edit Device Config" : "Add Modbus Device Node"}</h2>
                <button onClick={() => setShowDeviceModal(false)} style={{ background: "transparent", border: "none", color: "#fff", cursor: "pointer" }}><X size={20} /></button>
              </div>

              <form onSubmit={saveDevice}>
                <div className="form-group">
                  <label className="form-label">Device Name / Node Identifier</label>
                  <input type="text" className="form-control" placeholder="e.g. PLC_Chiller" value={deviceName} onChange={e => setDeviceName(e.target.value)} required />
                </div>

                <div className="form-group">
                  <label className="form-label">Connection Type</label>
                  <select className="form-control" value={connectionType} onChange={e => setConnectionType(e.target.value as "TCP" | "RTU")}>
                    <option value="TCP">Modbus TCP (Ethernet / IP)</option>
                    <option value="RTU">Modbus RTU (Serial COM Port)</option>
                  </select>
                </div>

                {connectionType === "TCP" ? (
                  <div className="form-row">
                    <div className="form-group">
                      <label className="form-label">Server IP Address</label>
                      <input type="text" className="form-control" placeholder="192.168.1.50" value={tcpHost} onChange={e => setTcpHost(e.target.value)} required />
                    </div>
                    <div className="form-group">
                      <label className="form-label">Port</label>
                      <input type="number" className="form-control" value={tcpPort} onChange={e => setTcpPort(Number(e.target.value))} required />
                    </div>
                  </div>
                ) : (
                  <div>
                    <div className="form-row">
                      <div className="form-group">
                        <label className="form-label">COM Port</label>
                        <input type="text" className="form-control" placeholder="COM3" value={rtuComPort} onChange={e => setRtuComPort(e.target.value)} required />
                      </div>
                      <div className="form-group">
                        <label className="form-label">Baud Rate</label>
                        <select className="form-control" value={rtuBaud} onChange={e => setRtuBaud(Number(e.target.value))}>
                          <option value={4800}>4800</option>
                          <option value={9600}>9600</option>
                          <option value={19200}>19200</option>
                          <option value={38400}>38400</option>
                          <option value={115200}>115200</option>
                        </select>
                      </div>
                    </div>
                    <div className="form-row">
                      <div className="form-group">
                        <label className="form-label">Parity</label>
                        <select className="form-control" value={rtuParity} onChange={e => setRtuParity(e.target.value as any)}>
                          <option value="N">None (N)</option>
                          <option value="E">Even (E)</option>
                          <option value="O">Odd (O)</option>
                        </select>
                      </div>
                      <div className="form-group">
                        <label className="form-label">Data Bits</label>
                        <input type="number" className="form-control" value={rtuBytesize} onChange={e => setRtuBytesize(Number(e.target.value))} required />
                      </div>
                      <div className="form-group">
                        <label className="form-label">Stop Bits</label>
                        <input type="number" className="form-control" value={rtuStopbits} onChange={e => setRtuStopbits(Number(e.target.value))} required />
                      </div>
                    </div>
                  </div>
                )}

                <div style={{ display: "flex", justifyContent: "flex-end", gap: "12px", marginTop: "24px" }}>
                  <button type="button" className="btn btn-secondary" onClick={() => setShowDeviceModal(false)}>Cancel</button>
                  <button type="submit" className="btn btn-primary">Save Node</button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* REGISTER FORM MODAL */}
        {showRegisterModal && (
          <div className="modal-overlay">
            <div className="modal-content" style={{ maxWidth: "600px" }}>
              <div className="modal-header">
                <h2 className="page-title" style={{ fontSize: "20px" }}>{editingRegister ? "Edit Register Mapping" : "Map Modbus Register Point"}</h2>
                <button onClick={() => setShowRegisterModal(false)} style={{ background: "transparent", border: "none", color: "#fff", cursor: "pointer" }}><X size={20} /></button>
              </div>

              <form onSubmit={saveRegister}>
                <div className="form-row">
                  <div className="form-group">
                    <label className="form-label">Register Description Name</label>
                    <input type="text" className="form-control" placeholder="e.g. Temperature" value={regName} onChange={e => setRegName(e.target.value)} required />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Register Address (0-Based Offset)</label>
                    <input type="number" className="form-control" placeholder="e.g. 40001" value={regAddress} onChange={e => setRegAddress(Number(e.target.value))} required />
                  </div>
                </div>

                <div className="form-row">
                  <div className="form-group">
                    <label className="form-label">Modbus Function Code (Type)</label>
                    <select className="form-control" value={regType} onChange={e => setRegType(e.target.value as any)}>
                      <option value="Coil (FC01)">Coil (FC01) - Read/Write Bits</option>
                      <option value="Discrete Input (FC02)">Discrete Input (FC02) - Read Bits</option>
                      <option value="Holding Register (FC03)">Holding Register (FC03) - Read/Write 16-Bit Word</option>
                      <option value="Input Register (FC04)">Input Register (FC04) - Read 16-Bit Word</option>
                    </select>
                  </div>
                  <div className="form-group">
                    <label className="form-label">Data Decoding Format</label>
                    <select className="form-control" value={regDataType} onChange={e => setRegDataType(e.target.value as any)}>
                      <option value="INT16">Signed 16-Bit Integer (INT16)</option>
                      <option value="UINT16">Unsigned 16-Bit Integer (UINT16)</option>
                      <option value="INT32">Signed 32-Bit Double-Word (INT32)</option>
                      <option value="UINT32">Unsigned 32-Bit Double-Word (UINT32)</option>
                      <option value="FLOAT32">Floating Point 32-Bit Single Precision (FLOAT32)</option>
                      <option value="BCD">Binary Coded Decimal (BCD)</option>
                    </select>
                  </div>
                </div>

                <div className="form-row">
                  <div className="form-group">
                    <label className="form-label">Scaling Multiplier</label>
                    <input type="number" step="any" className="form-control" value={regMultiplier} onChange={e => setRegMultiplier(Number(e.target.value))} required />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Scaling Divisor</label>
                    <input type="number" step="any" className="form-control" value={regDivisor} onChange={e => setRegDivisor(Number(e.target.value))} required />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Unit of Measure</label>
                    <input type="text" className="form-control" placeholder="e.g. °C, V, A, kW" value={regUnit} onChange={e => setRegUnit(e.target.value)} />
                  </div>
                </div>

                <div className="form-row">
                  <div className="form-group">
                    <label className="form-label">Email Trigger Minimum (Low Limit)</label>
                    <input type="number" step="any" className="form-control" placeholder="Alert if less than (optional)" value={regMin} onChange={e => setRegMin(e.target.value === "" ? "" : Number(e.target.value))} />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Email Trigger Maximum (High Limit)</label>
                    <input type="number" step="any" className="form-control" placeholder="Alert if greater than (optional)" value={regMax} onChange={e => setRegMax(e.target.value === "" ? "" : Number(e.target.value))} />
                  </div>
                </div>

                <div style={{ display: "flex", justifyContent: "flex-end", gap: "12px", marginTop: "24px" }}>
                  <button type="button" className="btn btn-secondary" onClick={() => setShowRegisterModal(false)}>Cancel</button>
                  <button type="submit" className="btn btn-primary">Map Register</button>
                </div>
              </form>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
