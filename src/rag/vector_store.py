from __future__ import annotations

import logging
from typing import Any

import chromadb
from chromadb.config import Settings as ChromaSettings

from src.config import settings

logger = logging.getLogger(__name__)


class VectorStore:
    def __init__(self, persist_dir: str | None = None, collection_name: str = "code_docs"):
        self.persist_dir = persist_dir or settings.chroma_persist_dir
        self.collection_name = collection_name
        self._client: chromadb.PersistentClient | None = None
        self._collection = None

    @property
    def client(self) -> chromadb.PersistentClient:
        if self._client is None:
            self._client = chromadb.PersistentClient(
                path=self.persist_dir,
                settings=ChromaSettings(anonymized_telemetry=False),
            )
        return self._client

    @property
    def collection(self):
        if self._collection is None:
            self._collection = self.client.get_or_create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"},
            )
        return self._collection

    def add_documents(
        self,
        ids: list[str],
        documents: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict[str, Any]] | None = None,
    ):
        self.collection.add(
            ids=ids,
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas,
        )
        logger.info("Added %d documents to vector store", len(documents))

    def query(
        self,
        query_embedding: list[float],
        top_k: int | None = None,
        filter_metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        top_k = top_k or settings.retrieval_top_k
        where_filter = filter_metadata if filter_metadata else None

        result = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=where_filter,
            include=["documents", "metadatas", "distances"],
        )
        return result

    def count(self) -> int:
        return self.collection.count()

    def list_all(self, limit: int = 100, offset: int = 0) -> dict[str, Any]:
        """List all documents in the collection with pagination."""
        total = self.collection.count()
        if total == 0:
            return {"total": 0, "items": []}
        result = self.collection.get(
            limit=min(limit, total),
            offset=offset,
            include=["documents", "metadatas"],
        )
        items = []
        ids = result.get("ids", [])
        docs = result.get("documents", [])
        metas = result.get("metadatas", [])
        for i, doc_id in enumerate(ids):
            items.append({
                "id": doc_id,
                "document": docs[i][:200] if i < len(docs) and docs[i] else "",
                "metadata": metas[i] if i < len(metas) and metas[i] else {},
            })
        return {"total": total, "items": items}

    def delete_by_ids(self, ids: list[str]) -> int:
        """Delete documents by their IDs. Returns count deleted."""
        if not ids:
            return 0
        self.collection.delete(ids=ids)
        logger.info("Deleted %d documents from vector store", len(ids))
        return len(ids)

    def delete_collection(self):
        self.client.delete_collection(self.collection_name)
        self._collection = None
