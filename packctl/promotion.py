from __future__ import annotations

import json
import os
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from .common import (
    canonical_json_bytes,
    finding,
    git_commit,
    git_is_dirty,
    git_tracked_files,
    is_relative_contract_path,
    is_within,
    load_json,
    make_report,
    sha256_bytes,
    sha256_file,
    sort_findings,
    tree_digest,
    write_json,
)
from .validation import SOURCE_MAP_PATH


REQUIRED_SKILL_TARGETS = {"claude_user_skills", "agents_user_skills"}


def _route_contains(repo_path: str, kind: object, output_path: str) -> bool:
    if kind == "file":
        return output_path == repo_path
    if kind != "tree":
        return False
    if repo_path == ".":
        return True
    prefix = repo_path.rstrip("/") + "/"
    return output_path == repo_path or output_path.startswith(prefix)


def _tracked_projection(root: Path, repo_path: str, kind: object) -> list[str]:
    tracked = git_tracked_files(root)
    if kind == "file":
        return [Path(repo_path).name] if repo_path in tracked else []
    prefix = "" if repo_path == "." else repo_path.rstrip("/") + "/"
    return [
        relative if not prefix else relative[len(prefix) :]
        for relative in tracked
        if not prefix or relative.startswith(prefix)
    ]


def _projection_entries(
    source: Path,
    kind: str,
    source_files: object,
) -> list[tuple[str, str]]:
    if (
        not isinstance(source_files, list)
        or not source_files
        or not all(
            isinstance(item, str)
            and item != "."
            and is_relative_contract_path(item)
            for item in source_files
        )
        or source_files != sorted(set(source_files))
    ):
        raise ValueError("invalid source projection")
    if kind == "file":
        if source_files != [source.name] or not source.is_file():
            raise ValueError("invalid file projection")
        return [(source.name, sha256_file(source))]
    if kind != "tree" or not source.is_dir():
        raise ValueError("invalid tree projection")
    resolved_source = source.resolve(strict=True)
    entries: list[tuple[str, str]] = []
    for relative in source_files:
        candidate = (source / relative).resolve(strict=True)
        if not candidate.is_file() or not is_within(candidate, resolved_source):
            raise ValueError("projected source escapes its route")
        entries.append((relative, sha256_file(candidate)))
    return entries


def _projection_digest(source: Path, kind: str, source_files: object) -> str:
    material = bytearray()
    for relative, file_hash in _projection_entries(source, kind, source_files):
        material.extend(relative.encode("utf-8"))
        material.extend(b"\0")
        material.extend(file_hash.encode("ascii"))
        material.extend(b"\n")
    return sha256_bytes(bytes(material))


def _plan_digest(plan: dict[str, object]) -> str:
    material = dict(plan)
    material.pop("plan_digest", None)
    return sha256_bytes(canonical_json_bytes(material))


def _load_object(path: Path, code: str) -> tuple[dict[str, object] | None, list[dict[str, object]]]:
    try:
        value = load_json(path)
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        return None, [
            finding(
                code,
                path=path.name,
                line=1,
                message="A promotion contract cannot be loaded as JSON.",
                evidence=type(error).__name__,
            )
        ]
    if not isinstance(value, dict):
        return None, [
            finding(
                code,
                path=path.name,
                line=1,
                message="A promotion contract root must be an object.",
                evidence=type(value).__name__,
            )
        ]
    return value, []


def _routing_findings(
    root: Path,
    promotion_map: dict[str, object],
) -> list[dict[str, object]]:
    findings: list[dict[str, object]] = []
    if set(promotion_map) != {"schema_version", "artifacts"} or promotion_map.get("schema_version") != 1 or not isinstance(promotion_map.get("artifacts"), list):
        return [
            finding(
                "PROMOTION-ROUTING-INVALID",
                path="promotion-map.json",
                line=1,
                message="The promotion map does not match schema v1.",
                evidence="Expected schema_version and artifacts.",
            )
        ]
    required = {
        "artifact_id",
        "repo_path",
        "artifact_kind",
        "applicability",
        "vault_targets",
        "skill_target_ids",
    }
    allowed = required | {"not_applicable_reason"}
    routes_by_id: dict[str, list[dict[str, object]]] = {}
    for index, route in enumerate(promotion_map["artifacts"]):
        if not isinstance(route, dict) or not required.issubset(route) or set(route) - allowed:
            findings.append(
                finding(
                    "PROMOTION-ROUTING-INVALID",
                    path="promotion-map.json",
                    line=1,
                    message="A promotion route has invalid fields.",
                    evidence=f"artifacts[{index}]",
                )
            )
            continue
        artifact_id = str(route["artifact_id"])
        routes_by_id.setdefault(artifact_id, []).append(route)
        if len(routes_by_id[artifact_id]) > 1:
            findings.append(
                finding(
                    "PROMOTION-ROUTING-INVALID",
                    path="promotion-map.json",
                    line=1,
                    message="Promotion artifact identifiers must be unique.",
                    evidence=artifact_id,
                )
            )
        repo_path = str(route["repo_path"])
        if not is_relative_contract_path(repo_path):
            findings.append(
                finding(
                    "PROMOTION-ROUTING-INVALID",
                    path="promotion-map.json",
                    line=1,
                    message="A route repo_path is not a safe relative path.",
                    evidence=artifact_id,
                )
            )
            continue
        source = root / repo_path
        kind = route["artifact_kind"]
        if kind not in {"file", "tree"} or not source.exists() or (kind == "file") != source.is_file():
            findings.append(
                finding(
                    "PROMOTION-ROUTING-INVALID",
                    path=repo_path,
                    line=0,
                    message="A routed source is missing or has the wrong artifact kind.",
                    evidence=f"artifact_id={artifact_id} kind={kind}",
                )
            )
        if not isinstance(route["vault_targets"], list) or not route["vault_targets"]:
            findings.append(
                finding(
                    "PROMOTION-ROUTING-INVALID",
                    path="promotion-map.json",
                    line=1,
                    message="Every route requires at least one vault target.",
                    evidence=artifact_id,
                )
            )
        skill_targets = set(route["skill_target_ids"]) if isinstance(route["skill_target_ids"], list) else set()
        applicability = route["applicability"]
        if applicability == "domain_invariant":
            if skill_targets != REQUIRED_SKILL_TARGETS:
                findings.append(
                    finding(
                        "PROMOTION-ROUTING-INVALID",
                        path="promotion-map.json",
                        line=1,
                        message="A domain invariant must route to both installed skill roots.",
                        evidence=f"artifact_id={artifact_id} targets={sorted(skill_targets)}",
                    )
                )
        elif applicability in {"governance", "tooling"}:
            if not skill_targets and not str(route.get("not_applicable_reason", "")).strip():
                findings.append(
                    finding(
                        "PROMOTION-NOT-APPLICABLE-INVALID",
                        path="promotion-map.json",
                        line=1,
                        message="A route without skill targets requires a concrete reason.",
                        evidence=artifact_id,
                    )
                )
        else:
            findings.append(
                finding(
                    "PROMOTION-ROUTING-INVALID",
                    path="promotion-map.json",
                    line=1,
                    message="A route has an unsupported applicability.",
                    evidence=f"artifact_id={artifact_id}",
                )
            )

    try:
        source_map = load_json(root / SOURCE_MAP_PATH)
        expected = [
            (
                str(item["routing_artifact_id"]),
                str(item["output_path"]),
            )
            for item in source_map["artifacts"]
            if isinstance(item, dict)
        ]
    except (OSError, UnicodeError, json.JSONDecodeError, KeyError, TypeError):
        expected = []
    for artifact_id, output_path in sorted(expected):
        matching_routes = routes_by_id.get(artifact_id, [])
        if not any(
            _route_contains(
                str(route.get("repo_path", "")),
                route.get("artifact_kind"),
                output_path,
            )
            for route in matching_routes
        ):
            findings.append(
                finding(
                    "PROMOTION-UNROUTED",
                    path=SOURCE_MAP_PATH,
                    line=0,
                    message=(
                        "A source-map output is not contained by its named "
                        "promotion route."
                    ),
                    evidence=f"artifact_id={artifact_id} output_path={output_path}",
                )
            )
    return sort_findings(findings)


