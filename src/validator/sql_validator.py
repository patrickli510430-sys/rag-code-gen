from __future__ import annotations

import logging
import re as re_mod
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

FORBIDDEN_SQL_KEYWORDS = [
    "DROP", "TRUNCATE", "ALTER TABLE", "ALTER DATABASE",
    "GRANT", "REVOKE", "EXEC", "EXECUTE", "EXECUTE IMMEDIATE",
    "SHUTDOWN", "KILL",
]

FORBIDDEN_SQL_PATTERNS = [
    r"DROP\s+(TABLE|DATABASE|INDEX|SCHEMA|VIEW|FUNCTION|PROCEDURE|TRIGGER)",
    r"TRUNCATE\s+(TABLE\s+)?\w+",
    r"ALTER\s+(TABLE|DATABASE)\s+\w+\s+DROP",
    r"EXEC\s*\(.*\)",
    r"INTO\s+OUTFILE",
    r"INTO\s+DUMPFILE",
    r"LOAD_FILE\s*\(",
    r"LOAD\s+DATA\s+INFILE",
    r"BENCHMARK\s*\(",
    r"SLEEP\s*\(",
]


@dataclass
class SQLValidationResult:
    is_valid: bool
    is_safe: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    parsed_tokens: list[str] = field(default_factory=list)
    statement_type: str = ""


class SQLValidator:
    def validate(self, sql: str) -> SQLValidationResult:
        errors: list[str] = []
        warnings: list[str] = []

        if not sql or not sql.strip():
            errors.append("Empty SQL statement")
            return SQLValidationResult(is_valid=False, is_safe=True, errors=errors, warnings=warnings)

        syntax_errors = self._check_sqlite_syntax(sql)
        if syntax_errors:
            errors.extend(syntax_errors)

        is_safe = self._check_safety(sql, errors)

        stmt_type = self._detect_statement_type(sql)

        return SQLValidationResult(
            is_valid=len(errors) == 0,
            is_safe=is_safe,
            errors=errors,
            warnings=warnings,
            statement_type=stmt_type,
        )

    def _check_sqlite_syntax(self, sql: str) -> list[str]:
        import sqlite3
        try:
            conn = sqlite3.connect(":memory:")
            conn.execute("EXPLAIN " + sql)
            conn.close()
        except sqlite3.OperationalError as e:
            msg = str(e)
            if "no such table" in msg or "no such column" in msg:
                return []
            return [f"SQL syntax error: {e}"]
        except Exception:
            pass
        return []

    def _check_safety(self, sql: str, errors: list[str]) -> bool:
        sql_upper = sql.upper()

        for keyword in FORBIDDEN_SQL_KEYWORDS:
            if re_mod.search(rf"\b{keyword}\b", sql_upper):
                errors.append(f"Security: forbidden keyword '{keyword}' detected")
                return False

        for pattern in FORBIDDEN_SQL_PATTERNS:
            if re_mod.search(pattern, sql_upper):
                errors.append(f"Security: dangerous pattern detected matching '{pattern[:40]}...'")
                return False

        return True

    @staticmethod
    def _detect_statement_type(sql: str) -> str:
        sql_upper = sql.strip().upper()
        if sql_upper.startswith("SELECT") or sql_upper.startswith("WITH"):
            return "SELECT"
        if sql_upper.startswith("INSERT"):
            return "INSERT"
        if sql_upper.startswith("UPDATE"):
            return "UPDATE"
        if sql_upper.startswith("DELETE"):
            return "DELETE"
        if sql_upper.startswith("CREATE"):
            return "CREATE"
        return "OTHER"
