from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

from packctl.install import (
    DESCRIPTION_LIMIT,
    MARKER,
    InstallError,
    install,
    render_router,
    write_bundle_zip,
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


def _git_commit_all(root: Path, message: str = "init") -> None:
    def run(*a: str) -> None:
        subprocess.run(
            ["git", "-c", "user.name=t", "-c", "user.email=t@t", *a],
            cwd=root,
            check=True,
            capture_output=True,
        )

    run("init", "-q")
    run("add", "-A")
    run("commit", "-q", "-m", message)


@pytest.fixture
def mini_git(mini: Path) -> Path:
    _git_commit_all(mini)
    return mini


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_bundle_zip_is_reproducible_and_has_one_toplevel_folder(mini_git: Path, tmp_path: Path) -> None:
    a, b = tmp_path / "a.zip", tmp_path / "b.zip"
    write_bundle_zip(mini_git, a)
    write_bundle_zip(mini_git, b)
    assert _sha(a) == _sha(b)
    with zipfile.ZipFile(a) as z:
        names = z.namelist()
        assert names == sorted(names)
        assert {n.split("/")[0] for n in names} == {"dayz"}
        assert all("\\" not in n for n in names)
        assert "dayz/SKILL.md" in names and f"dayz/{MARKER}" in names
        assert "dayz/dayz-b/scripts/m.py" in names
        assert not [n for n in names if "/tests/" in n or "__pycache__" in n or n.endswith(".pyc")]
        assert {i.date_time for i in z.infolist()} == {(1980, 1, 1, 0, 0, 0)}
        assert {i.external_attr >> 16 for i in z.infolist()} == {0o100644}
        assert b"\r" not in z.read("dayz/SKILL.md")
        assert z.read("dayz/SKILL.md").decode() == render_router(mini_git)
        marker = json.loads(z.read(f"dayz/{MARKER}"))
    assert marker["skills"] == ["dayz-a", "dayz-b"]
    assert marker["mode"] == "copy" and "installed_at" not in marker
    assert marker["source_commit"] != "unknown"


def test_bundle_zip_matches_install_tree_and_unzip_is_replaceable(mini_git: Path, tmp_path: Path) -> None:
    archive = tmp_path / "out.zip"
    write_bundle_zip(mini_git, archive)
    home = tmp_path / "home"
    home.mkdir()
    with zipfile.ZipFile(archive) as z:
        z.extractall(home)
    installed = tmp_path / "installed"
    install(mini_git, installed)

    def tree(base: Path) -> dict[str, bytes]:
        return {
            p.relative_to(base).as_posix(): p.read_bytes()
            for p in sorted(base.rglob("*"))
            if p.is_file() and p.name != MARKER
        }

    assert tree(home / "dayz") == tree(installed / "dayz")
    assert install(mini_git, home)["replaced"] == "bundle"


def test_bundle_zip_refuses_dirty_tree_and_output_in_root(mini_git: Path, tmp_path: Path) -> None:
    with pytest.raises(InstallError, match="outside the source tree"):
        write_bundle_zip(mini_git, mini_git / "x.zip")
    (mini_git / "skills/dayz-a/new.md").write_text("x", encoding="utf-8")
    with pytest.raises(InstallError, match="clean Git worktree"):
        write_bundle_zip(mini_git, tmp_path / "x.zip")
    assert not (tmp_path / "x.zip").exists()


@pytest.mark.skipif(os.name == "nt", reason="needs POSIX exec bit")
def test_bundle_zip_keeps_executable_bit_from_git(mini: Path, tmp_path: Path) -> None:
    script = mini / "skills/_shared/run.sh"
    script.write_text("#!/bin/sh\n", encoding="utf-8")
    script.chmod(0o755)
    _git_commit_all(mini)
    write_bundle_zip(mini, tmp_path / "x.zip")
    with zipfile.ZipFile(tmp_path / "x.zip") as z:
        modes = {i.filename: i.external_attr >> 16 for i in z.infolist()}
    assert modes["dayz/_shared/run.sh"] == 0o100755
    assert modes["dayz/_shared/s.md"] == 0o100644


def test_cli_bundle(mini_git: Path, tmp_path: Path) -> None:
    def run(out: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, "-m", "packctl", "bundle", "--root", str(mini_git), "--output", out],
            cwd=REPO,
            capture_output=True,
            text=True,
        )

    first = run(str(tmp_path / "cli.zip"))
    assert first.returncode == 0, first.stderr
    assert (tmp_path / "cli.zip").is_file()
    (mini_git / "skills/dayz-a/new.md").write_text("x", encoding="utf-8")
    dirty = run(str(tmp_path / "d.zip"))
    assert dirty.returncode == 1 and "Traceback" not in dirty.stderr


