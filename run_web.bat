@echo off
echo ========================================================
echo        THE LOGGER - Web Application Controller
echo ========================================================
echo.

echo [1/2] Launching FastAPI Backend (Port 8000)...
start "THE LOGGER - Backend API" cmd /k "cd logger\backend && uvicorn main:app --reload --host 0.0.0.0 --port 8000"

echo [2/2] Launching Next.js Frontend (Port 3000)...
start "THE LOGGER - Next.js UI" cmd /k "cd logger\frontend && npm run dev"

echo.
echo --------------------------------------------------------
echo Both services have been launched!
echo.
echo   - Next.js UI:   http://localhost:3000
echo   - Backend API:  http://localhost:8000
echo --------------------------------------------------------
echo.
pause
