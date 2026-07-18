# Modbus Auto-Discovery & Simulation Guide

This document describes the design, architecture, scale capabilities, and testing steps for the **Modbus Network Scanner Wizard** implemented in **The Logger** platform.

---

## 1. Capacity & Scaling

* **Unlimited Gateway IPs**: Gateways and IP connection settings are no longer static or hardcoded in configuration files. They are stored dynamically in the relational database, permitting connection to and polling of **unlimited unique IP addresses**.
* **Up to 247 Slave IDs per IP**: The application fully adheres to the Modbus protocol specification, supporting up to **247 Modbus Slave IDs** per target IP address. Each Slave ID functions as an independent node and maintains its own discrete register-to-telemetry mapping.
* **Asynchronous & Concurrent Operations**: 
  * The backend polling worker executes async polling loops to query all registered devices concurrently without performance bottlenecks.
  * The IP and Slave scanners use a multi-threaded `ThreadPoolExecutor` to speed up subnet scans and slave ping iterations.

---

## 2. Functional Architecture (Before vs. Now)

| Feature | Legacy State | Upgraded State (Current) |
| :--- | :--- | :--- |
| **IP Management** | Manually entered static IPs. | Dynamically discoverable subnets & online hosts. |
| **Slave ID Selection** | Manual configuration; blind mapping. | Automated ping scanner querying standard Modbus range (1-247). |
| **Node Provisioning** | Manual setup of devices and individual registers. | Single-click Auto-Binding which registers the gateway and maps default templates. |
| **Testing Flow** | Required physical PLC connection. | Integrated local loopback TCP socket simulator. |

---

## 3. System Architecture & Components

```
┌────────────────────────────────────────────────────────┐
│                   React Frontend                       │
│  (Scan Wizard UI: Subnet Inputs -> Detected Slaves)    │
└───────────┬────────────────────────────────┬───────────┘
            │                                │
            │ (1) Scan Subnet                │ (3) Scan Slaves
            ▼                                ▼
┌────────────────────────────────────────────────────────┐
│                   FastAPI Backend                      │
└───────────┬────────────────────────────────┬───────────┘
            │                                │
            │ (2) Ping Port 502/5020         │ (4) Send FC03 to Slave IDs
            ▼                                ▼
┌────────────────────────────────────────────────────────┐
│               Modbus Network Simulator                 │
│  • Simulates Gateway A (127.0.0.1:5020) Slaves [1, 2]  │
│  • Simulates Gateway B (127.0.0.1:5021) Slaves [3, 4]  │
└────────────────────────────────────────────────────────┘
```

### 3.1. Subnet Scan (`POST /api/scan/ips`)
Scans a target subnet range (or loopback `127.0.0.1`) on specified ports (e.g. `5020, 5021`). It attempts a TCP socket handshake with a timeout of 200ms. Discovered active listeners are returned as active gateways.

### 3.2. Slave ID Scan (`POST /api/scan/slaves`)
For a target gateway IP/Port, sequentially sends a raw Modbus TCP Read Holding Registers frame (Function Code 3, Register 0) to Unit IDs (Slave IDs) in the requested range. If the target responds with either a Modbus data payload (`0x03`) or a Modbus exception (`0x83`), the slave ID is registered as active.

---

## 4. Local Simulator Testing Instructions

To test the end-to-end auto-discovery flow locally without physical hardware:

### Step 1: Start the Modbus Simulator
Run the simulator in your terminal. This spawns TCP listeners on port `5020` (allowed Slave IDs: `1, 2`) and port `5021` (allowed Slave IDs: `3, 4`).
```bash
python backend/simulator.py
```

### Step 2: Start the Backend Server
Run the FastAPI backend server:
```bash
python backend/main.py
```

### Step 3: Launch Next.js Dev Server
```bash
npm run dev
```

### Step 4: Run the UI Discovery Scan
1. Open the platform in your browser, log in as `admin`, and navigate to **Devices**.
2. Click **Scan Network** in the top header.
3. In the Scan Wizard modal, set the subnet to `127.0.0.1` and the ports to `5020, 5021`.
4. Click **Scan Subnet**. It will list `127.0.0.1:5020` and `127.0.0.1:5021` as detected gateways.
5. Click on `127.0.0.1:5020` and click **Ping Slave IDs**. It will output `Slave 1` and `Slave 2` as active.
6. Click **Provision Discovered Nodes** to bind the device and map its registers instantly.
