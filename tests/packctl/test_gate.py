from __future__ import annotations

import json
from pathlib import Path

from packctl.gate import run_gate


PASSING_SUITE = "def test_passes():\n    assert 1 + 1 == 2\n"
FAILING_SUITE = "def test_fails():\n    assert 1 + 1 == 3\n"
# What a Blender-only module does on a machine without Blender: it skips itself
# at import, so pytest collects no test and exits 5 with one skip recorded.
SKIPPED_SUITE = (
    "import pytest\n\n"
    'pytest.importorskip("packctl_fixture_module_that_is_not_installed")\n\n\n'
    "def test_needs_the_module():\n"
    "    assert False\n"
)
# A script-style check: pytest imports it, finds no test and exits 5 too.
SCRIPT_SUITE = "FAILURES = ['the check this script makes failed']\n"


def test_gate_runs_validation_and_two_reproducible_builds(
    repo_factory,
    tmp_path: Path,
) -> None:
    root = repo_factory(payload={"LICENSE", "README.md"})
    report_dir = tmp_path / "reports"

    report = run_gate(root, report_dir)

    assert report["verdict"] == "PASS"
    assert report["checks"]["validate"]["verdict"] == "PASS"
    assert report["checks"]["build_reproducible"]["verdict"] == "PASS"
    assert report["artifacts"]["build_a_sha256"] == report["artifacts"][
        "build_b_sha256"
    ]
    assert (report_dir / "gate.json").is_file()


def test_gate_detects_non_reproducible_build_bytes(
    repo_factory,
    tmp_path: Path,
    monkeypatch,
) -> None:
    root = repo_factory(payload={"LICENSE", "README.md"})
    report_dir = tmp_path / "reports"
    calls = 0

    def fake_build(_root: Path, output: Path) -> dict[str, object]:
        nonlocal calls
        calls += 1
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(f"build-{calls}".encode("ascii"))
        return {
            "schema_version": 1,
            "command": "build",
            "source_commit": "fixture",
            "verdict": "PASS",
            "findings": [],
            "checks": {},
            "artifacts": {"archive_sha256": str(calls)},
        }

    monkeypatch.setattr("packctl.gate.build_archive", fake_build)

    report = run_gate(root, report_dir)

    assert report["verdict"] == "FAIL"
    assert [item["code"] for item in report["findings"]] == [
        "BUILD-NONDETERMINISTIC"
    ]


def test_gate_requires_external_skills_ref_when_skills_exist(
    repo_factory,
    tmp_path: Path,
    monkeypatch,
) -> None:
    root = repo_factory(
        {
            "skills/demo/SKILL.md": (
                "---\nname: demo\ndescription: Gate fixture.\n---\n# Demo\n"
            )
        },
        payload={"LICENSE", "README.md", "skills/demo/SKILL.md"},
    )
    monkeypatch.delenv("PACK_SKILLS_REF_ROOT", raising=False)

    report = run_gate(root, tmp_path / "reports")

    assert "SKILLS-REF-NOT-CONFIGURED" in [
        item["code"] for item in report["findings"]
    ]


def test_gate_rejects_missing_evidence_even_when_fail_is_expected(
    repo_factory,
    tmp_path: Path,
) -> None:
    case = {
        "schema_version": 1,
        "case_id": "missing-evidence",
        "family": "api",
        "prompt": "Answer from evidence.",
        "fixtures": {"fixture.c": "class Demo {};\n"},
        "assertions": [
            {
                "assertion_id": "mentions-demo",
                "type": "contains",
                "value": "Demo",
                "evidence": ["proof.txt"],
            }
        ],
        "grader": {"type": "mechanical"},
        "required_evidence": ["proof.txt"],
        "variants": [
            {
                "variant_id": "baseline",
                "skill_revision": "absent",
                "baseline_revision": "absent",
                "runner_id": "fixture",
                "expected_verdict": "FAIL",
                "response": "Demo",
                "evidence": {},
                "tokens_input": 1,
                "tokens_output": 1,
            },
            {
                "variant_id": "current",
                "skill_revision": "current",
                "baseline_revision": "absent",
                "runner_id": "fixture",
                "expected_verdict": "PASS",
                "response": "Demo",
                "evidence": {"proof.txt": "fixture.c:1\n"},
                "tokens_input": 1,
                "tokens_output": 1,
            }
        ],
    }
    root = repo_factory(
        {"evals/cases/missing-evidence.json": json.dumps(case)},
        payload={"LICENSE", "README.md"},
    )

    report = run_gate(root, tmp_path / "reports")

    assert "EVAL-MISSING-EVIDENCE" in [
        item["code"] for item in report["findings"]
    ]
    assert report["checks"]["evals"]["verdict"] == "FAIL"


