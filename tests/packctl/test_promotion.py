from __future__ import annotations

import json
from pathlib import Path

import pytest

from conftest import run_git, write_json

from packctl.common import tree_digest
from packctl.promotion import apply_promotion, check_promotion


REQUIRED_SKILL_TARGETS = ["claude_user_skills", "agents_user_skills"]


def codes(report: dict[str, object]) -> list[str]:
    return [str(item["code"]) for item in report["findings"]]


def promotion_fixture(
    repo_factory,
    tmp_path: Path,
    *,
    alias_skills: bool = False,
    writable: bool = True,
) -> tuple[Path, Path, Path, Path, dict[str, Path]]:
    root = repo_factory(
        {
            "skills/demo/SKILL.md": (
                "---\nname: demo\ndescription: Promotion fixture.\n---\n# Demo\n"
            )
        },
        payload={"LICENSE", "README.md", "skills/demo/SKILL.md"},
    )
    targets_root = tmp_path / "targets"
    claude = targets_root / "claude"
    agents = claude if alias_skills else targets_root / "agents"
    vault = targets_root / "vault"
    backups = targets_root / "backups"
    for path in {claude, agents, vault, backups}:
        path.mkdir(parents=True, exist_ok=True)

    promotion_map = {
        "schema_version": 1,
        "artifacts": [
            {
                "artifact_id": "fixture",
                "repo_path": "skills/demo",
                "artifact_kind": "tree",
                "applicability": "domain_invariant",
                "vault_targets": ["obsidian_snapshots"],
                "skill_target_ids": REQUIRED_SKILL_TARGETS,
            }
        ],
    }
    map_path = tmp_path / "promotion-map.json"
    write_json(map_path, promotion_map)
    config = {
        "schema_version": 1,
        "allowed_physical_roots": [str(targets_root)],
        "forbidden_physical_roots": [str(targets_root / "plugins")],
        "backup_root": str(backups),
        "targets": {
            "claude_user_skills": {
                "path": str(claude),
                "ownership": "user_owned",
                "writable": writable,
            },
            "agents_user_skills": {
                "path": str(agents),
                "ownership": "user_owned",
                "writable": writable,
            },
            "obsidian_snapshots": {
                "path": str(vault),
                "ownership": "user_owned",
                "writable": writable,
            },
        },
    }
    config_path = tmp_path / "local-targets.json"
    write_json(config_path, config)
    plan_path = tmp_path / "plan.json"
    return root, map_path, config_path, plan_path, {
        "targets": targets_root,
        "claude": claude,
        "agents": agents,
        "vault": vault,
        "backups": backups,
    }


def test_promotion_check_routes_repo_vault_and_both_skill_roots(
    repo_factory,
    tmp_path: Path,
) -> None:
    root, map_path, config_path, plan_path, _ = promotion_fixture(
        repo_factory, tmp_path
    )

    report = check_promotion(root, map_path, config_path, plan_path)

    assert report["verdict"] == "WARN"
    assert codes(report) == ["PROMOTION-DRIFT"]
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    assert plan["source_commit"] == run_git(root, "rev-parse", "HEAD")
    assert set(plan["artifact_ids"]) == {"fixture"}
    assert set(plan["target_ids"]) == {
        "claude_user_skills",
        "agents_user_skills",
        "obsidian_snapshots",
    }
    assert len(plan["operations"]) == 3


def test_alias_targets_dedupe_physical_write_but_keep_logical_readbacks(
    repo_factory,
    tmp_path: Path,
) -> None:
    root, map_path, config_path, plan_path, _ = promotion_fixture(
        repo_factory, tmp_path, alias_skills=True
    )

    report = check_promotion(root, map_path, config_path, plan_path)

    assert report["verdict"] == "WARN"
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    skill_operation = next(
        operation
        for operation in plan["operations"]
        if "claude_user_skills" in operation["logical_target_ids"]
    )
    assert set(skill_operation["logical_target_ids"]) == set(REQUIRED_SKILL_TARGETS)
    assert len(plan["operations"]) == 2


