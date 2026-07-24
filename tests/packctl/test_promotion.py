from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from conftest import run_git, write_json

import packctl.common as common
from packctl.common import canonical_json_bytes, sha256_bytes, tree_digest
from packctl.promotion import apply_promotion, check_promotion
import packctl.promotion as promotion


REQUIRED_SKILL_TARGETS = ["claude_user_skills", "agents_user_skills"]


def run_promote_process(
    cwd: Path,
    *args: str,
    environment: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    process_environment = dict(os.environ)
    project_root = str(Path(__file__).resolve().parents[2])
    process_environment["PYTHONPATH"] = (
        project_root
        + os.pathsep
        + process_environment.get("PYTHONPATH", "")
    )
    process_environment.update(environment or {})
    return subprocess.run(
        [sys.executable, "-m", "packctl", "promote", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=process_environment,
    )


def transaction_root(plan: dict[str, object]) -> Path:
    return Path(str(plan["backup_root"])) / str(plan["transaction_id"])


def journal_events(root: Path) -> list[dict[str, object]]:
    return [
        json.loads(path.read_text(encoding="utf-8"))
        for path in sorted((root / "events").glob("*.json"))
    ]


def assert_valid_event_chain(root: Path) -> list[dict[str, object]]:
    events = journal_events(root)
    assert events
    previous_hash = "0" * 64
    for sequence, event in enumerate(events):
        event_path = root / "events" / f"{sequence:08d}.json"
        assert event_path.is_file()
        assert event["schema_version"] == 1
        assert event["sequence"] == sequence
        assert event["transaction_id"] == root.name
        assert event["previous_event_hash"] == previous_hash
        material = dict(event)
        event_hash = str(material.pop("event_hash"))
        assert event_hash == sha256_bytes(canonical_json_bytes(material))
        previous_hash = event_hash
    return events


def seed_every_target_with_pre_state(
    root: Path,
    paths: dict[str, Path],
) -> None:
    commit = run_git(root, "rev-parse", "HEAD")
    targets = [
        paths["claude"] / "demo",
        paths["agents"] / "demo",
        paths["vault"] / "fixture" / commit,
        paths["vault"] / "fixture-root" / commit,
    ]
    for index, target in enumerate(dict.fromkeys(targets)):
        target.mkdir(parents=True, exist_ok=True)
        (target / "pre.txt").write_text(
            f"pre-{index}\n",
            encoding="utf-8",
        )


def assert_plan_state(
    plan: dict[str, object],
    *,
    state: str,
) -> None:
    digest_key = "before_digest" if state == "PRE" else "after_digest"
    for operation in plan["operations"]:
        target = Path(str(operation["target_path"]))
        assert tree_digest(target) == operation[digest_key]
        for logical_path in operation["logical_target_paths"].values():
            logical = Path(str(logical_path))
            assert (
                os.path.normcase(str(logical.resolve(strict=False)))
                == os.path.normcase(str(target.resolve(strict=False)))
            )
            assert tree_digest(logical) == operation[digest_key]


def start_lock_holder(lock_path: Path) -> subprocess.Popen[str]:
    script = r"""
import os
import sys

path = sys.argv[1]
fd = os.open(path, os.O_RDWR | os.O_CREAT)
if os.fstat(fd).st_size == 0:
    os.write(fd, b"\0")
    os.fsync(fd)
os.lseek(fd, 0, os.SEEK_SET)
if os.name == "nt":
    import msvcrt
    msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
else:
    import fcntl
    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
sys.stdout.write("ready\n")
sys.stdout.flush()
sys.stdin.readline()
"""
    holder = subprocess.Popen(
        [sys.executable, "-c", script, str(lock_path)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
    )
    assert holder.stdout is not None
    assert holder.stdout.readline().strip() == "ready"
    return holder


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
    source_map_path = root / "sources/source-map.json"
    source_map = json.loads(source_map_path.read_text(encoding="utf-8"))
    for item in source_map["artifacts"]:
        item["routing_artifact_id"] = (
            "fixture"
            if str(item["output_path"]).startswith("skills/demo/")
            else "fixture-root"
        )
    write_json(source_map_path, source_map)
    run_git(root, "add", "sources/source-map.json")
    run_git(root, "commit", "-qm", "route fixture artifacts")

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
            },
            {
                "artifact_id": "fixture-root",
                "repo_path": ".",
                "artifact_kind": "tree",
                "applicability": "governance",
                "vault_targets": ["obsidian_snapshots"],
                "skill_target_ids": [],
                "not_applicable_reason": (
                    "Fixture repository contract is durable vault context, "
                    "not an installed skill."
                ),
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
    assert set(plan["artifact_ids"]) == {"fixture", "fixture-root"}
    assert set(plan["target_ids"]) == {
        "claude_user_skills",
        "agents_user_skills",
        "obsidian_snapshots",
    }
    assert len(plan["operations"]) == 4
    assert plan["plan_digest"]
    assert plan["promotion_map_hash"]
    assert plan["local_targets_hash"]


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
    assert len(plan["operations"]) == 3


def test_unrouted_source_artifact_fails_closed(repo_factory, tmp_path: Path) -> None:
    root, map_path, config_path, plan_path, _ = promotion_fixture(
        repo_factory, tmp_path
    )
    write_json(map_path, {"schema_version": 1, "artifacts": []})

    report = check_promotion(root, map_path, config_path, plan_path)

    assert "PROMOTION-UNROUTED" in codes(report)
    assert not plan_path.exists()


def test_routing_id_must_cover_each_source_map_output(
    repo_factory,
    tmp_path: Path,
) -> None:
    root, map_path, config_path, plan_path, _ = promotion_fixture(
        repo_factory, tmp_path
    )
    source_map_path = root / "sources/source-map.json"
    value = json.loads(source_map_path.read_text(encoding="utf-8"))
    readme = next(
        item for item in value["artifacts"] if item["output_path"] == "README.md"
    )
    readme["routing_artifact_id"] = "fixture"
    write_json(source_map_path, value)
    run_git(root, "add", "sources/source-map.json")
    run_git(root, "commit", "-qm", "misroute fixture artifact")

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


@pytest.mark.parametrize(
    ("location", "expected_code"),
    [
        ("outside", "PROMOTION-BACKUP-ESCAPE"),
        ("forbidden", "PROMOTION-BACKUP-FORBIDDEN"),
    ],
)
def test_backup_root_must_be_allowlisted_and_not_forbidden(
    repo_factory,
    tmp_path: Path,
    location: str,
    expected_code: str,
) -> None:
    root, map_path, config_path, plan_path, paths = promotion_fixture(
        repo_factory, tmp_path
    )
    backup_root = (
        tmp_path / "outside-backups"
        if location == "outside"
        else paths["targets"] / "plugins" / "backups"
    )
    backup_root.mkdir(parents=True)
    config = json.loads(config_path.read_text(encoding="utf-8"))
    config["backup_root"] = str(backup_root)
    write_json(config_path, config)

    report = check_promotion(root, map_path, config_path, plan_path)

    assert expected_code in codes(report)
    assert not plan_path.exists()


def test_apply_rejects_tampered_plan_before_any_write(
    repo_factory,
    tmp_path: Path,
) -> None:
    root, map_path, config_path, plan_path, paths = promotion_fixture(
        repo_factory, tmp_path
    )
    check_promotion(root, map_path, config_path, plan_path)
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    plan["operations"][0]["after_digest"] = "0" * 64
    write_json(plan_path, plan)

    report = apply_promotion(plan_path)

    assert codes(report) == ["PROMOTION-PLAN-TAMPERED"]
    assert not (paths["claude"] / "demo").exists()
    assert not (paths["agents"] / "demo").exists()


@pytest.mark.parametrize("contract", ["promotion_map", "local_targets"])
def test_apply_rejects_contract_change_after_check(
    repo_factory,
    tmp_path: Path,
    contract: str,
) -> None:
    root, map_path, config_path, plan_path, paths = promotion_fixture(
        repo_factory, tmp_path
    )
    check_promotion(root, map_path, config_path, plan_path)
    changed_path = map_path if contract == "promotion_map" else config_path
    changed_path.write_text(
        changed_path.read_text(encoding="utf-8") + "\n",
        encoding="utf-8",
        newline="\n",
    )

    report = apply_promotion(plan_path)

    assert codes(report) == ["PROMOTION-CONTRACT-CHANGED"]
    assert not (paths["claude"] / "demo").exists()


def test_tree_promotion_copies_only_tracked_projection(
    repo_factory,
    tmp_path: Path,
) -> None:
    root, map_path, config_path, plan_path, paths = promotion_fixture(
        repo_factory, tmp_path
    )
    ignored = root / "skills/demo/local-secret.txt"
    ignored.write_text("must not leave source tree\n", encoding="utf-8")
    (root / ".git/info/exclude").write_text(
        "skills/demo/local-secret.txt\n",
        encoding="utf-8",
        newline="\n",
    )

    check_report = check_promotion(root, map_path, config_path, plan_path)
    assert check_report["verdict"] == "WARN"
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    skill_operation = next(
        item
        for item in plan["operations"]
        if item["artifact_id"] == "fixture" and item["target_role"] == "skill"
    )
    assert skill_operation["source_files"] == ["SKILL.md"]

    report = apply_promotion(plan_path)

    assert report["verdict"] == "PASS"
    assert not (paths["claude"] / "demo/local-secret.txt").exists()
    assert not (
        paths["vault"]
        / "fixture"
        / run_git(root, "rev-parse", "HEAD")
        / "local-secret.txt"
    ).exists()


def test_tree_promotion_uses_consistent_order_for_mixed_case_projection(
    repo_factory,
    tmp_path: Path,
) -> None:
    root, map_path, config_path, plan_path, paths = promotion_fixture(
        repo_factory, tmp_path
    )
    reference = root / "skills/demo/references/detail.md"
    reference.parent.mkdir()
    reference.write_text("reference\n", encoding="utf-8", newline="\n")
    run_git(root, "add", "skills/demo/references/detail.md")
    run_git(root, "commit", "-qm", "add mixed-case projection fixture")

    check_report = check_promotion(root, map_path, config_path, plan_path)
    assert check_report["verdict"] == "WARN"
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    skill_operation = next(
        item
        for item in plan["operations"]
        if item["artifact_id"] == "fixture" and item["target_role"] == "skill"
    )
    assert skill_operation["source_files"] == [
        "SKILL.md",
        "references/detail.md",
    ]
    assert tree_digest(root / "skills/demo") == skill_operation["after_digest"]

    report = apply_promotion(plan_path)

    assert report["verdict"] == "PASS"
    assert tree_digest(paths["claude"] / "demo") == skill_operation["after_digest"]


def test_file_promotion_hashes_content_independently_of_snapshot_name(
    repo_factory,
    tmp_path: Path,
) -> None:
    root, map_path, config_path, plan_path, paths = promotion_fixture(
        repo_factory, tmp_path
    )
    source_map_path = root / "sources/source-map.json"
    source_map = json.loads(source_map_path.read_text(encoding="utf-8"))
    readme_artifact = next(
        item
        for item in source_map["artifacts"]
        if item["output_path"] == "README.md"
    )
    readme_artifact["routing_artifact_id"] = "fixture-file"
    write_json(source_map_path, source_map)
    run_git(root, "add", "sources/source-map.json")
    run_git(root, "commit", "-qm", "route file fixture")
    promotion_map = json.loads(map_path.read_text(encoding="utf-8"))
    promotion_map["artifacts"].append(
        {
            "artifact_id": "fixture-file",
            "repo_path": "README.md",
            "artifact_kind": "file",
            "applicability": "governance",
            "vault_targets": ["obsidian_snapshots"],
            "skill_target_ids": [],
            "not_applicable_reason": (
                "Fixture file is durable vault context, not a skill."
            ),
        }
    )
    write_json(map_path, promotion_map)
    check = check_promotion(root, map_path, config_path, plan_path)
    assert check["verdict"] == "WARN"
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    file_operation = next(
        operation
        for operation in plan["operations"]
        if operation["artifact_id"] == "fixture-file"
    )

    report = apply_promotion(plan_path)

    target = Path(str(file_operation["target_path"]))
    assert report["verdict"] == "PASS"
    assert target.read_bytes() == (root / "README.md").read_bytes()
    assert target == (
        paths["vault"]
        / "fixture-file"
        / run_git(root, "rev-parse", "HEAD")
    )


@pytest.mark.parametrize("residue_kind", ["stage", "old"])
def test_apply_rejects_preexisting_residue_without_deleting_it(
    repo_factory,
    tmp_path: Path,
    residue_kind: str,
) -> None:
    root, map_path, config_path, plan_path, _ = promotion_fixture(
        repo_factory, tmp_path
    )
    check_promotion(root, map_path, config_path, plan_path)
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    operation = plan["operations"][0]
    target = Path(operation["target_path"])
    residue = target.parent / (
        f".{target.name}.packctl-{residue_kind}-{plan['transaction_id']}"
    )
    residue.mkdir(parents=True)
    sentinel = residue / "foreign.txt"
    sentinel.write_text("do not delete\n", encoding="utf-8")

    report = apply_promotion(plan_path)

    assert "PROMOTION-APPLY-FAILED" in codes(report)
    assert sentinel.read_text(encoding="utf-8") == "do not delete\n"


def test_partial_stage_from_failed_copy_is_removed(
    repo_factory,
    tmp_path: Path,
    monkeypatch,
) -> None:
    root, map_path, config_path, plan_path, _ = promotion_fixture(
        repo_factory, tmp_path
    )
    check_promotion(root, map_path, config_path, plan_path)
    created_stage: Path | None = None

    def fail_after_partial_copy(source, destination, kind, source_files=None):
        nonlocal created_stage
        created_stage = Path(destination)
        created_stage.mkdir(parents=True)
        (created_stage / "partial.txt").write_text(
            "partial\n", encoding="utf-8"
        )
        raise OSError("copy fault")

    monkeypatch.setattr("packctl.promotion._copy_artifact", fail_after_partial_copy)

    report = apply_promotion(plan_path)

    assert "PROMOTION-APPLY-FAILED" in codes(report)
    assert created_stage is not None
    assert not created_stage.exists()


def test_stale_lock_file_does_not_block_apply(
    repo_factory,
    tmp_path: Path,
) -> None:
    root, map_path, config_path, plan_path, paths = promotion_fixture(
        repo_factory, tmp_path
    )
    check_promotion(root, map_path, config_path, plan_path)
    lock = promotion._lock_path_for_root(paths["targets"])
    lock.write_text("stale metadata\n", encoding="utf-8")

    report = apply_promotion(plan_path)

    assert report["verdict"] == "PASS"
    assert lock.exists()
    assert (paths["claude"] / "demo/SKILL.md").is_file()


def test_root_lock_sidecar_does_not_modify_an_exact_target(
    tmp_path: Path,
) -> None:
    target = tmp_path / "exact-target"
    target.mkdir()
    (target / "content.txt").write_text("stable\n", encoding="utf-8")
    before = tree_digest(target)

    with promotion._RootLocks([target]):
        assert tree_digest(target) == before
        assert not (target / ".packctl.lock").exists()
        assert (tmp_path / ".exact-target.packctl.lock").is_file()

    assert tree_digest(target) == before


@pytest.mark.skipif(os.name != "nt", reason="Windows rename retry contract")
def test_windows_durable_rename_retries_transient_delete_denial(
    monkeypatch,
    tmp_path: Path,
) -> None:
    source = tmp_path / "source"
    source.mkdir()
    (source / "payload.txt").write_text("payload\n", encoding="utf-8")
    destination = tmp_path / "destination"
    outcomes = [
        (False, 5, "Access is denied."),
        (False, 32, "The process cannot access the file."),
        (True, 0, ""),
    ]
    calls: list[tuple[Path, Path, int]] = []
    delays: list[float] = []

    def fake_move(
        candidate_source: Path,
        candidate_destination: Path,
        flags: int,
    ) -> tuple[bool, int, str]:
        calls.append((candidate_source, candidate_destination, flags))
        outcome = outcomes.pop(0)
        if outcome[0]:
            candidate_source.rename(candidate_destination)
        return outcome

    monkeypatch.setattr(
        common,
        "_windows_move_file_ex",
        fake_move,
    )
    monkeypatch.setattr(
        common,
        "_sleep_before_windows_rename_retry",
        delays.append,
    )

    common.durable_rename(source, destination, replace=False)

    assert destination.joinpath("payload.txt").read_text(encoding="utf-8") == (
        "payload\n"
    )
    assert [call[2] for call in calls] == [0x00000008] * 3
    assert delays == [0.05, 0.1]


@pytest.mark.skipif(os.name != "nt", reason="Windows rename retry contract")
def test_windows_durable_rename_does_not_retry_ambiguous_state(
    monkeypatch,
    tmp_path: Path,
) -> None:
    source = tmp_path / "source"
    source.mkdir()
    (source / "payload.txt").write_text("payload\n", encoding="utf-8")
    destination = tmp_path / "destination"
    calls = 0
    delays: list[float] = []

    def ambiguous_move(
        candidate_source: Path,
        candidate_destination: Path,
        flags: int,
    ) -> tuple[bool, int, str]:
        nonlocal calls
        calls += 1
        candidate_source.rename(candidate_destination)
        return False, 5, "Access is denied."

    monkeypatch.setattr(
        common,
        "_windows_move_file_ex",
        ambiguous_move,
    )
    monkeypatch.setattr(
        common,
        "_sleep_before_windows_rename_retry",
        delays.append,
    )

    with pytest.raises(PermissionError) as captured:
        common.durable_rename(source, destination, replace=False)

    assert captured.value.winerror == 5
    assert calls == 1
    assert delays == []
    assert destination.joinpath("payload.txt").is_file()


def test_live_os_lock_blocks_apply_with_exit_2(
    repo_factory,
    tmp_path: Path,
) -> None:
    root, map_path, config_path, plan_path, paths = promotion_fixture(
        repo_factory, tmp_path
    )
    check_promotion(root, map_path, config_path, plan_path)
    lock = promotion._lock_path_for_root(paths["targets"])
    holder = start_lock_holder(lock)
    try:
        report = apply_promotion(plan_path)
    finally:
        assert holder.stdin is not None
        holder.stdin.write("\n")
        holder.stdin.flush()
        holder.wait(timeout=10)

    assert "PROMOTION-LOCK-ACTIVE" in codes(report)
    assert report["artifacts"]["requires_intervention"] is True
    assert report["artifacts"]["exit_code"] == 2
    assert not (paths["claude"] / "demo").exists()


@pytest.mark.parametrize(
    "state",
    ["starting", "replacing", "readback-complete", "rollback-failed", "complete"],
)
def test_unverifiable_journal_blocks_apply_with_exit_2(
    repo_factory,
    tmp_path: Path,
    state: str,
) -> None:
    root, map_path, config_path, plan_path, paths = promotion_fixture(
        repo_factory, tmp_path
    )
    check_promotion(root, map_path, config_path, plan_path)
    prior_id = "a" * 24
    prior_root = paths["backups"] / prior_id
    prior_root.mkdir()
    write_json(
        prior_root / "journal.json",
        {
            "schema_version": 1,
            "transaction_id": prior_id,
            "source_commit": "0" * 40,
            "state": state,
            "touched_aliases": [],
            "rollback_errors": (
                ["physical-0001:OSError"]
                if state == "rollback-failed"
                else []
            ),
        },
    )

    report = apply_promotion(plan_path)

    assert "PROMOTION-RECOVERY-REQUIRED" in codes(report)
    assert report["artifacts"]["requires_intervention"] is True
    assert report["artifacts"]["exit_code"] == 2
    assert not (paths["claude"] / "demo").exists()


def test_legacy_mutable_journal_does_not_count_as_terminal_evidence(
    repo_factory,
    tmp_path: Path,
) -> None:
    root, map_path, config_path, plan_path, paths = promotion_fixture(
        repo_factory, tmp_path
    )
    check_promotion(root, map_path, config_path, plan_path)
    prior_id = "b" * 24
    prior_root = paths["backups"] / prior_id
    prior_root.mkdir()
    write_json(
        prior_root / "journal.json",
        {
            "schema_version": 1,
            "transaction_id": prior_id,
            "source_commit": "0" * 40,
            "state": "rolled-back",
            "touched_aliases": [],
            "rollback_errors": [],
        },
    )

    report = apply_promotion(plan_path)

    assert "PROMOTION-RECOVERY-REQUIRED" in codes(report)
    assert report["artifacts"]["exit_code"] == 2
    assert not (paths["claude"] / "demo/SKILL.md").exists()


def test_check_revalidates_destination_after_child_link_resolution(
    repo_factory,
    tmp_path: Path,
) -> None:
    root, map_path, config_path, plan_path, paths = promotion_fixture(
        repo_factory, tmp_path
    )
    forbidden = paths["targets"] / "plugins"
    forbidden.mkdir()
    linked = paths["agents"] / "demo"
    try:
        os.symlink(forbidden, linked, target_is_directory=True)
    except OSError as error:
        pytest.skip(f"directory symlink unavailable: {error}")

    report = check_promotion(root, map_path, config_path, plan_path)

    assert "PROMOTION-TARGET-FORBIDDEN" in codes(report)
    assert not plan_path.exists()


def test_apply_revalidates_every_logical_alias(
    repo_factory,
    tmp_path: Path,
) -> None:
    root, map_path, config_path, plan_path, paths = promotion_fixture(
        repo_factory, tmp_path
    )
    physical = paths["claude"] / "demo"
    physical.mkdir()
    (physical / "old.txt").write_text("old\n", encoding="utf-8")
    logical = paths["agents"] / "demo"
    try:
        os.symlink(physical, logical, target_is_directory=True)
    except OSError as error:
        pytest.skip(f"directory symlink unavailable: {error}")
    check_promotion(root, map_path, config_path, plan_path)
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    aliased = next(
        item
        for item in plan["operations"]
        if set(item["logical_target_ids"]) == set(REQUIRED_SKILL_TARGETS)
    )
    assert set(aliased["logical_target_paths"]) == set(REQUIRED_SKILL_TARGETS)

    logical.unlink()
    replacement = paths["targets"] / "replacement"
    replacement.mkdir()
    os.symlink(replacement, logical, target_is_directory=True)

    report = apply_promotion(plan_path)

    assert "PROMOTION-LOGICAL-TARGET-CHANGED" in codes(report)
    assert (physical / "old.txt").read_text(encoding="utf-8") == "old\n"


def test_idempotent_operation_is_read_back_without_replace(
    repo_factory,
    tmp_path: Path,
    monkeypatch,
) -> None:
    root, map_path, config_path, plan_path, paths = promotion_fixture(
        repo_factory, tmp_path
    )
    target = paths["claude"] / "demo"
    target.mkdir()
    (target / "SKILL.md").write_bytes((root / "skills/demo/SKILL.md").read_bytes())
    check_promotion(root, map_path, config_path, plan_path)
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    noop = next(
        item
        for item in plan["operations"]
        if item["target_path"] == str(target.resolve())
    )
    assert noop["before_digest"] == noop["after_digest"]
    original_copy = __import__("packctl.promotion", fromlist=["_copy_artifact"])._copy_artifact
    destinations: list[Path] = []

    def recording_copy(source, destination, kind, source_files=None):
        destinations.append(Path(destination))
        return original_copy(source, destination, kind, source_files)

    monkeypatch.setattr("packctl.promotion._copy_artifact", recording_copy)

    report = apply_promotion(plan_path)

    assert report["verdict"] == "PASS"
    assert not any(
        destination.parent == target.parent
        and f".{target.name}.packctl-stage-" in destination.name
        for destination in destinations
    )


def test_failure_after_moving_old_restores_original_target(
    repo_factory,
    tmp_path: Path,
) -> None:
    root, map_path, config_path, plan_path, paths = promotion_fixture(
        repo_factory, tmp_path
    )
    existing = paths["claude"] / "demo"
    existing.mkdir()
    (existing / "old.txt").write_text("original\n", encoding="utf-8")
    check_promotion(root, map_path, config_path, plan_path)
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    index = next(
        index
        for index, item in enumerate(plan["operations"])
        if item["target_path"] == str(existing.resolve())
    )
    before = tree_digest(existing)

    report = apply_promotion(plan_path, fault_at=f"after_old_move:{index}")

    assert "PROMOTION-APPLY-FAILED" in codes(report)
    assert tree_digest(existing) == before
    assert (existing / "old.txt").read_text(encoding="utf-8") == "original\n"


def test_apply_reports_winerror_without_physical_path(
    repo_factory,
    tmp_path: Path,
    monkeypatch,
) -> None:
    root, map_path, config_path, plan_path, paths = promotion_fixture(
        repo_factory, tmp_path
    )
    check_promotion(root, map_path, config_path, plan_path)
    blocked_target = paths["claude"] / "demo"
    original_rename = promotion.durable_rename
    failed = False

    def deny_publish_once(
        source: Path,
        destination: Path,
        *,
        replace: bool,
    ) -> None:
        nonlocal failed
        if (
            not failed
            and destination == blocked_target
            and ".packctl-stage-" in source.name
        ):
            failed = True
            raise OSError(
                None,
                "Access is denied.",
                str(destination),
                5,
            )
        original_rename(source, destination, replace=replace)

    monkeypatch.setattr(
        "packctl.promotion.durable_rename",
        deny_publish_once,
    )

    report = apply_promotion(plan_path)

    assert report["verdict"] == "FAIL"
    assert report["findings"][0]["evidence"] == "PermissionError:winerror=5"
    assert str(paths["targets"]) not in report["findings"][0]["evidence"]
    assert_plan_state(
        json.loads(plan_path.read_text(encoding="utf-8")),
        state="PRE",
    )


def test_receipt_is_not_published_when_commit_event_write_fails(
    repo_factory,
    tmp_path: Path,
    monkeypatch,
) -> None:
    root, map_path, config_path, plan_path, _ = promotion_fixture(
        repo_factory, tmp_path
    )
    check_promotion(root, map_path, config_path, plan_path)
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    original_append = promotion._append_event

    def fail_commit_event(
        transaction: Path,
        event_type: str,
        payload: dict[str, object],
    ) -> dict[str, object]:
        if event_type == "COMMIT":
            raise OSError("commit event fault")
        return original_append(transaction, event_type, payload)

    monkeypatch.setattr("packctl.promotion._append_event", fail_commit_event)

    report = apply_promotion(plan_path)

    assert "PROMOTION-APPLY-FAILED" in codes(report)
    assert not Path(plan["receipt_path"]).exists()


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


APPLY_TERMINATION_BOUNDARIES = (
    ["after_pending"]
    + [
        f"{boundary}:{index}"
        for boundary in (
            "after_stage",
            "after_backup",
            "after_old_move",
            "after_publish",
            "after_target_event",
        )
        for index in range(4)
    ]
    + ["after_post_verified", "after_commit"]
)


def test_apply_publishes_hash_chained_terminal_journal(
    repo_factory,
    tmp_path: Path,
) -> None:
    root, map_path, config_path, plan_path, _ = promotion_fixture(
        repo_factory, tmp_path
    )
    check_promotion(root, map_path, config_path, plan_path)
    plan = json.loads(plan_path.read_text(encoding="utf-8"))

    report = apply_promotion(plan_path)

    assert report["verdict"] == "PASS"
    transaction = transaction_root(plan)
    assert json.loads((transaction / "plan.json").read_text(encoding="utf-8")) == plan
    events = assert_valid_event_chain(transaction)
    assert events[0]["event_type"] == "PENDING"
    assert events[-2]["event_type"] == "POST_VERIFIED"
    assert events[-1]["event_type"] == "COMMIT"
    assert sum(event["event_type"] == "COMMIT" for event in events) == 1
    assert all(event["event_type"] != "ABORT" for event in events)


@pytest.mark.parametrize("boundary", APPLY_TERMINATION_BOUNDARIES)
def test_apply_process_termination_recovers_to_one_decided_state(
    repo_factory,
    tmp_path: Path,
    boundary: str,
) -> None:
    root, map_path, config_path, plan_path, paths = promotion_fixture(
        repo_factory, tmp_path
    )
    seed_every_target_with_pre_state(root, paths)
    check_promotion(root, map_path, config_path, plan_path)
    plan = json.loads(plan_path.read_text(encoding="utf-8"))

    killed = run_promote_process(
        root,
        "--apply",
        "--plan",
        str(plan_path),
        environment={"PACKCTL_TERMINATE_AT": boundary},
    )

    assert killed.returncode == 97
    transaction = transaction_root(plan)
    recovered = promotion.recover_promotion(transaction)
    assert recovered["verdict"] == "PASS"
    events = assert_valid_event_chain(transaction)
    receipt_path = Path(str(plan["receipt_path"]))
    if boundary == "after_commit":
        assert events[-1]["event_type"] == "COMMIT"
        assert_plan_state(plan, state="POST")
        assert receipt_path.is_file()
    else:
        assert events[-1]["event_type"] == "ABORT"
        assert_plan_state(plan, state="PRE")
        assert not receipt_path.exists()


@pytest.mark.parametrize(
    "boundary",
    [
        "after_recovery_stage:0",
        "after_recovery_old_move:0",
        "after_pre_publish:0",
        "after_pre_verified:0",
        "after_abort",
    ],
)
def test_recovery_process_termination_is_restartable(
    repo_factory,
    tmp_path: Path,
    boundary: str,
) -> None:
    root, map_path, config_path, plan_path, paths = promotion_fixture(
        repo_factory, tmp_path
    )
    seed_every_target_with_pre_state(root, paths)
    check_promotion(root, map_path, config_path, plan_path)
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    killed_apply = run_promote_process(
        root,
        "--apply",
        "--plan",
        str(plan_path),
        environment={"PACKCTL_TERMINATE_AT": "after_publish:0"},
    )
    assert killed_apply.returncode == 97
    transaction = transaction_root(plan)

    killed_recovery = run_promote_process(
        root,
        "--recover",
        "--transaction-root",
        str(transaction),
        environment={"PACKCTL_RECOVER_TERMINATE_AT": boundary},
    )
    assert killed_recovery.returncode == 97

    recovered = run_promote_process(
        root,
        "--recover",
        "--transaction-root",
        str(transaction),
    )
    assert recovered.returncode == 0, recovered.stderr
    events = assert_valid_event_chain(transaction)
    assert events[-1]["event_type"] == "ABORT"
    assert_plan_state(plan, state="PRE")
    assert not Path(str(plan["receipt_path"])).exists()


@pytest.mark.parametrize(
    "mutation",
    ["payload", "truncate", "sequence", "plan"],
)
def test_recovery_rejects_corrupt_authoritative_evidence_without_target_writes(
    repo_factory,
    tmp_path: Path,
    mutation: str,
) -> None:
    root, map_path, config_path, plan_path, paths = promotion_fixture(
        repo_factory, tmp_path
    )
    seed_every_target_with_pre_state(root, paths)
    check_promotion(root, map_path, config_path, plan_path)
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    killed = run_promote_process(
        root,
        "--apply",
        "--plan",
        str(plan_path),
        environment={"PACKCTL_TERMINATE_AT": "after_pending"},
    )
    assert killed.returncode == 97
    transaction = transaction_root(plan)
    before = {
        str(operation["target_path"]): tree_digest(
            Path(str(operation["target_path"]))
        )
        for operation in plan["operations"]
    }
    first_event = transaction / "events/00000000.json"
    if mutation == "payload":
        event = json.loads(first_event.read_text(encoding="utf-8"))
        event["payload"] = {"tampered": True}
        write_json(first_event, event)
    elif mutation == "truncate":
        first_event.write_text("{", encoding="utf-8")
    elif mutation == "sequence":
        first_event.rename(transaction / "events/00000001.json")
    else:
        sealed_plan = json.loads(
            (transaction / "plan.json").read_text(encoding="utf-8")
        )
        sealed_plan["source_commit"] = "0" * 40
        write_json(transaction / "plan.json", sealed_plan)

    report = promotion.recover_promotion(transaction)

    assert report["verdict"] == "FAIL"
    assert report["artifacts"]["exit_code"] == 2
    assert "PROMOTION-JOURNAL-INVALID" in codes(report)
    assert {
        path: tree_digest(Path(path))
        for path in before
    } == before


def test_recovery_rejects_foreign_target_digest_without_deleting_it(
    repo_factory,
    tmp_path: Path,
) -> None:
    root, map_path, config_path, plan_path, paths = promotion_fixture(
        repo_factory, tmp_path
    )
    seed_every_target_with_pre_state(root, paths)
    check_promotion(root, map_path, config_path, plan_path)
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    killed = run_promote_process(
        root,
        "--apply",
        "--plan",
        str(plan_path),
        environment={"PACKCTL_TERMINATE_AT": "after_publish:0"},
    )
    assert killed.returncode == 97
    target = Path(str(plan["operations"][0]["target_path"]))
    sentinel = target / "foreign-after-crash.txt"
    sentinel.write_text("operator data\n", encoding="utf-8")
    foreign_digest = tree_digest(target)

    report = promotion.recover_promotion(transaction_root(plan))

    assert report["verdict"] == "FAIL"
    assert report["artifacts"]["exit_code"] == 2
    assert "PROMOTION-FOREIGN-TARGET" in codes(report)
    assert tree_digest(target) == foreign_digest
    assert sentinel.read_text(encoding="utf-8") == "operator data\n"


def test_commit_recovery_refuses_to_overwrite_foreign_receipt(
    repo_factory,
    tmp_path: Path,
) -> None:
    root, map_path, config_path, plan_path, _ = promotion_fixture(
        repo_factory, tmp_path
    )
    check_promotion(root, map_path, config_path, plan_path)
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    killed = run_promote_process(
        root,
        "--apply",
        "--plan",
        str(plan_path),
        environment={"PACKCTL_TERMINATE_AT": "after_commit"},
    )
    assert killed.returncode == 97
    receipt_path = Path(str(plan["receipt_path"]))
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    foreign = b'{"foreign":true}\n'
    receipt_path.write_bytes(foreign)

    report = promotion.recover_promotion(transaction_root(plan))

    assert report["verdict"] == "FAIL"
    assert report["artifacts"]["exit_code"] == 2
    assert "PROMOTION-RECEIPT-CONFLICT" in codes(report)
    assert receipt_path.read_bytes() == foreign


@pytest.mark.parametrize(
    ("termination_boundary", "terminal", "state"),
    [
        ("after_publish:0", "ABORT", "PRE"),
        ("after_commit", "COMMIT", "POST"),
    ],
)
def test_recovery_is_idempotent_after_terminal_decision(
    repo_factory,
    tmp_path: Path,
    termination_boundary: str,
    terminal: str,
    state: str,
) -> None:
    root, map_path, config_path, plan_path, paths = promotion_fixture(
        repo_factory, tmp_path
    )
    seed_every_target_with_pre_state(root, paths)
    check_promotion(root, map_path, config_path, plan_path)
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    killed = run_promote_process(
        root,
        "--apply",
        "--plan",
        str(plan_path),
        environment={"PACKCTL_TERMINATE_AT": termination_boundary},
    )
    assert killed.returncode == 97
    transaction = transaction_root(plan)

    first = promotion.recover_promotion(transaction)
    event_bytes = {
        path.name: path.read_bytes()
        for path in (transaction / "events").glob("*.json")
    }
    second = promotion.recover_promotion(transaction)

    assert first["verdict"] == second["verdict"] == "PASS"
    assert {
        path.name: path.read_bytes()
        for path in (transaction / "events").glob("*.json")
    } == event_bytes
    assert assert_valid_event_chain(transaction)[-1]["event_type"] == terminal
    assert_plan_state(plan, state=state)


def test_commit_seals_exact_create_only_receipt_hash(
    repo_factory,
    tmp_path: Path,
) -> None:
    root, map_path, config_path, plan_path, _ = promotion_fixture(
        repo_factory, tmp_path
    )
    check_promotion(root, map_path, config_path, plan_path)
    plan = json.loads(plan_path.read_text(encoding="utf-8"))

    report = apply_promotion(plan_path)

    assert report["verdict"] == "PASS"
    events = assert_valid_event_chain(transaction_root(plan))
    commit = events[-1]
    receipt_path = Path(str(plan["receipt_path"]))
    receipt_bytes = receipt_path.read_bytes()
    assert commit["payload"]["receipt_hash"] == sha256_bytes(receipt_bytes)
    assert str(tmp_path).encode("utf-8") not in receipt_bytes


def test_apply_refuses_mixed_pending_transaction_until_recovery(
    repo_factory,
    tmp_path: Path,
) -> None:
    root, map_path, config_path, plan_path, paths = promotion_fixture(
        repo_factory, tmp_path
    )
    seed_every_target_with_pre_state(root, paths)
    check_promotion(root, map_path, config_path, plan_path)
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    killed = run_promote_process(
        root,
        "--apply",
        "--plan",
        str(plan_path),
        environment={"PACKCTL_TERMINATE_AT": "after_publish:0"},
    )
    assert killed.returncode == 97
    mixed = {
        str(operation["target_path"]): tree_digest(
            Path(str(operation["target_path"]))
        )
        for operation in plan["operations"]
    }

    refused = run_promote_process(
        root,
        "--apply",
        "--plan",
        str(plan_path),
    )

    assert refused.returncode == 2
    report = json.loads(
        plan_path.with_suffix(".apply-report.json").read_text(
            encoding="utf-8"
        )
    )
    assert "PROMOTION-RECOVERY-REQUIRED" in codes(report)
    assert {
        path: tree_digest(Path(path))
        for path in mixed
    } == mixed


@pytest.mark.parametrize(
    ("termination_boundary", "terminal_code"),
    [
        ("after_commit", "PROMOTION-COMMIT-STATE-INVALID"),
        ("after_pending", "PROMOTION-ABORT-STATE-INVALID"),
    ],
)
def test_terminal_decision_rejects_later_target_mutation(
    repo_factory,
    tmp_path: Path,
    termination_boundary: str,
    terminal_code: str,
) -> None:
    root, map_path, config_path, plan_path, paths = promotion_fixture(
        repo_factory, tmp_path
    )
    seed_every_target_with_pre_state(root, paths)
    check_promotion(root, map_path, config_path, plan_path)
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    killed = run_promote_process(
        root,
        "--apply",
        "--plan",
        str(plan_path),
        environment={"PACKCTL_TERMINATE_AT": termination_boundary},
    )
    assert killed.returncode == 97
    transaction = transaction_root(plan)
    if termination_boundary == "after_pending":
        assert promotion.recover_promotion(transaction)["verdict"] == "PASS"
    target = Path(str(plan["operations"][0]["target_path"]))
    sentinel = target / "foreign-after-terminal.txt"
    sentinel.write_text("operator mutation\n", encoding="utf-8")
    foreign_digest = tree_digest(target)

    report = promotion.recover_promotion(transaction)

    assert report["verdict"] == "FAIL"
    assert report["artifacts"]["exit_code"] == 2
    assert terminal_code in codes(report)
    assert tree_digest(target) == foreign_digest
    assert sentinel.read_text(encoding="utf-8") == "operator mutation\n"


def test_three_sequential_commits_accept_superseded_terminal_history(
    repo_factory,
    tmp_path: Path,
) -> None:
    root, map_path, config_path, plan_path, paths = promotion_fixture(
        repo_factory, tmp_path
    )
    exclude = root / ".git/info/exclude"
    exclude.write_text(
        exclude.read_text(encoding="utf-8")
        + "\npromotions/receipts/\n",
        encoding="utf-8",
    )
    transaction_ids: list[str] = []
    for version in range(1, 4):
        skill = root / "skills/demo/SKILL.md"
        skill.write_text(
            "---\n"
            "name: demo\n"
            f"description: Promotion fixture v{version}.\n"
            "---\n"
            "# Demo\n",
            encoding="utf-8",
        )
        run_git(root, "add", "skills/demo/SKILL.md")
        run_git(root, "commit", "-qm", f"fixture v{version}")
        checked = check_promotion(
            root,
            map_path,
            config_path,
            plan_path,
        )
        assert checked["verdict"] in {"PASS", "WARN"}
        plan = json.loads(plan_path.read_text(encoding="utf-8"))
        transaction_ids.append(str(plan["transaction_id"]))

        applied = apply_promotion(plan_path)

        assert applied["verdict"] == "PASS"
        assert tree_digest(paths["claude"] / "demo") == tree_digest(
            root / "skills/demo"
        )
    assert len(set(transaction_ids)) == 3


def test_clean_abort_can_be_rechecked_and_retried_as_new_transaction(
    repo_factory,
    tmp_path: Path,
) -> None:
    root, map_path, config_path, plan_path, paths = promotion_fixture(
        repo_factory, tmp_path
    )
    check_promotion(root, map_path, config_path, plan_path)
    first_plan = json.loads(plan_path.read_text(encoding="utf-8"))
    failed = apply_promotion(plan_path, fault_at="after_stage:0")
    assert "PROMOTION-APPLY-FAILED" in codes(failed)
    assert assert_valid_event_chain(transaction_root(first_plan))[-1][
        "event_type"
    ] == "ABORT"

    check_promotion(root, map_path, config_path, plan_path)
    retry_plan = json.loads(plan_path.read_text(encoding="utf-8"))
    retried = apply_promotion(plan_path)

    assert retry_plan["transaction_id"] != first_plan["transaction_id"]
    assert retried["verdict"] == "PASS"
    assert (paths["claude"] / "demo/SKILL.md").is_file()


def test_cli_recovery_does_not_write_report_inside_invalid_transaction(
    repo_factory,
    tmp_path: Path,
) -> None:
    root, map_path, config_path, plan_path, _ = promotion_fixture(
        repo_factory, tmp_path
    )
    check_promotion(root, map_path, config_path, plan_path)
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    killed = run_promote_process(
        root,
        "--apply",
        "--plan",
        str(plan_path),
        environment={"PACKCTL_TERMINATE_AT": "after_pending"},
    )
    assert killed.returncode == 97
    transaction = transaction_root(plan)
    (transaction / "events/00000000.json").write_text(
        "{",
        encoding="utf-8",
    )

    recovered = run_promote_process(
        root,
        "--recover",
        "--transaction-root",
        str(transaction),
    )

    assert recovered.returncode == 2
    assert not (transaction / "recover-report.json").exists()


def test_failed_transaction_initialization_never_publishes_a_transaction(
    repo_factory,
    tmp_path: Path,
    monkeypatch,
) -> None:
    root, map_path, config_path, plan_path, paths = promotion_fixture(
        repo_factory, tmp_path
    )
    check_promotion(root, map_path, config_path, plan_path)
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    original_write = promotion.durable_write_json

    def fail_sealed_plan(
        path: Path,
        value: object,
        *,
        create_only: bool,
    ) -> bytes:
        if path.name == "plan.json":
            raise OSError("sealed plan fsync fault")
        return original_write(path, value, create_only=create_only)

    monkeypatch.setattr(
        "packctl.promotion.durable_write_json",
        fail_sealed_plan,
    )

    report = apply_promotion(plan_path)

    assert "PROMOTION-APPLY-FAILED" in codes(report)
    assert "exit_code" not in report["artifacts"]
    assert not transaction_root(plan).exists()
    assert not any(
        path.name.endswith(".packctl-init")
        for path in paths["backups"].iterdir()
    )
    assert not (paths["claude"] / "demo").exists()


def test_apply_revalidates_sealed_contracts_after_acquiring_os_locks(
    repo_factory,
    tmp_path: Path,
    monkeypatch,
) -> None:
    root, map_path, config_path, plan_path, paths = promotion_fixture(
        repo_factory, tmp_path
    )
    check_promotion(root, map_path, config_path, plan_path)
    original_enter = promotion._RootLocks.__enter__
    mutated = False

    def mutate_after_lock(self):
        nonlocal mutated
        result = original_enter(self)
        if not mutated:
            config = json.loads(config_path.read_text(encoding="utf-8"))
            config["targets"]["claude_user_skills"]["ownership"] = (
                "changed-after-preflight"
            )
            write_json(config_path, config)
            mutated = True
        return result

    monkeypatch.setattr(
        promotion._RootLocks,
        "__enter__",
        mutate_after_lock,
    )

    report = apply_promotion(plan_path)

    assert "PROMOTION-CONTRACT-CHANGED" in codes(report)
    assert not transaction_root(
        json.loads(plan_path.read_text(encoding="utf-8"))
    ).exists()
    assert not (paths["claude"] / "demo").exists()


def test_target_change_after_backup_is_preserved_before_old_move(
    repo_factory,
    tmp_path: Path,
    monkeypatch,
) -> None:
    root, map_path, config_path, plan_path, paths = promotion_fixture(
        repo_factory, tmp_path
    )
    seed_every_target_with_pre_state(root, paths)
    check_promotion(root, map_path, config_path, plan_path)
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    first_target = Path(str(plan["operations"][0]["target_path"]))
    sentinel = first_target / "external-after-backup.txt"
    original_append = promotion._append_event
    injected = False

    def mutate_after_backup(
        transaction: Path,
        event_type: str,
        payload: dict[str, object],
    ) -> dict[str, object]:
        nonlocal injected
        event = original_append(transaction, event_type, payload)
        if event_type == "BACKUP_READY" and not injected:
            sentinel.write_text("external mutation\n", encoding="utf-8")
            injected = True
        return event

    monkeypatch.setattr(
        "packctl.promotion._append_event",
        mutate_after_backup,
    )

    report = apply_promotion(plan_path)

    assert report["verdict"] == "FAIL"
    assert report["artifacts"]["exit_code"] == 2
    assert sentinel.read_text(encoding="utf-8") == "external mutation\n"
