"""The local-server, client and packaging helpers from bzed/dayz-dev-plugin, without Steam or DayZ.

What needs a Steam install, a game or Proton was measured by hand (see
skills/dayz-test-ingame/references/linux-native-server.md); these tests cover the scripts
themselves: syntax, shellcheck, and the parts that run on a fake Steam tree.
"""

from __future__ import annotations

import os
import platform
import shutil
import struct
import subprocess
import sys
import time
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
    assert not (install / "tree").exists()


def test_experimental_workshop_falls_back_to_the_stable_items(tmp_path: Path) -> None:
    steam = fake_steam(tmp_path, appid=221100, installdir="DayZ")
    (steam / "steamapps" / "workshop" / "content" / "221100" / "1559212036").mkdir(parents=True)
    done = run("find-dayzserver.sh", "-e", "-w", env=isolated_env(tmp_path, steam))
    assert done.returncode == 0, done.stderr
    assert done.stdout.strip().endswith("workshop/content/221100")


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
    subprocess.run(["git", "init", "-q", str(project)], check=True)
    done = run("dayz-mod-pack.sh", "-C", str(project), "init", "MyMod", env=isolated_env(tmp_path, None))
    assert done.returncode == 0, done.stderr
    for secret_path in ("secrets/MyMod.biprivatekey", "root_leak.biprivatekey", "build/@MyMod/addons/x.pbo"):
        chk = subprocess.run(["git", "-C", str(project), "check-ignore", "-q", secret_path], check=False)
        assert chk.returncode == 0, f"{secret_path} is not git-ignored"
    not_ignored = subprocess.run(["git", "-C", str(project), "check-ignore", "-q", "keys/MyMod.bikey"], check=False)
    assert not_ignored.returncode != 0
    assert 'WORKSHOP_TAGS="Mod"' in (project / ".dayzmod").read_text()


def _is_dayzmake(tool: str | None) -> bool:
    if tool is None:
        return False
    out = subprocess.run([tool, "-h"], capture_output=True, text=True, check=False)
    return "--proton-binarize" in out.stdout + out.stderr


# --- S1-S9 negative tests ---------------------------------------------------

requires_x86 = pytest.mark.skipif(platform.machine() not in ("x86_64", "AMD64"), reason="needs the x86_64 ELF pause fixture")


def _pause_binary(path: Path) -> None:
    assert platform.machine() in ("x86_64", "AMD64")
    path.parent.mkdir(parents=True, exist_ok=True)
    code = bytes.fromhex("b8220000000f05ebf7")
    total = 64 + 56 + len(code)
    elf = struct.pack("<16sHHIQQQIHHHHHH", b"\x7fELF\x02\x01\x01" + b"\x00" * 9, 2, 62, 1, 0x400078, 64, 0, 0, 64, 56, 1, 0, 0, 0) + struct.pack("<IIQQQQQQ", 1, 5, 0, 0x400000, 0x400000, total, total, 0x1000) + code
    path.write_bytes(elf)
    path.chmod(0o755)


def _wait_gone(pid: int, seconds: float = 5.0) -> bool:
    deadline = time.time() + seconds
    while time.time() < deadline:
        stat = Path(f"/proc/{pid}/stat")
        if not stat.exists():
            return True
        try:
            if stat.read_text().rsplit(")", 1)[1].split()[0] == "Z":
                return True
        except (OSError, IndexError):
            return True
        time.sleep(0.05)
    return False


def _kill_process_tree(pid: int) -> None:
    if pid <= 0 or pid == os.getpid():
        return
    proc = Path("/proc")
    children: list[int] = []
    if proc.exists():
        for entry in proc.iterdir():
            if not entry.name.isdigit():
                continue
            cpid = int(entry.name)
            if cpid in (pid, os.getpid()):
                continue
            try:
                ppid = int((entry / "stat").read_text().rsplit(")", 1)[1].split()[1])
            except (OSError, IndexError, ValueError):
                continue
            if ppid == pid:
                children.append(cpid)
    for child in children:
        _kill_process_tree(child)
    try:
        os.kill(pid, 9)
    except OSError:
        pass
    _wait_gone(pid, 2.0)


def _kill_matching(needle: str, pids_file: Path | None = None) -> None:
    roots: set[int] = set()
    if pids_file is not None and pids_file.exists():
        for line in pids_file.read_text(errors="replace").splitlines():
            line = line.strip()
            if line.isdigit():
                roots.add(int(line))
    proc = Path("/proc")
    if proc.exists():
        for entry in proc.iterdir():
            if not entry.name.isdigit() or int(entry.name) == os.getpid():
                continue
            try:
                argv = (entry / "cmdline").read_bytes().decode(errors="surrogateescape")
            except OSError:
                continue
            if needle in argv:
                roots.add(int(entry.name))
    for pid in roots:
        _kill_process_tree(pid)


def _env_with_bin(tmp_path: Path, steam: Path | None, bin_dir: Path) -> dict[str, str]:
    env = isolated_env(tmp_path, steam)
    env["PATH"] = f"{bin_dir}{os.pathsep}{env['PATH']}"
    return env


