import pytest
from src.llm.providers import MockProvider, OpenAIProvider, LLMResponse


class TestMockProvider:
    async def test_generate(self):
        provider = MockProvider()
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Write a SELECT query for all users."},
        ]
        response = await provider.generate(messages)
        assert isinstance(response, LLMResponse)
        assert response.content
        assert response.model == "mock-model"
        assert "total_tokens" in response.usage

    async def test_generate_with_json(self):
        provider = MockProvider()
        messages = [{"role": "user", "content": "Evaluate this code."}]
        result = await provider.generate_with_json(messages)
        assert isinstance(result, dict)
        assert result.get("mock") is True


class TestSQLGenerator:
    async def test_generate_with_mock(self):
        from src.llm.sql_generator import SQLGenerator
        from src.llm.providers import MockProvider

        generator = SQLGenerator(provider=MockProvider())
        result = await generator.generate(
            requirement="Get all active users",
            table_schema="users(id INT, name VARCHAR, active BOOLEAN)",
            use_rag=False,
        )
        assert "sql" in result
        assert "model" in result
        assert "generation_time_ms" in result
        assert not result["context_used"]

    async def test_complete_with_mock(self):
        from src.llm.sql_generator import SQLGenerator
        from src.llm.providers import MockProvider

        generator = SQLGenerator(provider=MockProvider())
        result = await generator.complete(
            partial_sql="SELECT * FROM users WHERE",
            requirement="Add condition for active users",
            use_rag=False,
        )
        assert "sql" in result
        assert "generation_time_ms" in result


class TestPythonGenerator:
    async def test_generate_with_mock(self):
        from src.llm.python_generator import PythonGenerator
        from src.llm.providers import MockProvider

        generator = PythonGenerator(provider=MockProvider())
        result = await generator.generate(
            requirement="Write a function to calculate factorial",
            use_rag=False,
        )
        assert "code" in result
        assert "model" in result
        assert "generation_time_ms" in result

    async def test_complete_with_mock(self):
        from src.llm.python_generator import PythonGenerator
        from src.llm.providers import MockProvider

        generator = PythonGenerator(provider=MockProvider())
        result = await generator.complete(
            partial_code="def factorial(n):\n    if n <= 1:\n        ",
            requirement="Complete the factorial function",
            use_rag=False,
        )
        assert "code" in result


class TestExtractCode:
    def test_extract_sql_from_markdown(self):
        from src.llm.sql_generator import SQLGenerator
        gen = SQLGenerator.__new__(SQLGenerator)
        content = "```sql\nSELECT * FROM users\n```"
        assert gen._extract_sql(content) == "SELECT * FROM users"

    def test_extract_sql_plain(self):
        from src.llm.sql_generator import SQLGenerator
        gen = SQLGenerator.__new__(SQLGenerator)
        content = "SELECT * FROM users WHERE active = true"
        result = gen._extract_sql(content)
        assert "SELECT * FROM users" in result
        assert "active" in result

    def test_extract_python_from_markdown(self):
        from src.llm.python_generator import PythonGenerator
        gen = PythonGenerator.__new__(PythonGenerator)
        content = "```python\ndef hello():\n    return 'world'\n```"
        assert gen._extract_code(content) == "def hello():\n    return 'world'"
