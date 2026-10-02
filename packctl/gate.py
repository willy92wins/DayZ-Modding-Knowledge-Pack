from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path
from xml.etree import ElementTree

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
    # The caller's pytest options do not reach the gate's pytest runs: one
    # --collect-only or -k in PYTEST_ADDOPTS lets a red suite exit 0.
    environment.pop("PYTEST_ADDOPTS", None)
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


# pytest's closing summary names deselected tests ("1 skipped, 1 deselected in
# 0.16s"); the JUnit report does not list them.
_DESELECTED = re.compile(r"\b\d+ deselected\b")


def _suite_passed(returncode: int, junit: Path, stdout: str) -> bool:
    # A folder passes when pytest ran it to the end -- exit 0, or exit 5 ("no
    # test collected") -- and its JUnit report counts at least one test case,
    # none failed or in error, and nothing was deselected. Exit 5 also needs
    # every case to be a skip: a folder whose modules all skip themselves at
    # import (pytest.importorskip("bpy") on a machine without Blender) ends
    # there, and that is a clean skip. An empty folder, script-style checks
    # and a collection-only run report no test case and fail.
    if returncode not in (0, 5):
        return False
    lines = stdout.strip().splitlines()
    if lines and _DESELECTED.search(lines[-1]):
        return False
    counts = dict.fromkeys(("tests", "skipped", "failures", "errors"), 0)
    try:
        for suite in ElementTree.parse(junit).getroot().iter("testsuite"):
            for key in counts:
                counts[key] += int(suite.get(key, "0"))
    except (OSError, ElementTree.ParseError, ValueError):
        return False
    if min(counts.values()) < 0 or counts["tests"] == 0:
        return False
    if counts["failures"] or counts["errors"]:
        return False
    return returncode == 0 or counts["skipped"] == counts["tests"]


def _run_test_suites(
    root: Path,
    suites: list[Path],
    log_dir: Path,
    *,
    pycache_dir: Path,
) -> tuple[dict[str, object], str]:
    # One pytest process per folder. Several folders ship a test module with
    # the same basename (test_install_py3d.py in four skills), and one process
    # collecting them all aborts under the default import mode ("import file
    # mismatch", exit 2) before a single test runs. A process per folder also
    # keeps one suite's sys.path and sys.modules out of the next.
    outcomes: dict[str, dict[str, object]] = {}
    failed: list[str] = []
    tails: list[str] = []
    for suite in suites:
        name = suite.parent.name
        log_dir.mkdir(parents=True, exist_ok=True)
        junit = log_dir / f"{name}.xml"
        junit.unlink(missing_ok=True)
        result = _run_process(
            root,
            [
                sys.executable,
                "-m",
                "pytest",
                "-q",
                "-p",
                "no:cacheprovider",
                "-rs",
                f"--junitxml={junit}",
                str(suite),
            ],
            pycache_dir=pycache_dir,
        )
        output = result.stdout + result.stderr
        (log_dir / f"{name}.txt").write_text(
            output,
            encoding="utf-8",
            newline="\n",
        )
        passed = _suite_passed(result.returncode, junit, result.stdout)
        outcomes[name] = {
            "verdict": "PASS" if passed else "FAIL",
            "returncode": result.returncode,
        }
        if not passed:
            failed.append(f"{name} (exit {result.returncode})")
            tails.append(output[-600:])
    check: dict[str, object] = {
        "verdict": "FAIL" if failed else "PASS",
        "suite_count": len(suites),
        "suites": outcomes,
    }
    return check, "\n".join([", ".join(failed), *tails])[:2000]


# Per tree: the check its test folders report under, the directory their logs
# go to and the finding a red folder raises.
_TEST_FOLDER_TREES = {
    "skills": ("skill_tests", "skill-tests", "SKILL-TESTS-FAILED"),
    "tools": ("tool_tests", "tool-tests", "TOOL-TESTS-FAILED"),
}
TEST_FOLDER_TREES = tuple(_TEST_FOLDER_TREES)


def _test_folder_check(
    root: Path,
    tree: str,
    report_dir: Path,
    *,
    pycache_dir: Path,
) -> tuple[str, dict[str, object], list[dict[str, object]]]:
    # Every <tree>/<name>/tests folder, each in its own pytest process.
    # tools/py3d/tests has its own check in the gate.
    check_name, log_name, code = _TEST_FOLDER_TREES[tree]
    py3d_tests = root / "tools" / "py3d" / "tests"
    suites = sorted(
        path
        for path in (root / tree).glob("*/tests")
        if path.is_dir() and path != py3d_tests
    )
    check, evidence = _run_test_suites(
        root,
        suites,
        report_dir / log_name,
        pycache_dir=pycache_dir,
    )
    findings: list[dict[str, object]] = []
    if check["verdict"] == "FAIL":
        findings.append(
            finding(
                code,
                path=tree,
                line=0,
                message=(
                    f"A test folder under {tree}/ failed, ran no test or "
                    "deselected tests."
                ),
                evidence=evidence,
            )
        )
    return check_name, check, findings


def _report_dir_in_root(
    command: str,
    root: Path,
    report_dir: Path,
) -> dict[str, object] | None:
    if not is_within(report_dir, root):
        return None
    return make_report(
        command,
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


def run_test_folders(
    root: Path,
    report_dir: Path,
    trees: list[str],
) -> dict[str, object]:
    # The gate's test-folder checks on their own, for CI, which has no
    # skills-ref validator to run the whole gate with.
    root = Path(root).resolve()
    report_dir = Path(report_dir).resolve()
    refusal = _report_dir_in_root("test-folders", root, report_dir)
    if refusal is not None:
        return refusal
    report_dir.mkdir(parents=True, exist_ok=True)
    findings: list[dict[str, object]] = []
    checks: dict[str, dict[str, object]] = {}
    for tree in dict.fromkeys(trees):
        check_name, check, tree_findings = _test_folder_check(
            root,
            tree,
            report_dir,
            pycache_dir=report_dir / "pycache",
        )
        checks[check_name] = check
        findings.extend(tree_findings)
    report = make_report("test-folders", root, findings, checks=checks)
    write_json(report_dir / "test-folders.json", report)
    return report


def run_gate(root: Path, report_dir: Path) -> dict[str, object]:
    root = Path(root).resolve()
    report_dir = Path(report_dir).resolve()
    findings: list[dict[str, object]] = []
    checks: dict[str, dict[str, object]] = {}
    artifacts: dict[str, object] = {}
    refusal = _report_dir_in_root("gate", root, report_dir)
    if refusal is not None:
        return refusal
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

    # Every other test folder the pack ships, skills/<skill>/tests and
    # tools/<tool>/tests, each in its own pytest process. tools/py3d/tests ran
    # above.
    for tree in TEST_FOLDER_TREES:
        check_name, check, tree_findings = _test_folder_check(
            root,
            tree,
            report_dir,
            pycache_dir=pycache_dir,
        )
        checks[check_name] = check
        findings.extend(tree_findings)

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
