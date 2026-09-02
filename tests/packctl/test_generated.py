"""Cover `packctl.generated`: the header scan and the PAIRS backstop.

The module shipped without tests and its backstop failed every synthetic root,
so five builder/gate/cli tests went red. These pin both halves: the backstop
still catches a copy that goes missing or loses its header, and it stays quiet
on a tree that never carried the edited source.
"""
from __future__ import annotations

from pathlib import Path

from packctl import generated
from packctl.validation import validate_generated


SOURCE_BODY = b"print('viewer scaffold')\n"


def codes(problems: list[dict[str, str]]) -> list[str]:
    return [item["code"] for item in problems]


def write_sources(root: Path, body: bytes = SOURCE_BODY) -> None:
    """Place the edited half of every declared pair, and nothing else."""
    for source_rel, _ in generated.PAIRS:
        path = root / source_rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(body)


def test_pairs_stay_quiet_on_a_tree_without_the_edited_source(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("# Not the pack\n", encoding="utf-8")

    assert generated.scan(tmp_path) == []


def test_fixture_repo_reports_no_generated_findings(repo_factory) -> None:
    root = repo_factory(payload={"LICENSE", "README.md"})

    assert validate_generated(root) == []


def test_missing_copy_is_reported_when_the_source_is_present(tmp_path: Path) -> None:
    write_sources(tmp_path)

    problems = generated.scan(tmp_path)

    assert codes(problems) == ["GENERATED-COPY-UNMARKED"] * len(generated.PAIRS)
    assert [item["path"] for item in problems] == [
        target_rel for _, target_rel in generated.PAIRS
    ]


def test_synced_copies_scan_clean(tmp_path: Path) -> None:
    write_sources(tmp_path)

    written = generated.sync(tmp_path)

    assert written == [target_rel for _, target_rel in generated.PAIRS]
    assert generated.scan(tmp_path) == []


def test_copy_that_lost_its_header_falls_back_to_the_pair(tmp_path: Path) -> None:
    write_sources(tmp_path)
    generated.sync(tmp_path)
    target = tmp_path / generated.PAIRS[0][1]
    target.write_bytes(SOURCE_BODY)

    problems = generated.scan(tmp_path)

    assert codes(problems) == ["GENERATED-COPY-UNMARKED"]
    assert problems[0]["path"] == generated.PAIRS[0][1]


def test_hand_edited_copy_is_reported_as_drift(tmp_path: Path) -> None:
    write_sources(tmp_path)
    generated.sync(tmp_path)
    target = tmp_path / generated.PAIRS[0][1]
    target.write_bytes(target.read_bytes() + b"print('by hand')\n")

    problems = generated.scan(tmp_path)

    assert codes(problems) == ["GENERATED-COPY-DRIFT"]


def test_source_edited_without_regeneration_is_a_stale_pin(tmp_path: Path) -> None:
    write_sources(tmp_path)
    generated.sync(tmp_path)
    (tmp_path / generated.PAIRS[0][0]).write_bytes(b"print('moved on')\n")

    problems = generated.scan(tmp_path)

    assert codes(problems) == ["GENERATED-COPY-STALE-PIN", "GENERATED-COPY-DRIFT"]


def test_copy_naming_a_missing_source_is_reported(tmp_path: Path) -> None:
    copy = tmp_path / "tools/orphan.py"
    copy.parent.mkdir(parents=True, exist_ok=True)
    copy.write_bytes(
        generated.header_for("skills/_shared/gone.py", generated.sha_upper(SOURCE_BODY))
        + SOURCE_BODY
    )

    problems = generated.scan(tmp_path)

    assert codes(problems) == ["GENERATED-COPY-SOURCE-MISSING"]
    assert problems[0]["evidence"] == "source=skills/_shared/gone.py"


def test_header_without_source_or_pin_is_incomplete(tmp_path: Path) -> None:
    copy = tmp_path / "tools/bare.py"
    copy.parent.mkdir(parents=True, exist_ok=True)
    copy.write_bytes(generated.MARK.encode("utf-8") + b"\n" + SOURCE_BODY)

    problems = generated.scan(tmp_path)

    assert codes(problems) == ["GENERATED-COPY-HEADER-INCOMPLETE"]


def test_skipped_directories_are_not_scanned(tmp_path: Path) -> None:
    for part in sorted(generated.SKIP_PARTS):
        copy = tmp_path / part / "copy.py"
        copy.parent.mkdir(parents=True, exist_ok=True)
        copy.write_bytes(generated.MARK.encode("utf-8") + b"\n" + SOURCE_BODY)

    assert generated.scan(tmp_path) == []