def _target_config_findings(
    config: dict[str, object],
) -> tuple[dict[str, Path], list[Path], list[Path], Path | None, list[dict[str, object]]]:
    findings: list[dict[str, object]] = []
    required = {
        "schema_version",
        "allowed_physical_roots",
        "forbidden_physical_roots",
        "backup_root",
        "targets",
    }
    if set(config) != required or config.get("schema_version") != 1:
        return {}, [], [], None, [
            finding(
                "PROMOTION-CONFIG-INVALID",
                path="local-targets.json",
                line=1,
                message="The local target configuration does not match schema v1.",
                evidence="Invalid top-level fields.",
            )
        ]
    try:
        allowed = [Path(item).resolve(strict=True) for item in config["allowed_physical_roots"]]
        forbidden = [Path(item).resolve(strict=False) for item in config["forbidden_physical_roots"]]
        backup_root = Path(str(config["backup_root"])).resolve(strict=True)
    except (OSError, TypeError) as error:
        return {}, [], [], None, [
            finding(
                "PROMOTION-CONFIG-INVALID",
                path="local-targets.json",
                line=1,
                message="A configured physical root cannot be resolved.",
                evidence=type(error).__name__,
            )
        ]
    if any(is_within(backup_root, blocked) for blocked in forbidden):
        findings.append(
            finding(
                "PROMOTION-BACKUP-FORBIDDEN",
                path="backup_root",
                line=0,
                message="The configured backup root resolves inside a forbidden root.",
                evidence="backup_root",
            )
        )
    elif not any(is_within(backup_root, root) for root in allowed):
        findings.append(
            finding(
                "PROMOTION-BACKUP-ESCAPE",
                path="backup_root",
                line=0,
                message="The configured backup root resolves outside all allowlisted roots.",
                evidence="backup_root",
            )
        )
    targets: dict[str, Path] = {}
    if not isinstance(config["targets"], dict):
        findings.append(
            finding(
                "PROMOTION-CONFIG-INVALID",
                path="local-targets.json",
                line=1,
                message="targets must be an object.",
                evidence=type(config["targets"]).__name__,
            )
        )
        return targets, allowed, forbidden, backup_root, findings
    for target_id, item in config["targets"].items():
        if not isinstance(item, dict) or set(item) != {"path", "ownership", "writable"}:
            findings.append(
                finding(
                    "PROMOTION-CONFIG-INVALID",
                    path="local-targets.json",
                    line=1,
                    message="A target configuration has invalid fields.",
                    evidence=str(target_id),
                )
            )
            continue
        path = Path(os.path.abspath(Path(str(item["path"]))))
        if not path.exists() or not path.is_dir():
            findings.append(
                finding(
                    "PROMOTION-TARGET-MISSING",
                    path=str(target_id),
                    line=0,
                    message="A configured target root does not exist.",
                    evidence=str(target_id),
                )
            )
            continue
        resolved = path.resolve(strict=True)
        if any(is_within(resolved, blocked) for blocked in forbidden):
            findings.append(
                finding(
                    "PROMOTION-TARGET-FORBIDDEN",
                    path=str(target_id),
                    line=0,
                    message="A configured target resolves inside a forbidden root.",
                    evidence=str(target_id),
                )
            )
            continue
        if not any(is_within(resolved, root) for root in allowed):
            findings.append(
                finding(
                    "PROMOTION-TARGET-ESCAPE",
                    path=str(target_id),
                    line=0,
                    message="A configured target resolves outside all allowlisted roots.",
                    evidence=str(target_id),
                )
            )
            continue
        if item["ownership"] != "user_owned" or item["writable"] is not True:
            findings.append(
                finding(
                    "PROMOTION-TARGET-READONLY",
                    path=str(target_id),
                    line=0,
                    message="A target is not explicitly user-owned and writable.",
                    evidence=str(target_id),
                )
            )
            continue
        targets[str(target_id)] = path
    return targets, allowed, forbidden, backup_root, sort_findings(findings)


