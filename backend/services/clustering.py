"""
Clustering and dimensionality reduction services
"""
from typing import Optional, Callable
import numpy as np
from sklearn.cluster import KMeans
import umap


def cluster_kmeans(
    embeddings: np.ndarray,
    k: int = 5,
    random_state: int = 42
) -> np.ndarray:
    """
    Perform k-means clustering on embeddings.
    Returns cluster labels.
    """
    if len(embeddings) < k:
        k = max(2, len(embeddings))

    kmeans = KMeans(
        n_clusters=k,
        random_state=random_state,
        n_init=10,
        max_iter=300
    )
    return kmeans.fit_predict(embeddings)


def reduce_umap(
    embeddings: np.ndarray,
    n_components: int = 2,
    n_neighbors: int = 15,
    min_dist: float = 0.1,
    spread: float = 1.0,
    random_state: int = 42,
    progress_callback: Optional[Callable[[float, str], None]] = None
) -> np.ndarray:
    """
    Reduce embedding dimensions using UMAP.
    Returns 2D coordinates.
    """
    if progress_callback:
        progress_callback(0.0, "Initializing UMAP...")

    # Adjust n_neighbors if dataset is small
    effective_neighbors = min(n_neighbors, len(embeddings) - 1)
    effective_neighbors = max(2, effective_neighbors)

    reducer = umap.UMAP(
        n_components=n_components,
        n_neighbors=effective_neighbors,
        min_dist=min_dist,
        spread=spread,
        random_state=random_state,
        verbose=False
    )

    if progress_callback:
        progress_callback(0.1, "Running UMAP dimensionality reduction...")

    coords = reducer.fit_transform(embeddings)

    if progress_callback:
        progress_callback(1.0, "UMAP complete")

    return coords


def compute_visualization(
    embeddings: np.ndarray,
    k: int = 5,
    n_neighbors: int = 15,
    min_dist: float = 0.1,
    progress_callback: Optional[Callable[[float, str], None]] = None
) -> tuple[np.ndarray, np.ndarray]:
    """
    Compute both UMAP coordinates and cluster assignments.
    Returns (coords, clusters).
    """
    def umap_progress(p, m):
        if progress_callback:
            progress_callback(p * 0.8, m)

    if progress_callback:
        progress_callback(0.0, "Starting visualization computation...")

    # UMAP first
    coords = reduce_umap(
        embeddings,
        n_neighbors=n_neighbors,
        min_dist=min_dist,
        progress_callback=umap_progress
    )

    if progress_callback:
        progress_callback(0.85, "Clustering...")

    # K-means on original embeddings
    clusters = cluster_kmeans(embeddings, k)

    if progress_callback:
        progress_callback(1.0, "Visualization complete")

    return coords, clusters


def normalize_coords(coords: np.ndarray) -> np.ndarray:
    """
    Normalize coordinates to [-1, 1] range for visualization.
    """
    min_vals = coords.min(axis=0)
    max_vals = coords.max(axis=0)
    ranges = max_vals - min_vals

    # Avoid division by zero
    ranges[ranges == 0] = 1

    normalized = 2 * (coords - min_vals) / ranges - 1
    return normalized


def get_bounds(coords: np.ndarray) -> dict:
    """
    Get coordinate bounds for visualization setup.
    """
    min_x, min_y = coords.min(axis=0)
    max_x, max_y = coords.max(axis=0)
    center_x = (min_x + max_x) / 2
    center_y = (min_y + max_y) / 2
    span_x = max_x - min_x
    span_y = max_y - min_y

    return {
        "min_x": float(min_x),
        "min_y": float(min_y),
        "max_x": float(max_x),
        "max_y": float(max_y),
        "center_x": float(center_x),
        "center_y": float(center_y),
        "span_x": float(span_x),
        "span_y": float(span_y)
    }
