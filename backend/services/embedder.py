"""
Embedding service using sentence-transformers and CLIP
"""
import io
import base64
from typing import Optional, Callable
import numpy as np
from PIL import Image

# Lazy imports for models
_text_model = None
_clip_model = None
_clip_processor = None


def get_text_model(model_name: str = "all-MiniLM-L6-v2"):
    """Get or load text embedding model"""
    global _text_model
    if _text_model is None:
        from sentence_transformers import SentenceTransformer
        _text_model = SentenceTransformer(model_name)
    return _text_model


def get_clip_model(model_name: str = "openai/clip-vit-base-patch32"):
    """Get or load CLIP model and processor"""
    global _clip_model, _clip_processor
    if _clip_model is None:
        from transformers import CLIPModel, CLIPProcessor
        _clip_model = CLIPModel.from_pretrained(model_name)
        _clip_processor = CLIPProcessor.from_pretrained(model_name)
    return _clip_model, _clip_processor


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

    embeddings = []
    total = len(texts)

    for i in range(0, total, batch_size):
        batch = texts[i:i + batch_size]
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

    embeddings = []
    total = len(texts)

    with torch.no_grad():
        for i in range(0, total, batch_size):
            batch = texts[i:i + batch_size]
            inputs = processor(text=batch, return_tensors="pt", padding=True, truncation=True)
            outputs = model.get_text_features(**inputs)
            # Normalize
            normalized = outputs / outputs.norm(dim=-1, keepdim=True)
            embeddings.append(normalized.numpy())

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
    import requests
    model, processor = get_clip_model(model_name)

    embeddings = []
    total = len(images)
    failed_indices = []

    with torch.no_grad():
        for i, img_source in enumerate(images):
            try:
                img = _load_image(img_source)
                inputs = processor(images=img, return_tensors="pt")
                outputs = model.get_image_features(**inputs)
                normalized = outputs / outputs.norm(dim=-1, keepdim=True)
                embeddings.append(normalized.numpy().squeeze())
            except Exception as e:
                # Zero vector for failed images
                dim = 512  # CLIP ViT-B/32 dimension
                embeddings.append(np.zeros(dim))
                failed_indices.append(i)

            if progress_callback:
                progress = (i + 1) / total
                progress_callback(progress, f"Embedding image {i + 1}/{total}")

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

    embeddings = []
    total = len(video_frames)
    dim = 512  # CLIP dimension

    with torch.no_grad():
        for i, frames in enumerate(video_frames):
            if not frames:
                embeddings.append(np.zeros(dim))
                continue

            frame_embeddings = []
            for frame in frames:
                try:
                    img = _load_image(frame)
                    inputs = processor(images=img, return_tensors="pt")
                    outputs = model.get_image_features(**inputs)
                    normalized = outputs / outputs.norm(dim=-1, keepdim=True)
                    frame_embeddings.append(normalized.numpy().squeeze())
                except Exception:
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

            if progress_callback:
                progress = (i + 1) / total
                progress_callback(progress, f"Embedding video {i + 1}/{total}")

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
        # Both - average normalized embeddings
        def text_progress(p, m):
            if progress_callback:
                progress_callback(p * 0.5, m)

        def img_progress(p, m):
            if progress_callback:
                progress_callback(0.5 + p * 0.5, m)

        text_emb = embed_texts_clip(texts, model_name, batch_size, text_progress)
        img_emb = embed_images(images, model_name, batch_size, img_progress)

        # Average where both exist
        combined = []
        for t, im, text, image in zip(text_emb, img_emb, texts, images):
            has_text = text and text.strip()
            has_image = image and image.strip()

            if has_text and has_image:
                avg = (t + im) / 2
                avg = avg / (np.linalg.norm(avg) + 1e-10)
                combined.append(avg)
            elif has_text:
                combined.append(t)
            elif has_image:
                combined.append(im)
            else:
                combined.append(np.zeros_like(t))

        return np.array(combined)


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
    """Load image from URL or base64 data URL"""
    import requests

    if source.startswith('data:'):
        # Base64 data URL
        header, data = source.split(',', 1)
        img_bytes = base64.b64decode(data)
        return Image.open(io.BytesIO(img_bytes)).convert('RGB')
    else:
        # URL
        response = requests.get(source, timeout=30)
        response.raise_for_status()
        return Image.open(io.BytesIO(response.content)).convert('RGB')
