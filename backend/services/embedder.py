"""
Embedding service using sentence-transformers and CLIP
"""
import io
import base64
from pathlib import Path
from typing import Optional, Callable, Any
from urllib.parse import urlparse
import numpy as np
from PIL import Image

# Lazy imports for models
_text_models: dict[str, Any] = {}
_clip_models: dict[str, Any] = {}
_clip_processors: dict[str, Any] = {}
_device = None
_UPLOAD_DIR = Path("uploads").resolve()


def get_device():
    """Detect and return the best available device (MPS, CUDA, or CPU)"""
    global _device
    if _device is None:
        import torch
        if torch.backends.mps.is_available():
            _device = torch.device("mps")
            print("🚀 Using Apple Metal (MPS) for GPU acceleration")
        elif torch.cuda.is_available():
            _device = torch.device("cuda")
            print(f"🚀 Using CUDA GPU: {torch.cuda.get_device_name(0)}")
        else:
            _device = torch.device("cpu")
            print("⚠️  Using CPU (no GPU detected)")
    return _device


def get_text_model(model_name: str = "all-MiniLM-L6-v2"):
    """Get or load text embedding model"""
    global _text_models
    if model_name not in _text_models:
        from sentence_transformers import SentenceTransformer
        device = get_device()
        _text_models[model_name] = SentenceTransformer(model_name, device=str(device))
    return _text_models[model_name]


def get_clip_model(model_name: str = "openai/clip-vit-base-patch32"):
    """Get or load CLIP model and processor"""
    global _clip_models, _clip_processors
    if model_name not in _clip_models:
        from transformers import CLIPModel, CLIPProcessor
        device = get_device()
        _clip_models[model_name] = CLIPModel.from_pretrained(model_name).to(device)
        _clip_processors[model_name] = CLIPProcessor.from_pretrained(model_name)
    return _clip_models[model_name], _clip_processors[model_name]


def resolve_media_source_path(source: str) -> Path:
    """
    Resolve a /api/media/* URL to a local file path inside uploads/.
    Reject path traversal.
    """
    if not source.startswith("/api/media/"):
        raise ValueError("Unsupported media source path")

    relative = source.replace("/api/media/", "", 1)
    resolved = (_UPLOAD_DIR / relative).resolve()

    # Ensure resolved path is within uploads directory.
    if resolved != _UPLOAD_DIR and _UPLOAD_DIR not in resolved.parents:
        raise ValueError(f"Invalid media path: {source}")

    if not resolved.exists():
        raise FileNotFoundError(f"Media file not found: {resolved}")

    return resolved


def embed_texts(
    texts: list[str],
    model_name: str = "all-MiniLM-L6-v2",
    batch_size: int = 32,
    progress_callback: Optional[Callable[[float, str], None]] = None
) -> np.ndarray:
    """
    Generate embeddings for text using sentence-transformers.
    Returns normalized embeddings.
    """
    model = get_text_model(model_name)
    dim = model.get_sentence_embedding_dimension()

    embeddings = []
    total = len(texts)
    if total == 0:
        return np.empty((0, dim), dtype=np.float32)

    for i in range(0, total, batch_size):
        batch = ["" if t is None else str(t) for t in texts[i:i + batch_size]]
        batch_emb = model.encode(
            batch,
            normalize_embeddings=True,
            show_progress_bar=False
        )
        embeddings.append(batch_emb)

        if progress_callback:
            progress = min((i + len(batch)) / total, 1.0)
            progress_callback(progress, f"Embedding text {min(i + batch_size, total)}/{total}")

    return np.vstack(embeddings)


def embed_texts_clip(
    texts: list[str],
    model_name: str = "openai/clip-vit-base-patch32",
    batch_size: int = 32,
    progress_callback: Optional[Callable[[float, str], None]] = None
) -> np.ndarray:
    """
    Generate CLIP text embeddings (for multimodal search).
    """
    import torch
    model, processor = get_clip_model(model_name)
    device = get_device()

    embeddings = []
    total = len(texts)
    dim = model.config.projection_dim
    if total == 0:
        return np.empty((0, dim), dtype=np.float32)

    with torch.no_grad():
        for i in range(0, total, batch_size):
            batch = ["" if t is None else str(t) for t in texts[i:i + batch_size]]
            inputs = processor(text=batch, return_tensors="pt", padding=True, truncation=True)
            inputs = {k: v.to(device) for k, v in inputs.items()}
            outputs = model.get_text_features(**inputs)
            # Normalize
            normalized = outputs / outputs.norm(dim=-1, keepdim=True)
            embeddings.append(normalized.cpu().numpy())

            if progress_callback:
                progress = min((i + len(batch)) / total, 1.0)
                progress_callback(progress, f"Embedding text (CLIP) {min(i + batch_size, total)}/{total}")

    return np.vstack(embeddings)


