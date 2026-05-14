from __future__ import annotations

import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from src.api.routes import router

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(
    title="FinReg RAG — 银行制度文档智能问答与审查系统",
    description="基于 RAG 的银行制度文档智能问答、文档审查与代码生成平台",
    version="2.0.0",
)

app.include_router(router)

DASHBOARD_PATH = Path(__file__).parent / "dashboard.html"


@app.get("/", response_class=HTMLResponse)
async def dashboard():
    if DASHBOARD_PATH.exists():
        return DASHBOARD_PATH.read_text(encoding="utf-8")
    return "<h1>Dashboard not found</h1>"


@app.get("/health")
async def health_check():
    from src.api.routes import _retriever
    return {
        "status": "ok",
        "service": "finreg-rag",
        "vector_store_count": _retriever.vector_store.count(),
    }


def main():
    import uvicorn
    from src.config import settings

    uvicorn.run(
        "src.app:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True,
    )


if __name__ == "__main__":
    main()
