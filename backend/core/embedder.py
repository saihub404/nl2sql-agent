"""
Embedder — sentence-transformers + FAISS for top-K table selection.
Converts table descriptions into dense vectors and performs similarity
search to retrieve the most relevant tables for a given NL query.
"""
import numpy as np
from typing import Optional

from sentence_transformers import SentenceTransformer
import faiss

from backend.config import settings
from backend.core.schema_loader import TableSchema


class SchemaEmbedder:
    """
    Maintains a FAISS index over table embedding vectors.
    Call `build_index` once after schema loading, then
    use `get_top_k_tables` for each incoming query.
    """

    def __init__(self):
        self._model: Optional[SentenceTransformer] = None
        self._index: Optional[faiss.IndexFlatIP] = None
        self._table_names: list[str] = []
        self._similarity_cache: dict[str, dict[str, float]] = {}

    def _get_model(self) -> SentenceTransformer:
        if self._model is None:
            self._model = SentenceTransformer(settings.embedding_model)
        return self._model

    def build_index(self, schema: dict[str, TableSchema]) -> None:
        """
        Embed all table descriptions and build a FAISS inner-product index.
        Call once at startup after schema loading.
        """
        model = self._get_model()
        self._table_names = list(schema.keys())

        texts = [schema[t].to_embedding_text() for t in self._table_names]
        embeddings: np.ndarray = model.encode(
            texts,
            normalize_embeddings=True,   # unit vectors for cosine similarity
            show_progress_bar=False,
        )

        dim = embeddings.shape[1]
        self._index = faiss.IndexFlatIP(dim)
        self._index.add(embeddings.astype(np.float32))

    def get_top_k_tables(
        self,
        query: str,
        k: Optional[int] = None,
    ) -> tuple[list[str], dict[str, float]]:
        """
        Returns (top_k_table_names, similarity_scores_dict).
        scores are cosine similarities in [0, 1].
        """
        if self._index is None:
            raise RuntimeError("Call build_index() before get_top_k_tables()")

        k = k or settings.top_k_tables
        k = min(k, len(self._table_names))

        # Check cache
        if query in self._similarity_cache:
            scores = self._similarity_cache[query]
            top_k = sorted(scores, key=scores.get, reverse=True)[:k]
            return top_k, {t: scores[t] for t in top_k}

        model = self._get_model()
        query_vec: np.ndarray = model.encode(
            [query],
            normalize_embeddings=True,
            show_progress_bar=False,
        ).astype(np.float32)

        scores, indices = self._index.search(query_vec, k)
        top_k_names = [self._table_names[i] for i in indices[0]]
        score_map = {
            self._table_names[indices[0][i]]: float(scores[0][i])
            for i in range(len(indices[0]))
        }

        # Cache result
        self._similarity_cache[query] = score_map
        return top_k_names, score_map

    def is_ready(self) -> bool:
        return self._index is not None

    def add_table(self, table_name: str, table_schema: TableSchema) -> None:
        """
        Hot-add a new table embedding to the live FAISS index.
        No full rebuild — O(1) operation.
        """
        if self._index is None:
            # If index doesn't exist yet, just add and build
            self.build_index({table_name: table_schema})
            return

        model = self._get_model()
        text = table_schema.to_embedding_text()
        vec = model.encode(
            [text],
            normalize_embeddings=True,
            show_progress_bar=False,
        ).astype(np.float32)

        self._index.add(vec)
        self._table_names.append(table_name)
        # Invalidate cache since index changed
        self._similarity_cache.clear()

    def remove_table(self, table_name: str) -> None:
        """
        Remove a table from the index by rebuilding from remaining tables.
        FAISS FlatIP doesn't support in-place deletion, so we rebuild.
        """
        if table_name not in self._table_names:
            return

        self._table_names.remove(table_name)
        self._similarity_cache.clear()

        if not self._table_names:
            self._index = None
            return

        # Rebuild from remaining tables using schema cache
        from backend.core.schema_loader import schema_loader
        remaining = {
            t: schema_loader.get_cached()[t]
            for t in self._table_names
            if t in schema_loader.get_cached()
        }
        if remaining:
            self.build_index(remaining)


# Module-level singleton
schema_embedder = SchemaEmbedder()
