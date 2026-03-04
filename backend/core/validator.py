"""
Validator — two-stage SQL validation.
Stage A: Syntax check via sqlglot parser.
Stage B: Security enforcement (allowlist/blocklist at AST level).
"""
import re
from typing import Optional

import sqlglot
import sqlglot.expressions as exp

from backend.models.schemas import ValidationResult

# ─── Security blocklist (keyword-level check as first line of defense)
BLOCKED_KEYWORDS = re.compile(
    r"\b(DROP|DELETE|UPDATE|ALTER|INSERT|TRUNCATE|CREATE|REPLACE|EXEC|EXECUTE|GRANT|REVOKE|COPY|LOAD)\b",
    re.IGNORECASE,
)

# Block multi-statement execution (semicolons inside the query)
MULTI_STATEMENT = re.compile(r";\s*\S")


class SQLValidator:
    """
    Validates a SQL string for both correctness and security.
    Returns a ValidationResult with passed=True/False and an error message.
    """

    def validate(self, sql: str) -> ValidationResult:
        sql = sql.strip()

        # ── Stage 0: Non-empty ───────────────────────────────
        if not sql:
            return ValidationResult(passed=False, error="SQL query is empty.")

        # ── Stage 1: Keyword blocklist ───────────────────────
        match = BLOCKED_KEYWORDS.search(sql)
        if match:
            return ValidationResult(
                passed=False,
                error=f"Forbidden keyword detected: '{match.group()}'. Only SELECT statements are allowed."
            )

        # ── Stage 2: Multi-statement guard ───────────────────
        if MULTI_STATEMENT.search(sql):
            return ValidationResult(
                passed=False,
                error="Multi-statement queries are not allowed. Use a single SELECT statement."
            )

        # ── Stage 3: sqlglot syntax parse ────────────────────
        try:
            parsed = sqlglot.parse(sql, error_level=sqlglot.ErrorLevel.RAISE)
        except sqlglot.errors.ParseError as e:
            return ValidationResult(
                passed=False,
                error=f"SQL syntax error: {str(e)}"
            )

        if not parsed:
            return ValidationResult(
                passed=False,
                error="SQL could not be parsed (empty AST)."
            )

        # ── Stage 4: AST-level SELECT enforcement ────────────
        for statement in parsed:
            if not isinstance(statement, exp.Select):
                stmt_type = type(statement).__name__
                return ValidationResult(
                    passed=False,
                    error=f"Only SELECT statements are allowed. Got: {stmt_type}."
                )

        return ValidationResult(passed=True)

    def sanitize_limit(self, sql: str, max_rows: int) -> str:
        """
        Injects or replaces the LIMIT clause to enforce max_rows.
        Uses sqlglot to safely rewrite the AST.
        """
        try:
            statements = sqlglot.parse(sql)
            if not statements:
                return sql
            stmt = statements[0]
            # Remove existing LIMIT if it exceeds max_rows
            existing_limit = stmt.find(exp.Limit)
            if existing_limit:
                limit_val = existing_limit.find(exp.Literal)
                if limit_val and int(limit_val.this) <= max_rows:
                    return sql   # existing limit is fine
            # Set / override LIMIT
            stmt = stmt.limit(max_rows)
            return stmt.sql(dialect="postgres")
        except Exception:
            # Fallback: string-level injection
            return f"SELECT * FROM ({sql}) _nl2sql_wrapper LIMIT {max_rows}"


# Module-level singleton
sql_validator = SQLValidator()
