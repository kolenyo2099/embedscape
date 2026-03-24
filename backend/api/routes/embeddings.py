"""
Embedding generation routes
"""
import asyncio
from typing import Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel

from models.schemas import ProcessRequest, EmbeddingResult, ColumnConfig, EmbeddingConfig
from api.routes.data import get_current_data, get_modified_indices, clear_modified_indices
from services.embedder import (
    embed_texts, embed_texts_clip, embed_images,
    embed_video_frames, embed_multimodal, embed_mixed_media, resolve_media_source_path
)
from services.clustering import compute_visualization, get_bounds
from services.video_processor import extract_frames
from api.websocket import broadcast_progress

router = APIRouter()

# Store for current embeddings state
_current_embeddings: Optional[list[list[float]]] = None
_current_coords: Optional[list[list[float]]] = None
_current_clusters: Optional[list[int]] = None
_current_config: Optional[EmbeddingConfig] = None
_processing: bool = False


def _as_str(value) -> str:
    return "" if value is None else str(value)


def _is_selected(col: Optional[str]) -> bool:
    return bool(col and col.strip())


def _validate_columns_for_config(columns: ColumnConfig, config: EmbeddingConfig):
    valid_modes = {"text", "multimodal"}
    valid_sources = {"text", "image", "video", "both", "mixed"}

    if config.mode not in valid_modes:
        raise HTTPException(status_code=400, detail=f"Invalid mode '{config.mode}'")
    if config.source not in valid_sources:
        raise HTTPException(status_code=400, detail=f"Invalid source '{config.source}'")

    if config.mode == "text":
        if not _is_selected(columns.text):
            raise HTTPException(status_code=400, detail="Text mode requires a text column")
        return

    # Multimodal mode
    if config.source == "text" and not _is_selected(columns.text):
        raise HTTPException(status_code=400, detail="Multimodal text source requires a text column")
    if config.source == "image" and not _is_selected(columns.image):
        raise HTTPException(status_code=400, detail="Image source requires an image column")
    if config.source == "video" and not _is_selected(columns.video):
        raise HTTPException(status_code=400, detail="Video source requires a video column")
    if config.source == "both":
        if not _is_selected(columns.text) and not _is_selected(columns.image):
            raise HTTPException(status_code=400, detail="Both source requires text and/or image columns")
    if config.source == "mixed":
        if not _is_selected(columns.image) and not _is_selected(columns.video):
            raise HTTPException(status_code=400, detail="Mixed source requires image and/or video columns")


def get_embeddings_state():
    return _current_embeddings, _current_coords, _current_clusters, _current_config


def set_embeddings_state(embeddings, coords, clusters, config):
    global _current_embeddings, _current_coords, _current_clusters, _current_config
    _current_embeddings = embeddings
    _current_coords = coords
    _current_clusters = clusters
    _current_config = config


@router.post("/generate")
async def generate_embeddings(request: ProcessRequest, background_tasks: BackgroundTasks):
    """Start embedding generation process"""
    global _processing

    if _processing:
        raise HTTPException(status_code=409, detail="Processing already in progress")

    data, columns = get_current_data()
    if not data:
        raise HTTPException(status_code=400, detail="No data loaded")
    _validate_columns_for_config(request.columns, request.config)

    _processing = True

    # Run in background
    background_tasks.add_task(
        _process_embeddings,
        data,
        request.columns,
        request.config
    )

    return {"status": "started", "total_items": len(data)}