def _skill_name(skill_file: Path) -> str | None:
    try:
        text = skill_file.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return None
    match = re.search(r"(?m)^name:\s*['\"]?([a-z0-9-]+)", text)
    return match.group(1) if match else None


def _legacy_overlap_findings(
    routes: list[dict[str, object]],
    targets: dict[str, Path],
) -> list[dict[str, object]]:
    findings: list[dict[str, object]] = []
    for route in routes:
        if route["applicability"] != "domain_invariant":
            continue
        source_name = _skill_name(Path(route["_resolved_source"]) / "SKILL.md")
        if not source_name:
            continue
        destination_name = Path(str(route["repo_path"])).name
        for target_id in route["skill_target_ids"]:
            root = targets.get(str(target_id))
            if root is None:
                continue
            for skill_file in sorted(root.glob("*/SKILL.md")):
                if skill_file.parent.name == destination_name:
                    continue
                if _skill_name(skill_file) == source_name:
                    findings.append(
                        finding(
                            "PROMOTION-LEGACY-OVERLAP",
                            path=str(target_id),
                            line=0,
                            message="A legacy installed skill overlaps the promoted skill name.",
                            evidence=f"skill={source_name} legacy={skill_file.parent.name}",
                        )
                    )
    return sort_findings(findings)


def _destination_findings(
    destination: Path,
    artifact_id: str,
    allowed: list[Path],
    forbidden: list[Path],
) -> list[dict[str, object]]:
    resolved = destination.resolve(strict=False)
    if any(is_within(resolved, blocked) for blocked in forbidden):
        return [
            finding(
                "PROMOTION-TARGET-FORBIDDEN",
                path=artifact_id,
                line=0,
                message="A routed destination resolves inside a forbidden root.",
                evidence=artifact_id,
            )
        ]
    if not any(is_within(resolved, root) for root in allowed):
        return [
            finding(
                "PROMOTION-TARGET-ESCAPE",
                path=artifact_id,
                line=0,
                message="A routed destination resolves outside all allowlisted roots.",
                evidence=artifact_id,
            )
        ]
    return []


