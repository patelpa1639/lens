"""Tests for security scanning."""

from __future__ import annotations

from pathlib import Path

import pytest

from lens.analyzer.security import (
    SecurityFinding,
    SecurityReport,
    _calculate_risk_score,
    scan_security,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def tmp_insecure_project(tmp_path: Path) -> Path:
    """Create a small project with known security issues."""
    (tmp_path / "config.py").write_text(
        'DB_PASSWORD = "super_secret_123"\n'
        'API_KEY = "sk-1234567890abcdef"\n'
        "DEBUG = True\n"
    )
    (tmp_path / "db.py").write_text(
        "import os\n"
        "def run_query(user_input):\n"
        '    os.system("echo " + user_input)\n'
        '    cursor.execute("SELECT * FROM users WHERE id = %s" % user_input)\n'
    )
    return tmp_path


@pytest.fixture()
def tmp_clean_project(tmp_path: Path) -> Path:
    """Create a project with no security issues."""
    (tmp_path / "main.py").write_text(
        "import sys\n"
        "\n"
        "def greet(name: str) -> str:\n"
        '    return f"Hello, {name}"\n'
        "\n"
        'if __name__ == "__main__":\n'
        "    print(greet(sys.argv[1]))\n"
    )
    return tmp_path


# ---------------------------------------------------------------------------
# Detection tests
# ---------------------------------------------------------------------------


class TestHardcodedPasswords:
    def test_detects_password(self, tmp_insecure_project: Path) -> None:
        report = scan_security(tmp_insecure_project)
        password_findings = [f for f in report.findings if f.title == "Hardcoded password"]
        assert len(password_findings) >= 1
        assert password_findings[0].severity == "critical"
        assert password_findings[0].category == "secrets"

    def test_skips_password_in_test_files(self, tmp_path: Path) -> None:
        tests_dir = tmp_path / "tests"
        tests_dir.mkdir()
        (tests_dir / "test_auth.py").write_text('password = "test_pass_123"\n')
        report = scan_security(tmp_path)
        password_findings = [f for f in report.findings if f.title == "Hardcoded password"]
        assert len(password_findings) == 0

    def test_skips_password_in_comments(self, tmp_path: Path) -> None:
        (tmp_path / "app.py").write_text('# password = "old_default"\n')
        report = scan_security(tmp_path)
        password_findings = [f for f in report.findings if f.title == "Hardcoded password"]
        assert len(password_findings) == 0


class TestAPIKeys:
    def test_detects_api_key(self, tmp_insecure_project: Path) -> None:
        report = scan_security(tmp_insecure_project)
        key_findings = [f for f in report.findings if "API key" in f.title or "secret" in f.title.lower()]
        assert len(key_findings) >= 1

    def test_detects_aws_key(self, tmp_path: Path) -> None:
        (tmp_path / "creds.py").write_text('aws_key = "AKIAIOSFODNN7EXAMPLE"\n')
        report = scan_security(tmp_path)
        aws_findings = [f for f in report.findings if f.title == "AWS access key"]
        assert len(aws_findings) == 1
        assert aws_findings[0].severity == "critical"

    def test_detects_private_key(self, tmp_path: Path) -> None:
        (tmp_path / "key.pem").write_text("-----BEGIN RSA PRIVATE KEY-----\ndata\n-----END RSA PRIVATE KEY-----\n")
        report = scan_security(tmp_path)
        pk_findings = [f for f in report.findings if f.title == "Private key"]
        assert len(pk_findings) == 1


class TestSQLInjection:
    def test_detects_sql_percent_format(self, tmp_insecure_project: Path) -> None:
        report = scan_security(tmp_insecure_project)
        sql_findings = [f for f in report.findings if "SQL injection" in f.title]
        assert len(sql_findings) >= 1
        assert sql_findings[0].severity == "high"
        assert sql_findings[0].category == "injection"

    def test_detects_sql_format_method(self, tmp_path: Path) -> None:
        (tmp_path / "query.py").write_text(
            'cursor.execute("SELECT * FROM t WHERE id = {}".format(uid))\n'
        )
        report = scan_security(tmp_path)
        sql_findings = [f for f in report.findings if "SQL injection" in f.title]
        assert len(sql_findings) >= 1


class TestEvalExec:
    def test_detects_eval(self, tmp_path: Path) -> None:
        (tmp_path / "danger.py").write_text("result = eval(user_input)\n")
        report = scan_security(tmp_path)
        eval_findings = [f for f in report.findings if f.title == "eval() usage"]
        assert len(eval_findings) == 1
        assert eval_findings[0].severity == "high"

    def test_detects_exec(self, tmp_path: Path) -> None:
        (tmp_path / "danger.py").write_text("exec(code_string)\n")
        report = scan_security(tmp_path)
        exec_findings = [f for f in report.findings if f.title == "exec() usage"]
        assert len(exec_findings) == 1

    def test_detects_os_system(self, tmp_insecure_project: Path) -> None:
        report = scan_security(tmp_insecure_project)
        os_findings = [f for f in report.findings if f.title == "os.system() usage"]
        assert len(os_findings) >= 1


class TestDebugMode:
    def test_detects_debug_true(self, tmp_insecure_project: Path) -> None:
        report = scan_security(tmp_insecure_project)
        debug_findings = [f for f in report.findings if "Debug mode" in f.title]
        assert len(debug_findings) >= 1
        assert debug_findings[0].severity == "medium"
        assert debug_findings[0].category == "permissions"


class TestCleanProject:
    def test_no_findings(self, tmp_clean_project: Path) -> None:
        report = scan_security(tmp_clean_project)
        assert report.total_count == 0
        assert report.findings == []
        assert report.risk_score == 0.0
        assert "No security issues" in report.summary


class TestCryptoRules:
    def test_detects_md5(self, tmp_path: Path) -> None:
        (tmp_path / "hash.py").write_text("digest = md5(data)\n")
        report = scan_security(tmp_path)
        md5_findings = [f for f in report.findings if "MD5" in f.title]
        assert len(md5_findings) == 1
        assert md5_findings[0].severity == "medium"

    def test_detects_hardcoded_iv(self, tmp_path: Path) -> None:
        (tmp_path / "crypto.py").write_text("iv = b'1234567890123456'\n")
        report = scan_security(tmp_path)
        iv_findings = [f for f in report.findings if "IV" in f.title]
        assert len(iv_findings) == 1


class TestConfigRules:
    def test_detects_http_url(self, tmp_path: Path) -> None:
        (tmp_path / "client.py").write_text('url = "http://example.com/api"\n')
        report = scan_security(tmp_path)
        http_findings = [f for f in report.findings if "HTTP" in f.title]
        assert len(http_findings) >= 1
        assert http_findings[0].severity == "low"

    def test_allows_localhost_http(self, tmp_path: Path) -> None:
        (tmp_path / "dev.py").write_text('url = "http://localhost:8000"\n')
        report = scan_security(tmp_path)
        http_findings = [f for f in report.findings if f.title == "Insecure HTTP URL"]
        assert len(http_findings) == 0

    def test_detects_verify_false(self, tmp_path: Path) -> None:
        (tmp_path / "req.py").write_text("requests.get(url, verify=False)\n")
        report = scan_security(tmp_path)
        ssl_findings = [f for f in report.findings if "SSL" in f.title]
        assert len(ssl_findings) >= 1

    def test_detects_cors_wildcard(self, tmp_path: Path) -> None:
        (tmp_path / "server.py").write_text('headers["Access-Control-Allow-Origin"] = "*"\n')
        report = scan_security(tmp_path)
        cors_findings = [f for f in report.findings if "CORS" in f.title]
        assert len(cors_findings) == 1


# ---------------------------------------------------------------------------
# Risk score tests
# ---------------------------------------------------------------------------


class TestRiskScore:
    def test_empty_findings(self) -> None:
        assert _calculate_risk_score([]) == 0.0

    def test_single_critical(self) -> None:
        findings = [
            SecurityFinding("a.py", 1, "critical", "secrets", "t", "d", "x"),
        ]
        assert _calculate_risk_score(findings) == 20.0

    def test_capped_critical(self) -> None:
        findings = [
            SecurityFinding("a.py", i, "critical", "secrets", "t", "d", "x")
            for i in range(10)
        ]
        # 10 * 20 = 200, capped at 60
        assert _calculate_risk_score(findings) == 60.0

    def test_mixed_severities(self) -> None:
        findings = [
            SecurityFinding("a.py", 1, "critical", "secrets", "t", "d", "x"),
            SecurityFinding("a.py", 2, "high", "injection", "t", "d", "x"),
            SecurityFinding("a.py", 3, "medium", "crypto", "t", "d", "x"),
            SecurityFinding("a.py", 4, "low", "config", "t", "d", "x"),
        ]
        # 20 + 10 + 5 + 2 = 37
        assert _calculate_risk_score(findings) == 37.0

    def test_overall_cap_at_100(self) -> None:
        findings = [
            SecurityFinding("a.py", i, "critical", "secrets", "t", "d", "x")
            for i in range(5)
        ] + [
            SecurityFinding("a.py", i, "high", "injection", "t", "d", "x")
            for i in range(5)
        ] + [
            SecurityFinding("a.py", i, "medium", "crypto", "t", "d", "x")
            for i in range(5)
        ] + [
            SecurityFinding("a.py", i, "low", "config", "t", "d", "x")
            for i in range(10)
        ]
        score = _calculate_risk_score(findings)
        assert score <= 100.0


class TestSeverityClassification:
    """Verify that each category maps to the expected severity."""

    def test_secrets_are_critical(self, tmp_path: Path) -> None:
        (tmp_path / "s.py").write_text('password = "hunter2_secret"\n')
        report = scan_security(tmp_path)
        for f in report.findings:
            if f.category == "secrets":
                assert f.severity == "critical"

    def test_injection_is_high(self, tmp_path: Path) -> None:
        (tmp_path / "s.py").write_text("os.system(cmd)\n")
        report = scan_security(tmp_path)
        for f in report.findings:
            if f.category == "injection":
                assert f.severity == "high"


class TestReportStructure:
    def test_report_fields(self, tmp_insecure_project: Path) -> None:
        report = scan_security(tmp_insecure_project)
        assert isinstance(report, SecurityReport)
        assert report.total_count == len(report.findings)
        assert report.total_count > 0
        assert sum(report.by_severity.values()) == report.total_count
        assert sum(report.by_category.values()) == report.total_count
        assert 0 <= report.risk_score <= 100
        assert isinstance(report.summary, str)
        assert "Risk score:" in report.summary

    def test_finding_fields(self, tmp_insecure_project: Path) -> None:
        report = scan_security(tmp_insecure_project)
        for f in report.findings:
            assert f.file_path
            assert f.line_number >= 1
            assert f.severity in ("critical", "high", "medium", "low")
            assert f.category in ("secrets", "injection", "crypto", "permissions", "config")
            assert f.title
            assert f.description
            assert f.line_text