async def _process_embeddings(
    data: list[dict],
    columns: ColumnConfig,
    config: EmbeddingConfig
):
    """Background task to generate embeddings"""
    global _processing
    import numpy as np
    import asyncio as aio

    try:
        total = len(data)
        # Get the event loop for thread-safe callbacks
        loop = aio.get_running_loop()

        async def progress(pct: float, msg: str):
            await broadcast_progress("embedding", pct, msg, current=int(pct * total), total=total)

        await progress(0.01, "Starting embedding process...")

        # Extract data based on column config
        texts = []
        images = []
        videos = []

        for row in data:
            texts.append(_as_str(row.get(columns.text, '')) if columns.text else '')
            images.append(_as_str(row.get(columns.image, '')) if columns.image else '')
            videos.append(_as_str(row.get(columns.video, '')) if columns.video else '')

        embeddings = None

        if config.mode == "text":
            # Text-only mode
            await progress(0.05, "Loading text embedding model...")

            def sync_progress(p, m):
                # Use run_coroutine_threadsafe for thread safety
                aio.run_coroutine_threadsafe(progress(0.05 + p * 0.7, m), loop)

            # Run in thread to avoid blocking
            embeddings = await aio.to_thread(
                embed_texts,
                texts,
                model_name=config.model,
                batch_size=config.batch_size,
                progress_callback=sync_progress
            )

        else:
            # Multimodal mode
            if config.source == "video" and columns.video:
                await progress(0.05, "Extracting video frames...")

                # Extract frames from videos
                video_frames = []
                for i, vid in enumerate(videos):
                    if vid and vid.strip():
                        try:
                            # Convert /api/media/ paths to actual file paths
                            video_path = vid
                            if vid.startswith('/api/media/'):
                                video_path = str(resolve_media_source_path(vid))
                            
                            # Run frame extraction in thread
                            frames = await aio.to_thread(
                                extract_frames,
                                video_path,
                                fps=config.video_fps,
                                max_frames=config.video_max_frames
                            )
                            video_frames.append(frames)
                        except Exception as e:
                            print(f"Error extracting frames from {vid}: {e}")
                            video_frames.append([])
                    else:
                        video_frames.append([])
                    await progress(0.05 + (i + 1) / len(videos) * 0.2, f"Extracting frames: {i + 1}/{len(videos)}")

                await progress(0.25, "Embedding video frames...")

                def sync_progress(p, m):
                    # Use run_coroutine_threadsafe for thread safety
                    aio.run_coroutine_threadsafe(progress(0.25 + p * 0.5, m), loop)

                # Run in thread to avoid blocking
                embeddings = await aio.to_thread(
                    embed_video_frames,
                    video_frames,
                    model_name=config.image_model,
                    progress_callback=sync_progress
                )

            elif config.source == "image":
                await progress(0.05, "Loading CLIP model...")

                def sync_progress(p, m):
                    # Use run_coroutine_threadsafe for thread safety
                    aio.run_coroutine_threadsafe(progress(0.05 + p * 0.7, m), loop)

                # Run in thread to avoid blocking
                embeddings = await aio.to_thread(
                    embed_images,
                    images,
                    model_name=config.image_model,
                    batch_size=config.batch_size,
                    progress_callback=sync_progress
                )

            elif config.source == "mixed":
                # Smart mixed media: detect per-row and embed accordingly
                await progress(0.05, "Loading CLIP model for mixed media...")

                def sync_progress(p, m):
                    # Use run_coroutine_threadsafe for thread safety
                    aio.run_coroutine_threadsafe(progress(0.05 + p * 0.7, m), loop)

                # Run in thread to avoid blocking
                embeddings = await aio.to_thread(
                    embed_mixed_media,
                    images,
                    videos,
                    model_name=config.image_model,
                    video_fps=config.video_fps,
                    video_max_frames=config.video_max_frames,
                    progress_callback=sync_progress
                )

            elif config.source == "both":
                await progress(0.05, "Loading CLIP model...")

                def sync_progress(p, m):
                    # Use run_coroutine_threadsafe for thread safety
                    aio.run_coroutine_threadsafe(progress(0.05 + p * 0.7, m), loop)

                # Run in thread to avoid blocking
                embeddings = await aio.to_thread(
                    embed_multimodal,
                    texts,
                    images,
                    source="both",
                    model_name=config.image_model,
                    batch_size=config.batch_size,
                    progress_callback=sync_progress
                )

            else:
                # Text with CLIP
                await progress(0.05, "Loading CLIP text model...")

                def sync_progress(p, m):
                    # Use run_coroutine_threadsafe for thread safety
                    aio.run_coroutine_threadsafe(progress(0.05 + p * 0.7, m), loop)

                # Run in thread to avoid blocking
                embeddings = await aio.to_thread(
                    embed_texts_clip,
                    texts,
                    model_name=config.image_model,
                    batch_size=config.batch_size,
                    progress_callback=sync_progress
                )

        await progress(0.75, "Running UMAP and clustering...")

        def viz_progress(p, m):
            # Use run_coroutine_threadsafe for thread safety
            aio.run_coroutine_threadsafe(progress(0.75 + p * 0.2, m), loop)

        # Run UMAP/clustering in thread to avoid blocking event loop
        coords, clusters = await aio.to_thread(
            compute_visualization,
            embeddings,
            k=config.k_clusters,
            progress_callback=viz_progress
        )

        # Store results
        set_embeddings_state(
            embeddings.tolist(),
            coords.tolist(),
            clusters.tolist(),
            config
        )

        # Add cluster column to data
        for i, cluster_id in enumerate(clusters):
            if i < len(data):
                data[i]['_cluster'] = int(cluster_id)

        await progress(1.0, "Complete!")

        # Send completion message
        await broadcast_progress("complete", 1.0, "Embedding complete", current=total, total=total)

    except Exception as e:
        await broadcast_progress("error", 0, str(e))
        raise

    finally:
        _processing = False


