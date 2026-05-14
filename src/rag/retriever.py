from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from src.rag.chunker import DocumentChunker
from src.rag.embedding import EmbeddingGenerator
from src.rag.vector_store import VectorStore


@dataclass
class RetrievalResult:
    document: str
    metadata: dict[str, Any] = field(default_factory=dict)
    score: float = 0.0
    index: int = 0


class Retriever:
    def __init__(
        self,
        vector_store: VectorStore | None = None,
        embedding_generator: EmbeddingGenerator | None = None,
        chunker: DocumentChunker | None = None,
        collection_name: str = "code_docs",
    ):
        self.collection_name = collection_name
        self.vector_store = vector_store or VectorStore(collection_name=collection_name)
        self.embedding_generator = embedding_generator or EmbeddingGenerator()
        self.chunker = chunker or DocumentChunker()

    def index_documents(
        self,
        documents: list[dict[str, Any]],
    ) -> int:
        ids: list[str] = []
        texts: list[str] = []
        metadatas: list[dict[str, Any]] = []
        embeddings_list: list[list[float]] = []

        for doc in documents:
            chunks = self.chunker.chunk_text(doc["content"], doc.get("metadata", {}))
            for chunk in chunks:
                chunk_id = f"{doc.get('url', 'unknown')}#{chunk.chunk_index}"
                ids.append(chunk_id)
                texts.append(chunk.text)
                metadatas.append(chunk.metadata)
            embeddings_list.extend(self.embedding_generator.embed([c.text for c in chunks]))

        if ids:
            self.vector_store.add_documents(
                ids=ids,
                documents=texts,
                embeddings=embeddings_list,
                metadatas=metadatas,
            )
        return len(ids)

    def retrieve(
        self,
        query: str,
        top_k: int | None = None,
        filter_metadata: dict[str, Any] | None = None,
    ) -> list[RetrievalResult]:
        start = time.perf_counter()
        query_embedding = self.embedding_generator.embed_single(query)
        result = self.vector_store.query(
            query_embedding=query_embedding,
            top_k=top_k,
            filter_metadata=filter_metadata,
        )

        retrieval_results: list[RetrievalResult] = []
        if result.get("ids") and result["ids"][0]:
            for i, doc_id in enumerate(result["ids"][0]):
                retrieval_results.append(RetrievalResult(
                    document=result["documents"][0][i] if result.get("documents") else "",
                    metadata=result["metadatas"][0][i] if result.get("metadatas") else {},
                    score=1 - result["distances"][0][i] if result.get("distances") else 0.0,
                    index=i,
                ))

        elapsed = time.perf_counter() - start
        retrieval_results.sort(key=lambda x: x.score, reverse=True)

        return retrieval_results

    def retrieve_context(self, query: str, top_k: int | None = None) -> str:
        results = self.retrieve(query, top_k=top_k)
        parts = []
        for r in results:
            source = r.metadata.get("url", r.metadata.get("source_type", "unknown"))
            parts.append(f"// Source: {source}\n{r.document}")
        return "\n\n---\n\n".join(parts)
