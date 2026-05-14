import pytest
from src.validator.sql_validator import SQLValidator, SQLValidationResult
from src.validator.python_validator import PythonValidator, PythonValidationResult
from src.validator.sandbox import CodeSandbox, SandboxResult


class TestSQLValidator:
    def test_valid_select(self):
        validator = SQLValidator()
        result = validator.validate("SELECT * FROM users WHERE id = 1")
        assert result.is_valid
        assert result.is_safe
        assert result.statement_type == "SELECT"

    def test_valid_with_cte(self):
        validator = SQLValidator()
        result = validator.validate("WITH active AS (SELECT * FROM users) SELECT * FROM active")
        assert result.is_valid
        assert result.statement_type == "SELECT"

    def test_dangerous_drop(self):
        validator = SQLValidator()
        result = validator.validate("DROP TABLE users")
        assert not result.is_safe

    def test_dangerous_truncate(self):
        validator = SQLValidator()
        result = validator.validate("TRUNCATE TABLE users")
        assert not result.is_safe

    def test_dangerous_exec(self):
        validator = SQLValidator()
        result = validator.validate("EXEC('DROP TABLE users')")
        assert not result.is_safe

    def test_empty_sql(self):
        validator = SQLValidator()
        result = validator.validate("")
        assert not result.is_valid

    def test_simple_insert(self):
        validator = SQLValidator()
        result = validator.validate("INSERT INTO users (name) VALUES ('test')")
        assert result.is_valid
        assert result.statement_type == "INSERT"


class TestPythonValidator:
    def test_valid_code(self):
        validator = PythonValidator()
        result = validator.validate("def hello():\n    return 'world'")
        assert result.is_valid
        assert result.is_safe

    def test_forbidden_import_os(self):
        validator = PythonValidator()
        result = validator.validate("import os\nos.system('ls')")
        assert not result.is_safe

    def test_forbidden_import_subprocess(self):
        validator = PythonValidator()
        result = validator.validate("import subprocess\nsubprocess.run(['ls'])")
        assert not result.is_safe

    def test_forbidden_eval(self):
        validator = PythonValidator()
        result = validator.validate("eval('1+1')")
        assert not result.is_safe

    def test_syntax_error(self):
        validator = PythonValidator()
        result = validator.validate("def broken(:")
        assert not result.is_valid

    def test_empty_code(self):
        validator = PythonValidator()
        result = validator.validate("")
        assert not result.is_valid

    def test_safe_math_import(self):
        validator = PythonValidator()
        result = validator.validate("import math\nprint(math.sqrt(4))")
        assert result.is_valid


class TestCodeSandbox:
    def test_execute_python_success(self):
        sandbox = CodeSandbox(timeout=5)
        code = "print('hello world')"
        result = sandbox.execute_python(code)
        assert result.success
        assert "hello world" in result.output

    def test_execute_python_function(self):
        sandbox = CodeSandbox(timeout=5)
        code = "def add(a, b):\n    return a + b\nprint(add(1, 2))"
        result = sandbox.execute_python(code)
        assert result.success
        assert "3" in result.output

    def test_execute_python_error(self):
        sandbox = CodeSandbox(timeout=5)
        code = "raise ValueError('test error')"
        result = sandbox.execute_python(code)
        assert not result.success
        assert "ValueError" in result.error

    def test_execute_sql_select(self):
        sandbox = CodeSandbox(timeout=5)
        sql = "SELECT 1 AS col1, 2 AS col2"
        result = sandbox.execute_sql(sql)
        assert result.success
        assert "Rows:" in result.output

    def test_execute_sql_error(self):
        sandbox = CodeSandbox(timeout=5)
        sql = "SELECT * FROM nonexistent_table"
        result = sandbox.execute_sql(sql)
        assert not result.success
