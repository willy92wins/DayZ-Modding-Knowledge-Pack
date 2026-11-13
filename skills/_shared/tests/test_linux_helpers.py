"""The local-server, client and packaging helpers from bzed/dayz-dev-plugin, without Steam or DayZ.

What needs a Steam install, a game or Proton was measured by hand (see
skills/dayz-test-ingame/references/linux-native-server.md); these tests cover the scripts
themselves: syntax, shellcheck, and the parts that run on a fake Steam tree.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
AUTOTEST = Path(__file__).resolve().parents[2] / "dayz-test-ingame" / "assets" / "autotest-mod"
POSIX = ["find-dayzserver.sh", "make-server-tree.sh", "free-ports.sh", "dayz-client-headless.sh", "dayz-client-test.sh"]
BASH = ["dayz-mod-pack.sh", "extract-dayz-sources.sh"]

pytestmark = pytest.mark.skipif(os.name == "nt", reason="the Linux helper scripts")


def fake_steam(tmp_path: Path, appid: int = 223350, installdir: str = "DayZServer", state: int = 4) -> Path:
    """A Steam root with one library holding one installed app with a mission."""
    root = tmp_path / "steam"
    apps = root / "steamapps"
    install = apps / "common" / installdir
    mission = install / "mpmissions" / "dayzOffline.chernarusplus"
    (mission / "storage_1").mkdir(parents=True)
    (mission / "init.c").write_text("void main() {}\n")
    (install / "keys").mkdir()
    (install / "keys" / "dayz.bikey").write_text("key")
    (install / "DayZServer").write_text("#!/bin/sh\n")
    (install / "DayZServer").chmod(0o755)
    (install / "serverDZ.cfg").write_text("hostname = \"x\";\n")
    (apps / f"appmanifest_{appid}.acf").write_text(
        f'"AppState"\n{{\n\t"appid"\t\t"{appid}"\n\t"StateFlags"\t\t"{state}"\n'
        f'\t"installdir"\t\t"{installdir}"\n\t"buildid"\t\t"26220720"\n}}\n'
    )
    return root


def run(script: str, *args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    shell = "bash" if script in BASH else "sh"
    return subprocess.run(
        [shell, str(SCRIPTS / script), *args], env=env, capture_output=True, text=True, timeout=60, check=False
    )


def isolated_env(tmp_path: Path, steam: Path | None) -> dict[str, str]:
    home = tmp_path / "home"
    home.mkdir(exist_ok=True)
    env = {"PATH": os.environ["PATH"], "HOME": str(home)}
    if steam is not None:
        env["STEAM_ROOT"] = str(steam)
    return env


@pytest.mark.parametrize("script", POSIX + BASH)
def test_the_script_parses(script: str) -> None:
    subprocess.run(["bash" if script in BASH else "sh", "-n", str(SCRIPTS / script)], check=True)


@pytest.mark.skipif(shutil.which("shellcheck") is None, reason="shellcheck is not installed")
@pytest.mark.parametrize("script", POSIX + BASH)
def test_shellcheck_finds_no_warnings(script: str) -> None:
    done = subprocess.run(
        ["shellcheck", "-S", "warning", str(SCRIPTS / script)], capture_output=True, text=True, check=False
    )
    assert done.returncode == 0, done.stdout


def test_free_ports_are_distinct_spaced_and_not_defaults() -> None:
    done = run("free-ports.sh", "3")
    ports = [int(p) for p in done.stdout.split()]
    assert len(ports) == 3
    assert all(not 2300 <= p < 2310 and p not in (27015, 27016, 27017) for p in ports)
    assert all(abs(a - b) >= 10 for i, a in enumerate(ports) for b in ports[i + 1 :])


def test_find_dayzserver_reads_the_manifest(tmp_path: Path) -> None:
    steam = fake_steam(tmp_path)
    done = run("find-dayzserver.sh", "-v", env=isolated_env(tmp_path, steam))
    assert done.returncode == 0, done.stderr
    assert done.stdout.strip() == str((steam / "steamapps" / "common" / "DayZServer").resolve())
    assert "26220720" in done.stderr


def test_find_dayzserver_without_an_install_says_how_to_get_one(tmp_path: Path) -> None:
    (tmp_path / "steam" / "steamapps").mkdir(parents=True)
    done = run("find-dayzserver.sh", env=isolated_env(tmp_path, tmp_path / "steam"))
    assert done.returncode == 1
    assert "223350" in done.stderr


def test_make_server_tree_links_steam_and_keeps_storage_in_the_tree(tmp_path: Path) -> None:
    steam = fake_steam(tmp_path)
    install = steam / "steamapps" / "common" / "DayZServer"
    tree = tmp_path / "tree"
    done = run("make-server-tree.sh", str(tree), str(install), env=isolated_env(tmp_path, steam))
    assert done.returncode == 0, done.stderr
    assert (tree / "DayZServer").is_symlink()
    assert (tree / "serverDZ.cfg").is_file() and not (tree / "serverDZ.cfg").is_symlink()
    mission = tree / "mpmissions" / "dayzOffline.chernarusplus"
    assert mission.is_dir() and not mission.is_symlink()
    assert (mission / "init.c").is_symlink()
    assert not (mission / "storage_1").exists()
    assert (tree / "keys" / "dayz.bikey").is_symlink()
    assert (tree / "profiles").is_dir()


def test_make_server_tree_refuses_a_tree_inside_the_install(tmp_path: Path) -> None:
    steam = fake_steam(tmp_path)
    install = steam / "steamapps" / "common" / "DayZServer"
    done = run("make-server-tree.sh", str(install / "tree"), str(install), env=isolated_env(tmp_path, steam))
    assert done.returncode == 2
    assert "outside the Steam install" in done.stderr


def test_api_index_builds_and_answers(tmp_path: Path) -> None:
    scripts = tmp_path / "scripts"
    (scripts / "3_Game").mkdir(parents=True)
    (scripts / "4_World").mkdir()
    (scripts / "3_Game" / "base.c").write_text("class EntityAI : Managed\n{\n\tvoid OnCEIterate(float t, float e);\n}\n")
    (scripts / "4_World" / "item.c").write_text(
        "class ItemBase : EntityAI\n{\n\toverride void OnCEIterate(float t, float e) {}\n\tint m_Count;\n}\n"
    )
    out = tmp_path / "api"
    subprocess.run([sys.executable, str(SCRIPTS / "build-api-index.py"), str(scripts), str(out)], check=True)
    env = dict(os.environ, DAYZ_API_DIR=str(out))
    chain = subprocess.run(
        [sys.executable, str(SCRIPTS / "dayz-api.py"), "chain", "ItemBase"], env=env, capture_output=True, text=True
    )
    assert chain.stdout.strip().startswith("ItemBase > EntityAI")
    found = subprocess.run(
        [sys.executable, str(SCRIPTS / "dayz-api.py"), "find", "OnCEIterate"], env=env, capture_output=True, text=True
    )
    assert "EntityAI: void OnCEIterate" in found.stdout


def test_api_lookup_without_an_index_says_how_to_build_one(tmp_path: Path) -> None:
    env = dict(os.environ, DAYZ_API_DIR=str(tmp_path / "none"))
    done = subprocess.run(
        [sys.executable, str(SCRIPTS / "dayz-api.py"), "class", "PlayerBase"], env=env, capture_output=True, text=True
    )
    assert done.returncode != 0
    assert "build-api-index.py" in done.stderr


def test_mod_pack_init_keeps_secrets_out_of_git(tmp_path: Path) -> None:
    project = tmp_path / "MyMod"
    project.mkdir()
    done = run("dayz-mod-pack.sh", "-C", str(project), "init", "MyMod", env=isolated_env(tmp_path, None))
    assert done.returncode == 0, done.stderr
    ignored = (project / ".gitignore").read_text().split()
    assert "secrets/" in ignored and "*.biprivatekey" in ignored
    assert 'WORKSHOP_TAGS="Mod"' in (project / ".dayzmod").read_text()


def _is_dayzmake(tool: str | None) -> bool:
    if tool is None:
        return False
    out = subprocess.run([tool, "-h"], capture_output=True, text=True, check=False)
    return "--proton-binarize" in out.stdout + out.stderr


@pytest.mark.skipif(not _is_dayzmake(shutil.which("dayzmake")), reason="dayzmake (bzed's fork) is not installed")
def test_autotest_mod_builds_signs_and_verifies(tmp_path: Path) -> None:
    project = tmp_path / "autotest"
    shutil.copytree(AUTOTEST, project)
    subprocess.run(["git", "init", "-q", str(project)], check=True)
    env = isolated_env(tmp_path, None)
    for step in ("keygen", "build", "check"):
        done = run("dayz-mod-pack.sh", "-C", str(project), step, env=env)
        assert done.returncode == 0, f"{step}: {done.stdout}{done.stderr}"
    content = project / "build" / "@AutoTest"
    assert (content / "addons" / "AutoTest.pbo.AutoTest.bisign").is_file()
    assert (content / "keys" / "AutoTest.bikey").is_file()
    assert not list(content.rglob("*.biprivatekey"))
