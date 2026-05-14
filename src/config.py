from __future__ import annotations

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    openai_api_key: str = ""
    openai_base_url: str = "https://api.deepseek.com"
    llm_model: str = "deepseek-v4-flash"
    llm_temperature: float = 0.1
    llm_max_tokens: int = 4096

    embedding_model: str = "all-MiniLM-L6-v2"
    hf_endpoint: str = "https://hf-mirror.com"
    chroma_persist_dir: str = "./chroma_data"
    chunk_size: int = 1000
    chunk_overlap: int = 200
    retrieval_top_k: int = 5

    crawler_max_pages: int = 50
    crawler_timeout: int = 30

    validator_sandbox_timeout: int = 10

    api_host: str = "0.0.0.0"
    api_port: int = 8000

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
