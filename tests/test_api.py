import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
from src.app import app


@pytest.fixture
def client():
    return TestClient(app)


class TestHealthEndpoint:
    def test_health_check(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"


class TestValidationEndpoint:
    def test_validate_sql_valid(self, client):
        response = client.post("/api/v1/validate", json={
            "code": "SELECT * FROM users",
            "language": "sql",
        })
        assert response.status_code == 200
        data = response.json()
        assert data["is_valid"]
        assert data["is_safe"]

    def test_validate_sql_dangerous(self, client):
        response = client.post("/api/v1/validate", json={
            "code": "DROP TABLE users",
            "language": "sql",
        })
        assert response.status_code == 200
        data = response.json()
        assert not data["is_safe"]

    def test_validate_python_valid(self, client):
        response = client.post("/api/v1/validate", json={
            "code": "def hello():\n    return 'world'",
            "language": "python",
        })
        assert response.status_code == 200
        data = response.json()
        assert data["is_valid"]

    def test_validate_unknown_language(self, client):
        response = client.post("/api/v1/validate", json={
            "code": "hello world",
            "language": "ruby",
        })
        assert response.status_code == 400


class TestSearchEndpoint:
    def test_search(self, client):
        response = client.post("/api/v1/search", json={
            "query": "SQL SELECT",
            "top_k": 3,
        })
        assert response.status_code == 200
        data = response.json()
        assert "query" in data
        assert "results" in data


class TestDocumentIndexEndpoint:
    def test_index_documents(self, client):
        docs = [
            {"content": "SELECT is a SQL keyword for querying data", "url": "http://example.com/1"},
            {"content": "Python is a programming language", "url": "http://example.com/2"},
        ]
        response = client.post("/api/v1/documents/index", json={"documents": docs})
        assert response.status_code == 200
        data = response.json()
        assert "indexed_count" in data
        assert data["indexed_count"] > 0


class TestMetricsEndpoint:
    def test_get_metrics(self, client):
        response = client.get("/api/v1/metrics")
        assert response.status_code == 200
        data = response.json()
        assert "sql" in data
        assert "python" in data


class TestBenchmarkEndpoint:
    def test_run_benchmark(self, client):
        response = client.post("/api/v1/benchmark", json={"use_mock_llm": True})
        assert response.status_code == 200
        data = response.json()
        assert "total_cases" in data
        assert "benchmark_results" in data
