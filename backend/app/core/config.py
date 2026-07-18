import os
from dotenv import load_dotenv

# Root backend directory
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load dotenv from backend root
load_dotenv(os.path.join(BACKEND_DIR, ".env"))

# Data directory paths
DATA_PATH = os.path.join(BACKEND_DIR, "data")
LIVE_LOGS_PATH = os.path.join(DATA_PATH, "live")
REPORTS_PATH = os.path.join(DATA_PATH, "reports")

os.makedirs(DATA_PATH, exist_ok=True)
os.makedirs(LIVE_LOGS_PATH, exist_ok=True)
os.makedirs(REPORTS_PATH, exist_ok=True)

# Database connection URL
DATABASE_URL = os.environ.get("DATABASE_URL", f"sqlite:///{os.path.join(DATA_PATH, 'logger.db')}")

# CORS settings
origins_str = os.environ.get("CORS_ORIGINS", "*")
if origins_str == "*":
    CORS_ORIGINS = ["*"]
else:
    CORS_ORIGINS = [origin.strip() for origin in origins_str.split(",") if origin.strip()]

# Server Host & Port
SERVER_HOST = os.environ.get("SERVER_HOST", "0.0.0.0")
SERVER_PORT = int(os.environ.get("SERVER_PORT", 8000))

# Decryption Keys for Legacy Desktop Configurations
LEGACY_AUTH_DECRYPT_KEY = os.environ.get("LEGACY_AUTH_DECRYPT_KEY", "5DD8180B9BC94632")
LEGACY_DEVICE_DECRYPT_KEY = os.environ.get("LEGACY_DEVICE_DECRYPT_KEY", "0E441257DCFDB6C2")

# Default Admin Credentials
DEFAULT_ADMIN_USERNAME = os.environ.get("DEFAULT_ADMIN_USERNAME", "admin")
DEFAULT_ADMIN_PASSWORD = os.environ.get("DEFAULT_ADMIN_PASSWORD", "admin123")

# Modbus Connection Overrides
MODBUS_OVERRIDE_HOST = os.environ.get("MODBUS_OVERRIDE_HOST", "").strip() or None
MODBUS_OVERRIDE_PORT_STR = os.environ.get("MODBUS_OVERRIDE_PORT", "").strip()
MODBUS_OVERRIDE_PORT = int(MODBUS_OVERRIDE_PORT_STR) if (MODBUS_OVERRIDE_PORT_STR and MODBUS_OVERRIDE_PORT_STR.isdigit()) else None

# JWT Authentication Settings
JWT_SECRET = os.environ.get("JWT_SECRET", "428df13b2c2df23145dae64bbdf023d6a97825dcf29a1b1819d4432101742de8")
JWT_ALGORITHM = os.environ.get("JWT_ALGORITHM", "HS256")
JWT_EXPIRY_MINUTES = int(os.environ.get("JWT_EXPIRY_MINUTES", 1440))


