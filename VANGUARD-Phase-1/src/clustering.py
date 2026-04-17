"""
Grievance clustering and theme detection.
Uses K-means clustering on TF-IDF or embedding vectors.
"""

import logging
from typing import List, Dict, Tuple, Optional
import numpy as np
from collections import Counter

from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score, silhouette_samples

try:
    from sentence_transformers import SentenceTransformer
    HAS_EMBEDDINGS = True
except ImportError:
    HAS_EMBEDDINGS = False

from src.models import Grievance, GrievanceCluster
from src.text_processing import TextProcessor, get_text_processor
from src.standards import GRIEVANCE_THEMES, get_all_themes
from src.utils import get_logger, MIN_GRIEVANCES_FOR_CLUSTERING, DEFAULT_N_CLUSTERS, MAX_N_CLUSTERS, MIN_SILHOUETTE_SCORE

logger = get_logger(__name__)


class GrievanceClustering:
    """Clustering grievances into themes."""
    
    def __init__(self, method: str = 'tfidf', embedding_model: str = 'all-MiniLM-L6-v2'):
        """
        Initialize clustering.
        
        Args:
            method: 'tfidf' or 'embedding'
            embedding_model: Name of sentence transformer model (if method='embedding')
        """
        self.method = method
        self.embedding_model = embedding_model
        self.text_processor = get_text_processor()
        self.model = None
        self.kmeans = None
        self.n_clusters = None
        self.silhouette_avg = None
        
        if method == 'embedding':
            if not HAS_EMBEDDINGS:
                logger.warning("sentence-transformers not installed. Falling back to TF-IDF.")
                self.method = 'tfidf'
            else:
                logger.info(f"Loading embedding model: {embedding_model}")
                try:
                    self.model = SentenceTransformer(embedding_model)
                    logger.info(f"Model loaded successfully")
                except Exception as e:
                    logger.warning(f"Failed to load embedding model: {e}. Falling back to TF-IDF.")
                    self.method = 'tfidf'
    
    def _vectorize_tfidf(self, texts: List[str]) -> np.ndarray:
        """Vectorize texts using TF-IDF."""
        tfidf_matrix, _ = self.text_processor.vectorize_tfidf(texts, max_features=100)
        return tfidf_matrix.toarray()
    
    def _vectorize_embedding(self, texts: List[str]) -> np.ndarray:
        """Vectorize texts using sentence embeddings."""
        logger.info(f"Encoding {len(texts)} texts with sentence transformer")
        embeddings = self.model.encode(texts, show_progress_bar=False)
        return embeddings
    
    def _find_optimal_clusters(self, vectors: np.ndarray, min_k: int = 3, max_k: int = 12) -> Tuple[int, float]:
        """
        Find optimal number of clusters using silhouette score.
        
        Args:
            vectors: Feature vectors
            min_k: Minimum number of clusters
            max_k: Maximum number of clusters
        
        Returns:
            Tuple of (optimal_k, silhouette_score)
        """
        if len(vectors) < min_k:
            logger.warning(f"Only {len(vectors)} documents, using K={min(len(vectors)-1, 3)}")
            optimal_k = max(2, min(len(vectors) - 1, 3))
            return optimal_k, 0.0
        
        max_k = min(max_k, len(vectors) - 1)
        best_k = min_k
        best_score = -1
        
        logger.info(f"Finding optimal clusters (K range: {min_k}-{max_k})")
        
        for k in range(min_k, max_k + 1):
            kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
            cluster_labels = kmeans.fit_predict(vectors)
            
            silhouette_avg = silhouette_score(vectors, cluster_labels)
            logger.debug(f"K={k}: silhouette_score={silhouette_avg:.3f}")
            
            if silhouette_avg > best_score:
                best_score = silhouette_avg
                best_k = k
        
        logger.info(f"Optimal K: {best_k} with silhouette score: {best_score:.3f}")
        return best_k, best_score
    
    def cluster(self, grievances: List[Grievance]) -> List[GrievanceCluster]:
        """
        Cluster grievances by text similarity.
        
        Args:
            grievances: List of grievances
        
        Returns:
            List of GrievanceCluster objects
        
        Raises:
            ValueError: If insufficient grievances
        """
        if len(grievances) < MIN_GRIEVANCES_FOR_CLUSTERING:
            logger.warning(f"Only {len(grievances)} grievances, minimum {MIN_GRIEVANCES_FOR_CLUSTERING} required")
            # Return each grievance as its own cluster
            clusters = []
            for i, grievance in enumerate(grievances):
                cluster = GrievanceCluster(
                    cluster_id=i,
                    theme=f"Complaint_{i}",
                    grievance_ids=[grievance.id],
                    count=1,
                    top_keywords=[],
                    silhouette_score=0.0,
                )
                clusters.append(cluster)
            return clusters
        
        logger.info(f"Clustering {len(grievances)} grievances using {self.method} method")
        
        # Extract texts
        texts = [g.text for g in grievances]
        grievance_ids = [g.id for g in grievances]
        
        # Vectorize
        if self.method == 'embedding' and self.model:
            vectors = self._vectorize_embedding(texts)
        else:
            vectors = self._vectorize_tfidf(texts)
        
        logger.info(f"Vectorized to shape: {vectors.shape}")
        
        # Find optimal k
        optimal_k, silhouette_avg = self._find_optimal_clusters(
            vectors,
            min_k=3,
            max_k=min(MAX_N_CLUSTERS, len(grievances) // 2)
        )
        self.n_clusters = optimal_k
        self.silhouette_avg = silhouette_avg
        
        # Fit K-means with optimal k
        self.kmeans = KMeans(n_clusters=optimal_k, random_state=42, n_init=10)
        cluster_labels = self.kmeans.fit_predict(vectors)
        
        # Calculate silhouette samples
        silhouette_vals = silhouette_samples(vectors, cluster_labels)
        
        # Create clusters
        clusters = []
        for cluster_id in range(optimal_k):
            mask = cluster_labels == cluster_id
            cluster_grievance_ids = [gid for gid, m in zip(grievance_ids, mask) if m]
            cluster_texts = [text for text, m in zip(texts, mask) if m]
            
            # Extract top keywords
            top_keywords = self.text_processor.extract_keywords_from_cluster(cluster_texts, top_n=5)
            
            # Calculate average silhouette score for this cluster
            cluster_silhouette_scores = silhouette_vals[cluster_labels == cluster_id]
            avg_silhouette = float(np.mean(cluster_silhouette_scores)) if len(cluster_silhouette_scores) > 0 else 0.0
            
            cluster = GrievanceCluster(
                cluster_id=cluster_id,
                theme=f"Theme_{cluster_id}",  # Will be labeled later
                grievance_ids=cluster_grievance_ids,
                count=len(cluster_grievance_ids),
                top_keywords=top_keywords,
                silhouette_score=avg_silhouette,
            )
            clusters.append(cluster)
        
        logger.info(f"Created {len(clusters)} clusters")
        return clusters
    
    def label_clusters(self, clusters: List[GrievanceCluster], grievances: List[Grievance]) -> List[GrievanceCluster]:
        """
        Label clusters with theme names based on keywords.
        
        Args:
            clusters: List of GrievanceCluster objects
            grievances: List of Grievance objects (for reference)
        
        Returns:
            Clusters with theme labels
        """
        # Create ID -> grievance mapping
        grievance_map = {g.id: g for g in grievances}
        
        # Define theme keywords
        theme_keywords = GRIEVANCE_THEMES
        
        for cluster in clusters:
            # Get top keywords for this cluster
            cluster_text = " ".join([
                grievance_map[gid].text for gid in cluster.grievance_ids
                if gid in grievance_map
            ])
            
            keywords = self.text_processor.extract_keywords_from_cluster([cluster_text], top_n=10)
            cluster.top_keywords = keywords
            
            # Find best matching theme
            best_theme = None
            best_match_count = 0
            
            for theme, theme_kws in theme_keywords.items():
                # Count how many keywords match
                match_count = sum(1 for kw in keywords if kw in theme_kws)
                if match_count > best_match_count:
                    best_match_count = match_count
                    best_theme = theme
            
            # If no theme matched well, use keywords to generate theme
            if best_theme is None or best_match_count < 1:
                if keywords:
                    best_theme = f"{keywords[0].title()} Issues"
                else:
                    best_theme = f"Theme_{cluster.cluster_id}"
            
            cluster.theme = best_theme
        
        logger.info("Labeled clusters with themes")
        return clusters


def cluster_grievances(
    grievances: List[Grievance],
    method: str = 'tfidf',
    label_clusters: bool = True
) -> List[GrievanceCluster]:
    """
    Cluster grievances and optionally label them.
    
    Args:
        grievances: List of Grievance objects
        method: 'tfidf' or 'embedding'
        label_clusters: Whether to auto-label clusters
    
    Returns:
        List of GrievanceCluster objects
    """
    clusterer = GrievanceClustering(method=method)
    clusters = clusterer.cluster(grievances)
    
    if label_clusters:
        clusters = clusterer.label_clusters(clusters, grievances)
    
    return clusters
