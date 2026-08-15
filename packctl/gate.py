from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from .builder import build_archive
from .common import (
    finding,
    git_tracked_files,
    is_within,
    make_report,
    sha256_file,
    write_json,
)
from .evals import run_eval_case, validate_eval_case
from .validation import validate_repo


def _run_process(
    root: Path,
    args: list[str],
    *,
    pycache_dir: Path,
) -> subprocess.CompletedProcess[str]:
    environment = dict(os.environ)
    environment["PYTHONUTF8"] = "1"
    environment["PYTHONPYCACHEPREFIX"] = str(pycache_dir)
    return subprocess.run(
        args,
        cwd=root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=environment,
    )


# The reference validator ships on PyPI as the distribution `skills-ref`, but its
# console script is named `agentskills`. The older name is kept first so an
# existing checkout keeps working.
_SKILLS_REF_COMMANDS = ("skills-ref", "agentskills")


def _skills_ref_executable(configured: str) -> Path | None:
    candidate = Path(configured)
    if candidate.is_file():
        return candidate
    for command in _SKILLS_REF_COMMANDS:
        for relative in (
            Path(".venv") / "Scripts" / f"{command}.exe",
            Path(".venv") / "bin" / command,
            Path("Scripts") / f"{command}.exe",
            Path("bin") / command,
        ):
            resolved = candidate / relative
            if resolved.is_file():
                return resolved
    return None


