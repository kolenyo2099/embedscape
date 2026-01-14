"""
Session save/load routes
"""
import json
from datetime import datetime
from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import JSONResponse, StreamingResponse
import io

from models.schemas import SessionData, ColumnConfig, EmbeddingConfig
from api.routes.data import get_current_data, set_current_data
from api.routes.embeddings import get_embeddings_state, set_embeddings_state

router = APIRouter()

# Tag storage
_tags: dict[str, list[int]] = {}  # tag_name -> list of node ids
_tag_colors: dict[str, str] = {}


def get_tags():
    return _tags, _tag_colors


def set_tags(tags: dict[str, list[int]], colors: dict[str, str]):
    global _tags, _tag_colors
    _tags = tags
    _tag_colors = colors


@router.post("/save")
async def save_session():
    """Save current session to JSON"""
    data, columns = get_current_data()
    embeddings, coords, clusters, config = get_embeddings_state()
    tags, tag_colors = get_tags()

    if not data:
        raise HTTPException(status_code=400, detail="No data to save")

    if embeddings is None:
        raise HTTPException(status_code=400, detail="No embeddings to save")

    # Build session object
    session = {
        "version": "2.0",
        "timestamp": datetime.now().isoformat(),
        "data": data,
        "columns": columns,
        "config": config.model_dump() if config else {},
        "embeddings": embeddings,
        "coords": coords,
        "clusters": clusters,
        "tags": tags,
        "tag_colors": tag_colors
    }

    # Generate filename
    filename = f"embedscape_session_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

    # Return as downloadable JSON
    content = json.dumps(session, indent=2)
    return StreamingResponse(
        io.BytesIO(content.encode('utf-8')),
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.post("/load")
async def load_session(file: UploadFile = File(...)):
    """Load session from JSON file"""
    if not file.filename or not file.filename.endswith('.json'):
        raise HTTPException(status_code=400, detail="Please upload a JSON file")

    content = await file.read()

    try:
        session = json.loads(content.decode('utf-8'))
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON file")

    # Validate version
    version = session.get('version', '1.0')

    # Extract data
    data = session.get('data', [])
    if not data:
        raise HTTPException(status_code=400, detail="No data in session file")

    columns = session.get('columns', [])
    if not columns and data:
        columns = list(data[0].keys())

    # Set data
    set_current_data(data, columns)

    # Extract embeddings
    embeddings = session.get('embeddings')
    coords = session.get('coords')
    clusters = session.get('clusters')

    if embeddings:
        # Reconstruct config
        config_dict = session.get('config', {})
        config = EmbeddingConfig(**config_dict) if config_dict else EmbeddingConfig()

        set_embeddings_state(embeddings, coords, clusters, config)

    # Extract tags
    tags = session.get('tags', {})
    tag_colors = session.get('tag_colors', {})
    set_tags(tags, tag_colors)

    return {
        "success": True,
        "version": version,
        "rows": len(data),
        "has_embeddings": embeddings is not None,
        "embedding_count": len(embeddings) if embeddings else 0,
        "tag_count": len(tags)
    }


@router.get("/tags")
async def get_all_tags():
    """Get all tags and their assignments"""
    tags, tag_colors = get_tags()
    return {
        "tags": tags,
        "colors": tag_colors
    }


@router.post("/tags/add")
async def add_tag(tag_name: str, node_ids: list[int]):
    """Add tag to nodes"""
    global _tags, _tag_colors

    if tag_name not in _tags:
        _tags[tag_name] = []
        # Generate color
        colors = ['#e6194b', '#3cb44b', '#ffe119', '#4363d8', '#f58231',
                  '#911eb4', '#46f0f0', '#f032e6', '#bcf60c', '#fabebe',
                  '#008080', '#e6beff', '#9a6324', '#fffac8', '#800000']
        _tag_colors[tag_name] = colors[len(_tags) % len(colors)]

    for node_id in node_ids:
        if node_id not in _tags[tag_name]:
            _tags[tag_name].append(node_id)

    return {"success": True, "tag": tag_name, "count": len(_tags[tag_name])}


@router.post("/tags/remove")
async def remove_tag(tag_name: str, node_ids: list[int]):
    """Remove tag from nodes"""
    global _tags

    if tag_name not in _tags:
        raise HTTPException(status_code=404, detail="Tag not found")

    for node_id in node_ids:
        if node_id in _tags[tag_name]:
            _tags[tag_name].remove(node_id)

    # Remove empty tags
    if not _tags[tag_name]:
        del _tags[tag_name]
        if tag_name in _tag_colors:
            del _tag_colors[tag_name]

    return {"success": True, "tag": tag_name}


@router.delete("/tags/{tag_name}")
async def delete_tag(tag_name: str):
    """Delete a tag entirely"""
    global _tags, _tag_colors

    if tag_name not in _tags:
        raise HTTPException(status_code=404, detail="Tag not found")

    del _tags[tag_name]
    if tag_name in _tag_colors:
        del _tag_colors[tag_name]

    return {"success": True}


@router.delete("/tags")
async def clear_all_tags():
    """Clear all tags"""
    set_tags({}, {})
    return {"success": True}
