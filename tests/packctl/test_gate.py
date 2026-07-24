from __future__ import annotations

from pathlib import Path

from packctl.gate import run_gate


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
