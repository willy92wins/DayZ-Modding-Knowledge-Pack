from __future__ import annotations

import json
from pathlib import Path

import pytest

from conftest import ZERO_COMMIT, artifact, make_source_map, source, write_json

from packctl.validation import (
    validate_claims,
    validate_licenses,
    validate_links,
    validate_privacy,
    validate_skills,
    validate_source_map,
)


def codes(findings: list[dict[str, object]]) -> list[str]:
    return [str(finding["code"]) for finding in findings]


def test_source_clean_maps_every_tracked_file_once(repo_factory) -> None:
    root = repo_factory()

    assert validate_source_map(root) == []


def test_source_unmapped_has_stable_code(repo_factory) -> None:
    root = repo_factory()
    extra = root / "tracked-extra.txt"
    extra.write_text("unmapped\n", encoding="utf-8")
    from conftest import run_git

    run_git(root, "add", "tracked-extra.txt")

    assert codes(validate_source_map(root)) == ["SOURCE-UNMAPPED"]


def test_source_conflict_with_two_adopted_hashes_is_undecided(
    repo_factory,
) -> None:
    root = repo_factory()
    source_map_path = root / "sources/source-map.json"
    value = json.loads(source_map_path.read_text(encoding="utf-8"))
    target = next(
        item for item in value["artifacts"] if item["output_path"] == "README.md"
    )
    target["inputs"].append(
        {
            **target["inputs"][0],
            "source_id": "other",
            "source_hash": "f" * 64,
            "decision_evidence": "Second source also marked authoritative.",
        }
    )
    value["sources"].append(source("other"))
    write_json(source_map_path, value)

    assert "SOURCE-CONFLICT-UNDECIDED" in codes(validate_source_map(root))


def test_excluded_input_cannot_overlap_an_artifact_input(repo_factory) -> None:
    root = repo_factory()
    source_map_path = root / "sources/source-map.json"
    value = json.loads(source_map_path.read_text(encoding="utf-8"))
    source_input = value["artifacts"][0]["inputs"][0]
    value["excluded_inputs"].append(
        {
            "source_id": source_input["source_id"],
            "source_revision": source_input["source_revision"],
            "source_path": source_input["source_path"],
            "source_hash": source_input["source_hash"],
            "reason": "superseded",
            "decision_evidence": "Deliberate overlap fixture.",
        }
    )
    write_json(source_map_path, value)

    assert "SOURCE-INPUT-DUPLICATE" in codes(validate_source_map(root))


def test_source_map_rejects_private_physical_root(repo_factory) -> None:
    root = repo_factory()
    source_map_path = root / "sources/source-map.json"
    value = json.loads(source_map_path.read_text(encoding="utf-8"))
    value["sources"][0]["physical_path"] = "C:\\Users\\person\\private"
    write_json(source_map_path, value)

    assert "SOURCE-SCHEMA-INVALID" in codes(validate_source_map(root))


def test_skill_clean_description_and_allowed_frontmatter(repo_factory) -> None:
    root = repo_factory(
        {
            "skills/demo/SKILL.md": (
                "---\n"
                "name: demo\n"
                "description: Use for a clean fixture.\n"
                "license: MIT\n"
                "compatibility: DayZ 1.29\n"
                "metadata:\n"
                "  owner: fixture\n"
                "allowed-tools: shell\n"
                "---\n"
                "# Demo\n"
            )
        }
    )

    assert validate_skills(root) == []


def test_skill_description_1025_fails(repo_factory) -> None:
    root = repo_factory(
        {
            "skills/demo/SKILL.md": (
                "---\nname: demo\ndescription: " + ("x" * 1025) + "\n---\n# Demo\n"
            )
        }
    )

    assert codes(validate_skills(root)) == ["SKILL-DESCRIPTION-TOO-LONG"]


def test_skill_extra_frontmatter_fails(repo_factory) -> None:
    root = repo_factory(
        {
            "skills/demo/SKILL.md": (
                "---\n"
                "name: demo\n"
                "description: Clean description.\n"
                "invented-field: false\n"
                "---\n"
            )
        }
    )

    assert codes(validate_skills(root)) == ["SKILL-FRONTMATTER-UNSUPPORTED"]


def test_links_broken_but_fenced_example_is_ignored(repo_factory) -> None:
    root = repo_factory(
        {
            "docs/links.md": (
                "[good](../README.md)\n\n"
                "```markdown\n[fixture](does-not-exist.md)\n```\n"
            )
        }
    )

    assert validate_links(root) == []


def test_links_broken_outside_fence_fails(repo_factory) -> None:
    root = repo_factory({"docs/links.md": "[broken](does-not-exist.md)\n"})

    assert codes(validate_links(root)) == ["LINK-BROKEN"]