def embed_images(
    images: list[str],  # URLs or base64 data URLs
    model_name: str = "openai/clip-vit-base-patch32",
    batch_size: int = 16,
    progress_callback: Optional[Callable[[float, str], None]] = None
) -> np.ndarray:
    """
    Generate CLIP image embeddings.
    Images can be URLs or base64 data URLs.
    """
    import torch
    model, processor = get_clip_model(model_name)
    device = get_device()

    embeddings = []
    total = len(images)
    if total == 0:
        return np.empty((0, 512), dtype=np.float32)
    failed_indices = []

    with torch.no_grad():
        for i, img_source in enumerate(images):
            try:
                img = _load_image(img_source)
                inputs = processor(images=img, return_tensors="pt")
                inputs = {k: v.to(device) for k, v in inputs.items()}
                outputs = model.get_image_features(**inputs)
                normalized = outputs / outputs.norm(dim=-1, keepdim=True)
                embeddings.append(normalized.cpu().numpy().squeeze())
            except Exception as e:
                # Zero vector for failed images
                dim = 512  # CLIP ViT-B/32 dimension
                embeddings.append(np.zeros(dim))
                failed_indices.append(i)
                img_preview = str(img_source)[:100]
                print(f"⚠️  Failed to embed image {i}: {img_preview}... Error: {e}")

            if progress_callback:
                progress = (i + 1) / total
                progress_callback(progress, f"Embedding image {i + 1}/{total}")

    # Raise an error if ALL embeddings failed
    if total > 0 and len(failed_indices) == total:
        raise ValueError(f"Failed to embed all {total} images. Check file paths and formats.")
    elif len(failed_indices) > 0:
        print(f"⚠️  Warning: {len(failed_indices)}/{total} images failed to embed")

    return np.array(embeddings)


def embed_video_frames(
    video_frames: list[list[str]],  # List of frame lists (data URLs)
    model_name: str = "openai/clip-vit-base-patch32",
    progress_callback: Optional[Callable[[float, str], None]] = None
) -> np.ndarray:
    """
    Generate CLIP embeddings for videos by embedding frames and max-pooling.
    """
    import torch
    model, processor = get_clip_model(model_name)
    device = get_device()

    embeddings = []
    total = len(video_frames)
    dim = 512  # CLIP dimension
    if total == 0:
        return np.empty((0, dim), dtype=np.float32)
    failed_videos = 0

    with torch.no_grad():
        for i, frames in enumerate(video_frames):
            if not frames:
                embeddings.append(np.zeros(dim))
                failed_videos += 1
                print(f"⚠️  Video {i}: No frames extracted")
                continue

            frame_embeddings = []
            for j, frame in enumerate(frames):
                try:
                    img = _load_image(frame)
                    inputs = processor(images=img, return_tensors="pt")
                    inputs = {k: v.to(device) for k, v in inputs.items()}
                    outputs = model.get_image_features(**inputs)
                    normalized = outputs / outputs.norm(dim=-1, keepdim=True)
                    frame_embeddings.append(normalized.cpu().numpy().squeeze())
                except Exception as e:
                    print(f"⚠️  Failed to embed frame {j} of video {i}: {e}")
                    continue

            if frame_embeddings:
                # Max pooling across frames
                stacked = np.stack(frame_embeddings)
                pooled = np.max(stacked, axis=0)
                # Re-normalize
                pooled = pooled / (np.linalg.norm(pooled) + 1e-10)
                embeddings.append(pooled)
            else:
                embeddings.append(np.zeros(dim))
                failed_videos += 1
                print(f"⚠️  Video {i}: All frames failed to embed")

            if progress_callback:
                progress = (i + 1) / total
                progress_callback(progress, f"Embedding video {i + 1}/{total}")

    # Raise an error if ALL videos failed
    if total > 0 and failed_videos == total:
        raise ValueError(f"Failed to embed all {total} videos. Check video files and frame extraction.")
    elif failed_videos > 0:
        print(f"⚠️  Warning: {failed_videos}/{total} videos failed to embed")

    return np.array(embeddings)