def _fake_dayzmake(tmp_path: Path, entries: dict) -> Path:
    bin_dir = tmp_path / "fakebin"
    bin_dir.mkdir(exist_ok=True)
    tool = bin_dir / "dayzmake"
    tool.write_text(
        "#!/usr/bin/env python3\n"
        "import os, pathlib, sys\n"
        f"ENTRIES = {entries!r}\n"
        "a = sys.argv[1:]\n"
        "if a and a[0] in ('-h', '--help'): print('--proton-binarize')\n"
        "elif a and a[0] == '--version': print('dayzmake v1.0.0')\n"
        "elif a and a[0] == 'inspect': sys.stdout.write(open(os.environ['FAKE_LISTING']).read())\n"
        "elif a and a[0] == 'cat':\n"
        "    inner, target = a[2], a[3]\n"
        "    act = ENTRIES.get(inner)\n"
        "    if act is None or act[0] == 'missing': print('not found')\n"
        "    elif act[0] == 'ioerror':\n"
        "        open(target, 'w').write(act[1])\n"
        "        sys.stderr.write('I/O error\\n')\n"
        "        sys.exit(1)\n"
        "    elif act[0] == 'link':\n"
        "        p = pathlib.Path(target); p.write_text('link-entry'); os.symlink(act[1], str(p.parent / act[2]))\n"
        "    else: open(target, 'w').write(act[1])\n"
        "elif a and a[0] == 'derapify': open(a[3], 'w').write('derapified\\n')\n"
        "elif a and a[0] == 'keygen':\n"
        "    stem = a[-1]\n"
        "    open(stem + '.biprivatekey', 'w').write('priv\\n')\n"
        "    open(stem + '.bikey', 'w').write('pub\\n')\n"
        "elif a and a[0] in ('build', 'pack'):\n"
        "    open(a[-1], 'w').write('pbo')\n"
        "elif a and a[0] == 'sign':\n"
        "    priv, pbo = pathlib.Path(a[-2]), pathlib.Path(a[-1])\n"
        "    (pbo.parent / f'{pbo.name}.{priv.stem}.bisign').write_text('sig\\n')\n"
        "elif a and a[0] == 'verify':\n"
        "    for req in a[1:4]:\n"
        "        if not pathlib.Path(req).is_file():\n"
        "            sys.stderr.write(f'missing {req}\\n')\n"
        "            sys.exit(1)\n"
    )
    tool.chmod(0o755)
    return bin_dir


def _valid_mod_project(tmp_path: Path, mod_name: str = "MyMod") -> tuple[Path, dict[str, str]]:
    bin_dir = _fake_dayzmake(tmp_path, {})
    project = tmp_path / mod_name
    (project / "src" / "Addon").mkdir(parents=True, exist_ok=True)
    (project / "src" / "Addon" / "config.cpp").write_text("class CfgPatches {};\n")
    (project / "keys").mkdir(exist_ok=True)
    (project / "keys" / f"{mod_name}.bikey").write_text("pub\n")
    (project / "secrets").mkdir(exist_ok=True)
    (project / "secrets" / f"{mod_name}.biprivatekey").write_text("priv\n")
    (project / ".dayzmod").write_text(f"MOD_NAME={mod_name}\n")
    env = _env_with_bin(tmp_path, None, bin_dir)
    env["DAYZMAKE"] = "dayzmake"
    return project, env


def _make_install(tmp_path: Path) -> Path:
    install = tmp_path / "install"
    (install / "dta").mkdir(parents=True)
    (install / "dta" / "x.pbo").write_text("fake pbo")
    return install


def _extract(tmp_path: Path, bin_dir: Path, install: Path, out: Path, *extra: str) -> subprocess.CompletedProcess[str]:
    env = _env_with_bin(tmp_path, None, bin_dir)
    env["DAYZMAKE"] = "dayzmake"
    env["FAKE_LISTING"] = str(tmp_path / "listing.txt")
    return run("extract-dayz-sources.sh", *extra, str(install), str(out), env=env)


def test_extract_rejects_pbo_prefix_escape(tmp_path: Path) -> None:
    bin_dir = _fake_dayzmake(tmp_path, {r"scripts\a.c": ("content", "class A {}\n")})
    (tmp_path / "listing.txt").write_text("- prefix=../../../escape\n# Files: 1\n====\n" + r"scripts\a.c" + " stored 9 9\n")
    install = _make_install(tmp_path)
    out = tmp_path / "out"
    done = _extract(tmp_path, bin_dir, install, out)
    assert done.returncode != 0
    assert "invalid PBO prefix" in done.stderr
    assert not (tmp_path / "escape").exists()
    assert not (out / "pbo-map.tsv").exists()


def test_extract_rejects_entry_escape_and_lf_listing(tmp_path: Path) -> None:
    bin_dir = _fake_dayzmake(tmp_path, {})
    (tmp_path / "listing.txt").write_text("- prefix=scripts\n# Files: 1\n====\n" + r"..\..\victim.c" + " stored 9 9\n")
    install = _make_install(tmp_path)
    done = _extract(tmp_path, bin_dir, install, tmp_path / "out")
    assert done.returncode != 0
    assert "invalid entry name" in done.stderr
    assert not (tmp_path / "victim.c").exists()
    (tmp_path / "listing.txt").write_text("- prefix=scripts\n# Files: 1\n====\nbad row with\nembedded lf stored 9 9\n")
    done = _extract(tmp_path, bin_dir, install, tmp_path / "out2")
    assert done.returncode != 0
    assert "invalid listing structure" in done.stderr