def test_unrouted_source_artifact_fails_closed(repo_factory, tmp_path: Path) -> None:
    root, map_path, config_path, plan_path, _ = promotion_fixture(
        repo_factory, tmp_path
    )
    write_json(map_path, {"schema_version": 1, "artifacts": []})

    report = check_promotion(root, map_path, config_path, plan_path)

    assert "PROMOTION-UNROUTED" in codes(report)
    assert not plan_path.exists()


def test_domain_invariant_requires_both_skill_targets(
    repo_factory,
    tmp_path: Path,
) -> None:
    root, map_path, config_path, plan_path, _ = promotion_fixture(
        repo_factory, tmp_path
    )
    value = json.loads(map_path.read_text(encoding="utf-8"))
    value["artifacts"][0]["skill_target_ids"] = ["claude_user_skills"]
    write_json(map_path, value)

    report = check_promotion(root, map_path, config_path, plan_path)

    assert codes(report) == ["PROMOTION-ROUTING-INVALID"]
    assert not plan_path.exists()


def test_not_applicable_requires_reason(repo_factory, tmp_path: Path) -> None:
    root, map_path, config_path, plan_path, _ = promotion_fixture(
        repo_factory, tmp_path
    )
    value = json.loads(map_path.read_text(encoding="utf-8"))
    value["artifacts"][0]["applicability"] = "governance"
    value["artifacts"][0]["skill_target_ids"] = []
    write_json(map_path, value)

    report = check_promotion(root, map_path, config_path, plan_path)

    assert codes(report) == ["PROMOTION-NOT-APPLICABLE-INVALID"]


def test_readonly_or_missing_target_fails_before_staging(
    repo_factory,
    tmp_path: Path,
) -> None:
    root, map_path, config_path, plan_path, paths = promotion_fixture(
        repo_factory, tmp_path, writable=False
    )

    readonly = check_promotion(root, map_path, config_path, plan_path)

    assert "PROMOTION-TARGET-READONLY" in codes(readonly)
    config = json.loads(config_path.read_text(encoding="utf-8"))
    for target in config["targets"].values():
        target["writable"] = True
    config["targets"]["agents_user_skills"]["path"] = str(
        paths["targets"] / "missing"
    )
    write_json(config_path, config)

    missing = check_promotion(root, map_path, config_path, plan_path)

    assert "PROMOTION-TARGET-MISSING" in codes(missing)


def test_escape_and_forbidden_target_fail_closed(repo_factory, tmp_path: Path) -> None:
    root, map_path, config_path, plan_path, paths = promotion_fixture(
        repo_factory, tmp_path
    )
    config = json.loads(config_path.read_text(encoding="utf-8"))
    outside = tmp_path / "outside"
    outside.mkdir()
    config["targets"]["agents_user_skills"]["path"] = str(outside)
    write_json(config_path, config)

    escaped = check_promotion(root, map_path, config_path, plan_path)

    assert "PROMOTION-TARGET-ESCAPE" in codes(escaped)
    plugin = paths["targets"] / "plugins"
    plugin.mkdir()
    config["targets"]["agents_user_skills"]["path"] = str(plugin)
    write_json(config_path, config)

    forbidden = check_promotion(root, map_path, config_path, plan_path)

    assert "PROMOTION-TARGET-FORBIDDEN" in codes(forbidden)


def test_compare_and_swap_rejects_target_change_without_writes(
    repo_factory,
    tmp_path: Path,
) -> None:
    root, map_path, config_path, plan_path, paths = promotion_fixture(
        repo_factory, tmp_path
    )
    check_promotion(root, map_path, config_path, plan_path)
    changed = paths["claude"] / "demo"
    changed.mkdir()
    (changed / "foreign.txt").write_text("changed\n", encoding="utf-8")
    before = tree_digest(changed)

    report = apply_promotion(plan_path)

    assert codes(report) == ["PROMOTION-TARGET-CHANGED"]
    assert tree_digest(changed) == before
    assert not (paths["agents"] / "demo").exists()


