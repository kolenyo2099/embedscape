"""
EmbedScape Backend - FastAPI Application
"""
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import data, embeddings, search, sessions
from api.websocket import router as ws_router


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
    allow_origins=["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173"],
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


@app.get("/")
async def root():
    return {"message": "EmbedScape API v2.0", "status": "running"}


@app.get("/health")
async def health():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