def test_gate_fails_when_a_skill_test_fails(
    repo_factory,
    tmp_path: Path,
) -> None:
    root = repo_factory(
        {
            "skills/bad/tests/test_bad.py": FAILING_SUITE,
            "skills/good/tests/test_good.py": PASSING_SUITE,
        },
        payload={"LICENSE", "README.md"},
    )
    report_dir = tmp_path / "reports"

    report = run_gate(root, report_dir)

    assert report["verdict"] == "FAIL"
    assert [item["code"] for item in report["findings"]] == [
        "SKILL-TESTS-FAILED"
    ]
    assert report["checks"]["skill_tests"] == {
        "verdict": "FAIL",
        "suite_count": 2,
        "suites": {
            "bad": {"verdict": "FAIL", "returncode": 1},
            "good": {"verdict": "PASS", "returncode": 0},
        },
    }
    assert "bad (exit 1)" in report["findings"][0]["evidence"]
    assert "1 failed" in (report_dir / "skill-tests" / "bad.txt").read_text(
        encoding="utf-8"
    )


def test_gate_fails_when_a_tool_test_fails_and_runs_py3d_once(
    repo_factory,
    tmp_path: Path,
) -> None:
    root = repo_factory(
        {
            "tools/broken/tests/test_broken.py": FAILING_SUITE,
            "tools/py3d/tests/test_py3d.py": PASSING_SUITE,
        },
        payload={"LICENSE", "README.md"},
    )

    report = run_gate(root, tmp_path / "reports")

    assert [item["code"] for item in report["findings"]] == [
        "TOOL-TESTS-FAILED"
    ]
    assert report["checks"]["py3d_tests"]["verdict"] == "PASS"
    assert report["checks"]["tool_tests"]["suites"] == {
        "broken": {"verdict": "FAIL", "returncode": 1},
    }


def test_gate_passes_same_named_and_cleanly_skipped_suites(
    repo_factory,
    tmp_path: Path,
) -> None:
    # Two skills shipping test files with one basename abort a single pytest
    # run ("import file mismatch", exit 2) -- the state of main before the
    # gate ran these folders.
    root = repo_factory(
        {
            "skills/alpha/tests/test_install.py": PASSING_SUITE,
            "skills/beta/tests/test_install.py": PASSING_SUITE,
            "skills/blender/tests/test_needs_blender.py": SKIPPED_SUITE,
            "tools/demo/tests/test_install.py": PASSING_SUITE,
        },
        payload={"LICENSE", "README.md"},
    )

    report = run_gate(root, tmp_path / "reports")

    assert report["verdict"] == "PASS"
    assert report["checks"]["skill_tests"]["suites"] == {
        "alpha": {"verdict": "PASS", "returncode": 0},
        "beta": {"verdict": "PASS", "returncode": 0},
        "blender": {"verdict": "PASS", "returncode": 5},
    }
    assert report["checks"]["tool_tests"]["suites"] == {
        "demo": {"verdict": "PASS", "returncode": 0},
    }


def test_gate_fails_a_test_folder_that_runs_nothing(
    repo_factory,
    tmp_path: Path,
) -> None:
    root = repo_factory(
        {"skills/script/tests/test_script.py": SCRIPT_SUITE},
        payload={"LICENSE", "README.md"},
    )

    report = run_gate(root, tmp_path / "reports")

    assert [item["code"] for item in report["findings"]] == [
        "SKILL-TESTS-FAILED"
    ]
    assert report["checks"]["skill_tests"]["suites"] == {
        "script": {"verdict": "FAIL", "returncode": 5},
    }


def test_gate_refuses_a_report_dir_inside_the_root_before_any_suite_runs(
    repo_factory,
    tmp_path: Path,
) -> None:
    marker = tmp_path / "suite-ran.txt"
    root = repo_factory(
        {
            "skills/demo/tests/test_marks.py": (
                "from pathlib import Path\n\n\n"
                "def test_marks():\n"
                f"    Path({str(marker)!r}).write_text('ran', encoding='utf-8')\n"
            )
        },
        payload={"LICENSE", "README.md"},
    )

    report = run_gate(root, root / "gate-reports")

    assert [item["code"] for item in report["findings"]] == [
        "GATE-REPORT-IN-ROOT"
    ]
    assert not marker.exists()
    assert not (root / "gate-reports").exists()
