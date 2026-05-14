from __future__ import annotations

import logging
import re
import subprocess
import tempfile
from dataclasses import dataclass, field

from src.config import settings

logger = logging.getLogger(__name__)


@dataclass
class SandboxResult:
    success: bool
    output: str = ""
    error: str = ""
    exit_code: int = -1
    execution_time_ms: float = 0.0


class CodeSandbox:
    def __init__(self, timeout: int | None = None):
        self.timeout = timeout or settings.validator_sandbox_timeout

    def execute_python(
        self,
        code: str,
        input_data: str = "",
    ) -> SandboxResult:
        import time

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False, encoding="utf-8"
        ) as f:
            f.write(code)
            tmp_path = f.name

        try:
            start = time.perf_counter()
            proc = subprocess.run(
                ["python", tmp_path],
                capture_output=True,
                text=True,
                timeout=self.timeout,
                input=input_data,
            )
            elapsed = (time.perf_counter() - start) * 1000

            return SandboxResult(
                success=proc.returncode == 0,
                output=proc.stdout.strip(),
                error=proc.stderr.strip(),
                exit_code=proc.returncode,
                execution_time_ms=round(elapsed, 2),
            )
        except subprocess.TimeoutExpired:
            return SandboxResult(
                success=False,
                error=f"Execution timed out after {self.timeout}s",
                exit_code=-1,
            )
        except Exception as e:
            return SandboxResult(
                success=False,
                error=str(e),
                exit_code=-1,
            )
        finally:
            import os
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

    def execute_sql(
        self,
        sql: str,
        db_url: str = "sqlite:///:memory:",
        table_schema: str = "",
    ) -> SandboxResult:
        import time

        ddl_statements: list[str] = []

        try:
            from sqlalchemy import create_engine, text

            engine = create_engine(db_url)
            start = time.perf_counter()

            ddl_statements = self._extract_ddl(table_schema)

            with engine.connect() as conn:
                for ddl in ddl_statements:
                    try:
                        conn.execute(text(ddl))
                    except Exception as e:
                        pass
                if ddl_statements:
                    conn.commit()

                result = conn.execute(text(sql))
                if sql.strip().upper().startswith("SELECT"):
                    rows = result.fetchall()
                    output = f"Rows: {len(rows)}\n"
                    if rows:
                        output += str(rows[:10])
                else:
                    conn.commit()
                    output = f"Affected rows: {result.rowcount}"

            elapsed = (time.perf_counter() - start) * 1000
            return SandboxResult(
                success=True,
                output=output,
                execution_time_ms=round(elapsed, 2),
            )
        except Exception as e:
            err_msg = str(e)
            # Strip SQLAlchemy help URLs
            if "(Background on this error" in err_msg:
                err_msg = err_msg.split("(Background on this error")[0].strip()
            if not ddl_statements and "no such table" in err_msg:
                err_msg = (
                    "当前为通用模式，未选择银行场景，内存库中没有业务表。"
                    "请在 Dashboard 中选择一个银行场景（如「风险监控」），系统会自动建表后再执行。"
                    "\n或者使用不依赖表的 SQL（如 SELECT 1+1）。"
                )
            return SandboxResult(
                success=False,
                error=err_msg,
                exit_code=-1,
            )

    @staticmethod
    def _extract_ddl(table_schema: str) -> list[str]:
        if not table_schema or not table_schema.strip():
            return []
        statements = []
        cleaned = re.sub(r"--[^\n]*", "", table_schema)
        for part in re.split(r";\s*\n?", cleaned.strip()):
            part = part.strip()
            if not part:
                continue
            upper = part.upper()
            if any(upper.lstrip().startswith(kw) or kw in upper[:60] for kw in ("CREATE TABLE", "CREATE INDEX", "INSERT ", "CREATE VIEW")):
                statements.append(part + ";")
        return statements
