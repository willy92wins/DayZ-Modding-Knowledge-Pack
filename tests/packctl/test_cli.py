from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


def run_cli(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    project_root = str(Path(__file__).resolve().parents[2])
    env["PYTHONPATH"] = project_root + os.pathsep + env.get("PYTHONPATH", "")
    return subprocess.run(
        [sys.executable, "-m", "packctl", *args],
        cwd=root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=env,
    )


def test_missing_arguments_return_usage_exit_2(tmp_path: Path) -> None:
    result = run_cli(tmp_path, "validate")

    assert result.returncode == 2


def test_validate_writes_stable_json_report(repo_factory, tmp_path: Path) -> None:
    root = repo_factory()
    report_path = tmp_path / "report.json"

    result = run_cli(
        root,
        "validate",
        "--root",
        str(root),
        "--report",
        str(report_path),
    )

    assert result.returncode == 0
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["schema_version"] == 1
    assert report["command"] == "validate"
    assert report["verdict"] == "PASS"
    assert report["findings"] == []


def test_validation_finding_returns_exit_1(repo_factory, tmp_path: Path) -> None:
    root = repo_factory({"notes.md": "C:\\Users\\person\\secret\n"})
    report_path = tmp_path / "report.json"

    result = run_cli(
        root,
        "validate",
        "--root",
        str(root),
        "--report",
        str(report_path),
    )

    assert result.returncode == 1
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["verdict"] == "FAIL"
    assert any(item["code"] == "PRIVACY-PRIVATE-PATH" for item in report["findings"])


def test_eval_cli_runs_versioned_case(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[2]
    output = tmp_path / "eval"

    result = run_cli(
        root,
        "eval",
        "run",
        "--case",
        "api-enforce",
        "--variant",
        "current",
        "--out",
        str(output),
    )

    assert result.returncode == 0
    assert (output / "grading.json").is_file()


def test_promotion_cli_apply_uses_existing_plan(
    repo_factory,
    tmp_path: Path,
) -> None:
    from test_promotion import promotion_fixture

    root, map_path, config_path, plan_path, paths = promotion_fixture(
        repo_factory, tmp_path
    )

    checked = run_cli(
        root,
        "promote",
        "--check",
        "--root",
        str(root),
        "--promotion-map",
        str(map_path),
        "--local-targets",
        str(config_path),
        "--plan",
        str(plan_path),
    )
    applied = run_cli(root, "promote", "--apply", "--plan", str(plan_path))

    assert checked.returncode == 0
    assert applied.returncode == 0
    assert (paths["claude"] / "demo" / "SKILL.md").is_file()
