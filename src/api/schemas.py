from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class SQLGenerateRequest(BaseModel):
    requirement: str = Field(..., description="The SQL query requirement in natural language")
    table_schema: str = Field(default="", description="DDL or description of table schemas")
    use_rag: bool = Field(default=True, description="Whether to use RAG retrieval for context")


class SQLCompleteRequest(BaseModel):
    partial_sql: str = Field(..., description="Partial or incomplete SQL query")
    requirement: str = Field(default="", description="The completion requirement")
    table_schema: str = Field(default="", description="DDL or description of table schemas")
    use_rag: bool = Field(default=True)


class PythonGenerateRequest(BaseModel):
    requirement: str = Field(..., description="The Python code requirement in natural language")
    additional_context: str = Field(default="", description="Additional context or constraints")
    use_rag: bool = Field(default=True)


class PythonCompleteRequest(BaseModel):
    partial_code: str = Field(..., description="Partial or incomplete Python code")
    requirement: str = Field(default="", description="The completion requirement")
    use_rag: bool = Field(default=True)


class CodeValidateRequest(BaseModel):
    code: str = Field(..., description="The code to validate")
    language: str = Field(..., description="The language: 'sql' or 'python'")


class CodeExecuteRequest(BaseModel):
    code: str = Field(..., description="The code to execute")
    language: str = Field(..., description="The language: 'sql' or 'python'")
    db_url: str = Field(default="sqlite:///:memory:", description="Database URL for SQL execution")
    table_schema: str = Field(default="", description="Table DDL schema to create before executing SQL")


class DocumentIndexRequest(BaseModel):
    documents: list[dict[str, Any]] = Field(..., description="List of documents to index")


class SearchRequest(BaseModel):
    query: str = Field(..., description="Search query")
    top_k: int = Field(default=5, description="Number of results to return")
    filter_type: str | None = Field(default=None, description="Filter by source_type")


class CrawlRequest(BaseModel):
    url: str = Field(..., description="Starting URL to crawl")
    max_pages: int = Field(default=50, description="Maximum pages to crawl")
    crawler_type: str = Field(default="doc", description="Crawler type: 'doc' or 'code'")
    collection: str = Field(default="", description="Target collection: 'regulatory_docs' or 'code_docs'")


class PipelineAskRequest(BaseModel):
    requirement: str = Field(..., description="The code requirement in natural language")
    language: str = Field(..., description="'sql' or 'python'")
    table_schema: str = Field(default="", description="Table schema (for SQL) or additional context (for Python)")


class BenchmarkRequest(BaseModel):
    use_mock_llm: bool = Field(default=True, description="Whether to use mock LLM for benchmark")


class GenerationResult(BaseModel):
    code: str = ""
    sql: str = ""
    raw_response: str = ""
    model: str = ""
    usage: dict[str, int] = Field(default_factory=dict)
    generation_time_ms: float = 0.0
    context_used: bool = False


class ValidationResult(BaseModel):
    is_valid: bool
    is_safe: bool
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class SandboxExecutionResult(BaseModel):
    success: bool
    output: str = ""
    error: str = ""
    exit_code: int = -1
    execution_time_ms: float = 0.0


class MetricsSummary(BaseModel):
    sql: dict[str, Any] = Field(default_factory=dict)
    python: dict[str, Any] = Field(default_factory=dict)
    retrieval: dict[str, Any] = Field(default_factory=dict)
    total_tokens_used: int = 0


class BenchmarkSummary(BaseModel):
    total_cases: int = 0
    overall_pass_rate: float = 0.0
    sql: dict[str, Any] = Field(default_factory=dict)
    python: dict[str, Any] = Field(default_factory=dict)
    retrieval: dict[str, Any] = Field(default_factory=dict)
    benchmark_results: list[dict[str, Any]] = Field(default_factory=list)
    total_tokens_used: int = 0


class DocQARequest(BaseModel):
    question: str = Field(..., description="用户关于制度文档的问题")


class DocReviewRequest(BaseModel):
    title: str = Field(..., description="待审查文档标题")
    content: str = Field(..., description="待审查文档完整内容")


class DocClassifyRequest(BaseModel):
    title: str = Field(default="", description="文档标题")
    content: str = Field(..., description="待分类的文档内容")
