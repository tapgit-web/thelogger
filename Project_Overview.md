# THE LOGGER Project Overview

This document provides a comprehensive overview of the THE LOGGER project's workflow, key functionalities, and the underlying frameworks/libraries used.

## 1. Technology Stack & Frameworks

The project is built entirely in **Python** as a desktop application. It utilizes several robust libraries for its core functionalities:

*   **Tkinter**: The primary GUI framework used to build the desktop interface.
*   **Pymodbus**: A comprehensive library used for all Modbus communications (both Modbus TCP and Modbus RTU/Serial). It supports various register types and data formatting.
*   **ReportLab**: Used for generating PDF documents, specifically the Trend Reports and data exports.
*   **Pillow (PIL)**: Used for loading, resizing, and rendering images and icons within the Tkinter GUI.
*   **Requests**: Handles HTTP requests for the online licensing and activation system.
*   **PyInstaller**: Used in the build pipeline (`build.bat`) to compile the Python scripts into a standalone Windows executable.
*   **Inno Setup**: A Windows installer creator used (`installer.iss`) to wrap the PyInstaller executable into a distributable `THE_LOGGER_Setup.exe` wizard.

## 2. Core Functionalities

*   **Modbus Communication (TCP & Serial RTU)**
    *   Connects to PLCs, sensors, and meters over network (IP) or COM ports.
    *   Supports Input Registers (FC04), Holding Registers (FC03), Input Coils (FC02), and Output Coils (FC01).
    *   Handles complex data decoding including `FLOAT32`, `UINT32`, `INT32`, `INT16`, `BCD`, and Double Integer types (including ABCD endianness).
*   **Live Data Logging**
    *   Acquires data through background worker threads to keep the UI responsive.
    *   Logs live readings continuously into daily rotated CSV files (stored in the `live` directory).
*   **Email Alert System**
    *   Monitors live register values against user-defined thresholds (e.g., `>`, `<`, `==`).
    *   Sends automated alerts via SMTP when conditions are met.
*   **Trend Reporting & Export**
    *   Parses historical CSV logs to generate structured PDF reports (TrendReports) showing historical data and limits.
*   **Security & Obfuscation**
    *   Local JSON configuration files (devices, users, email settings) are obfuscated using a custom XOR and Base64 encryption tied to the machine's Hardware ID (HWID).
    *   Includes a licensing system that checks an activation key against an external API server (`https://tap-server-v2.onrender.com/activate`) and stores a local hashed license file.
*   **User Management**
    *   Role-based access control (Admin vs. Standard Users) restricting access to critical features like configuration, exporting data, and user management.

## 3. Application Workflow

1.  **Initialization**: 
    *   The application starts up and checks for the existence of `APPDATA/The Logger` directories for localized data storage.
    *   It migrates/obfuscates any plain-text JSON configuration files on startup.
    *   The license manager checks the local machine HWID and the stored license.
2.  **Configuration Loading**:
    *   The application reads `devices.json`, `users.json`, `email_settings.json`, and `trend_settings.json` from the configuration directory, deobfuscating them in memory.
3.  **Background Polling**:
    *   For every configured Modbus device, a dedicated background thread is launched (`read_modbus_device`).
    *   The thread establishes a persistent connection to the device and continuously polls the specified registers.
    *   Retrieved raw data is decoded based on its type and scaled using configured multipliers/divisors.
4.  **Data Processing & UI Update**:
    *   The scaled values are formatted and sent to the main Tkinter thread to update the real-time UI dashboards.
    *   Values are appended to the daily CSV logs.
    *   The system evaluates if any register values have breached configured email alert thresholds and triggers email dispatches if necessary.
5.  **Build & Deployment**:
    *   Developers use `build.bat` to package the Python environment into a single executable using PyInstaller.
    *   `installer.iss` is compiled with Inno Setup to create a professional `Setup.exe` for end-users, placing shortcuts and managing installation paths.