def test_apply_writes_all_targets_and_receipt_without_physical_paths(
    repo_factory,
    tmp_path: Path,
) -> None:
    root, map_path, config_path, plan_path, paths = promotion_fixture(
        repo_factory, tmp_path
    )
    check_promotion(root, map_path, config_path, plan_path)

    report = apply_promotion(plan_path)

    assert report["verdict"] == "PASS"
    commit = run_git(root, "rev-parse", "HEAD")
    source_digest = tree_digest(root / "skills/demo")
    assert tree_digest(paths["claude"] / "demo") == source_digest
    assert tree_digest(paths["agents"] / "demo") == source_digest
    assert tree_digest(paths["vault"] / "fixture" / commit) == source_digest
    receipt_path = Path(str(report["artifacts"]["receipt_path"]))
    receipt_text = receipt_path.read_text(encoding="utf-8")
    assert str(tmp_path) not in receipt_text
    receipt = json.loads(receipt_text)
    assert receipt["verdict"] == "PASS"
    assert set(receipt["target_ids"]) == {
        "claude_user_skills",
        "agents_user_skills",
        "obsidian_snapshots",
    }


@pytest.mark.parametrize(
    "fault_at",
    [
        "after_staging:0",
        "after_backup:0",
        "after_replace:0",
        "after_readback:0",
    ],
)
def test_fault_injection_restores_every_touched_target(
    repo_factory,
    tmp_path: Path,
    fault_at: str,
) -> None:
    root, map_path, config_path, plan_path, paths = promotion_fixture(
        repo_factory, tmp_path
    )
    existing = paths["claude"] / "demo"
    existing.mkdir()
    (existing / "old.txt").write_text("original\n", encoding="utf-8")
    existing_agents = paths["agents"] / "demo"
    existing_agents.mkdir()
    (existing_agents / "old.txt").write_text("original\n", encoding="utf-8")
    check_promotion(root, map_path, config_path, plan_path)
    before = tree_digest(existing)

    report = apply_promotion(plan_path, fault_at=fault_at)

    assert "PROMOTION-APPLY-FAILED" in codes(report)
    assert tree_digest(existing) == before
    assert tree_digest(existing_agents) == before
    assert not report["artifacts"].get("receipt_path")
    residue = [
        path
        for path in paths["targets"].rglob("*")
        if ".packctl-stage-" in path.name or ".packctl-old-" in path.name
    ]
    assert residue == []


def test_failed_rollback_requires_intervention_exit_2(
    repo_factory,
    tmp_path: Path,
) -> None:
    root, map_path, config_path, plan_path, _ = promotion_fixture(
        repo_factory, tmp_path
    )
    check_promotion(root, map_path, config_path, plan_path)

    report = apply_promotion(
        plan_path,
        fault_at="after_replace:0",
        rollback_fault=True,
    )

    assert "PROMOTION-ROLLBACK-FAILED" in codes(report)
    assert report["artifacts"]["requires_intervention"] is True
    assert report["artifacts"]["exit_code"] == 2


def test_legacy_skill_overlap_blocks_apply(repo_factory, tmp_path: Path) -> None:
    root, map_path, config_path, plan_path, paths = promotion_fixture(
        repo_factory, tmp_path
    )
    legacy = paths["claude"] / "legacy-demo"
    legacy.mkdir()
    (legacy / "SKILL.md").write_text(
        "---\nname: demo\ndescription: Old duplicate.\n---\n",
        encoding="utf-8",
    )

    report = check_promotion(root, map_path, config_path, plan_path)

    assert "PROMOTION-LEGACY-OVERLAP" in codes(report)
    assert not plan_path.exists()


def test_vault_snapshot_preserves_private_note(repo_factory, tmp_path: Path) -> None:
    root, map_path, config_path, plan_path, paths = promotion_fixture(
        repo_factory, tmp_path
    )
    private = paths["vault"] / "private-note.md"
    private.write_text("private durable context\n", encoding="utf-8")
    before = private.read_bytes()
    check_promotion(root, map_path, config_path, plan_path)

    apply_promotion(plan_path)

    assert private.read_bytes() == before