def test_extract_rejects_lf_forged_row_count_and_duplicate_names(tmp_path: Path) -> None:
    entries = {
        r"scripts\good.c": ("content", "class Good {}\n"),
        r"scripts\a.c": ("content", "class A {}\n"),
        r"scripts\b.c": ("content", "class B {}\n"),
        r"scripts\c.c": ("content", "class C {}\n"),
        r"scripts\forged.c": ("content", "class Forged {}\n"),
        "scripts/a.c": ("content", "class A2 {}\n"),
    }
    bin_dir = _fake_dayzmake(tmp_path, entries)
    install = _make_install(tmp_path)
    out = tmp_path / "out"
    (tmp_path / "listing.txt").write_text("- prefix=scripts\n# Files: 1\n====\n" + r"scripts\good.c" + " stored 9 9\n")
    assert _extract(tmp_path, bin_dir, install, out).returncode == 0
    # Fake inspect prints '# Files: 3' and four valid-looking rows (as when an LF in entry 3 forges row 4).
    (tmp_path / "listing.txt").write_text(
        "- prefix=scripts\n# Files: 3\n====\n"
        + r"scripts\a.c" + " stored 9 9\n"
        + r"scripts\b.c" + " stored 9 9\n"
        + r"scripts\c.c" + " stored 1 1\n"
        + r"scripts\forged.c" + " stored 9 9\n"
    )
    done = _extract(tmp_path, bin_dir, install, out)
    assert done.returncode != 0
    assert "invalid listing structure" in done.stderr
    assert not list(out.rglob("forged.c"))
    assert list(out.rglob("good.c"))
    # Duplicate normalised names (backslash vs slash) with matching '# Files: 2' are also rejected.
    (tmp_path / "listing.txt").write_text(
        "- prefix=scripts\n# Files: 2\n====\n"
        + r"scripts\a.c" + " stored 9 9\n"
        + "scripts/a.c stored 9 9\n"
    )
    done = _extract(tmp_path, bin_dir, install, out)
    assert done.returncode != 0
    assert "invalid listing structure" in done.stderr


def test_extract_cat_partial_ioerror_and_unreadable_dir_fail_without_promoting(tmp_path: Path) -> None:
    entries = {
        r"scripts\good.c": ("content", "class Good {}\n"),
        r"scripts\bad.c": ("ioerror", "partial"),
    }
    bin_dir = _fake_dayzmake(tmp_path, entries)
    install = _make_install(tmp_path)
    out = tmp_path / "out"
    (tmp_path / "listing.txt").write_text("- prefix=scripts\n# Files: 1\n====\n" + r"scripts\good.c" + " stored 9 9\n")
    assert _extract(tmp_path, bin_dir, install, out).returncode == 0
    assert list(out.rglob("good.c"))
    # Partial write + exit 1 ('I/O error') must fail the run and never promote over prior out.
    (tmp_path / "listing.txt").write_text("- prefix=scripts\n# Files: 1\n====\n" + r"scripts\bad.c" + " stored 9 9\n")
    done = _extract(tmp_path, bin_dir, install, out)
    assert done.returncode != 0
    assert "cat failed" in done.stderr
    assert list(out.rglob("good.c"))
    assert not list(out.rglob("bad.c"))
    if hasattr(os, "geteuid") and os.geteuid() != 0:
        (tmp_path / "listing.txt").write_text("- prefix=scripts\n# Files: 1\n====\n" + r"scripts\good.c" + " stored 9 9\n")
        (install / "dta").chmod(0o000)
        try:
            done_perm = _extract(tmp_path, bin_dir, install, out)
            assert done_perm.returncode != 0
            assert list(out.rglob("good.c"))
        finally:
            (install / "dta").chmod(0o755)