def test_exact_context_link_allowlist_suppresses_only_declared_target(
    repo_factory,
) -> None:
    root = repo_factory(
        {
            "docs/links.md": (
                "[private context](../private/session.md)\n"
                "[still broken](other.md)\n"
            ),
            "sources/link-allowlist.json": (
                '{\n'
                '  "schema_version": 1,\n'
                '  "entries": [\n'
                '    {\n'
                '      "path": "docs/links.md",\n'
                '      "target": "../private/session.md",\n'
                '      "reason": "Private context is intentionally not distributed."\n'
                '    }\n'
                '  ]\n'
                '}\n'
            ),
        }
    )

    findings = validate_links(root)

    assert codes(findings) == ["LINK-BROKEN"]
    assert findings[0]["evidence"] == "other.md"


def test_private_absolute_path_is_rejected(repo_factory) -> None:
    root = repo_factory({"notes.md": "Open C:\\Users\\alice\\private\\file.txt\n"})

    assert codes(validate_privacy(root)) == ["PRIVACY-PRIVATE-PATH"]


def test_secret_finding_redacts_the_value(repo_factory) -> None:
    token = "ghp_" + ("a" * 36)
    root = repo_factory({"notes.md": f"token={token}\n"})

    findings = validate_privacy(root)

    assert codes(findings) == ["PRIVACY-SECRET"]
    assert token not in json.dumps(findings)
    assert "[REDACTED]" in json.dumps(findings)


@pytest.mark.parametrize(
    "secret_line",
    [
        "-----BEGIN PRIVATE KEY-----",
        'password = "this-is-a-real-literal-secret"',
        "api_key: '0123456789abcdef0123456789abcdef'",
    ],
)
def test_privacy_rejects_private_keys_and_literal_credentials(
    repo_factory,
    secret_line: str,
) -> None:
    root = repo_factory(
        {"notes.md": secret_line + "\n"},
        payload={"LICENSE", "README.md", "notes.md"},
    )

    findings = validate_privacy(root)

    assert [item["code"] for item in findings] == ["PRIVACY-SECRET"]
    assert findings[0]["evidence"] == "[REDACTED]"
    assert secret_line not in json.dumps(findings)


def test_license_missing_fails(repo_factory) -> None:
    root = repo_factory()
    (root / "LICENSE").unlink()

    assert "LICENSE-MISSING" in codes(validate_licenses(root))


def test_forbidden_payload_license_fails(repo_factory) -> None:
    root = repo_factory()
    source_map_path = root / "sources/source-map.json"
    value = json.loads(source_map_path.read_text(encoding="utf-8"))
    target = next(
        item for item in value["artifacts"] if item["output_path"] == "README.md"
    )
    target["license"] = "GPL-3.0-only"
    write_json(source_map_path, value)

    assert "LICENSE-FORBIDDEN-PAYLOAD" in codes(validate_licenses(root))


def test_claim_registry_requires_marker_and_exact_range(repo_factory) -> None:
    root = repo_factory(
        {
            "skills/demo/SKILL.md": (
                "---\nname: demo\ndescription: Demo.\n---\n"
                "[EXACT][CLAIM-DEMO-API] Call `Demo()`.\n"
            )
        }
    )
    claims = {
        "schema_version": 1,
        "claim_baseline_commit": ZERO_COMMIT,
        "claims": [
            {
                "claim_id": "CLAIM-DEMO-API",
                "artifact_id": "skills-demo-SKILL-md",
                "line_start": 5,
                "line_end": 5,
                "source_id": "pack",
                "source_revision": ZERO_COMMIT,
                "evidence_locator": "fixture.c:1",
                "license": "MIT",
                "observed_at": "2026-07-24",
                "verification_level": "source_verified",
                "promotion_artifact_id": "fixture",
            }
        ],
    }
    write_json(root / "sources/claims.json", claims)

    assert validate_claims(root) == []


def test_claim_registry_ignores_repo_only_contract_examples(repo_factory) -> None:
    root = repo_factory(
        {
            "specs/example.md": (
                "Example syntax: [EXACT][CLAIM-EXAMPLE-ONLY]\n"
            )
        },
        payload={"LICENSE", "README.md"},
    )

    assert validate_claims(root) == []


def test_unregistered_exact_claim_fails(repo_factory) -> None:
    root = repo_factory(
        {
            "skills/demo/SKILL.md": (
                "---\nname: demo\ndescription: Demo.\n---\n"
                "[EXACT][CLAIM-MISSING] Call `Missing()`.\n"
            )
        }
    )

    assert codes(validate_claims(root)) == ["CLAIM-UNREGISTERED"]