def check_promotion(
    root: Path,
    promotion_map_path: Path,
    local_targets_path: Path,
    plan_path: Path,
) -> dict[str, object]:
    root = Path(root).resolve()
    promotion_map_path = Path(promotion_map_path).resolve()
    local_targets_path = Path(local_targets_path).resolve()
    plan_path = Path(plan_path).resolve()
    findings: list[dict[str, object]] = []
    if git_is_dirty(root):
        findings.append(
            finding(
                "PROMOTION-DIRTY",
                path=".",
                line=0,
                message="Promotion requires a clean source commit.",
                evidence="git status --porcelain is non-empty",
            )
        )
    promotion_map, map_load_findings = _load_object(
        promotion_map_path, "PROMOTION-ROUTING-INVALID"
    )
    config, config_load_findings = _load_object(
        local_targets_path, "PROMOTION-CONFIG-INVALID"
    )
    findings.extend(map_load_findings)
    findings.extend(config_load_findings)
    if promotion_map is None or config is None:
        return make_report("promote check", root, findings)
    findings.extend(_routing_findings(root, promotion_map))
    targets, allowed, forbidden, backup_root, target_findings = _target_config_findings(config)
    findings.extend(target_findings)
    if any(item["severity"] == "error" for item in findings):
        plan_path.unlink(missing_ok=True)
        return make_report("promote check", root, findings)

    routes: list[dict[str, object]] = []
    for route_value in promotion_map["artifacts"]:
        route = dict(route_value)
        route["_resolved_source"] = str(
            (root / str(route["repo_path"])).resolve(strict=True)
        )
        route["_source_files"] = _tracked_projection(
            root,
            str(route["repo_path"]),
            route["artifact_kind"],
        )
        if not route["_source_files"]:
            findings.append(
                finding(
                    "PROMOTION-SOURCE-UNTRACKED",
                    path=str(route["repo_path"]),
                    line=0,
                    message="A promotion route has no tracked source files.",
                    evidence=str(route["artifact_id"]),
                )
            )
        if not is_within(Path(str(route["_resolved_source"])), root):
            findings.append(
                finding(
                    "PROMOTION-SOURCE-ESCAPE",
                    path=str(route["repo_path"]),
                    line=0,
                    message="A routed source resolves outside the repository.",
                    evidence=str(route["artifact_id"]),
                )
            )
        routes.append(route)
    findings.extend(_legacy_overlap_findings(routes, targets))
    if any(item["severity"] == "error" for item in findings):
        plan_path.unlink(missing_ok=True)
        return make_report("promote check", root, findings)

    commit = git_commit(root)
    raw_operations: list[dict[str, object]] = []
    for route in routes:
        source = Path(str(route["_resolved_source"]))
        source_files = list(route["_source_files"])
        try:
            after_digest = _projection_digest(
                source,
                str(route["artifact_kind"]),
                source_files,
            )
        except (OSError, ValueError) as error:
            findings.append(
                finding(
                    "PROMOTION-SOURCE-INVALID",
                    path=str(route["repo_path"]),
                    line=0,
                    message="A tracked source projection cannot be read safely.",
                    evidence=f"{route['artifact_id']}:{type(error).__name__}",
                )
            )
            continue
        artifact_id = str(route["artifact_id"])
        for target_id in route["vault_targets"]:
            target_root = targets.get(str(target_id))
            if target_root is None:
                findings.append(
                    finding(
                        "PROMOTION-TARGET-MISSING",
                        path=str(target_id),
                        line=0,
                        message="A routed target has no valid local configuration.",
                        evidence=artifact_id,
                    )
                )
                continue
            logical_destination = target_root / artifact_id / commit
            destination = logical_destination.resolve(strict=False)
            findings.extend(
                _destination_findings(
                    destination,
                    artifact_id,
                    allowed,
                    forbidden,
                )
            )
            raw_operations.append(
                {
                    "artifact_id": artifact_id,
                    "artifact_kind": route["artifact_kind"],
                    "source_path": str(source),
                    "source_files": source_files,
                    "target_path": str(destination),
                    "logical_target_ids": [str(target_id)],
                    "logical_target_paths": {
                        str(target_id): str(logical_destination)
                    },
                    "before_digest": tree_digest(destination),
                    "after_digest": after_digest,
                    "target_role": "vault",
                }
            )
        for target_id in route["skill_target_ids"]:
            target_root = targets.get(str(target_id))
            if target_root is None:
                findings.append(
                    finding(
                        "PROMOTION-TARGET-MISSING",
                        path=str(target_id),
                        line=0,
                        message="A routed target has no valid local configuration.",
                        evidence=artifact_id,
                    )
                )
                continue
            logical_destination = (
                target_root / Path(str(route["repo_path"])).name
            )
            destination = logical_destination.resolve(strict=False)
            findings.extend(
                _destination_findings(
                    destination,
                    artifact_id,
                    allowed,
                    forbidden,
                )
            )
            raw_operations.append(
                {
                    "artifact_id": artifact_id,
                    "artifact_kind": route["artifact_kind"],
                    "source_path": str(source),
                    "source_files": source_files,
                    "target_path": str(destination),
                    "logical_target_ids": [str(target_id)],
                    "logical_target_paths": {
                        str(target_id): str(logical_destination)
                    },
                    "before_digest": tree_digest(destination),
                    "after_digest": after_digest,
                    "target_role": "skill",
                }
            )
    if any(item["severity"] == "error" for item in findings):
        plan_path.unlink(missing_ok=True)
        return make_report("promote check", root, findings)

    deduped: dict[str, dict[str, object]] = {}
    for operation in raw_operations:
        key = os.path.normcase(str(Path(str(operation["target_path"])).resolve(strict=False)))
        existing = deduped.get(key)
        if existing is None:
            deduped[key] = operation
        else:
            if (
                existing["after_digest"] != operation["after_digest"]
                or existing["source_path"] != operation["source_path"]
            ):
                findings.append(
                    finding(
                        "PROMOTION-ALIAS-CONFLICT",
                        path=str(operation["artifact_id"]),
                        line=0,
                        message="Two logical targets alias one path with different content.",
                        evidence=",".join(
                            sorted(
                                set(existing["logical_target_ids"])
                                | set(operation["logical_target_ids"])
                            )
                        ),
                    )
                )
            existing["logical_target_ids"] = sorted(
                set(existing["logical_target_ids"]) | set(operation["logical_target_ids"])
            )
            existing_paths = existing["logical_target_paths"]
            operation_paths = operation["logical_target_paths"]
            for target_id, logical_path in operation_paths.items():
                prior = existing_paths.get(target_id)
                if prior is not None and prior != logical_path:
                    findings.append(
                        finding(
                            "PROMOTION-ALIAS-CONFLICT",
                            path=str(operation["artifact_id"]),
                            line=0,
                            message=(
                                "One logical target identifier maps to multiple "
                                "paths."
                            ),
                            evidence=str(target_id),
                        )
                    )
                existing_paths[target_id] = logical_path
    if any(item["severity"] == "error" for item in findings):
        plan_path.unlink(missing_ok=True)
        return make_report("promote check", root, findings)
    operations = sorted(deduped.values(), key=lambda item: os.path.normcase(str(item["target_path"])))
    for index, operation in enumerate(operations, 1):
        operation["physical_alias"] = f"physical-{index:04d}"
    drifted = [
        operation
        for operation in operations
        if operation["before_digest"] != operation["after_digest"]
    ]
    if drifted:
        findings.append(
            finding(
                "PROMOTION-DRIFT",
                severity="warning",
                path="",
                line=0,
                message="One or more configured targets differ from the source commit.",
                evidence=f"operation_count={len(drifted)}",
            )
        )
    transaction_material = {
        "source_commit": commit,
        "promotion_map_hash": sha256_file(promotion_map_path),
        "local_targets_hash": sha256_file(local_targets_path),
        "operations": [
            {
                "artifact_id": item["artifact_id"],
                "physical_alias": item["physical_alias"],
                "target_path": item["target_path"],
                "logical_target_ids": item["logical_target_ids"],
                "logical_target_paths": item["logical_target_paths"],
                "source_files": item["source_files"],
                "before_digest": item["before_digest"],
                "after_digest": item["after_digest"],
            }
            for item in operations
        ],
    }
    transaction_id = sha256_bytes(
        canonical_json_bytes(transaction_material)
    )[:24]
    receipt_path = root / "promotions" / "receipts" / f"{transaction_id}.json"
    plan = {
        "schema_version": 1,
        "transaction_id": transaction_id,
        "source_root": str(root),
        "source_commit": commit,
        "promotion_map_path": str(promotion_map_path),
        "promotion_map_hash": transaction_material["promotion_map_hash"],
        "local_targets_path": str(local_targets_path),
        "local_targets_hash": transaction_material["local_targets_hash"],
        "backup_root": str(backup_root),
        "allowed_physical_roots": [str(path) for path in allowed],
        "forbidden_physical_roots": [str(path) for path in forbidden],
        "receipt_path": str(receipt_path),
        "artifact_ids": sorted({str(item["artifact_id"]) for item in operations}),
        "target_ids": sorted(
            {
                target_id
                for item in operations
                for target_id in item["logical_target_ids"]
            }
        ),
        "operations": operations,
    }
    plan["plan_digest"] = _plan_digest(plan)
    write_json(plan_path, plan)
    return make_report(
        "promote check",
        root,
        findings,
        artifacts={
            "plan_path": str(plan_path),
            "operation_count": len(operations),
            "logical_target_count": len(plan["target_ids"]),
        },
    )


