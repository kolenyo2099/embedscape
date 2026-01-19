"""
Data upload and parsing routes
"""
import io
import json
from typing import Optional
from fastapi import APIRouter, UploadFile, File, HTTPException, Query, Body
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from models.schemas import DataPreview
from services.parser import parse_csv, parse_ndjson, flatten_social_media_data

router = APIRouter()

# In-memory storage for current session data
_current_data: list[dict] = []
_current_columns: list[str] = []
_modified_indices: set[int] = set()


class RowUpdate(BaseModel):
    updates: dict


class AddColumnRequest(BaseModel):
    name: str
    default_value: str = ""


def get_current_data():
    return _current_data, _current_columns


def get_modified_indices():
    return _modified_indices


def clear_modified_indices():
    global _modified_indices
    _modified_indices = set()


def set_current_data(data: list[dict], columns: list[str]):
    global _current_data, _current_columns, _modified_indices
    _current_data = data
    _current_columns = columns
    _modified_indices = set()  # Clear modified on new data load


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


@router.put("/row/{index}")
async def update_row(index: int, row_update: RowUpdate):
    """Update a specific row's data"""
    global _modified_indices
    
    if index < 0 or index >= len(_current_data):
        raise HTTPException(status_code=404, detail=f"Row index {index} out of range")
    
    # Update the row with new values
    for key, value in row_update.updates.items():
        _current_data[index][key] = value
    
    # Track as modified
    _modified_indices.add(index)
    
    return {"success": True, "index": index, "modified_count": len(_modified_indices)}


class SplitColumnRequest(BaseModel):
    source_column: str
    mode: str  # 'delimiter' or 'regex'
    pattern: str  # delimiter char or regex pattern
    new_column_prefix: str
    keep_original: bool = True


@router.post("/column")
async def add_column(request: AddColumnRequest):
    """Add a new column to all rows"""
    global _current_columns
    
    if not _current_data:
        raise HTTPException(status_code=400, detail="No data loaded")
    
    if request.name in _current_columns:
        raise HTTPException(status_code=400, detail=f"Column '{request.name}' already exists")
    
    # Add column to all rows
    for row in _current_data:
        row[request.name] = request.default_value
    
    # Add to columns list
    _current_columns.append(request.name)
    
    return {
        "success": True,
        "column": request.name,
        "total_columns": len([c for c in _current_columns if not c.startswith('__')])
    }


@router.post("/column/split")
async def split_column(request: SplitColumnRequest):
    """Split a column into multiple columns by delimiter or regex"""
    import re
    global _current_columns
    
    if not _current_data:
        raise HTTPException(status_code=400, detail="No data loaded")
    
    if request.source_column not in _current_columns:
        raise HTTPException(status_code=400, detail=f"Column '{request.source_column}' not found")
    
    # Determine the maximum number of parts we'll need
    max_parts = 0
    split_results = []
    
    for row in _current_data:
        value = str(row.get(request.source_column, "") or "")
        
        if request.mode == 'delimiter':
            # Handle special delimiters
            if request.pattern == '\\t':
                parts = value.split('\t')
            elif request.pattern == '\\n':
                parts = value.split('\n')
            else:
                parts = value.split(request.pattern)
        else:  # regex mode
            try:
                # Use findall for capture groups or split
                pattern = re.compile(request.pattern)
                if '(' in request.pattern:
                    # Has capture groups - use findall
                    matches = pattern.findall(value)
                    if matches:
                        # Flatten if we got tuples (multiple groups)
                        if isinstance(matches[0], tuple):
                            parts = list(matches[0])
                        else:
                            parts = matches
                    else:
                        parts = ['']
                else:
                    # No capture groups - use split
                    parts = pattern.split(value)
            except re.error as e:
                raise HTTPException(status_code=400, detail=f"Invalid regex: {str(e)}")
        
        # Strip whitespace from parts
        parts = [p.strip() for p in parts]
        split_results.append(parts)
        max_parts = max(max_parts, len(parts))
    
    if max_parts == 0:
        raise HTTPException(status_code=400, detail="No data to split")
    
    # Create new column names
    new_columns = []
    for i in range(max_parts):
        col_name = f"{request.new_column_prefix}_{i + 1}"
        # Ensure unique names
        base_name = col_name
        counter = 1
        while col_name in _current_columns:
            col_name = f"{base_name}_{counter}"
            counter += 1
        new_columns.append(col_name)
    
    # Add new columns to each row
    for i, row in enumerate(_current_data):
        parts = split_results[i]
        for j, col_name in enumerate(new_columns):
            row[col_name] = parts[j] if j < len(parts) else ""
    
    # Update columns list
    if request.keep_original:
        # Insert new columns after the source column
        source_idx = _current_columns.index(request.source_column)
        for i, col_name in enumerate(new_columns):
            _current_columns.insert(source_idx + 1 + i, col_name)
    else:
        # Replace the source column with new columns
        source_idx = _current_columns.index(request.source_column)
        _current_columns.remove(request.source_column)
        for i, col_name in enumerate(new_columns):
            _current_columns.insert(source_idx + i, col_name)
        # Remove source data from rows
        for row in _current_data:
            if request.source_column in row:
                del row[request.source_column]
    
    return {
        "success": True,
        "new_columns": new_columns,
        "total_columns": len([c for c in _current_columns if not c.startswith('__')])
    }


@router.get("/modified")
async def get_modified():
    """Get list of modified row indices"""
    return {
        "indices": list(_modified_indices),
        "count": len(_modified_indices)
    }


@router.delete("/modified/clear")
async def clear_modified():
    """Clear the modified indices tracking"""
    clear_modified_indices()
    return {"success": True}
