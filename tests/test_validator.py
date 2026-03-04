"""
Tests for the SQL validator module.
"""
import pytest
from backend.core.validator import SQLValidator

validator = SQLValidator()


class TestBlocklist:
    def test_blocks_drop(self):
        r = validator.validate("DROP TABLE users")
        assert not r.passed
        assert "DROP" in r.error

    def test_blocks_delete(self):
        r = validator.validate("DELETE FROM orders WHERE id = 1")
        assert not r.passed
        assert "DELETE" in r.error

    def test_blocks_update(self):
        r = validator.validate("UPDATE products SET price = 10 WHERE id = 1")
        assert not r.passed

    def test_blocks_insert(self):
        r = validator.validate("INSERT INTO users (name) VALUES ('hacker')")
        assert not r.passed

    def test_blocks_alter(self):
        r = validator.validate("ALTER TABLE users ADD COLUMN evil TEXT")
        assert not r.passed

    def test_blocks_exec(self):
        r = validator.validate("EXEC xp_cmdshell 'dir'")
        assert not r.passed


class TestMultiStatement:
    def test_blocks_semicolon_split(self):
        # "SELECT 1; DROP TABLE users" is blocked — either by the keyword
        # blocklist (DROP) or the multi-statement regex depending on order.
        r = validator.validate("SELECT 1; DROP TABLE users")
        assert not r.passed

    def test_blocks_pure_multi_statement(self):
        # Two SELECT statements — only the semicolon guard catches this.
        r = validator.validate("SELECT 1; SELECT 2")
        assert not r.passed
        assert "Multi-statement" in r.error


class TestValidSelect:
    def test_simple_select(self):
        r = validator.validate("SELECT * FROM users")
        assert r.passed

    def test_select_with_join(self):
        r = validator.validate(
            "SELECT u.name, o.amount FROM users u JOIN orders o ON u.id = o.user_id"
        )
        assert r.passed

    def test_select_with_aggregation(self):
        r = validator.validate(
            "SELECT region, COUNT(*) FROM orders GROUP BY region ORDER BY 2 DESC"
        )
        assert r.passed

    def test_empty_query(self):
        r = validator.validate("")
        assert not r.passed

    def test_select_with_subquery(self):
        r = validator.validate(
            "SELECT name FROM products WHERE price > (SELECT AVG(price) FROM products)"
        )
        assert r.passed


class TestLimitSanitization:
    def test_adds_limit_when_missing(self):
        sql = "SELECT * FROM users"
        result = validator.sanitize_limit(sql, 100)
        assert "100" in result or "LIMIT" in result.upper()

    def test_respects_lower_existing_limit(self):
        sql = "SELECT * FROM users LIMIT 10"
        result = validator.sanitize_limit(sql, 1000)
        # existing limit of 10 is below 1000, should keep 10
        assert "10" in result