def _symlinks_ok(tmp_path: Path) -> bool:
    probe = tmp_path / "probe"
    try:
        os.symlink(tmp_path, probe, target_is_directory=True)
    except OSError:
        return False
    probe.unlink()
    return True


def test_link_install_layout_and_replacement_safety(mini: Path, tmp_path: Path) -> None:
    if not _symlinks_ok(tmp_path):
        pytest.skip("symlinks unavailable")
    target = tmp_path / "t"
    result = install(mini, target, link=True)
    bundle = target / "dayz"
    assert result["mode"] == "link"
    router = bundle / "SKILL.md"
    assert router.is_file() and not router.is_symlink()
    assert router.read_text(encoding="utf-8") == render_router(mini)
    assert (bundle / MARKER).is_file() and not (bundle / MARKER).is_symlink()
    assert json.loads((bundle / MARKER).read_text(encoding="utf-8"))["mode"] == "link"
    for entry in ("_shared", "dayz-a", "dayz-b"):
        link = bundle / entry
        assert link.is_symlink()
        assert Path(os.readlink(link)) == (mini / "skills" / entry).resolve()
        assert Path(os.readlink(link)).is_absolute()
    (mini / "skills/dayz-a/new.md").write_text("live", encoding="utf-8")
    assert (bundle / "dayz-a/new.md").read_text(encoding="utf-8") == "live"
    assert (bundle / "dayz-b" / "../_shared/s.md").read_text(encoding="utf-8") == "shared\n"

    before = sorted(p.relative_to(mini).as_posix() for p in mini.rglob("*"))
    for kwargs in ({}, {"link": True}, {"link": True}):
        assert install(mini, target, **kwargs)["replaced"] == "bundle"
        assert sorted(p.relative_to(mini).as_posix() for p in mini.rglob("*")) == before
    assert (mini / "skills/dayz-b/references/r.md").read_text(encoding="utf-8") == "ref\n"
    assert [p.name for p in target.iterdir()] == ["dayz"]


def test_replacing_linked_bundle_with_copy_leaves_repo_untouched(mini: Path, tmp_path: Path) -> None:
    if not _symlinks_ok(tmp_path):
        pytest.skip("symlinks unavailable")
    target = tmp_path / "t"
    install(mini, target, link=True)
    install(mini, target)
    assert (mini / "skills/dayz-b/SKILL.md").is_file()
    assert (mini / "skills/_shared/s.md").is_file()
    assert not (target / "dayz/dayz-b").is_symlink()


def test_link_symlink_failure_message(mini: Path, tmp_path: Path, monkeypatch) -> None:
    def boom(*args, **kwargs):
        raise OSError("A required privilege is not held by the client")

    monkeypatch.setattr(os, "symlink", boom)
    target = tmp_path / "t"
    with pytest.raises(InstallError, match="without --link"):
        install(mini, target, link=True)
    assert [p.name for p in target.iterdir()] == []


def test_rename_permission_error_rolls_back_with_clear_message(mini: Path, tmp_path: Path, monkeypatch) -> None:
    target = tmp_path / "t"
    install(mini, target)
    (target / "dayz/keep.txt").write_text("old", encoding="utf-8")
    real = Path.rename

    def fail_move_aside(self, dest):
        if self.name == "dayz":
            raise PermissionError(13, "Access is denied")
        return real(self, dest)

    monkeypatch.setattr(Path, "rename", fail_move_aside)
    with pytest.raises(InstallError, match="Close Claude Code"):
        install(mini, target)
    assert (target / "dayz/keep.txt").is_file()
    assert [p.name for p in target.iterdir()] == ["dayz"]

    def fail_move_in(self, dest):
        if self.name.startswith(".dayz.new-"):
            raise PermissionError(13, "Access is denied")
        return real(self, dest)

    monkeypatch.setattr(Path, "rename", fail_move_in)
    with pytest.raises(InstallError, match="Close Claude Code"):
        install(mini, target)
    assert (target / "dayz/keep.txt").read_text(encoding="utf-8") == "old"
    assert [p.name for p in target.iterdir()] == ["dayz"]


def test_cli_prints_install_error_without_traceback(mini: Path, tmp_path: Path, monkeypatch, capsys) -> None:
    from packctl import cli

    def boom(*args, **kwargs):
        raise InstallError("could not x. Close Claude Code and retry.")

    monkeypatch.setattr(cli, "install", boom)
    code = cli.main(["install", "--root", str(mini), "--target", str(tmp_path / "t")])
    err = capsys.readouterr().err
    assert code == 1 and "Close Claude Code" in err and "Traceback" not in err