@router.get("/status")
async def get_status():
    """Get current embedding status"""
    embeddings, coords, clusters, config = get_embeddings_state()

    return {
        "processing": _processing,
        "has_embeddings": embeddings is not None,
        "count": len(embeddings) if embeddings else 0,
        "config": config.model_dump() if config else None
    }


@router.get("/result")
async def get_result():
    """Get embedding results"""
    embeddings, coords, clusters, config = get_embeddings_state()

    if embeddings is None:
        raise HTTPException(status_code=404, detail="No embeddings available")

    data, columns = get_current_data()
    bounds = get_bounds(np.array(coords)) if coords else None

    return {
        "embeddings": embeddings,
        "coords": coords,
        "clusters": clusters,
        "bounds": bounds,
        "count": len(embeddings)
    }


@router.get("/coords")
async def get_coords():
    """Get only coordinates and clusters (lighter response)"""
    embeddings, coords, clusters, config = get_embeddings_state()

    if coords is None:
        raise HTTPException(status_code=404, detail="No coordinates available")

    import numpy as np
    bounds = get_bounds(np.array(coords))

    return {
        "coords": coords,
        "clusters": clusters,
        "bounds": bounds
    }


@router.delete("/clear")
async def clear_embeddings():
    """Clear current embeddings"""
    set_embeddings_state(None, None, None, None)
    return {"success": True}


class SelectiveProcessRequest(BaseModel):
    indices: list[int]
    columns: ColumnConfig
    config: EmbeddingConfig


@router.post("/generate/selective")
async def generate_selective_embeddings(request: SelectiveProcessRequest, background_tasks: BackgroundTasks):
    """Re-embed only specified row indices"""
    global _processing

    if _processing:
        raise HTTPException(status_code=409, detail="Processing already in progress")

    data, columns = get_current_data()
    if not data:
        raise HTTPException(status_code=400, detail="No data loaded")

    # Validate indices
    valid_indices = [i for i in request.indices if 0 <= i < len(data)]
    if not valid_indices:
        raise HTTPException(status_code=400, detail="No valid indices provided")
    _validate_columns_for_config(request.columns, request.config)

    _processing = True

    # Run in background
    background_tasks.add_task(
        _process_selective_embeddings,
        data,
        valid_indices,
        request.columns,
        request.config
    )

    return {"status": "started", "total_items": len(valid_indices)}


