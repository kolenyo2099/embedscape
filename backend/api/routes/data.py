"""
Data upload and parsing routes
"""
import io
import json
from typing import Optional
from fastapi import APIRouter, UploadFile, File, HTTPException, Query
from fastapi.responses import JSONResponse

from models.schemas import DataPreview
from services.parser import parse_csv, parse_ndjson, flatten_social_media_data

router = APIRouter()

# In-memory storage for current session data
_current_data: list[dict] = []
_current_columns: list[str] = []


def get_current_data():
    return _current_data, _current_columns


def set_current_data(data: list[dict], columns: list[str]):
    global _current_data, _current_columns
    _current_data = data
    _current_columns = columns


@router.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """Upload and parse CSV or NDJSON file"""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    filename = file.filename.lower()
    content = await file.read()

    try:
        if filename.endswith('.csv'):
            data, columns = parse_csv(content)
        elif filename.endswith(('.ndjson', '.jsonl')):
            data, columns = parse_ndjson(content)
        else:
            raise HTTPException(
                status_code=400,
                detail="Unsupported file format. Use CSV, NDJSON, or JSONL."
            )

        set_current_data(data, columns)

        return {
            "success": True,
            "filename": file.filename,
            "rows": len(data),
            "columns": columns,
            "file_type": "csv" if filename.endswith('.csv') else "ndjson"
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Parse error: {str(e)}")


@router.post("/upload/media")
async def upload_media(files: list[UploadFile] = File(...)):
    """Upload images or videos for direct embedding"""
    import base64

    media_items = []

    for file in files:
        if not file.filename:
            continue

        content = await file.read()
        content_type = file.content_type or ""

        if content_type.startswith("image/"):
            media_type = "image"
        elif content_type.startswith("video/"):
            media_type = "video"
        else:
            continue

        # Convert to base64 data URL
        b64 = base64.b64encode(content).decode('utf-8')
        data_url = f"data:{content_type};base64,{b64}"

        media_items.append({
            "name": file.filename,
            "type": media_type,
            "data_url": data_url,
            "size": len(content)
        })

    # Convert to internal format
    data = []
    for i, item in enumerate(media_items):
        row = {
            "label": item["name"],
            "link": "",
            "text": "",
            "__media_type": item["type"],
            "__media_data": item["data_url"]
        }
        if item["type"] == "image":
            row["__imageData"] = item["data_url"]
            row["__videoData"] = ""
        else:
            row["__imageData"] = ""
            row["__videoData"] = item["data_url"]
        data.append(row)

    columns = ["label", "link", "text", "__media_type", "__media_data", "__imageData", "__videoData"]
    set_current_data(data, columns)

    return {
        "success": True,
        "count": len(media_items),
        "items": [{"name": m["name"], "type": m["type"]} for m in media_items]
    }


@router.get("/all")
async def get_all_data():
    """Get full current data"""
    data, columns = get_current_data()

    if not data:
        return {"rows": [], "columns": [], "total_rows": 0}

    # Filter out internal columns from display
    display_columns = [c for c in columns if not c.startswith('__')]

    clean_data = []
    for row in data:
        clean_row = {k: v for k, v in row.items() if not k.startswith('__')}
        clean_data.append(clean_row)

    return {
        "rows": clean_data,
        "columns": display_columns,
        "total_rows": len(data)
    }


@router.get("/preview", response_model=DataPreview)
async def get_preview(
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0)
):
    """Get preview of current data"""
    data, columns = get_current_data()

    if not data:
        return DataPreview(rows=[], columns=[], total_rows=0)

    # Filter out internal columns from display
    display_columns = [c for c in columns if not c.startswith('__')]

    preview_rows = []
    for row in data[offset:offset + limit]:
        preview_row = {k: v for k, v in row.items() if not k.startswith('__')}
        preview_rows.append(preview_row)

    return DataPreview(
        rows=preview_rows,
        columns=display_columns,
        total_rows=len(data)
    )


@router.get("/columns")
async def get_columns():
    """Get available columns for configuration"""
    data, columns = get_current_data()

    if not columns:
        return {"columns": [], "suggested": {}}

    # Filter internal columns
    display_columns = [c for c in columns if not c.startswith('__')]

    # Auto-suggest columns based on names
    suggested = {}
    for col in display_columns:
        col_lower = col.lower()
        if 'text' in col_lower or 'caption' in col_lower or 'content' in col_lower:
            suggested.setdefault('text', col)
        elif 'label' in col_lower or 'name' in col_lower or 'title' in col_lower:
            suggested.setdefault('label', col)
        elif 'url' in col_lower or 'link' in col_lower or 'href' in col_lower:
            if 'image' in col_lower or 'img' in col_lower or 'photo' in col_lower:
                suggested.setdefault('image', col)
            elif 'video' in col_lower or 'vid' in col_lower:
                suggested.setdefault('video', col)
            else:
                suggested.setdefault('link', col)

    return {
        "columns": display_columns,
        "suggested": suggested,
        "total_rows": len(data)
    }


@router.delete("/clear")
async def clear_data():
    """Clear current session data"""
    set_current_data([], [])
    return {"success": True}
