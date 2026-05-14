from __future__ import annotations

import logging
import time
from typing import Any

from src.llm.providers import BaseLLMProvider, get_llm_provider
from src.llm.prompts import (
    PYTHON_COMPLETION_SYSTEM,
    PYTHON_COMPLETION_USER,
    PYTHON_GENERATION_SYSTEM,
    PYTHON_GENERATION_USER,
)
from src.rag.retriever import Retriever

logger = logging.getLogger(__name__)


class PythonGenerator:
    def __init__(
        self,
        provider: BaseLLMProvider | None = None,
        retriever: Retriever | None = None,
    ):
        self.provider = provider or get_llm_provider()
        self.retriever = retriever or Retriever()

    async def generate(
        self,
        requirement: str,
        additional_context: str = "",
        use_rag: bool = True,
    ) -> dict[str, Any]:
        start_time = time.perf_counter()
        context = ""
        if use_rag:
            query = f"Python code: {requirement} {additional_context}"
            context = self.retriever.retrieve_context(query)

        system_msg = PYTHON_GENERATION_SYSTEM.format(context=context or "No additional context available.")
        user_msg = PYTHON_GENERATION_USER.format(
            requirement=requirement,
            additional_context=additional_context or "",
        )

        response = await self.provider.generate([
            {"role": "system", "content": system_msg},
            {"role": "user", "content": user_msg},
        ])

        elapsed = time.perf_counter() - start_time
        code = self._extract_code(response.content)
        return {
            "code": code,
            "raw_response": response.content,
            "model": response.model,
            "usage": response.usage,
            "generation_time_ms": round(elapsed * 1000, 2),
            "context_used": bool(context),
        }

    async def complete(
        self,
        partial_code: str,
        requirement: str = "",
        use_rag: bool = True,
    ) -> dict[str, Any]:
        start_time = time.perf_counter()
        context = ""
        if use_rag:
            query = f"Python completion: {requirement} {partial_code[:200]}"
            context = self.retriever.retrieve_context(query)

        system_msg = PYTHON_COMPLETION_SYSTEM.format(context=context or "No additional context available.")
        user_msg = PYTHON_COMPLETION_USER.format(
            partial_code=partial_code,
            requirement=requirement or "Complete this Python code correctly.",
        )

        response = await self.provider.generate([
            {"role": "system", "content": system_msg},
            {"role": "user", "content": user_msg},
        ])

        elapsed = time.perf_counter() - start_time
        code = self._extract_code(response.content)
        return {
            "code": code,
            "raw_response": response.content,
            "model": response.model,
            "usage": response.usage,
            "generation_time_ms": round(elapsed * 1000, 2),
            "context_used": bool(context),
        }

    @staticmethod
    def _extract_code(content: str) -> str:
        import re
        match = re.search(r"```python\s*(.*?)\s*```", content, re.DOTALL)
        if match:
            return match.group(1).strip()
        match = re.search(r"```\s*(.*?)\s*```", content, re.DOTALL)
        if match:
            return match.group(1).strip()
        return content.strip()
