// ==============================================================================
// THE LOGGER — PM2 ECOSYSTEM PRODUCTION CONFIGURATION
// Domain: logger.theautomationpeople.in
// ==============================================================================

module.exports = {
  apps: [
    // --------------------------------------------------------------------------
    // 1. Python FastAPI Backend Process (using backend/.venv)
    // --------------------------------------------------------------------------
    {
      name: "thelogger-backend",
      cwd: "./backend",
      script: "main.py",
      interpreter: "./.venv/bin/python", // Virtual environment Python executable
      autorestart: true,
      watch: false,
      max_memory_restart: "1G",
      env: {
        NODE_ENV: "production",
        PYTHONUNBUFFERED: "1",
        RELOAD: "false",
        PORT: 8000
      },
      env_production: {
        NODE_ENV: "production",
        PYTHONUNBUFFERED: "1",
        RELOAD: "false",
        PORT: 8000
      }
    },

    // --------------------------------------------------------------------------
    // 2. Next.js Frontend Process
    // --------------------------------------------------------------------------
    {
      name: "thelogger-frontend",
      cwd: "./frontend",
      script: "node_modules/next/dist/bin/next",
      args: "start -p 3000",
      autorestart: true,
      watch: false,
      max_memory_restart: "1G",
      env: {
        NODE_ENV: "production",
        PORT: 3000
      },
      env_production: {
        NODE_ENV: "production",
        PORT: 3000
      }
    }
  ]
};
