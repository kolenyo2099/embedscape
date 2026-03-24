"""
Pydantic schemas for API request/response models
"""
from typing import Optional, Any
from pydantic import BaseModel, Field


class ColumnConfig(BaseModel):
    text: Optional[str] = None
    label: Optional[str] = None
    link: Optional[str] = None
    image: Optional[str] = None
    video: Optional[str] = None


class EmbeddingConfig(BaseModel):
    mode: str = Field(default="text", description="'text' or 'multimodal'")
    source: str = Field(default="text", description="'text', 'image', 'video', 'both', or 'mixed'")
    model: str = Field(default="all-MiniLM-L6-v2", description="Model name for embeddings")
    image_model: str = Field(default="openai/clip-vit-base-patch32", description="CLIP model for images")
    batch_size: int = Field(default=32, ge=1, le=512)
    k_clusters: int = Field(default=0, ge=0, le=50, description="Number of clusters (0 = auto-detect)")
    video_fps: float = Field(default=1.0, gt=0.0)  # Must be positive, no upper limit
    video_max_frames: int = Field(default=30, ge=1)  # Must be at least 1, no upper limit


class ProcessRequest(BaseModel):
    columns: ColumnConfig
    config: EmbeddingConfig


class SearchRequest(BaseModel):
    query: str
    threshold: float = Field(default=0.7, ge=0.0, le=1.0)
    top_k: int = Field(default=100, ge=1, le=1000)


class ImageSearchRequest(BaseModel):
    image_data: str  # Base64 encoded image
    threshold: float = Field(default=0.7, ge=0.0, le=1.0)
    top_k: int = Field(default=100, ge=1, le=1000)


class TagUpdate(BaseModel):
    node_ids: list[int]
    tag: str
    action: str = Field(description="'add' or 'remove'")


class SessionData(BaseModel):
    version: str = "2.0"
    data: list[dict[str, Any]]
    columns: ColumnConfig
    config: EmbeddingConfig
    embeddings: list[list[float]]
    coords: list[list[float]]
    clusters: list[int]
    tags: dict[str, list[int]]  # tag_name -> list of node ids
    tag_colors: dict[str, str]


class DataPreview(BaseModel):
    rows: list[dict[str, Any]]
    columns: list[str]
    total_rows: int


class EmbeddingResult(BaseModel):
    embeddings: list[list[float]]
    coords: list[list[float]]
    clusters: list[int]


class SearchResult(BaseModel):
    matches: list[dict[str, Any]]  # [{index, similarity, label, ...}]


class ProgressUpdate(BaseModel):
    stage: str
    progress: float  # 0.0 to 1.0
    message: str
    current: Optional[int] = None
    total: Optional[int] = None
