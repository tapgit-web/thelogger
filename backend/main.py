import os
import sys

# Ensure backend root directory is in PYTHONPATH
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core import SERVER_HOST, SERVER_PORT
from app.main import app

if __name__ == "__main__":
    import uvicorn
    use_reload = os.environ.get("RELOAD", "true").lower() in ("true", "1")
    uvicorn.run("app.main:app", host=SERVER_HOST, port=SERVER_PORT, reload=use_reload)
