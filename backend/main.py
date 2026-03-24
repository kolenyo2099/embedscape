"""
EmbedScape Backend - FastAPI Application
"""
import os
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from api.routes import data, embeddings, search, sessions
from api.websocket import router as ws_router

# Create uploads directory if it doesn't exist
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: pre-load models if needed
    print("EmbedScape backend starting...")
    yield
    # Shutdown: cleanup
    print("EmbedScape backend shutting down...")


app = FastAPI(
    title="EmbedScape API",
    description="Semantic embedding visualization backend",
    version="2.0.0",
    lifespan=lifespan
)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173", "http://localhost:5174"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(data.router, prefix="/api/data", tags=["data"])
app.include_router(embeddings.router, prefix="/api/embeddings", tags=["embeddings"])
app.include_router(search.router, prefix="/api/search", tags=["search"])
app.include_router(sessions.router, prefix="/api/sessions", tags=["sessions"])
app.include_router(ws_router, tags=["websocket"])

# Serve uploaded media files
app.mount("/api/media", StaticFiles(directory=str(UPLOAD_DIR)), name="media")


@app.get("/")
async def root():
    return {"message": "EmbedScape API v2.0", "status": "running"}


@app.get("/health")
async def health():
    return {"status": "healthy"}


if __name__ == "__main__":
    import socket
    import uvicorn

    preferred = int(os.environ.get("BACKEND_PORT", 8000))
    port = preferred
    while True:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(("localhost", port)) != 0:
                break
            print(f"Port {port} is in use, trying {port + 1}...")
            port += 1

    if port != preferred:
        print(f"Warning: preferred port {preferred} was in use. Using port {port} instead.")
        print(f"Start the frontend with: BACKEND_PORT={port} npm run dev")

    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