def _copy_artifact(
    source: Path,
    destination: Path,
    kind: str,
    source_files: object | None = None,
) -> None:
    if kind == "tree" and source_files is None:
        shutil.copytree(source, destination)
    elif kind == "tree":
        entries = _projection_entries(source, kind, source_files)
        destination.mkdir(parents=True, exist_ok=False)
        for relative, _ in entries:
            target = destination / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source / relative, target)
    else:
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)


def _remove_artifact(path: Path) -> None:
    if not path.exists() and not path.is_symlink():
        return
    if path.is_dir() and not path.is_symlink():
        shutil.rmtree(path)
    else:
        path.unlink()


def _fault(fault_at: str | None, boundary: str, index: int) -> None:
    if fault_at == f"{boundary}:{index}":
        raise RuntimeError(f"fault injection at {boundary}:{index}")


def _is_junction(path: Path) -> bool:
    checker = getattr(path, "is_junction", None)
    return bool(checker()) if checker is not None else False


def _validate_plan_paths(plan: dict[str, object]) -> list[dict[str, object]]:
    findings: list[dict[str, object]] = []
    root = Path(str(plan["source_root"])).resolve(strict=True)
    allowed = [Path(item).resolve(strict=True) for item in plan["allowed_physical_roots"]]
    forbidden = [Path(item).resolve(strict=False) for item in plan["forbidden_physical_roots"]]
    backup_root = Path(str(plan["backup_root"])).resolve(strict=True)
    if any(is_within(backup_root, blocked) for blocked in forbidden):
        findings.append(
            finding(
                "PROMOTION-BACKUP-FORBIDDEN",
                path="backup_root",
                line=0,
                message="The planned backup root resolves inside a forbidden root.",
                evidence="backup_root",
            )
        )
    elif not any(is_within(backup_root, allowed_root) for allowed_root in allowed):
        findings.append(
            finding(
                "PROMOTION-BACKUP-ESCAPE",
                path="backup_root",
                line=0,
                message="The planned backup root resolves outside all allowlisted roots.",
                evidence="backup_root",
            )
        )
    for operation in plan["operations"]:
        source = Path(str(operation["source_path"])).resolve(strict=True)
        target = Path(str(operation["target_path"])).resolve(strict=False)
        if not is_within(source, root):
            findings.append(
                finding(
                    "PROMOTION-SOURCE-ESCAPE",
                    path=str(operation["artifact_id"]),
                    line=0,
                    message="A planned source resolves outside the repository.",
                    evidence=str(operation["physical_alias"]),
                )
            )
        if any(is_within(target, blocked) for blocked in forbidden):
            findings.append(
                finding(
                    "PROMOTION-TARGET-FORBIDDEN",
                    path=str(operation["artifact_id"]),
                    line=0,
                    message="A planned target resolves inside a forbidden root.",
                    evidence=str(operation["physical_alias"]),
                )
            )
        elif not any(is_within(target, allowed_root) for allowed_root in allowed):
            findings.append(
                finding(
                    "PROMOTION-TARGET-ESCAPE",
                    path=str(operation["artifact_id"]),
                    line=0,
                    message="A planned target resolves outside all allowlisted roots.",
                    evidence=str(operation["physical_alias"]),
                )
            )
        for target_id, logical_value in operation["logical_target_paths"].items():
            logical_target = Path(str(logical_value)).resolve(strict=False)
            if any(is_within(logical_target, blocked) for blocked in forbidden):
                findings.append(
                    finding(
                        "PROMOTION-TARGET-FORBIDDEN",
                        path=str(operation["artifact_id"]),
                        line=0,
                        message=(
                            "A planned logical target resolves inside a "
                            "forbidden root."
                        ),
                        evidence=str(target_id),
                    )
                )
            elif not any(
                is_within(logical_target, allowed_root)
                for allowed_root in allowed
            ):
                findings.append(
                    finding(
                        "PROMOTION-TARGET-ESCAPE",
                        path=str(operation["artifact_id"]),
                        line=0,
                        message=(
                            "A planned logical target resolves outside all "
                            "allowlisted roots."
                        ),
                        evidence=str(target_id),
                    )
                )
    return sort_findings(findings)


def _promotion_state_findings(
    plan: dict[str, object],
    root: Path,
) -> list[dict[str, object]]:
    findings: list[dict[str, object]] = []
    if git_commit(root) != plan["source_commit"] or git_is_dirty(root):
        findings.append(
            finding(
                "PROMOTION-SOURCE-CHANGED",
                path=".",
                line=0,
                message="The source commit/worktree changed after promote --check.",
                evidence=f"expected_commit={plan['source_commit']}",
            )
        )
    for operation in plan["operations"]:
        source = Path(str(operation["source_path"]))
        target = Path(str(operation["target_path"]))
        resolved_target = target.resolve(strict=False)
        if os.path.normcase(str(resolved_target)) != os.path.normcase(str(target)):
            findings.append(
                finding(
                    "PROMOTION-TARGET-CHANGED",
                    path=str(operation["artifact_id"]),
                    line=0,
                    message="A sealed physical target no longer resolves to itself.",
                    evidence=str(operation["physical_alias"]),
                )
            )
        for target_id, logical_value in operation["logical_target_paths"].items():
            logical_target = Path(str(logical_value)).resolve(strict=False)
            if os.path.normcase(str(logical_target)) != os.path.normcase(str(target)):
                findings.append(
                    finding(
                        "PROMOTION-LOGICAL-TARGET-CHANGED",
                        path=str(operation["artifact_id"]),
                        line=0,
                        message=(
                            "A logical target no longer resolves to its sealed "
                            "physical destination."
                        ),
                        evidence=str(target_id),
                    )
                )
        try:
            source_digest = _projection_digest(
                source,
                str(operation["artifact_kind"]),
                operation["source_files"],
            )
        except (OSError, ValueError):
            source_digest = "invalid"
        if source_digest != operation["after_digest"]:
            findings.append(
                finding(
                    "PROMOTION-SOURCE-CHANGED",
                    path=str(operation["artifact_id"]),
                    line=0,
                    message="A planned source digest changed after promote --check.",
                    evidence=str(operation["physical_alias"]),
                )
            )
        if tree_digest(target) != operation["before_digest"]:
            findings.append(
                finding(
                    "PROMOTION-TARGET-CHANGED",
                    path=str(operation["artifact_id"]),
                    line=0,
                    message=(
                        "A target changed after promote --check; "
                        "compare-and-swap rejected."
                    ),
                    evidence=str(operation["physical_alias"]),
                )
            )
    return sort_findings(findings)


