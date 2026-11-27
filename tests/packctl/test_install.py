from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from packctl.install import (
    DESCRIPTION_LIMIT,
    MARKER,
    install,
    render_router,
    router_description,
)
from packctl.validation import validate_router

REPO = Path(__file__).resolve().parents[2]


def skill(name: str, description: str, extra: str = "") -> str:
    return f"---\nname: {name}\ndescription: {description}\n---\n# {name}\n{extra}"


@pytest.fixture
def mini(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    files = {
        "skills/dayz-b/SKILL.md": skill("dayz-b", "Use for B things.", "See [s](../_shared/s.md)\n"),
        "skills/dayz-b/references/r.md": "ref\n",
        "skills/dayz-b/tests/test_b.py": "x\n",
        "skills/dayz-b/scripts/__pycache__/m.cpython-312.pyc": "bin",
        "skills/dayz-b/scripts/m.py": "pass\n",
        "skills/dayz-a/SKILL.md": skill("dayz-a", "Use for A things."),
        "skills/_shared/s.md": "shared\n",
        "skills/_shared/tests/test_s.py": "x\n",
    }
    for rel, text in files.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    return root


def test_render_is_deterministic_sorted_and_complete(mini: Path) -> None:
    first = render_router(mini)
    assert render_router(mini) == first
    assert "{{ROUTING_TABLE}}" not in first
    assert first.index("`dayz-a`") < first.index("`dayz-b`")
    for name, desc in (("dayz-a", "Use for A things."), ("dayz-b", "Use for B things.")):
        assert f"Read `{name}/SKILL.md`" in first
        assert desc in first
    assert first.endswith("\n") and not first.endswith("\n\n")


def test_real_pack_router_lists_every_skill_within_cap() -> None:
    rendered = render_router(REPO)
    folders = sorted(p.name for p in (REPO / "skills").glob("dayz-*") if p.is_dir())
    assert len(folders) == 45
    for name in folders:
        assert f"Read `{name}/SKILL.md`" in rendered
    description = router_description(rendered)
    assert 0 < len(description) <= DESCRIPTION_LIMIT
    assert rendered.startswith("---\nname: dayz\n")


def test_install_layout_marker_and_links(mini: Path, tmp_path: Path) -> None:
    target = tmp_path / "skills-home"
    result = install(mini, target)
    bundle = target / "dayz"
    assert result["leftovers"] == []
    assert (bundle / "SKILL.md").read_text(encoding="utf-8") == render_router(mini)
    assert (bundle / "dayz-a/SKILL.md").is_file()
    assert (bundle / "dayz-b/references/r.md").is_file()
    assert (bundle / "dayz-b/scripts/m.py").is_file()
    assert not (bundle / "dayz-b/tests").exists()
    assert not (bundle / "_shared/tests").exists()
    assert not list(bundle.rglob("__pycache__")) and not list(bundle.rglob("*.pyc"))
    marker = json.loads((bundle / MARKER).read_text(encoding="utf-8"))
    assert marker["installer"] == "packctl install"
    assert marker["skills"] == ["dayz-a", "dayz-b"]
    # ../_shared link from a sub-skill resolves
    assert (bundle / "dayz-b" / "../_shared/s.md").read_text(encoding="utf-8") == "shared\n"
    assert not [p for p in target.iterdir() if p.name != "dayz"]


def test_dry_run_writes_nothing(mini: Path, tmp_path: Path) -> None:
    target = tmp_path / "t"
    result = install(mini, target, dry_run=True)
    assert result["dry_run"] is True
    assert not target.exists()


def test_refuses_foreign_dir_without_force(mini: Path, tmp_path: Path) -> None:
    target = tmp_path / "t"
    (target / "dayz").mkdir(parents=True)
    (target / "dayz/mine.txt").write_text("keep", encoding="utf-8")
    with pytest.raises(FileExistsError):
        install(mini, target)
    assert (target / "dayz/mine.txt").read_text(encoding="utf-8") == "keep"
    result = install(mini, target, force=True)
    assert result["replaced"] == "foreign"
    assert not (target / "dayz/mine.txt").exists()
    assert (target / "dayz" / MARKER).is_file()


def test_replaces_previous_bundle_and_leaves_no_temp_dirs(mini: Path, tmp_path: Path) -> None:
    target = tmp_path / "t"
    install(mini, target)
    (target / "dayz/stale.txt").write_text("old", encoding="utf-8")
    (mini / "skills/dayz-c").mkdir()
    (mini / "skills/dayz-c/SKILL.md").write_text(skill("dayz-c", "C."), encoding="utf-8")
    result = install(mini, target)
    assert result["replaced"] == "bundle"
    assert not (target / "dayz/stale.txt").exists()
    assert (target / "dayz/dayz-c/SKILL.md").is_file()
    assert [p.name for p in target.iterdir()] == ["dayz"]


def test_leftover_old_shape_is_reported_not_deleted(mini: Path, tmp_path: Path) -> None:
    target = tmp_path / "t"
    for name in ("dayz-a", "_shared", "blender-animation", "unrelated"):
        (target / name).mkdir(parents=True)
    result = install(mini, target)
    assert result["leftovers"] == ["_shared", "blender-animation", "dayz-a"]
    assert (target / "dayz-a").is_dir() and (target / "unrelated").is_dir()


def test_cli_install_and_refusal(mini: Path, tmp_path: Path) -> None:
    target = tmp_path / "t"
    cmd = [sys.executable, "-m", "packctl", "install", "--root", str(mini), "--target", str(target)]
    run = lambda *extra: subprocess.run(  # noqa: E731
        [*cmd, *extra], cwd=REPO, capture_output=True, text=True
    )
    assert run().returncode == 0
    assert run("--dry-run").returncode == 0
    (target / "foreign").mkdir()
    assert run("--name", "foreign").returncode == 1
    assert run("--name", "foreign", "--force").returncode == 0


def test_validate_router_passes_on_fixture_and_flags_problems(mini: Path, monkeypatch) -> None:
    assert validate_router(mini) == []
    monkeypatch.setattr("packctl.install.DESCRIPTION_LIMIT", 10)
    assert [f["code"] for f in validate_router(mini)] == ["SKILL-ROUTER-DESCRIPTION"]
    monkeypatch.undo()
    (mini / "skills/dayz-a/SKILL.md").write_text("no frontmatter\n", encoding="utf-8")
    assert [f["code"] for f in validate_router(mini)] == ["SKILL-ROUTER-RENDER"]


def test_validate_router_on_real_pack_is_clean() -> None:
    assert validate_router(REPO) == []