def test_extract_staging_does_not_reuse_preexisting_pid_dir(tmp_path: Path) -> None:
    bin_dir = _fake_dayzmake(tmp_path, {r"scripts\a.c": ("content", "class A {}\n")})
    (tmp_path / "listing.txt").write_text("- prefix=scripts\n# Files: 1\n====\n" + r"scripts\a.c" + " stored 9 9\n")
    install = _make_install(tmp_path)
    out = tmp_path / "out"
    env = _env_with_bin(tmp_path, None, bin_dir)
    env["DAYZMAKE"] = "dayzmake"
    env["FAKE_LISTING"] = str(tmp_path / "listing.txt")
    # Pre-create "$out.new.$$" with a stale file and exec into extract-dayz-sources.sh (keeping PID $$).
    done = subprocess.run(
        [
            "sh",
            "-c",
            'mkdir -p "$1.new.$$" && printf poisoned > "$1.new.$$/poisoned.c" && exec bash "$2" "$3" "$1"',
            "sh",
            str(out),
            str(SCRIPTS / "extract-dayz-sources.sh"),
            str(install),
        ],
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert done.returncode == 0, done.stderr
    assert list(out.rglob("a.c"))
    assert not list(out.rglob("poisoned.c"))


def test_extract_refuses_symlink_destination(tmp_path: Path) -> None:
    victim = tmp_path / "victim.txt"
    victim.write_text("original")
    entries = {r"scripts\link.c": ("link", str(victim), "victim.c"), r"scripts\victim.c": ("content", "pwned\n")}
    bin_dir = _fake_dayzmake(tmp_path, entries)
    (tmp_path / "listing.txt").write_text("- prefix=scripts\n# Files: 2\n====\n" + r"scripts\link.c" + " stored 9 9\n" + r"scripts\victim.c" + " stored 9 9\n")
    install = _make_install(tmp_path)
    done = _extract(tmp_path, bin_dir, install, tmp_path / "out")
    assert done.returncode != 0
    assert "symlink" in done.stderr
    assert victim.read_text() == "original"


def test_extract_reextract_drops_stale_and_failure_keeps_old(tmp_path: Path) -> None:
    entries = {r"scripts\a.c": ("content", "class A {}\n"), r"scripts\stale.c": ("content", "class S {}\n"), r"scripts\missing.c": ("missing",)}
    bin_dir = _fake_dayzmake(tmp_path, entries)
    install = _make_install(tmp_path)
    out = tmp_path / "out"
    (tmp_path / "listing.txt").write_text("- prefix=scripts\n# Files: 2\n====\n" + r"scripts\a.c" + " stored 9 9\n" + r"scripts\stale.c" + " stored 9 9\n")
    done = _extract(tmp_path, bin_dir, install, out)
    assert done.returncode == 0, done.stderr
    assert (out / "scripts" / "scripts" / "stale.c").exists() or (out / "scripts" / "stale.c").exists() or list(out.rglob("stale.c"))
    # Second run: stale removed, no duplicate map rows.
    (tmp_path / "listing.txt").write_text("- prefix=scripts\n# Files: 1\n====\n" + r"scripts\a.c" + " stored 9 9\n")
    done = _extract(tmp_path, bin_dir, install, out)
    assert done.returncode == 0, done.stderr
    assert not list(out.rglob("stale.c"))
    rows = (out / "pbo-map.tsv").read_text().strip().splitlines()
    assert len(rows) == 1
    # Failed run (cat prints not found, exits 0 in real dayzmake) keeps the old tree.
    (tmp_path / "listing.txt").write_text("- prefix=scripts\n# Files: 1\n====\n" + r"scripts\missing.c" + " stored 9 9\n")
    done = _extract(tmp_path, bin_dir, install, out)
    assert done.returncode != 0
    assert list(out.rglob("a.c"))
    # Interrupted promotion is detected.
    (tmp_path / "out.old.999").mkdir()
    done = _extract(tmp_path, bin_dir, install, out)
    assert done.returncode != 0
    assert "mv --" in done.stderr


def test_extract_refuses_nonowned_out_without_force(tmp_path: Path) -> None:
    bin_dir = _fake_dayzmake(tmp_path, {r"scripts\a.c": ("content", "class A {}\n")})
    (tmp_path / "listing.txt").write_text("- prefix=scripts\n# Files: 1\n====\n" + r"scripts\a.c" + " stored 9 9\n")
    install = _make_install(tmp_path)
    out = tmp_path / "out"
    out.mkdir()
    (out / "mine.txt").write_text("mine")
    done = _extract(tmp_path, bin_dir, install, out)
    assert done.returncode != 0
    assert (out / "mine.txt").read_text() == "mine"
    done = _extract(tmp_path, bin_dir, install, out, "--force")
    assert done.returncode == 0, done.stderr


def test_make_server_tree_existing_profiles_in_source_stays_private(tmp_path: Path) -> None:
    steam = fake_steam(tmp_path)
    install = steam / "steamapps" / "common" / "DayZServer"
    (install / "profiles").mkdir()
    (install / "profiles" / "secret.txt").write_text("steam")
    tree = tmp_path / "tree"
    done = run("make-server-tree.sh", str(tree), str(install), env=isolated_env(tmp_path, steam))
    assert done.returncode == 0, done.stderr
    assert (tree / "profiles").is_dir() and not (tree / "profiles").is_symlink()
    assert not (tree / "profiles" / "secret.txt").exists()


def test_make_server_tree_mpmissions_link_into_source_is_replaced(tmp_path: Path) -> None:
    steam = fake_steam(tmp_path)
    install = steam / "steamapps" / "common" / "DayZServer"
    tree = tmp_path / "tree"
    done = run("make-server-tree.sh", str(tree), str(install), env=isolated_env(tmp_path, steam))
    assert done.returncode == 0, done.stderr
    shutil.rmtree(tree / "mpmissions")
    (tree / "mpmissions").symlink_to(install / "mpmissions")
    done = run("make-server-tree.sh", str(tree), str(install), env=isolated_env(tmp_path, steam))
    assert done.returncode == 0, done.stderr
    assert (tree / "mpmissions").is_dir() and not (tree / "mpmissions").is_symlink()
    assert (tree / "mpmissions" / "dayzOffline.chernarusplus" / "init.c").is_symlink()


def test_make_server_tree_inside_install_with_missing_parents_creates_nothing(tmp_path: Path) -> None:
    steam = fake_steam(tmp_path)
    install = steam / "steamapps" / "common" / "DayZServer"
    done = run("make-server-tree.sh", str(install / "new" / "sub" / "tree"), str(install), env=isolated_env(tmp_path, steam))
    assert done.returncode == 2
    assert not (install / "new").exists()


def test_make_server_tree_dotdot_in_missing_tail_creates_nothing(tmp_path: Path) -> None:
    steam = fake_steam(tmp_path)
    install = steam / "steamapps" / "common" / "DayZServer"
    outside = tmp_path / "outside"
    outside.mkdir()
    tricky = f"{outside}/missing/../../steam/steamapps/common/DayZServer/new/tree"
    done = run("make-server-tree.sh", tricky, str(install), env=isolated_env(tmp_path, steam))
    assert done.returncode == 2
    assert not (outside / "missing").exists()
    assert not (install / "new").exists()


def test_make_server_tree_reused_mission_symlink_without_storage_is_replaced(tmp_path: Path) -> None:
    steam = fake_steam(tmp_path)
    install = steam / "steamapps" / "common" / "DayZServer"
    empty_mission = install / "mpmissions" / "EmptyMission"
    empty_mission.mkdir(parents=True)
    (empty_mission / "init.c").write_text("void main() {}\n")
    tree = tmp_path / "tree"
    done = run("make-server-tree.sh", str(tree), str(install), env=isolated_env(tmp_path, steam))
    assert done.returncode == 0, done.stderr
    # Plant an extra directory symlink 'alias' into an install mission that has no storage_* yet.
    (tree / "mpmissions" / "alias").symlink_to(empty_mission)
    (tree / "keys" / "sub").symlink_to(install / "keys")
    done = run("make-server-tree.sh", str(tree), str(install), env=isolated_env(tmp_path, steam))
    assert done.returncode == 0, done.stderr
    assert "replacing directory symlink" in done.stderr
    alias = tree / "mpmissions" / "alias"
    assert alias.is_dir() and not alias.is_symlink()
    assert (alias / "init.c").is_symlink()
    (alias / "storage_1").mkdir()
    assert not (empty_mission / "storage_1").exists()
    assert (tree / "keys" / "sub").is_dir() and not (tree / "keys" / "sub").is_symlink()


def _fake_client_steam(tmp_path: Path) -> Path:
    steam = tmp_path / "steam"
    game = steam / "steamapps" / "common" / "DayZ"
    game.mkdir(parents=True)
    (game / "DayZ_x64.exe").write_text("exe")
    (steam / "compatibilitytools.d" / "GE-Proton11-1").mkdir(parents=True)
    return steam


@requires_x86
def test_headless_stop_does_not_signal_foreign_pid(tmp_path: Path) -> None:
    victim_bin = tmp_path / "victim"
    _pause_binary(victim_bin)
    helper = subprocess.Popen([str(victim_bin)])
    try:
        state = tmp_path / "state"
        state.mkdir()
        (state / "sway.pid").write_text(f"{helper.pid}\n")
        done = run("dayz-client-headless.sh", "stop", str(state), env=isolated_env(tmp_path, None))
        assert helper.poll() is None, "foreign process was signalled"
        assert not (state / "sway.pid").exists()
    finally:
        helper.kill()
        helper.wait(timeout=5)


@requires_x86
def test_headless_start_then_stop_signals_our_sway(tmp_path: Path) -> None:
    steam = _fake_client_steam(tmp_path)
    bin_dir = tmp_path / "fakebin"
    bin_dir.mkdir()
    _pause_binary(bin_dir / "sway")
    (bin_dir / "grim").write_text("#!/bin/sh\nexit 0\n")
    (bin_dir / "grim").chmod(0o755)
    state = tmp_path / "state"
    env = _env_with_bin(tmp_path, steam, bin_dir)
    pid = -1
    try:
        done = run("dayz-client-headless.sh", "start", str(state), env=env)
        assert done.returncode == 0, done.stderr
        pid = int((state / "sway.pid").read_text().strip())
        assert Path(f"/proc/{pid}").exists()
        done = run("dayz-client-headless.sh", "stop", str(state), env=env)
        assert done.returncode == 0, done.stderr
        assert _wait_gone(pid), "our sway was not signalled"
        assert not (state / "sway.pid").exists()
        pid = -1
    finally:
        _kill_matching(str(state))


@requires_x86
def test_headless_refuses_disallowed_state_path_and_newline_symlink(tmp_path: Path) -> None:
    steam = _fake_client_steam(tmp_path)
    bin_dir = tmp_path / "fakebin"
    bin_dir.mkdir()
    _pause_binary(bin_dir / "sway")
    env = _env_with_bin(tmp_path, steam, bin_dir)
    for bad_name in ("st a'te $(touch x) `tick`", "state\nwith-newline", r"a\tb"):
        bad_state = tmp_path / bad_name
        done = run("dayz-client-headless.sh", "start", str(bad_state), env=env)
        assert done.returncode != 0
        assert "may only contain" in done.stderr
        assert not bad_state.exists()
        assert not (tmp_path / "x").exists()
    # A symlink to a directory whose name ends in a newline must be refused (not truncated to sibling 'state').
    sibling = tmp_path / "state"
    nl_dir = tmp_path / "state\n"
    nl_dir.mkdir()
    alias = tmp_path / "alias"
    alias.symlink_to(nl_dir)
    pid = -1
    try:
        done = run("dayz-client-headless.sh", "start", str(sibling), env=env)
        assert done.returncode == 0, done.stderr
        pid = int((sibling / "sway.pid").read_text().strip())
        done_stop = run("dayz-client-headless.sh", "stop", str(alias), env=env)
        assert done_stop.returncode != 0
        assert "may only contain" in done_stop.stderr
        assert not _wait_gone(pid, 0.1), "sibling session in 'state' was signalled through newline symlink"
        assert (sibling / "sway.pid").exists()
        done_start = run("dayz-client-headless.sh", "start", str(alias), env=env)
        assert done_start.returncode != 0
        assert "may only contain" in done_start.stderr
        assert not list(nl_dir.iterdir())
        assert not _wait_gone(pid, 0.1)
        done_clean = run("dayz-client-headless.sh", "stop", str(sibling), env=env)
        assert done_clean.returncode == 0, done_clean.stderr
        assert _wait_gone(pid)
    finally:
        _kill_process_tree(pid)
        _kill_matching(str(tmp_path))


@requires_x86
def test_headless_invalid_wait_env_launches_nothing(tmp_path: Path) -> None:
    steam = _fake_client_steam(tmp_path)
    bin_dir = tmp_path / "fakebin"
    bin_dir.mkdir()
    marker = tmp_path / "launched.marker"
    for cmd_name in ("setsid", "sway"):
        p = bin_dir / cmd_name
        p.write_text(f"#!/bin/sh\n: > '{marker}'\nexit 0\n")
        p.chmod(0o755)
    state = tmp_path / "state"
    env = _env_with_bin(tmp_path, steam, bin_dir)
    env["DAYZ_CLIENT_START_WAIT_TENTHS"] = "abc"
    try:
        done = run("dayz-client-headless.sh", "start", str(state), env=env)
        assert done.returncode != 0
        assert "DAYZ_CLIENT_START_WAIT_TENTHS" in done.stderr
        assert not marker.exists(), "setsid or sway was launched despite invalid wait env"
        assert not (state / "sway.pid").exists()
        # Post-launch failure (wait=0) routes through failed_start_cleanup (sway.cancel + signal).
        real_bin = tmp_path / "realbin"
        real_bin.mkdir()
        _pause_binary(real_bin / "sway")
        env2 = _env_with_bin(tmp_path, steam, real_bin)
        env2["DAYZ_CLIENT_START_WAIT_TENTHS"] = "0"
        done_zero = run("dayz-client-headless.sh", "start", str(state), env=env2)
        assert done_zero.returncode != 0
        assert (state / "sway.cancel").exists()
        assert not (state / "sway.pid").exists()
        assert not (state / "sway.identity").exists()
    finally:
        _kill_matching(str(tmp_path))


@requires_x86
def test_headless_steam_root_with_spaces_and_metachars_quotes_safely(tmp_path: Path) -> None:
    steam_holder = tmp_path / "st eam ' $(touch x) `tick`"
    steam_holder.mkdir()
    steam = _fake_client_steam(steam_holder)
    capture = tmp_path / "capture.txt"
    pids_file = tmp_path / "pids.txt"
    runtime = steam / "steamapps" / "common" / "SteamLinuxRuntime_4"
    runtime.mkdir(parents=True)
    entry = runtime / "_v2-entry-point"
    entry.write_text(
        "#!/bin/sh\n"
        f"printf '%s\\n' \"$$\" >> '{pids_file}'\n"
        "while [ \"$1\" != \"--\" ]; do shift; done; shift; exec \"$@\"\n"
    )
    entry.chmod(0o755)
    tool = steam / "compatibilitytools.d" / "GE-Proton11-1" / "proton"
    tool.write_text(
        "#!/bin/sh\n"
        f"printf '%s\\n' \"$$\" >> '{pids_file}'\n"
        f"printf '%s\\n' \"$STEAM_COMPAT_INSTALL_PATH\" \"$@\" > '{capture}'\n"
    )
    tool.chmod(0o755)
    realbin = tmp_path / "realbin"
    realbin.mkdir()
    _pause_binary(realbin / "sway")
    bin_dir = tmp_path / "fakebin"
    bin_dir.mkdir()
    fake_sway = bin_dir / "sway"
    fake_sway.write_text(
        "#!/bin/sh\n"
        f"printf '%s\\n' \"$$\" >> '{pids_file}'\n"
        "conf=$2\n"
        "line=$(sed -n 's/^exec //p' \"$conf\")\n"
        "( sh -c \"$line\" )\n"
        f"exec '{realbin}/sway' \"$@\"\n"
    )
    fake_sway.chmod(0o755)
    state = tmp_path / "state"
    env = _env_with_bin(tmp_path, steam, bin_dir)
    pid = -1
    try:
        done = run("dayz-client-headless.sh", "start", str(state), "-mod=@a;@b", env=env)
        assert done.returncode == 0, done.stderr
        pid = int((state / "sway.pid").read_text().strip())
        assert capture.exists(), "game.sh did not reach the fake proton"
        text = capture.read_text()
        assert str(steam / "steamapps" / "common" / "DayZ") in text
        assert "-mod=@a;@b" in text
        assert not (state / "x").exists()
        assert not (tmp_path / "x").exists()
        assert not (steam_holder / "x").exists()
        assert str(steam) not in (state / "game.sh").read_text()
        assert "exec ./game.sh" in (state / "sway.conf").read_text()
        subprocess.run(["sh", "-n", str(state / "game.sh")], check=True)
        done = run("dayz-client-headless.sh", "stop", str(state), env=env)
        assert done.returncode == 0, done.stderr
        assert _wait_gone(pid)
        pid = -1
    finally:
        _kill_process_tree(pid)
        _kill_matching(str(tmp_path), pids_file)


def test_dayzmod_code_is_rejected_not_executed(tmp_path: Path) -> None:
    project = tmp_path / "MyMod"
    project.mkdir()
    (project / ".dayzmod").write_text("MOD_NAME=$(touch pwned)\n")
    done = run("dayz-mod-pack.sh", "-C", str(project), "publish-hint", env=isolated_env(tmp_path, None))
    assert done.returncode != 0
    assert "line 1" in done.stderr
    assert not (project / "pwned").exists() and not (tmp_path / "pwned").exists()
    (project / ".dayzmod").write_text("MOD_NAME=MyMod\nEVIL=1\n")
    done = run("dayz-mod-pack.sh", "-C", str(project), "publish-hint", env=isolated_env(tmp_path, None))
    assert done.returncode != 0
    assert "line 2" in done.stderr


def test_dayzmod_symlinked_content_is_not_deleted_through(tmp_path: Path) -> None:
    project, env = _valid_mod_project(tmp_path, "Safe")
    (project / "build").mkdir(parents=True)
    victim = tmp_path / "victim"
    (victim / "addons").mkdir(parents=True)
    (victim / "addons" / "keep.txt").write_text("keep")
    (project / "build" / "@Safe").symlink_to(victim)
    done = run("dayz-mod-pack.sh", "-C", str(project), "build", env=env)
    assert done.returncode != 0
    assert "is not a real directory under the project; refusing" in done.stderr
    assert (victim / "addons" / "keep.txt").read_text() == "keep"


def test_static_private_key_aborts_before_any_copy(tmp_path: Path) -> None:
    project, env = _valid_mod_project(tmp_path, "MyMod")
    content = project / "build" / "@MyMod"
    content.mkdir(parents=True)
    # Item 18: stale key in content must be cleaned BEFORE static/ scan aborts.
    (content / "old.biprivatekey").write_text("stale")
    (project / "static").mkdir(parents=True)
    (project / "static" / "leak.biprivatekey").write_text("secret")
    (project / "static" / "logo.txt").write_text("logo")
    done = run("dayz-mod-pack.sh", "-C", str(project), "build", env=env)
    assert done.returncode != 0
    assert "a .biprivatekey is inside static/; refusing before any copy" in done.stderr
    assert not (content / "logo.txt").exists()
    assert not (content / "old.biprivatekey").exists()
    assert not list(content.rglob("*.biprivatekey"))


def test_static_scan_with_many_files_does_not_miss_key_under_pipefail(tmp_path: Path) -> None:
    project, env = _valid_mod_project(tmp_path, "MyMod")
    static = project / "static"
    static.mkdir(parents=True)
    # Exceed a 64 KiB pipe buffer so an early-closing 'find ... | grep -q .' would SIGPIPE under pipefail.
    for idx in range(4000):
        (static / f"leak_{idx:04d}.biprivatekey").write_text("secret")
    done = run("dayz-mod-pack.sh", "-C", str(project), "build", env=env)
    assert done.returncode != 0
    assert "a .biprivatekey is inside static/; refusing before any copy" in done.stderr
    assert not (project / "build" / "@MyMod").exists()


def test_build_removes_stale_private_key_from_content(tmp_path: Path) -> None:
    project, env = _valid_mod_project(tmp_path, "MyMod")
    victim = tmp_path / "victim.biprivatekey"
    victim.write_text("outside-keep")
    content = project / "build" / "@MyMod"
    content.mkdir(parents=True)
    (content / "old.biprivatekey").write_text("stale")
    # Item 1: path containing an embedded newline whose second line is the absolute path of 'victim'.
    tricky = content.joinpath("split\n", *victim.parts[1:])
    tricky.parent.mkdir(parents=True, exist_ok=True)
    tricky.write_text("stale-nl")
    done = run("dayz-mod-pack.sh", "-C", str(project), "build", env=env)
    assert done.returncode == 0, done.stdout + done.stderr
    assert not list(content.rglob("*.biprivatekey"))
    assert victim.read_text() == "outside-keep"


def test_build_replaces_retained_symlinks_in_content_without_following(tmp_path: Path) -> None:
    project, env = _valid_mod_project(tmp_path, "MyMod")
    (project / "mod.cpp").write_text('name = "MyMod";\n')
    victim_meta = tmp_path / "victim_meta.cpp"
    victim_meta.write_text("original-meta")
    victim_mod = tmp_path / "victim_mod.cpp"
    victim_mod.write_text("original-mod")
    content = project / "build" / "@MyMod"
    content.mkdir(parents=True)
    (content / "meta.cpp").symlink_to(victim_meta)
    (content / "mod.cpp").symlink_to(victim_mod)
    done = run("dayz-mod-pack.sh", "-C", str(project), "build", env=env)
    assert done.returncode == 0, done.stdout + done.stderr
    assert "removing symlink" in done.stderr
    assert (content / "meta.cpp").is_file() and not (content / "meta.cpp").is_symlink()
    assert (content / "mod.cpp").is_file() and not (content / "mod.cpp").is_symlink()
    assert victim_meta.read_text() == "original-meta"
    assert victim_mod.read_text() == "original-mod"


def test_mod_pack_key_name_env_override_and_dayzmod_precedence(tmp_path: Path) -> None:
    bin_dir = _fake_dayzmake(tmp_path, {})
    project = tmp_path / "autotest"
    shutil.copytree(AUTOTEST, project)
    subprocess.run(["git", "init", "-q", str(project)], check=True)
    env = _env_with_bin(tmp_path, None, bin_dir)
    env["DAYZMAKE"] = "dayzmake"
    env["KEY_NAME"] = "ExternalKey"
    for step in ("keygen", "build", "check"):
        done = run("dayz-mod-pack.sh", "-C", str(project), step, env=env)
        assert done.returncode == 0, f"{step}: {done.stdout}{done.stderr}"
    assert (project / "secrets" / "ExternalKey.biprivatekey").is_file()
    assert (project / "keys" / "ExternalKey.bikey").is_file()
    assert (project / "build" / "@AutoTest" / "addons" / "AutoTest.pbo.ExternalKey.bisign").is_file()
    # Explicit KEY_NAME in .dayzmod wins over environment KEY_NAME.
    project2 = tmp_path / "override_test"
    shutil.copytree(AUTOTEST, project2)
    subprocess.run(["git", "init", "-q", str(project2)], check=True)
    with (project2 / ".dayzmod").open("a") as fh:
        fh.write("KEY_NAME=FromConf\n")
    done = run("dayz-mod-pack.sh", "-C", str(project2), "keygen", env=env)
    assert done.returncode == 0, done.stderr
    assert (project2 / "keys" / "FromConf.bikey").is_file()
    assert not (project2 / "keys" / "ExternalKey.bikey").exists()


def test_publish_hint_validates_app_id_and_quotes_values(tmp_path: Path) -> None:
    holder = tmp_path / "dir with space"
    project = holder / "MyMod"
    project.mkdir(parents=True)
    (project / ".dayzmod").write_text('MOD_NAME=MyMod\nWORKSHOP_TAGS="Mod Mechanics"\n')
    bad_env = isolated_env(tmp_path, None)
    bad_env["WORKSHOP_APP_ID"] = "221100; printf X #"
    bad = run("dayz-mod-pack.sh", "-C", str(project), "publish-hint", env=bad_env)
    assert bad.returncode != 0
    assert "WORKSHOP_APP_ID" in bad.stderr
    assert "printf X" not in bad.stdout
    ok_env = isolated_env(tmp_path, None)
    ok_env["WORKSHOP_APP_ID"] = "221100"
    ok = run("dayz-mod-pack.sh", "-C", str(project), "publish-hint", env=ok_env)
    assert ok.returncode == 0, ok.stderr
    assert "--app-id 221100" in ok.stdout
    assert "dir\\ with\\ space" in ok.stdout or "'dir with space" in ok.stdout


@pytest.mark.parametrize("bad", ["x/../../victim", "..", "/abs", "a\\b", "a/b"])
def test_api_index_rejects_mod_escape(tmp_path: Path, bad: str) -> None:
    scripts = tmp_path / "scripts"
    (scripts / "3_Game").mkdir(parents=True)
    (scripts / "3_Game" / "base.c").write_text("class EntityAI : Managed {}\n")
    out = tmp_path / "api"
    done = subprocess.run([sys.executable, str(SCRIPTS / "build-api-index.py"), str(scripts), str(out), "--mod", bad], capture_output=True, text=True)
    assert done.returncode == 2
    assert not (tmp_path / "victim.txt.xz").exists()


def test_api_index_refuses_symlink_output(tmp_path: Path) -> None:
    scripts = tmp_path / "scripts"
    (scripts / "3_Game").mkdir(parents=True)
    (scripts / "3_Game" / "base.c").write_text("class EntityAI : Managed {}\n")
    out = tmp_path / "api"
    out.mkdir()
    victim = tmp_path / "victim.txt"
    victim.write_text("victim")
    (out / "mod-good.txt.xz").symlink_to(victim)
    done = subprocess.run([sys.executable, str(SCRIPTS / "build-api-index.py"), str(scripts), str(out), "--mod", "good"], capture_output=True, text=True)
    assert done.returncode == 2
    assert "symlink" in done.stderr
    assert victim.read_text() == "victim"
    # Default output (without --mod) must also refuse a pre-existing symlink.
    (out / "dayz-api.txt.xz").symlink_to(victim)
    done_default = subprocess.run([sys.executable, str(SCRIPTS / "build-api-index.py"), str(scripts), str(out)], capture_output=True, text=True)
    assert done_default.returncode == 2
    assert "symlink" in done_default.stderr
    assert victim.read_text() == "victim"


def test_free_ports_impossible_count_fails_at_once() -> None:
    done = run("free-ports.sh", "3902")
    assert done.returncode != 0
    assert "maximum" in done.stderr


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
