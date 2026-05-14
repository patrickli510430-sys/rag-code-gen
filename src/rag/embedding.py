from __future__ import annotations

import logging
import os


def _set_hf_mirror():
    mirror = os.environ.get("HF_ENDPOINT", "https://hf-mirror.com")
    os.environ["HF_ENDPOINT"] = mirror
    os.environ["HF_MIRROR"] = mirror
    os.environ["HUGGINGFACE_HUB_ENDPOINT"] = mirror
    try:
        import huggingface_hub
        huggingface_hub.configure_hf_hub(mirror)
    except Exception:
        pass
    try:
        import huggingface_hub.constants as hfc
        hfc.ENDPOINT = mirror
        hfc.HF_HUB_ENDPOINT = mirror
    except Exception:
        pass


_set_hf_mirror()

from functools import lru_cache
from typing import Any

from sentence_transformers import SentenceTransformer

from src.config import settings

logger = logging.getLogger(__name__)


class EmbeddingGenerator:
    def __init__(self, model_name: str | None = None):
        self.model_name = model_name or settings.embedding_model
        self._model: SentenceTransformer | None = None
        self._error: str | None = None

    @property
    def model(self) -> SentenceTransformer | None:
        if self._model is not None:
            return self._model
        if self._error:
            return None
        try:
            self._load_model()
        except Exception as e:
            self._error = str(e)
            logger.error("Embedding model load failed: %s", e)
            return None
        return self._model

    @property
    def is_ready(self) -> bool:
        return self._model is not None

    def _load_model(self):
        mirror = settings.hf_endpoint
        os.environ["HF_ENDPOINT"] = mirror
        logger.info("Loading embedding model %s from HF mirror %s ...", self.model_name, mirror)

        # Try local files first, fall back to download
        try:
            self._model = SentenceTransformer(
                self.model_name,
                device="cpu",
                local_files_only=True,
            )
        except Exception:
            logger.info("Model not found locally, downloading from %s ...", mirror)
            self._model = SentenceTransformer(
                self.model_name,
                device="cpu",
                local_files_only=False,
            )

        logger.info("Embedding model loaded (dim=%d)", self._model.get_embedding_dimension())

    def embed(self, texts: list[str]) -> list[list[float]]:
        if self.model is None:
            raise RuntimeError(f"Embedding model not available: {self._error}")
        embeddings = self.model.encode(texts, convert_to_numpy=True)
        return embeddings.tolist()

    def embed_single(self, text: str) -> list[float]:
        return self.embed([text])[0]

    @property
    def dimension(self) -> int:
        if self._model is not None:
            return self._model.get_embedding_dimension()
        return 384


@lru_cache
def get_embedding_generator() -> EmbeddingGenerator:
    return EmbeddingGenerator()