def embed_multimodal(
    texts: list[str],
    images: list[str],
    source: str = "both",  # 'text', 'image', or 'both'
    model_name: str = "openai/clip-vit-base-patch32",
    batch_size: int = 16,
    progress_callback: Optional[Callable[[float, str], None]] = None
) -> np.ndarray:
    """
    Generate multimodal embeddings.
    When source='both', averages text and image embeddings.
    """
    if source == "text":
        return embed_texts_clip(texts, model_name, batch_size, progress_callback)
    elif source == "image":
        return embed_images(images, model_name, batch_size, progress_callback)
    else:
        # Both - average normalized embeddings where both modalities exist.
        # Handle missing modalities gracefully instead of failing the entire batch.
        total = max(len(texts), len(images))
        dim = 512
        if total == 0:
            return np.empty((0, dim), dtype=np.float32)

        safe_texts = ["" if t is None else str(t) for t in texts]
        safe_images = ["" if im is None else str(im) for im in images]
        if len(safe_texts) < total:
            safe_texts.extend([""] * (total - len(safe_texts)))
        if len(safe_images) < total:
            safe_images.extend([""] * (total - len(safe_images)))

        text_indices = [i for i, t in enumerate(safe_texts) if t.strip()]
        image_indices = [i for i, im in enumerate(safe_images) if im.strip()]
        text_index_set = set(text_indices)
        image_index_set = set(image_indices)

        text_emb = np.zeros((total, dim), dtype=np.float32)
        img_emb = np.zeros((total, dim), dtype=np.float32)

        if text_indices:
            if image_indices:
                def text_progress(p, m):
                    if progress_callback:
                        progress_callback(p * 0.5, m)
            else:
                text_progress = progress_callback

            partial = embed_texts_clip(
                [safe_texts[i] for i in text_indices],
                model_name=model_name,
                batch_size=batch_size,
                progress_callback=text_progress
            )
            text_emb[text_indices] = partial
        elif progress_callback and image_indices:
            progress_callback(0.5, "No text to embed, using images only")

        if image_indices:
            if text_indices:
                def img_progress(p, m):
                    if progress_callback:
                        progress_callback(0.5 + p * 0.5, m)
            else:
                img_progress = progress_callback

            partial = embed_images(
                [safe_images[i] for i in image_indices],
                model_name=model_name,
                batch_size=batch_size,
                progress_callback=img_progress
            )
            img_emb[image_indices] = partial
        elif progress_callback and text_indices:
            progress_callback(1.0, "No images to embed, using text only")

        combined = []
        for i in range(total):
            has_text = i in text_index_set
            has_image = i in image_index_set
            t = text_emb[i]
            im = img_emb[i]

            if has_text and has_image:
                avg = (t + im) / 2
                avg = avg / (np.linalg.norm(avg) + 1e-10)
                combined.append(avg)
            elif has_text:
                combined.append(t)
            elif has_image:
                combined.append(im)
            else:
                combined.append(np.zeros(dim, dtype=np.float32))

        return np.array(combined)


