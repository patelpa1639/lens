"""Security scanning — regex and heuristic checks for common vulnerabilities."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from lens.utils.file_utils import collect_files, read_file_safe


@dataclass
class SecurityFinding:
    file_path: str
    line_number: int
    severity: str  # "critical", "high", "medium", "low"
    category: str  # "secrets", "injection", "crypto", "permissions", "config"
    title: str
    description: str
    line_text: str


@dataclass
class SecurityReport:
    findings: list[SecurityFinding]
    total_count: int
    by_severity: dict[str, int]
    by_category: dict[str, int]
    risk_score: float  # 0-100, higher = more risky
    summary: str


# ---------------------------------------------------------------------------
# Detection rules
# ---------------------------------------------------------------------------

@dataclass
class _Rule:
    pattern: re.Pattern[str]
    severity: str
    category: str
    title: str
    description: str
    skip_tests: bool = False
    skip_comments: bool = False


_RULES: list[_Rule] = [
    # --- Secrets (critical) ---
    _Rule(
        pattern=re.compile(r"""password\s*=\s*["'][^"']+["']""", re.IGNORECASE),
        severity="critical",
        category="secrets",
        title="Hardcoded password",
        description="A password appears to be hardcoded in source code.",
        skip_tests=True,
        skip_comments=True,
    ),
    _Rule(
        pattern=re.compile(
            r"""(api[_\-]?key|api[_\-]?secret|access[_\-]?token)\s*=\s*["'][^"']+["']""",
            re.IGNORECASE,
        ),
        severity="critical",
        category="secrets",
        title="Hardcoded API key or token",
        description="An API key, secret, or access token appears to be hardcoded.",
        skip_tests=True,
        skip_comments=True,
    ),
    _Rule(
        pattern=re.compile(r"AKIA[0-9A-Z]{16}"),
        severity="critical",
        category="secrets",
        title="AWS access key",
        description="An AWS access key ID was detected.",
    ),
    _Rule(
        pattern=re.compile(r"-----BEGIN (RSA |EC |DSA )?PRIVATE KEY-----"),
        severity="critical",
        category="secrets",
        title="Private key",
        description="A private key block was found in source code.",
    ),
    _Rule(
        pattern=re.compile(
            r"""(secret|token|credential)\s*=\s*["'][^"']{8,}["']""",
            re.IGNORECASE,
        ),
        severity="critical",
        category="secrets",
        title="Hardcoded secret or credential",
        description="A secret, token, or credential appears to be hardcoded.",
        skip_tests=True,
        skip_comments=True,
    ),
    # --- Injection (high) ---
    _Rule(
        pattern=re.compile(r"""execute\(.*%s"""),
        severity="high",
        category="injection",
        title="Potential SQL injection",
        description="String formatting used in SQL execute() — use parameterized queries.",
    ),
    _Rule(
        pattern=re.compile(r"""execute\(.*\.format\("""),
        severity="high",
        category="injection",
        title="Potential SQL injection (format)",
        description="str.format() used in SQL execute() — use parameterized queries.",
    ),
    _Rule(
        pattern=re.compile(r"""execute\(.*\bf["']"""),
        severity="high",
        category="injection",
        title="Potential SQL injection (f-string)",
        description="f-string used in SQL execute() — use parameterized queries.",
    ),
    _Rule(
        pattern=re.compile(r"os\.system\("),
        severity="high",
        category="injection",
        title="os.system() usage",
        description="os.system() is vulnerable to shell injection — use subprocess with a list.",
    ),
    _Rule(
        pattern=re.compile(r"subprocess\.call\(.*shell\s*=\s*True"),
        severity="high",
        category="injection",
        title="subprocess with shell=True",
        description="shell=True enables shell injection — pass a list of args instead.",
    ),
    _Rule(
        pattern=re.compile(r"\beval\("),
        severity="high",
        category="injection",
        title="eval() usage",
        description="eval() can execute arbitrary code — avoid using it on untrusted input.",
    ),
    _Rule(
        pattern=re.compile(r"\bexec\("),
        severity="high",
        category="injection",
        title="exec() usage",
        description="exec() can execute arbitrary code — avoid using it on untrusted input.",
    ),
    _Rule(
        pattern=re.compile(r"\.\./"),
        severity="high",
        category="injection",
        title="Path traversal pattern",
        description="Relative path traversal detected — validate and sanitize file paths.",
    ),
    # --- Crypto (medium) ---
    _Rule(
        pattern=re.compile(r"\bmd5\("),
        severity="medium",
        category="crypto",
        title="Weak hash (MD5)",
        description="MD5 is cryptographically broken — use SHA-256 or better.",
        skip_tests=True,
    ),
    _Rule(
        pattern=re.compile(r"\bsha1\("),
        severity="medium",
        category="crypto",
        title="Weak hash (SHA-1)",
        description="SHA-1 is deprecated for security — use SHA-256 or better.",
        skip_tests=True,
    ),
    _Rule(
        pattern=re.compile(r"""iv\s*=\s*b["']""", re.IGNORECASE),
        severity="medium",
        category="crypto",
        title="Hardcoded IV/salt",
        description="Initialization vectors and salts should be randomly generated.",
    ),
    # --- Permissions (medium) ---
    _Rule(
        pattern=re.compile(r"chmod.*777"),
        severity="medium",
        category="permissions",
        title="World-writable permissions (chmod 777)",
        description="chmod 777 grants full access to all users — restrict permissions.",
    ),
    _Rule(
        pattern=re.compile(r"0o777"),
        severity="medium",
        category="permissions",
        title="World-writable permissions (0o777)",
        description="0o777 grants full access to all users — restrict permissions.",
    ),
    _Rule(
        pattern=re.compile(r"DEBUG\s*=\s*True"),
        severity="medium",
        category="permissions",
        title="Debug mode enabled",
        description="Debug mode should be disabled in production.",
    ),
    _Rule(
        pattern=re.compile(r"debug\s*=\s*true"),
        severity="medium",
        category="permissions",
        title="Debug mode enabled",
        description="Debug mode should be disabled in production.",
    ),
    # --- Config (low) ---
    _Rule(
        pattern=re.compile(r"http://(?!localhost)(?!127\.0\.0\.1)(?!0\.0\.0\.0)"),
        severity="low",
        category="config",
        title="Insecure HTTP URL",
        description="Use HTTPS instead of HTTP for secure communication.",
        skip_comments=True,
    ),
    _Rule(
        pattern=re.compile(r"verify\s*=\s*False"),
        severity="low",
        category="config",
        title="SSL verification disabled",
        description="Disabling SSL verification exposes connections to MITM attacks.",
    ),
    _Rule(
        pattern=re.compile(r"SSL_VERIFY.*false", re.IGNORECASE),
        severity="low",
        category="config",
        title="SSL verification disabled",
        description="Disabling SSL verification exposes connections to MITM attacks.",
    ),
    _Rule(
        pattern=re.compile(r"Access-Control-Allow-Origin.*\*"),
        severity="low",
        category="config",
        title="CORS wildcard origin",
        description="Wildcard CORS allows any origin — restrict to specific domains.",
    ),
]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_TEST_PATH_PARTS = {"test", "tests", "test_", "_test", "spec", "specs"}


def _is_test_file(path: str) -> bool:
    """Return True if *path* looks like a test file."""
    lower = path.lower()
    return any(marker in lower for marker in _TEST_PATH_PARTS)


def _is_comment_line(line: str) -> bool:
    """Quick check for common single-line comment prefixes."""
    stripped = line.lstrip()
    return stripped.startswith(("#", "//", "/*", "*", "<!--", "--", ";"))


# ---------------------------------------------------------------------------
# Core scanning
# ---------------------------------------------------------------------------


def _scan_file(file_path: Path, root: Path) -> list[SecurityFinding]:
    """Scan a single file and return findings."""
    content = read_file_safe(file_path)
    if content is None:
        return []

    rel_path = str(file_path.relative_to(root))
    is_test = _is_test_file(rel_path)
    findings: list[SecurityFinding] = []

    for line_number, line in enumerate(content.splitlines(), start=1):
        for rule in _RULES:
            if rule.skip_tests and is_test:
                continue
            if rule.skip_comments and _is_comment_line(line):
                continue
            if rule.pattern.search(line):
                findings.append(
                    SecurityFinding(
                        file_path=rel_path,
                        line_number=line_number,
                        severity=rule.severity,
                        category=rule.category,
                        title=rule.title,
                        description=rule.description,
                        line_text=line.rstrip(),
                    )
                )

    return findings


def _calculate_risk_score(findings: list[SecurityFinding]) -> float:
    """Calculate risk score 0-100 from findings."""
    severity_points = {"critical": 20, "high": 10, "medium": 5, "low": 2}
    severity_caps = {"critical": 60, "high": 30, "medium": 20, "low": 10}

    totals: dict[str, float] = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    for f in findings:
        sev = f.severity
        totals[sev] += severity_points.get(sev, 0)

    capped = sum(min(totals[s], severity_caps[s]) for s in totals)
    return min(capped, 100.0)


def _build_summary(findings: list[SecurityFinding], risk_score: float) -> str:
    """Generate a plain-English summary."""
    if not findings:
        return "No security issues detected. Risk score: 0/100."

    by_sev: dict[str, int] = {}
    for f in findings:
        by_sev[f.severity] = by_sev.get(f.severity, 0) + 1

    parts: list[str] = []
    # Describe each severity bucket with representative titles
    severity_order = ["critical", "high", "medium", "low"]
    for sev in severity_order:
        count = by_sev.get(sev, 0)
        if count == 0:
            continue
        # Collect unique titles for this severity
        titles = sorted({f.title for f in findings if f.severity == sev})
        label = titles[0].lower() if len(titles) == 1 else ", ".join(t.lower() for t in titles[:2])
        parts.append(f"{count} {sev} ({label})")

    total = len(findings)
    issue_word = "issue" if total == 1 else "issues"
    detail = ", ".join(parts)
    return f"Found {total} potential security {issue_word}: {detail}. Risk score: {risk_score:.0f}/100."


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def scan_security(root: Path, extra_ignores: list[str] | None = None) -> SecurityReport:
    """Scan project for common security issues."""
    root = root.resolve()
    files = collect_files(root, extra_ignores=extra_ignores)

    all_findings: list[SecurityFinding] = []
    for fp in files:
        all_findings.extend(_scan_file(fp, root))

    by_severity: dict[str, int] = {}
    by_category: dict[str, int] = {}
    for f in all_findings:
        by_severity[f.severity] = by_severity.get(f.severity, 0) + 1
        by_category[f.category] = by_category.get(f.category, 0) + 1

    risk_score = _calculate_risk_score(all_findings)
    summary = _build_summary(all_findings, risk_score)

    return SecurityReport(
        findings=all_findings,
        total_count=len(all_findings),
        by_severity=by_severity,
        by_category=by_category,
        risk_score=risk_score,
        summary=summary,
    )