async def _process_selective_embeddings(
    data: list[dict],
    indices: list[int],
    columns: ColumnConfig,
    config: EmbeddingConfig
):
    """Background task to selectively re-embed specific rows"""
    global _processing
    import numpy as np
    import asyncio as aio

    try:
        total = len(indices)
        # Get the event loop for thread-safe callbacks
        loop = aio.get_running_loop()

        async def progress(pct: float, msg: str):
            await broadcast_progress("embedding", pct, msg, current=int(pct * total), total=total)

        await progress(0.01, f"Re-embedding {total} modified rows...")

        # Get existing embeddings
        existing_embeddings, _, _, _ = get_embeddings_state()
        
        if existing_embeddings is None:
            await broadcast_progress("error", 0, "No existing embeddings to update")
            return

        # Extract data for selected indices
        selected_data = [data[i] for i in indices]
        texts = [_as_str(row.get(columns.text, '')) if columns.text else '' for row in selected_data]
        images = [_as_str(row.get(columns.image, '')) if columns.image else '' for row in selected_data]
        videos = [_as_str(row.get(columns.video, '')) if columns.video else '' for row in selected_data]

        new_embeddings = None

        if config.mode == "text":
            await progress(0.05, "Re-embedding text...")

            def sync_progress(p, m):
                # Use run_coroutine_threadsafe for thread safety
                aio.run_coroutine_threadsafe(progress(0.05 + p * 0.7, m), loop)

            # Run in thread to avoid blocking
            new_embeddings = await aio.to_thread(
                embed_texts,
                texts,
                model_name=config.model,
                batch_size=config.batch_size,
                progress_callback=sync_progress
            )
        else:
            # Multimodal mode
            if config.source == "video" and columns.video:
                await progress(0.05, "Extracting video frames...")

                video_frames = []
                for i, vid in enumerate(videos):
                    if vid and vid.strip():
                        try:
                            video_path = vid
                            if vid.startswith('/api/media/'):
                                video_path = str(resolve_media_source_path(vid))

                            frames = await aio.to_thread(
                                extract_frames,
                                video_path,
                                fps=config.video_fps,
                                max_frames=config.video_max_frames
                            )
                            video_frames.append(frames)
                        except Exception as e:
                            print(f"Error extracting frames from {vid}: {e}")
                            video_frames.append([])
                    else:
                        video_frames.append([])
                    await progress(0.05 + (i + 1) / len(videos) * 0.2, f"Extracting frames: {i + 1}/{len(videos)}")

                await progress(0.25, "Embedding video frames...")

                def sync_progress(p, m):
                    aio.run_coroutine_threadsafe(progress(0.25 + p * 0.5, m), loop)

                new_embeddings = await aio.to_thread(
                    embed_video_frames,
                    video_frames,
                    model_name=config.image_model,
                    progress_callback=sync_progress
                )

            elif config.source == "image":
                await progress(0.05, "Re-embedding images with CLIP...")

                def sync_progress(p, m):
                    aio.run_coroutine_threadsafe(progress(0.05 + p * 0.7, m), loop)

                new_embeddings = await aio.to_thread(
                    embed_images,
                    images,
                    model_name=config.image_model,
                    batch_size=config.batch_size,
                    progress_callback=sync_progress
                )

            elif config.source == "mixed":
                await progress(0.05, "Re-embedding mixed media...")

                def sync_progress(p, m):
                    aio.run_coroutine_threadsafe(progress(0.05 + p * 0.7, m), loop)

                new_embeddings = await aio.to_thread(
                    embed_mixed_media,
                    images,
                    videos,
                    model_name=config.image_model,
                    video_fps=config.video_fps,
                    video_max_frames=config.video_max_frames,
                    progress_callback=sync_progress
                )

            elif config.source == "both":
                await progress(0.05, "Re-embedding text + images with CLIP...")

                def sync_progress(p, m):
                    aio.run_coroutine_threadsafe(progress(0.05 + p * 0.7, m), loop)

                new_embeddings = await aio.to_thread(
                    embed_multimodal,
                    texts,
                    images,
                    source="both",
                    model_name=config.image_model,
                    batch_size=config.batch_size,
                    progress_callback=sync_progress
                )

            else:
                await progress(0.05, "Re-embedding text with CLIP...")

                def sync_progress(p, m):
                    aio.run_coroutine_threadsafe(progress(0.05 + p * 0.7, m), loop)

                new_embeddings = await aio.to_thread(
                    embed_texts_clip,
                    texts,
                    model_name=config.image_model,
                    batch_size=config.batch_size,
                    progress_callback=sync_progress
                )

        await progress(0.75, "Updating embeddings...")

        # Merge new embeddings into existing
        updated_embeddings = np.array(existing_embeddings)
        if updated_embeddings.shape[1] != new_embeddings.shape[1]:
            raise ValueError(
                "Embedding dimension mismatch during selective update. "
                "Run full embedding generation to refresh the entire dataset."
            )
        for i, idx in enumerate(indices):
            updated_embeddings[idx] = new_embeddings[i]

        await progress(0.85, "Recomputing visualization...")

        # Recompute UMAP and clustering with updated embeddings
        def viz_progress(p, m):
            # Use run_coroutine_threadsafe for thread safety
            aio.run_coroutine_threadsafe(progress(0.85 + p * 0.1, m), loop)

        # Run in thread to avoid blocking event loop
        coords, clusters = await aio.to_thread(
            compute_visualization,
            updated_embeddings,
            k=config.k_clusters,
            progress_callback=viz_progress
        )

        # Store results
        set_embeddings_state(
            updated_embeddings.tolist(),
            coords.tolist(),
            clusters.tolist(),
            config
        )

        # Clear modified indices
        clear_modified_indices()

        await progress(1.0, "Complete!")
        await broadcast_progress("complete", 1.0, "Selective embedding complete", current=total, total=total)

    except Exception as e:
        await broadcast_progress("error", 0, str(e))
        raise

    finally:
        _processing = False


# Import numpy for get_result
import numpy as np
