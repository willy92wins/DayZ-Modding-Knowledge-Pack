from __future__ import annotations

import hashlib
import json
import os
import subprocess
from pathlib import Path
from typing import Any, Iterable


SCHEMA_VERSION = 1
SEVERITY_RANK = {"error": 0, "warning": 1, "info": 2}


def canonical_json_bytes(value: object) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    ).encode("utf-8")


def write_json(path: Path, value: object, *, compact: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if compact:
        data = canonical_json_bytes(value)
    else:
        data = (
            json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
        ).encode("utf-8")
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_bytes(data)
    os.replace(temporary, path)


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def finding(
    code: str,
    *,
    severity: str = "error",
    path: str = "",
    line: int = 0,
    message: str,
    evidence: str,
) -> dict[str, object]:
    if severity not in SEVERITY_RANK:
        raise ValueError(f"Unsupported severity: {severity}")
    return {
        "code": code,
        "severity": severity,
        "path": path,
        "line": int(line),
        "message": message,
        "evidence": evidence,
    }


def sort_findings(
    findings: Iterable[dict[str, object]],
) -> list[dict[str, object]]:
    return sorted(
        findings,
        key=lambda item: (
            SEVERITY_RANK[str(item["severity"])],
            str(item["code"]),
            str(item["path"]),
            int(item["line"]),
            str(item["message"]),
        ),
    )


def verdict_for(findings: Iterable[dict[str, object]]) -> str:
    severities = {str(item["severity"]) for item in findings}
    if "error" in severities:
        return "FAIL"
    if "warning" in severities:
        return "WARN"
    return "PASS"


def git_output(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="strict",
    )
    return result.stdout


def git_commit(root: Path) -> str:
    try:
        return git_output(root, "rev-parse", "HEAD").strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def git_tracked_files(root: Path) -> list[str]:
    output = git_output(root, "ls-files", "-z")
    return sorted(item.replace("\\", "/") for item in output.split("\0") if item)


def git_is_dirty(root: Path) -> bool:
    try:
        return bool(git_output(root, "status", "--porcelain=v1", "-z"))
    except (OSError, subprocess.CalledProcessError):
        return True


def make_report(
    command: str,
    root: Path,
    findings: Iterable[dict[str, object]],
    *,
    checks: dict[str, object] | None = None,
    artifacts: dict[str, object] | None = None,
) -> dict[str, object]:
    ordered = sort_findings(findings)
    return {
        "schema_version": SCHEMA_VERSION,
        "command": command,
        "source_commit": git_commit(root),
        "verdict": verdict_for(ordered),
        "findings": ordered,
        "checks": checks or {},
        "artifacts": artifacts or {},
    }


def exit_code_for(report: dict[str, object]) -> int:
    artifacts = report.get("artifacts", {})
    if isinstance(artifacts, dict) and artifacts.get("exit_code") == 2:
        return 2
    return 1 if report["verdict"] == "FAIL" else 0


def posix_relative(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def is_relative_contract_path(value: object) -> bool:
    if not isinstance(value, str) or not value or "\0" in value:
        return False
    if "\\" in value or value.startswith("/") or Path(value).drive:
        return False
    return ".." not in Path(value).parts


def is_within(path: Path, root: Path) -> bool:
    try:
        path.resolve(strict=False).relative_to(root.resolve(strict=False))
        return True
    except ValueError:
        return False


def tree_digest(path: Path) -> str:
    if not path.exists():
        return "absent"
    if path.is_file():
        entries = [(path.name, sha256_file(path))]
    else:
        entries = [
            (item.relative_to(path).as_posix(), sha256_file(item))
            for item in sorted(path.rglob("*"))
            if item.is_file()
        ]
    digest = hashlib.sha256()
    for relative, file_hash in entries:
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(file_hash.encode("ascii"))
        digest.update(b"\n")
    return digest.hexdigest()
