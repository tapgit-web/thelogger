import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core import CORS_ORIGINS, run_migrations
from app.services.modbus_worker import start_polling, stop_polling
from app.api import (
    auth_router, users_router, devices_router, settings_router, polling_router, trends_router
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Run DB schema migrations and config copy from desktop app
    run_migrations()
    # Auto-start polling on startup
    loop = asyncio.get_event_loop()
    start_polling(loop)
    print("FastAPI startup finished: Database initialized and Modbus polling started.")
    yield
    # Stop polling on shutdown
    stop_polling()
    print("FastAPI server shut down: Modbus polling stopped.")

app = FastAPI(title="THE LOGGER Backend Server", version="2.0.0", lifespan=lifespan)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(devices_router)
app.include_router(settings_router)
app.include_router(polling_router)
app.include_router(trends_router)
