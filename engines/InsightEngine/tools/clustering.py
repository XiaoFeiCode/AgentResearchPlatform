"""
Clustering service for InsightEngine search results.
Uses sentence-transformers embeddings + KMeans to group and sample results.
"""

from typing import Any, List
from app.config import Settings
import numpy as np
from loguru import logger
from sklearn.cluster import KMeans


class ClusteringService:
    """Lazy-loaded clustering pipeline for deduplicated search results."""

    def __init__(self, config):
        self._config:Settings = config
        self._model: Any = None

    def _get_model(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer
            model_name = self._config.CLUSTERING_MODEL_NAME
            logger.info(f"  加载聚类模型 ({model_name})...")
            self._model = SentenceTransformer(model_name)
        return self._model

    def cluster_and_sample(self, results: list, max_results: int | None = None,
                           results_per_cluster: int | None = None) -> list:
        if max_results is None:
            max_results = self._config.MAX_CLUSTERED_RESULTS
        if results_per_cluster is None:
            results_per_cluster = self._config.RESULTS_PER_CLUSTER

        if len(results) <= max_results:
            return results

        try:
            texts = [r.title_or_content[:500] for r in results]
            model = self._get_model()
            embeddings = model.encode(texts, show_progress_bar=False)
            n_clusters = min(max(2, max_results // results_per_cluster), len(results))
            kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
            labels = kmeans.fit_predict(embeddings)

            sampled = []
            for cid in range(n_clusters):
                indices = np.flatnonzero(labels == cid)
                cluster = [(results[i], i) for i in indices]
                cluster.sort(key=lambda x: x[0].hotness_score or 0, reverse=True)
                for r, _ in cluster[:results_per_cluster]:
                    sampled.append(r)
                    if len(sampled) >= max_results:
                        break
                if len(sampled) >= max_results:
                    break
            logger.info(f"  聚类: {len(results)} 条 -> {n_clusters} 主题 -> {len(sampled)} 条")
            return sampled
        except Exception as e:
            logger.warning(f"  聚类失败: {e}")
            return results[:max_results]