def embed_mixed_media(
    images: list[str],
    videos: list[str],
    model_name: str = "openai/clip-vit-base-patch32",
    video_fps: float = 1.0,
    video_max_frames: int = 30,
    progress_callback: Optional[Callable[[float, str], None]] = None
) -> np.ndarray:
    """
    Embed mixed media (images and videos) intelligently.
    For each row:
    - If it has an image -> embed the image directly
    - If it has a video -> extract frames and embed (max pooling)
    - If both -> prioritize image (faster)
    - If neither -> zero vector
    
    All embeddings are in the same CLIP vector space.
    """
    import torch
    from services.video_processor import extract_frames
    
    model, processor = get_clip_model(model_name)
    device = get_device()
    
    embeddings = []
    total = len(images)
    dim = 512  # CLIP dimension
    if total == 0:
        return np.empty((0, dim), dtype=np.float32)
    
    stats = {"images": 0, "videos": 0, "failed": 0, "empty": 0}
    
    with torch.no_grad():
        for i in range(total):
            img_source = images[i] if i < len(images) else ""
            vid_source = videos[i] if i < len(videos) else ""
            
            has_image = img_source and img_source.strip()
            has_video = vid_source and vid_source.strip()
            
            embedding = None
            
            # Try image first (faster)
            if has_image:
                try:
                    img = _load_image(img_source)
                    inputs = processor(images=img, return_tensors="pt")
                    inputs = {k: v.to(device) for k, v in inputs.items()}
                    outputs = model.get_image_features(**inputs)
                    normalized = outputs / outputs.norm(dim=-1, keepdim=True)
                    embedding = normalized.cpu().numpy().squeeze()
                    stats["images"] += 1
                except Exception as e:
                    print(f"⚠️  Failed to embed image {i}: {e}")
                    # Fall through to try video
            
            # Try video if image failed or doesn't exist
            if embedding is None and has_video:
                try:
                    # Convert API path to file path
                    video_path = vid_source
                    if vid_source.startswith('/api/media/'):
                        video_path = str(resolve_media_source_path(vid_source))
                    
                    # Extract frames
                    frames = extract_frames(
                        video_path,
                        fps=video_fps,
                        max_frames=video_max_frames
                    )
                    
                    if frames:
                        # Embed all frames and max pool
                        frame_embeddings = []
                        for frame in frames:
                            try:
                                img = _load_image(frame)
                                inputs = processor(images=img, return_tensors="pt")
                                inputs = {k: v.to(device) for k, v in inputs.items()}
                                outputs = model.get_image_features(**inputs)
                                normalized = outputs / outputs.norm(dim=-1, keepdim=True)
                                frame_embeddings.append(normalized.cpu().numpy().squeeze())
                            except Exception:
                                continue
                        
                        if frame_embeddings:
                            stacked = np.stack(frame_embeddings)
                            pooled = np.max(stacked, axis=0)
                            embedding = pooled / (np.linalg.norm(pooled) + 1e-10)
                            stats["videos"] += 1
                        else:
                            print(f"⚠️  Video {i}: All frames failed to embed")
                    else:
                        print(f"⚠️  Video {i}: No frames extracted")
                        
                except Exception as e:
                    print(f"⚠️  Failed to embed video {i}: {e}")
            
            # Use zero vector if nothing worked
            if embedding is None:
                embedding = np.zeros(dim)
                if has_image or has_video:
                    stats["failed"] += 1
                else:
                    stats["empty"] += 1
            
            embeddings.append(embedding)
            
            if progress_callback:
                progress = (i + 1) / total
                progress_callback(progress, f"Embedding media {i + 1}/{total}")
    
    # Summary
    print(f"✓ Mixed media embedding complete:")
    print(f"  - Images embedded: {stats['images']}")
    print(f"  - Videos embedded: {stats['videos']}")
    print(f"  - Failed: {stats['failed']}")
    print(f"  - Empty (no media): {stats['empty']}")
    
    # Raise error if everything failed
    if stats["images"] + stats["videos"] == 0:
        raise ValueError("Failed to embed any media. Check file paths and formats.")
    
    return np.array(embeddings)


def search_similar(
    query_embedding: np.ndarray,
    embeddings: np.ndarray,
    threshold: float = 0.7,
    top_k: int = 100
) -> list[tuple[int, float]]:
    """
    Find similar items using cosine similarity.
    Returns list of (index, similarity) tuples.
    """
    # Normalize query
    query_norm = query_embedding / (np.linalg.norm(query_embedding) + 1e-10)

    # Compute similarities
    similarities = np.dot(embeddings, query_norm)

    # Filter by threshold
    mask = similarities >= threshold
    indices = np.where(mask)[0]
    sims = similarities[mask]

    # Sort by similarity
    sorted_idx = np.argsort(-sims)[:top_k]

    return [(int(indices[i]), float(sims[i])) for i in sorted_idx]


def encode_query_text(
    text: str,
    mode: str = "text",
    model_name: str = "all-MiniLM-L6-v2"
) -> np.ndarray:
    """Encode a text query for search"""
    if mode == "text":
        model = get_text_model(model_name)
        return model.encode(text, normalize_embeddings=True)
    else:
        # CLIP text encoding
        return embed_texts_clip([text], model_name)[0]


def encode_query_image(
    image_data: str,  # Base64 data URL
    model_name: str = "openai/clip-vit-base-patch32"
) -> np.ndarray:
    """Encode an image query for search"""
    return embed_images([image_data], model_name)[0]


def _load_image(source: str) -> Image.Image:
    """Load image from URL, base64 data URL, or local file path"""
    import requests

    # Reject empty or whitespace-only sources immediately
    if not source or not source.strip():
        raise ValueError("Empty image source provided")
    source = source.strip()

    if source.startswith('data:'):
        # Base64 data URL
        header, data = source.split(',', 1)
        img_bytes = base64.b64decode(data)
        return Image.open(io.BytesIO(img_bytes)).convert('RGB')
    elif source.startswith('/api/media/'):
        # Local file served via API - convert to actual file path
        file_path = resolve_media_source_path(source)
        return Image.open(file_path).convert('RGB')
    elif urlparse(source).scheme in ("http", "https"):
        # URL
        response = requests.get(source, timeout=30)
        response.raise_for_status()
        return Image.open(io.BytesIO(response.content)).convert('RGB')
    else:
        # Local file path
        file_path = Path(source).expanduser()
        if not file_path.exists():
            raise FileNotFoundError(f"Image file not found: {file_path}")
        return Image.open(file_path).convert('RGB')
