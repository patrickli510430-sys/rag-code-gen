from __future__ import annotations

import logging
import time
from typing import Any

from src.llm.providers import BaseLLMProvider, get_llm_provider
from src.llm.prompts import (
    SQL_COMPLETION_SYSTEM,
    SQL_COMPLETION_USER,
    SQL_GENERATION_SYSTEM,
    SQL_GENERATION_USER,
)
from src.rag.retriever import Retriever

logger = logging.getLogger(__name__)


class SQLGenerator:
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
        table_schema: str = "",
        use_rag: bool = True,
    ) -> dict[str, Any]:
        start_time = time.perf_counter()
        context = ""
        if use_rag:
            query = f"SQL query: {requirement} {table_schema[:200]}"
            context = self.retriever.retrieve_context(query)

        compact_schema = self._compact_ddl(table_schema) if table_schema else "No schema provided."

        system_msg = SQL_GENERATION_SYSTEM.format(context=context or "No additional context available.")
        user_msg = SQL_GENERATION_USER.format(
            requirement=requirement,
            table_schema=compact_schema,
        )

        response = await self.provider.generate([
            {"role": "system", "content": system_msg},
            {"role": "user", "content": user_msg},
        ])

        elapsed = time.perf_counter() - start_time

        sql = self._extract_sql(response.content)

        if response.finish_reason == "length":
            sql = await self._regenerate_truncated(requirement, table_schema, response.content, use_rag)

        return {
            "sql": sql,
            "raw_response": response.content,
            "model": response.model,
            "usage": response.usage,
            "generation_time_ms": round(elapsed * 1000, 2),
            "context_used": bool(context),
        }

    async def complete(
        self,
        partial_sql: str,
        requirement: str = "",
        table_schema: str = "",
        use_rag: bool = True,
    ) -> dict[str, Any]:
        start_time = time.perf_counter()
        context = ""
        if use_rag:
            query = f"SQL completion: {requirement} {partial_sql[:200]}"
            context = self.retriever.retrieve_context(query)

        compact_schema = self._compact_ddl(table_schema) if table_schema else "No schema provided."

        system_msg = SQL_COMPLETION_SYSTEM.format(context=context or "No additional context available.")
        user_msg = SQL_COMPLETION_USER.format(
            partial_sql=partial_sql,
            requirement=requirement or "Complete this SQL query correctly.",
            table_schema=compact_schema,
        )

        response = await self.provider.generate([
            {"role": "system", "content": system_msg},
            {"role": "user", "content": user_msg},
        ])

        elapsed = time.perf_counter() - start_time
        sql = self._extract_sql(response.content)
        return {
            "sql": sql,
            "raw_response": response.content,
            "model": response.model,
            "usage": response.usage,
            "generation_time_ms": round(elapsed * 1000, 2),
            "context_used": bool(context),
        }

    @staticmethod
    def _compact_ddl(ddl: str) -> str:
        import re
        if not ddl or not ddl.strip():
            return "No schema provided."
        cleaned = re.sub(r"--[^\n]*", "", ddl)
        cleaned = re.sub(r"\n\s{2,}", "\n", cleaned)
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
        result = "\n".join(line for line in cleaned.split("\n") if line.strip())
        if len(result) > 2500:
            result = result[:2500] + "\n-- (truncated)"
        return "Table Schema:\n" + result

    async def _regenerate_truncated(self, requirement: str, table_schema: str, previous: str, use_rag: bool) -> str:
        logger.warning("LLM output was truncated (max_tokens), retrying with higher limit...")
        from src.config import settings
        try:
            response = await self.provider.generate(
                [
                    {"role": "system", "content": "You are an expert SQL developer. Return ONLY the complete SQL query, no explanations."},
                    {"role": "user", "content": f"Requirement: {requirement}\n\nThe previous response was cut off. Generate ONLY the SQL, keep it concise:\n{self._compact_ddl(table_schema) if table_schema else ''}"},
                ],
                max_tokens=settings.llm_max_tokens,
            )
            sql = self._extract_sql(response.content)
            if sql and len(sql) > 20:
                return sql
        except Exception:
            pass
        return previous.strip()

    @staticmethod
    def _extract_sql(content: str) -> str:
        import re
        content = content.strip()
        if not content:
            return ""

        match = re.search(r"```sql\s*(.*?)\s*```", content, re.DOTALL | re.IGNORECASE)
        if match:
            return match.group(1).strip()

        match = re.search(r"```(?:sql)?\s*(\n?\s*(?:SELECT|WITH|INSERT|UPDATE|DELETE|CREATE)\b.*?)\s*```", content, re.DOTALL | re.IGNORECASE)
        if match:
            return match.group(1).strip()

        select_start = re.search(r"\b(SELECT\b.*?)(?:;|$)", content, re.DOTALL | re.IGNORECASE)
        if select_start:
            sql = select_start.group(1).strip()
            if len(sql) > 10:
                if not sql.endswith(";"):
                    sql += ";"
                return sql

        if content.upper().startswith(("SELECT", "WITH", "INSERT", "UPDATE", "DELETE", "CREATE")):
            return content

        return content
