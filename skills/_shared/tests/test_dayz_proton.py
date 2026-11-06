"""dayz-proton.sh without Steam or Proton: what a runner can check.

Everything that starts a tool needs a Steam install and is measured by hand; see
skills/_shared/linux-proton.md. POSIX only: the script is the Linux route.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "dayz-proton.sh"

pytestmark = pytest.mark.skipif(os.name == "nt", reason="the Linux runner script")


def run(tmp_path: Path, *args: str, steam: bool = True) -> subprocess.CompletedProcess[str]:
    home = tmp_path / "home"
    home.mkdir(exist_ok=True)
    env = {"PATH": os.environ["PATH"], "HOME": str(home)}
    if steam:
        (tmp_path / "steam" / "steamapps").mkdir(parents=True, exist_ok=True)
        env["STEAM_ROOT"] = str(tmp_path / "steam")
    return subprocess.run(
        ["sh", str(SCRIPT), *args], env=env, capture_output=True, text=True, timeout=30, check=False
    )


def test_the_script_parses() -> None:
    subprocess.run(["sh", "-n", str(SCRIPT)], check=True)


@pytest.mark.skipif(shutil.which("shellcheck") is None, reason="shellcheck is not installed")
def test_shellcheck_finds_no_warnings() -> None:
    done = subprocess.run(
        ["shellcheck", "-S", "warning", str(SCRIPT)], capture_output=True, text=True, check=False
    )
    assert done.returncode == 0, done.stdout


def test_no_steam_install_is_named_not_guessed(tmp_path: Path) -> None:
    done = run(tmp_path, "doctor", steam=False)
    assert done.returncode != 0
    assert "no Steam install found" in done.stderr


def test_no_arguments_print_the_usage_and_fail(tmp_path: Path) -> None:
    done = run(tmp_path)
    assert done.returncode == 2
    assert "dayz-proton.sh doctor" in done.stderr


def test_winpath_maps_a_linux_path_to_z(tmp_path: Path) -> None:
    done = run(tmp_path, "winpath", "/var/lib/mods/@Mod")
    assert done.returncode == 0, done.stderr
    assert done.stdout.strip() == "Z:\\var\\lib\\mods\\@Mod"


def test_doctor_names_a_missing_proton_and_changes_nothing(tmp_path: Path) -> None:
    done = run(tmp_path, "doctor")
    assert "no Proton found" in done.stdout + done.stderr
    assert not list((tmp_path / "home").rglob("dayz-proton"))