def _recovery_findings(
    root: Path,
    backup_root: Path,
    lock_roots: list[Path],
    transaction_id: str,
) -> list[dict[str, object]]:
    findings: list[dict[str, object]] = []
    for index, lock_root in enumerate(lock_roots):
        lock_candidates = {lock_root / ".packctl.lock"}
        lock_candidates.update(lock_root.glob(".packctl-*.lock"))
        for lock_path in sorted(
            lock_candidates,
            key=lambda path: os.path.normcase(str(path)),
        ):
            if lock_path.exists() or lock_path.is_symlink():
                findings.append(
                    finding(
                        "PROMOTION-LOCK-UNADJUDICATED",
                        path="allowed_physical_roots",
                        line=0,
                        message=(
                            "A promotion lock already exists and requires "
                            "operator adjudication."
                        ),
                        evidence=f"root-{index + 1}",
                    )
                )
                break

    try:
        transaction_roots = sorted(
            (
                child
                for child in backup_root.iterdir()
                if re.fullmatch(r"[0-9a-f]{24}", child.name)
            ),
            key=lambda path: path.name,
        )
    except OSError:
        transaction_roots = []
        findings.append(
            finding(
                "PROMOTION-RECOVERY-REQUIRED",
                path="backup_root",
                line=0,
                message="The promotion backup root cannot be inspected safely.",
                evidence="backup-root-unreadable",
            )
        )

    for transaction_root in transaction_roots:
        prior_id = transaction_root.name
        reason = ""
        journal: object = None
        if prior_id == transaction_id:
            reason = "current-transaction-root-exists"
        elif (
            transaction_root.is_symlink()
            or _is_junction(transaction_root)
            or not transaction_root.is_dir()
            or not is_within(transaction_root.resolve(strict=False), backup_root)
        ):
            reason = "unsafe-transaction-root"
        else:
            journal_path = transaction_root / "journal.json"
            if (
                not journal_path.is_file()
                or journal_path.is_symlink()
                or _is_junction(journal_path)
            ):
                reason = "journal-missing-or-unsafe"
            else:
                try:
                    journal = load_json(journal_path)
                except (OSError, UnicodeError, json.JSONDecodeError):
                    reason = "journal-unreadable"
        if not reason:
            if (
                not isinstance(journal, dict)
                or journal.get("schema_version") != 1
                or journal.get("transaction_id") != prior_id
            ):
                reason = "journal-invalid"
            elif (
                journal.get("state") == "rolled-back"
                and journal.get("rollback_errors") == []
            ):
                continue
            elif journal.get("state") == "complete":
                receipt_path = (
                    root / "promotions" / "receipts" / f"{prior_id}.json"
                )
                try:
                    receipt = load_json(receipt_path)
                except (OSError, UnicodeError, json.JSONDecodeError):
                    receipt = None
                if (
                    isinstance(receipt, dict)
                    and receipt.get("schema_version") == 1
                    and receipt.get("transaction_id") == prior_id
                    and receipt.get("source_commit") == journal.get("source_commit")
                    and receipt.get("verdict") == "PASS"
                ):
                    continue
                reason = "complete-journal-without-valid-receipt"
            else:
                reason = f"journal-state-{journal.get('state')}"
        findings.append(
            finding(
                "PROMOTION-RECOVERY-REQUIRED",
                path="backup_root",
                line=0,
                message=(
                    "A prior promotion is incomplete or unverifiable and "
                    "requires operator adjudication."
                ),
                evidence=f"{prior_id}:{reason}",
            )
        )
    return sort_findings(findings)


