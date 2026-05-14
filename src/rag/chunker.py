from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from src.config import settings


@dataclass
class Chunk:
    text: str
    metadata: dict[str, Any]
    chunk_index: int


class DocumentChunker:
    def __init__(
        self,
        chunk_size: int | None = None,
        chunk_overlap: int | None = None,
    ):
        self.chunk_size = chunk_size or settings.chunk_size
        self.chunk_overlap = chunk_overlap or settings.chunk_overlap

    def chunk_text(self, text: str, metadata: dict[str, Any] | None = None) -> list[Chunk]:
        if metadata is None:
            metadata = {}

        text = self._normalize(text)
        chunks: list[Chunk] = []

        if self._is_code(metadata.get("language", "")):
            chunks = self._chunk_code(text, metadata)
        else:
            chunks = self._chunk_by_sentences(text, metadata)

        return chunks

    def _chunk_by_sentences(self, text: str, metadata: dict[str, Any]) -> list[Chunk]:
        sentences = re.split(r"(?<=[。！？.!?\n])\s*", text)
        chunks: list[Chunk] = []
        current = ""
        chunk_index = 0

        for sentence in sentences:
            if len(current) + len(sentence) > self.chunk_size and current:
                chunks.append(Chunk(text=current.strip(), metadata={**metadata, "chunk_index": chunk_index}, chunk_index=chunk_index))
                chunk_index += 1
                current = sentence[-self.chunk_overlap:] + sentence if self.chunk_overlap else sentence
            else:
                current += sentence

        if current.strip():
            chunks.append(Chunk(text=current.strip(), metadata={**metadata, "chunk_index": chunk_index}, chunk_index=chunk_index))

        return chunks

    def _chunk_code(self, text: str, metadata: dict[str, Any]) -> list[Chunk]:
        lines = text.split("\n")
        chunks: list[Chunk] = []
        current = ""
        chunk_index = 0

        for line in lines:
            if len(current) + len(line) > self.chunk_size and current:
                chunks.append(Chunk(text=current.strip(), metadata={**metadata, "chunk_index": chunk_index}, chunk_index=chunk_index))
                chunk_index += 1
                current = line + "\n"
            else:
                current += line + "\n"

        if current.strip():
            chunks.append(Chunk(text=current.strip(), metadata={**metadata, "chunk_index": chunk_index}, chunk_index=chunk_index))

        return chunks

    @staticmethod
    def _is_code(language: str) -> bool:
        return language in ("python", "sql", "javascript", "typescript", "java", "go")

    @staticmethod
    def _normalize(text: str) -> str:
        text = re.sub(r"\r\n", "\n", text)
        text = re.sub(r"\n{4,}", "\n\n\n", text)
        return text
