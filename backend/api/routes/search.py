"""
Semantic search routes
"""
import numpy as np
from fastapi import APIRouter, HTTPException

from models.schemas import SearchRequest, ImageSearchRequest, SearchResult
from api.routes.data import get_current_data
from api.routes.embeddings import get_embeddings_state
from services.embedder import (
    encode_query_text, encode_query_image, search_similar
)

router = APIRouter()


@router.post("/text")
async def search_text(request: SearchRequest):
    """Search by text query"""
    embeddings, coords, clusters, config = get_embeddings_state()

    if embeddings is None:
        raise HTTPException(status_code=400, detail="No embeddings available. Process data first.")

    data, columns = get_current_data()

    # Determine mode from config
    mode = config.mode if config else "text"
    if config and mode == "text":
        model_name = config.model
    elif config:
        model_name = config.image_model
    else:
        model_name = "all-MiniLM-L6-v2"

    # Encode query
    query_embedding = encode_query_text(
        request.query,
        mode=mode,
        model_name=model_name
    )

    # Search
    embeddings_array = np.array(embeddings)
    results = search_similar(
        query_embedding,
        embeddings_array,
        threshold=request.threshold,
        top_k=request.top_k
    )

    # Build response with data
    matches = []
    for idx, similarity in results:
        match = {
            "index": idx,
            "similarity": similarity,
            "cluster": clusters[idx] if clusters else 0,
            "coords": coords[idx] if coords else [0, 0]
        }
        # Add row data
        if idx < len(data):
            row = data[idx]
            match["data"] = {k: v for k, v in row.items() if not k.startswith('__')}
        matches.append(match)

    return {"matches": matches, "query": request.query, "total": len(matches)}


@router.post("/image")
async def search_image(request: ImageSearchRequest):
    """Search by image query"""
    embeddings, coords, clusters, config = get_embeddings_state()

    if embeddings is None:
        raise HTTPException(status_code=400, detail="No embeddings available. Process data first.")

    if config and config.mode == "text":
        raise HTTPException(status_code=400, detail="Image search requires multimodal embeddings")

    data, columns = get_current_data()

    model_name = config.image_model if config else "openai/clip-vit-base-patch32"

    # Encode query image
    query_embedding = encode_query_image(
        request.image_data,
        model_name=model_name
    )

    # Search
    embeddings_array = np.array(embeddings)
    results = search_similar(
        query_embedding,
        embeddings_array,
        threshold=request.threshold,
        top_k=request.top_k
    )

    # Build response
    matches = []
    for idx, similarity in results:
        match = {
            "index": idx,
            "similarity": similarity,
            "cluster": clusters[idx] if clusters else 0,
            "coords": coords[idx] if coords else [0, 0]
        }
        if idx < len(data):
            row = data[idx]
            match["data"] = {k: v for k, v in row.items() if not k.startswith('__')}
        matches.append(match)

    return {"matches": matches, "total": len(matches)}


@router.get("/similar/{index}")
async def find_similar(index: int, threshold: float = 0.7, top_k: int = 20):
    """Find items similar to a specific item by index"""
    embeddings, coords, clusters, config = get_embeddings_state()

    if embeddings is None:
        raise HTTPException(status_code=400, detail="No embeddings available")

    if index < 0 or index >= len(embeddings):
        raise HTTPException(status_code=400, detail="Invalid index")

    data, columns = get_current_data()

    # Use the item's embedding as query
    query_embedding = np.array(embeddings[index])
    embeddings_array = np.array(embeddings)

    results = search_similar(
        query_embedding,
        embeddings_array,
        threshold=threshold,
        top_k=top_k + 1  # Include self
    )

    # Filter out self
    matches = []
    for idx, similarity in results:
        if idx == index:
            continue
        match = {
            "index": idx,
            "similarity": similarity,
            "cluster": clusters[idx] if clusters else 0,
            "coords": coords[idx] if coords else [0, 0]
        }
        if idx < len(data):
            row = data[idx]
            match["data"] = {k: v for k, v in row.items() if not k.startswith('__')}
        matches.append(match)

    return {"matches": matches[:top_k], "source_index": index, "total": len(matches)}