def apply_promotion(
    plan_path: Path,
    *,
    fault_at: str | None = None,
    rollback_fault: bool = False,
) -> dict[str, object]:
    plan_path = Path(plan_path).resolve()
    plan, load_findings = _load_object(plan_path, "PROMOTION-PLAN-INVALID")
    if plan is None:
        return make_report("promote apply", plan_path.parent, load_findings)
    root = Path(str(plan.get("source_root", "."))).resolve()
    required = {
        "schema_version",
        "transaction_id",
        "source_root",
        "source_commit",
        "promotion_map_path",
        "promotion_map_hash",
        "local_targets_path",
        "local_targets_hash",
        "backup_root",
        "allowed_physical_roots",
        "forbidden_physical_roots",
        "receipt_path",
        "artifact_ids",
        "target_ids",
        "operations",
        "plan_digest",
    }
    if set(plan) != required or plan.get("schema_version") != 1:
        return make_report(
            "promote apply",
            root,
            [
                finding(
                    "PROMOTION-PLAN-INVALID",
                    path=plan_path.name,
                    line=1,
                    message="The promotion plan does not match schema v1.",
                    evidence="Invalid plan fields.",
                )
            ],
        )
    if _plan_digest(plan) != plan["plan_digest"]:
        return make_report(
            "promote apply",
            root,
            [
                finding(
                    "PROMOTION-PLAN-TAMPERED",
                    path=plan_path.name,
                    line=1,
                    message="The promotion plan changed after it was sealed.",
                    evidence="plan_digest mismatch",
                )
            ],
        )
    contract_findings: list[dict[str, object]] = []
    for path_field, hash_field in (
        ("promotion_map_path", "promotion_map_hash"),
        ("local_targets_path", "local_targets_hash"),
    ):
        try:
            actual_hash = sha256_file(Path(str(plan[path_field])))
        except OSError:
            actual_hash = "unreadable"
        if actual_hash != plan[hash_field]:
            contract_findings.append(
                finding(
                    "PROMOTION-CONTRACT-CHANGED",
                    path=Path(str(plan[path_field])).name,
                    line=1,
                    message="A promotion contract changed after promote --check.",
                    evidence=hash_field,
                )
            )
    if contract_findings:
        return make_report("promote apply", root, contract_findings)
    findings = _validate_plan_paths(plan)
    if findings:
        return make_report("promote apply", root, findings)
    findings = _promotion_state_findings(plan, root)
    if findings:
        return make_report("promote apply", root, findings)

    transaction_id = str(plan["transaction_id"])
    backup_base = Path(str(plan["backup_root"]))
    allowed_roots = [
        Path(item).resolve(strict=True)
        for item in plan["allowed_physical_roots"]
    ]
    protected_paths = [
        Path(str(operation["target_path"]))
        for operation in plan["operations"]
    ] + [backup_base]
    lock_roots_by_key: dict[str, Path] = {}
    for protected_path in protected_paths:
        candidates = [
            allowed
            for allowed in allowed_roots
            if is_within(protected_path, allowed)
        ]
        selected = max(candidates, key=lambda path: len(path.parts))
        lock_roots_by_key[os.path.normcase(str(selected))] = selected
    lock_roots = sorted(
        lock_roots_by_key.values(),
        key=lambda path: os.path.normcase(str(path)),
    )
    recovery_findings = _recovery_findings(
        root,
        backup_base,
        lock_roots,
        transaction_id,
    )
    if recovery_findings:
        return make_report(
            "promote apply",
            root,
            recovery_findings,
            artifacts={
                "requires_intervention": True,
                "exit_code": 2,
            },
        )
    backup_root = backup_base / transaction_id
    try:
        backup_root.mkdir(exist_ok=False)
    except OSError as error:
        return make_report(
            "promote apply",
            root,
            [
                finding(
                    "PROMOTION-RECOVERY-REQUIRED",
                    path="backup_root",
                    line=0,
                    message=(
                        "A create-only transaction root could not be "
                        "materialized."
                    ),
                    evidence=type(error).__name__,
                )
            ],
            artifacts={
                "requires_intervention": True,
                "exit_code": 2,
            },
        )
    journal_path = backup_root / "journal.json"
    lock_paths: list[Path] = []
    preserve_locks = False
    lock_conflict = False
    touched: list[tuple[dict[str, object], Path, bool]] = []
    stage_paths: list[Path] = []
    old_paths: list[Path] = []
    journal: dict[str, object] = {
        "schema_version": 1,
        "transaction_id": transaction_id,
        "source_commit": plan["source_commit"],
        "state": "starting",
        "touched_aliases": [],
    }
    try:
        for lock_root in lock_roots:
            lock_path = lock_root / ".packctl.lock"
            try:
                descriptor = os.open(
                    lock_path,
                    os.O_CREAT | os.O_EXCL | os.O_WRONLY,
                )
            except FileExistsError:
                lock_conflict = True
                raise
            lock_paths.append(lock_path)
            try:
                os.write(descriptor, transaction_id.encode("ascii"))
                os.fsync(descriptor)
            finally:
                os.close(descriptor)
        write_json(journal_path, journal)
        locked_findings = _promotion_state_findings(plan, root)
        if locked_findings:
            journal["state"] = "rolled-back"
            journal["rollback_errors"] = []
            write_json(journal_path, journal)
            return make_report("promote apply", root, locked_findings)

        for index, operation in enumerate(plan["operations"]):
            source = Path(str(operation["source_path"]))
            target = Path(str(operation["target_path"]))
            alias = str(operation["physical_alias"])
            if operation["before_digest"] == operation["after_digest"]:
                continue
            stage = target.parent / f".{target.name}.packctl-stage-{transaction_id}"
            old = target.parent / f".{target.name}.packctl-old-{transaction_id}"
            if (
                stage.exists()
                or stage.is_symlink()
                or old.exists()
                or old.is_symlink()
            ):
                raise RuntimeError(
                    f"preexisting transaction residue for {alias}"
                )
            target.parent.mkdir(parents=True, exist_ok=True)
            stage_paths.append(stage)
            _copy_artifact(
                source,
                stage,
                str(operation["artifact_kind"]),
                operation["source_files"],
            )
            old_paths.append(old)
            if tree_digest(stage) != operation["after_digest"]:
                raise RuntimeError(f"staging verification failed for {alias}")
            _fault(fault_at, "after_staging", index)

            backup = backup_root / alias
            existed = target.exists() or target.is_symlink()
            if existed:
                _copy_artifact(
                    target,
                    backup,
                    "tree" if target.is_dir() and not target.is_symlink() else "file",
                )
                if tree_digest(backup) != operation["before_digest"]:
                    raise RuntimeError(f"backup verification failed for {alias}")
            else:
                (backup_root / f"{alias}.absent").write_text(
                    "absent\n", encoding="utf-8", newline="\n"
                )
            _fault(fault_at, "after_backup", index)

            touched.append((operation, backup, existed))
            if existed:
                os.replace(target, old)
            _fault(fault_at, "after_old_move", index)
            os.replace(stage, target)
            stage_paths.remove(stage)
            journal["state"] = "replacing"
            journal["touched_aliases"] = [
                str(item[0]["physical_alias"]) for item in touched
            ]
            write_json(journal_path, journal)
            _fault(fault_at, "after_replace", index)
            if tree_digest(target) != operation["after_digest"]:
                raise RuntimeError(f"readback verification failed for {alias}")
            _fault(fault_at, "after_readback", index)
            _remove_artifact(old)

        journal["state"] = "readback-complete"
        write_json(journal_path, journal)
        for operation in plan["operations"]:
            target = Path(str(operation["target_path"]))
            if tree_digest(target) != operation["after_digest"]:
                raise RuntimeError(
                    f"physical readback failed for {operation['physical_alias']}"
                )
            for target_id, logical_value in operation["logical_target_paths"].items():
                logical_target = Path(str(logical_value))
                if (
                    os.path.normcase(str(logical_target.resolve(strict=False)))
                    != os.path.normcase(str(target.resolve(strict=False)))
                    or tree_digest(logical_target) != operation["after_digest"]
                ):
                    raise RuntimeError(
                        f"logical readback failed for {target_id}"
                    )
        receipt = {
            "schema_version": 1,
            "transaction_id": transaction_id,
            "source_commit": plan["source_commit"],
            "artifact_ids": plan["artifact_ids"],
            "target_ids": plan["target_ids"],
            "operations": [
                {
                    "artifact_id": operation["artifact_id"],
                    "physical_alias": operation["physical_alias"],
                    "logical_target_ids": operation["logical_target_ids"],
                    "before_digest": operation["before_digest"],
                    "after_digest": operation["after_digest"],
                }
                for operation in plan["operations"]
            ],
            "verdict": "PASS",
            "completed_at": datetime.now(timezone.utc).isoformat(),
        }
        receipt_path = Path(str(plan["receipt_path"]))
        success_report = make_report(
            "promote apply",
            root,
            [],
            artifacts={
                "receipt_path": str(receipt_path),
                "operation_count": len(plan["operations"]),
                "logical_target_count": len(plan["target_ids"]),
            },
        )
        for stage in stage_paths:
            _remove_artifact(stage)
        stage_paths.clear()
        for old in old_paths:
            _remove_artifact(old)
        old_paths.clear()
        journal["state"] = "complete"
        write_json(journal_path, journal)
        for lock_path in lock_paths:
            lock_path.unlink(missing_ok=True)
        lock_paths.clear()
        write_json(receipt_path, receipt)
        return success_report
    except Exception as error:
        rollback_errors: list[str] = []
        for operation, backup, existed in reversed(touched):
            target = Path(str(operation["target_path"]))
            try:
                if rollback_fault:
                    raise RuntimeError("rollback fault injection")
                _remove_artifact(target)
                if existed:
                    _copy_artifact(
                        backup,
                        target,
                        "tree" if backup.is_dir() else "file",
                    )
                if tree_digest(target) != operation["before_digest"]:
                    raise RuntimeError("rollback digest mismatch")
            except Exception as rollback_error:
                rollback_errors.append(
                    f"{operation['physical_alias']}:{type(rollback_error).__name__}"
                )
        cleanup_errors: list[str] = []
        for stage in list(stage_paths):
            try:
                _remove_artifact(stage)
                stage_paths.remove(stage)
            except Exception as cleanup_error:
                cleanup_errors.append(
                    f"stage:{type(cleanup_error).__name__}"
                )
        if not rollback_errors and not cleanup_errors:
            for old in list(old_paths):
                try:
                    _remove_artifact(old)
                    old_paths.remove(old)
                except Exception as cleanup_error:
                    cleanup_errors.append(
                        f"old:{type(cleanup_error).__name__}"
                    )
        recovery_errors = rollback_errors + cleanup_errors
        journal["state"] = (
            "rollback-failed" if recovery_errors else "rolled-back"
        )
        journal["error_type"] = type(error).__name__
        journal["rollback_errors"] = recovery_errors
        try:
            write_json(journal_path, journal)
        except Exception as journal_error:
            recovery_errors.append(
                f"journal:{type(journal_error).__name__}"
            )
        if not recovery_errors:
            for lock_path in list(lock_paths):
                try:
                    lock_path.unlink(missing_ok=True)
                    lock_paths.remove(lock_path)
                except Exception as cleanup_error:
                    recovery_errors.append(
                        f"lock:{type(cleanup_error).__name__}"
                    )
        if recovery_errors:
            preserve_locks = True
        failure_findings = [
            finding(
                "PROMOTION-APPLY-FAILED",
                path=plan_path.name,
                line=0,
                message="Promotion failed and did not publish a success receipt.",
                evidence=type(error).__name__,
            )
        ]
        artifacts: dict[str, object] = {
            "journal_path": str(journal_path),
            "backup_root": str(backup_root),
        }
        if lock_conflict:
            failure_findings.append(
                finding(
                    "PROMOTION-LOCK-UNADJUDICATED",
                    path="allowed_physical_roots",
                    line=0,
                    message=(
                        "A promotion lock appeared during acquisition and "
                        "requires operator adjudication."
                    ),
                    evidence="lock-race",
                )
            )
            artifacts["requires_intervention"] = True
            artifacts["exit_code"] = 2
        if recovery_errors:
            failure_findings.append(
                finding(
                    "PROMOTION-ROLLBACK-FAILED",
                    path=plan_path.name,
                    line=0,
                    message=(
                        "Rollback or its recovery evidence/cleanup could not "
                        "be completed safely."
                    ),
                    evidence=",".join(recovery_errors),
                )
            )
            artifacts["requires_intervention"] = True
            artifacts["exit_code"] = 2
        return make_report(
            "promote apply",
            root,
            failure_findings,
            artifacts=artifacts,
        )
    finally:
        for stage in stage_paths:
            try:
                _remove_artifact(stage)
            except Exception:
                pass
        if not preserve_locks:
            for old in old_paths:
                try:
                    _remove_artifact(old)
                except Exception:
                    pass
            for lock_path in lock_paths:
                try:
                    lock_path.unlink(missing_ok=True)
                except Exception:
                    pass