def run_gate(root: Path, report_dir: Path) -> dict[str, object]:
    root = Path(root).resolve()
    report_dir = Path(report_dir).resolve()
    findings: list[dict[str, object]] = []
    checks: dict[str, dict[str, object]] = {}
    artifacts: dict[str, object] = {}
    if is_within(report_dir, root):
        report = make_report(
            "gate",
            root,
            [
                finding(
                    "GATE-REPORT-IN-ROOT",
                    path="",
                    line=0,
                    message="Gate reports must be written outside the source tree.",
                    evidence=str(report_dir),
                )
            ],
        )
        return report
    report_dir.mkdir(parents=True, exist_ok=True)
    pycache_dir = report_dir / "pycache"

    validation = validate_repo(root)
    write_json(report_dir / "validate.json", validation)
    checks["validate"] = {
        "verdict": validation["verdict"],
        "finding_count": len(validation["findings"]),
    }
    findings.extend(validation["findings"])

    # Compile what SHIPS, which is what git tracks -- the same definition the
    # archive builder uses. Walking the filesystem instead swept in ignored
    # scratch: report directories, virtualenvs and build output, none of which
    # reach a release. It also made the gate fail for the wrong reason, since a
    # leftover venv under reports/ carries read-only files and py_compile stops
    # on the PermissionError before compiling anything real.
    python_files = [path for path in git_tracked_files(root) if path.endswith(".py")]
    if python_files:
        compile_result = _run_process(
            root,
            [sys.executable, "-m", "py_compile", *python_files],
            pycache_dir=pycache_dir,
        )
        checks["python_compile"] = {
            "verdict": "PASS" if compile_result.returncode == 0 else "FAIL",
            "file_count": len(python_files),
        }
        if compile_result.returncode != 0:
            findings.append(
                finding(
                    "PYTHON-COMPILE-FAILED",
                    path="",
                    line=0,
                    message="One or more Python files failed to compile.",
                    evidence=compile_result.stderr[-1000:],
                )
            )
    else:
        checks["python_compile"] = {"verdict": "PASS", "file_count": 0}

    skill_dirs = sorted(
        path.parent for path in (root / "skills").rglob("SKILL.md")
    ) if (root / "skills").exists() else []
    if skill_dirs:
        configured = os.environ.get("PACK_SKILLS_REF_ROOT")
        executable = _skills_ref_executable(configured) if configured else None
        if executable is None:
            findings.append(
                finding(
                    "SKILLS-REF-NOT-CONFIGURED",
                    path="skills",
                    line=0,
                    message="The pinned external skills-ref validator is required for this gate.",
                    evidence="Set PACK_SKILLS_REF_ROOT to the pinned checkout or executable.",
                )
            )
            checks["skills_ref"] = {
                "verdict": "FAIL",
                "skill_count": len(skill_dirs),
            }
        else:
            failures: list[str] = []
            for skill_dir in skill_dirs:
                result = _run_process(
                    root,
                    [str(executable), "validate", str(skill_dir)],
                    pycache_dir=pycache_dir,
                )
                if result.returncode != 0:
                    failures.append(
                        f"{skill_dir.relative_to(root).as_posix()}:{result.stdout}{result.stderr}"
                    )
            checks["skills_ref"] = {
                "verdict": "PASS" if not failures else "FAIL",
                "skill_count": len(skill_dirs),
            }
            if failures:
                findings.append(
                    finding(
                        "SKILLS-REF-FAILED",
                        path="skills",
                        line=0,
                        message="At least one skill failed the pinned reference validator.",
                        evidence="\n".join(failures)[-2000:],
                    )
                )
    else:
        checks["skills_ref"] = {"verdict": "PASS", "skill_count": 0}

    packctl_tests = root / "tests" / "packctl"
    if packctl_tests.is_dir():
        result = _run_process(
            root,
            [
                sys.executable,
                "-m",
                "pytest",
                "-q",
                "-p",
                "no:cacheprovider",
                str(packctl_tests),
            ],
            pycache_dir=pycache_dir,
        )
        checks["packctl_tests"] = {
            "verdict": "PASS" if result.returncode == 0 else "FAIL",
            "returncode": result.returncode,
        }
        (report_dir / "packctl-tests.txt").write_text(
            result.stdout + result.stderr,
            encoding="utf-8",
            newline="\n",
        )
        if result.returncode != 0:
            findings.append(
                finding(
                    "PACKCTL-TESTS-FAILED",
                    path="tests/packctl",
                    line=0,
                    message="The packctl regression suite failed.",
                    evidence=(result.stdout + result.stderr)[-2000:],
                )
            )
    else:
        checks["packctl_tests"] = {"verdict": "PASS", "returncode": 0}

    py3d_tests = root / "tools" / "py3d" / "tests"
    if py3d_tests.is_dir():
        result = _run_process(
            root,
            [
                sys.executable,
                "-m",
                "pytest",
                "-q",
                "-p",
                "no:cacheprovider",
                str(py3d_tests),
            ],
            pycache_dir=pycache_dir,
        )
        checks["py3d_tests"] = {
            "verdict": "PASS" if result.returncode == 0 else "FAIL",
            "returncode": result.returncode,
        }
        (report_dir / "py3d-tests.txt").write_text(
            result.stdout + result.stderr,
            encoding="utf-8",
            newline="\n",
        )
        if result.returncode != 0:
            findings.append(
                finding(
                    "PY3D-TESTS-FAILED",
                    path="tools/py3d/tests",
                    line=0,
                    message="The py3d regression suite failed.",
                    evidence=(result.stdout + result.stderr)[-2000:],
                )
            )
    else:
        checks["py3d_tests"] = {"verdict": "PASS", "returncode": 0}

    eval_findings: list[dict[str, object]] = []
    eval_count = 0
    cases_root = root / "evals" / "cases"
    if cases_root.is_dir():
        for case_path in sorted(cases_root.glob("*.json")):
            schema_findings = validate_eval_case(case_path)
            eval_findings.extend(schema_findings)
            if schema_findings:
                continue
            case = __import__("json").loads(case_path.read_text(encoding="utf-8"))
            for variant in case["variants"]:
                eval_count += 1
                output = report_dir / "evals" / case["case_id"] / variant["variant_id"]
                result = run_eval_case(case_path, variant["variant_id"], output)
                grading_path = output / "grading.json"
                actual = result["verdict"]
                expected = variant["expected_verdict"]
                for eval_finding in result["findings"]:
                    if eval_finding["code"] == "EVAL-MISSING-EVIDENCE":
                        copied = dict(eval_finding)
                        copied["path"] = case_path.relative_to(root).as_posix()
                        copied["evidence"] = (
                            f"variant={variant['variant_id']} "
                            f"missing={eval_finding['evidence']}"
                        )
                        eval_findings.append(copied)
                if actual != expected:
                    eval_findings.append(
                        finding(
                            "EVAL-UNEXPECTED-VERDICT",
                            path=case_path.relative_to(root).as_posix(),
                            line=0,
                            message="An evaluation variant did not produce its pinned verdict.",
                            evidence=(
                                f"variant={variant['variant_id']} "
                                f"expected={expected} actual={actual}"
                            ),
                        )
                    )
                if not grading_path.is_file():
                    eval_findings.append(
                        finding(
                            "EVAL-GRADING-MISSING",
                            path=case_path.relative_to(root).as_posix(),
                            line=0,
                            message="An evaluation run did not emit grading.json.",
                            evidence=str(variant["variant_id"]),
                        )
                    )
    findings.extend(eval_findings)
    checks["evals"] = {
        "verdict": "FAIL" if eval_findings else "PASS",
        "variant_count": eval_count,
    }

    if not any(item["severity"] == "error" for item in findings):
        build_a = report_dir / "build-a.zip"
        build_b = report_dir / "build-b.zip"
        report_a = build_archive(root, build_a)
        report_b = build_archive(root, build_b)
        write_json(report_dir / "build-a.json", report_a)
        write_json(report_dir / "build-b.json", report_b)
        if report_a["verdict"] != "PASS" or report_b["verdict"] != "PASS":
            findings.extend(report_a["findings"])
            findings.extend(report_b["findings"])
            checks["build_reproducible"] = {"verdict": "FAIL"}
        else:
            digest_a = sha256_file(build_a)
            digest_b = sha256_file(build_b)
            artifacts["build_a_sha256"] = digest_a
            artifacts["build_b_sha256"] = digest_b
            checks["build_reproducible"] = {
                "verdict": "PASS" if digest_a == digest_b else "FAIL"
            }
            if digest_a != digest_b:
                findings.append(
                    finding(
                        "BUILD-NONDETERMINISTIC",
                        path="",
                        line=0,
                        message="Two clean builds of the same commit differ byte-for-byte.",
                        evidence=f"first={digest_a} second={digest_b}",
                    )
                )
    else:
        checks["build_reproducible"] = {"verdict": "SKIPPED"}

    report = make_report(
        "gate",
        root,
        findings,
        checks=checks,
        artifacts=artifacts,
    )
    write_json(report_dir / "gate.json", report)
    return report
