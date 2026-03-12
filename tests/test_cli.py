"""Tests for CLI commands using Click's CliRunner."""


from click.testing import CliRunner

from lens.cli import main


def test_cli_version():
    runner = CliRunner()
    result = runner.invoke(main, ["--version"])
    assert result.exit_code == 0
    assert "0.1.0" in result.output


def test_cli_help():
    runner = CliRunner()
    result = runner.invoke(main, ["--help"])
    assert result.exit_code == 0
    assert "Lens" in result.output


def test_cli_scan_help():
    runner = CliRunner()
    result = runner.invoke(main, ["scan", "--help"])
    assert result.exit_code == 0
    assert "--depth" in result.output


def test_cli_scan_python_project(tmp_python_project):
    runner = CliRunner()
    result = runner.invoke(main, ["scan", str(tmp_python_project), "--no-git"])
    assert result.exit_code == 0
    assert "LENS" in result.output


def test_cli_scan_nonexistent():
    runner = CliRunner()
    result = runner.invoke(main, ["scan", "/nonexistent/path"])
    assert result.exit_code != 0


def test_cli_explain(tmp_python_project):
    runner = CliRunner()
    result = runner.invoke(main, ["explain", str(tmp_python_project), "--no-git"])
    assert result.exit_code == 0
    assert "Python" in result.output


def test_cli_stats(tmp_python_project):
    runner = CliRunner()
    result = runner.invoke(main, ["stats", str(tmp_python_project), "--no-git"])
    assert result.exit_code == 0


def test_cli_export_json(tmp_python_project, tmp_path):
    runner = CliRunner()
    out = tmp_path / "out.json"
    result = runner.invoke(
        main, ["export", str(tmp_python_project), "--format", "json", "--output", str(out), "--no-git"]
    )
    assert result.exit_code == 0
    assert out.exists()


def test_cli_export_markdown(tmp_python_project, tmp_path):
    runner = CliRunner()
    out = tmp_path / "out.md"
    result = runner.invoke(
        main, ["export", str(tmp_python_project), "--format", "md", "--output", str(out), "--no-git"]
    )
    assert result.exit_code == 0
    assert out.exists()


def test_cli_map(tmp_python_project, tmp_path):
    runner = CliRunner()
    out = tmp_path / "report.html"
    result = runner.invoke(
        main, ["map", str(tmp_python_project), "--output", str(out), "--no-open", "--no-git"]
    )
    assert result.exit_code == 0
    assert out.exists()
