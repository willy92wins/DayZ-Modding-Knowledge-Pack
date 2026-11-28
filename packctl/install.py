"""Install the pack as one routed skill: <target>/<name>/SKILL.md plus siblings."""

from __future__ import annotations

import datetime as _dt
import json
import os
import re
import shutil
import tempfile
import zipfile
from pathlib import Path

from .common import git_commit, git_is_dirty, git_output

class InstallError(Exception):
    """An install or bundle step failed in a way the user can act on."""


MARKER = ".dayz-pack-bundle.json"
TEMPLATE_PATH = Path(__file__).with_name("router_template.md")
PLACEHOLDER = "{{ROUTING_TABLE}}"
COUNT_PLACEHOLDER = "{{SKILL_COUNT}}"
DESCRIPTION_LIMIT = 1024
SKILL_NAME_RE = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")

# Pre-rename (#214) unprefixed skill folders that old installs may still hold.
OLD_UNPREFIXED_NAMES = (
    "3d-generation-harness",
    "ai-3d-to-dayz",
    "ardy-motion-generation",
    "blender-animation",
    "blender-assembly",
    "blender-visual-review",
    "enforce-script-reference",
    "mixamo-retarget",
    "rigorous-data-audit",
    "rip-vehicle-import",
    "skill-conventions",
    "vehicle-proxy-contract",
    "vehicles-in-dayz",
)


def skill_folders(root: Path) -> list[Path]:
    skills = Path(root) / "skills"
    return sorted(
        p
        for p in skills.iterdir()
        if p.name.startswith("dayz-") and (p / "SKILL.md").is_file()
    )


def render_router(root: Path, template_path: Path | None = None) -> str:
    """Render the router SKILL.md deterministically from skills/dayz-*/SKILL.md."""
    from .validation import _parse_frontmatter

    template = (template_path or TEMPLATE_PATH).read_text(encoding="utf-8")
    if template.count(PLACEHOLDER) != 1:
        raise ValueError(f"router template needs exactly one {PLACEHOLDER}")
    entries: list[str] = []
    for folder in skill_folders(root):
        skill = folder / "SKILL.md"
        values, _, error = _parse_frontmatter(skill)
        if error:
            raise ValueError(f"{skill}: {error}")
        description = " ".join(str(values.get("description", "")).split())
        if not description:
            raise ValueError(f"{skill}: description is empty")
        entries.append(
            f"### `{folder.name}`\n\nRead `{folder.name}/SKILL.md`.\n\n{description}\n"
        )
    text = template.replace(COUNT_PLACEHOLDER, str(len(entries)))
    text = text.replace(PLACEHOLDER, "\n".join(entries).rstrip("\n"))
    return text.rstrip("\n") + "\n"


def router_description(rendered: str) -> str:
    """The front-matter description of a rendered (or template) router."""
    from .validation import _parse_frontmatter_text

    values, _, error = _parse_frontmatter_text(rendered)
    if error:
        raise ValueError(f"router frontmatter: {error}")
    return str(values.get("description", ""))


def _ignore(directory: str, names: list[str]) -> set[str]:
    skip = {n for n in names if n == "__pycache__" or n.endswith(".pyc")}
    # tests/ folders are for pack maintainers; only a skill's top level has one.
    if Path(directory).parent.name == "skills":
        skip |= {n for n in names if n == "tests"}
    return skip


def _leftovers(target: Path, name: str, skill_names: list[str]) -> list[str]:
    stale = set(skill_names) | {"_shared"} | set(OLD_UNPREFIXED_NAMES)
    stale.discard(name)
    if not target.is_dir():
        return []
    return sorted(
        e.name for e in target.iterdir() if e.name in stale and (e.is_dir() or e.is_symlink())
    )


def build_bundle(root: Path, destination: Path, *, router: str | None = None) -> list[str]:
    """Write the bundle tree (router SKILL.md, _shared/, dayz-*/) into destination.

    No marker, no leftover scan: deterministic and free of CLI side effects.
    Returns the skill folder names. destination must not hold a bundle yet.
    """
    root = Path(root).resolve()
    router = render_router(root) if router is None else router
    folders = skill_folders(root)
    for folder in [root / "skills" / "_shared", *folders]:
        shutil.copytree(folder, Path(destination) / folder.name, ignore=_ignore)
    (Path(destination) / "SKILL.md").write_text(router, encoding="utf-8", newline="\n")
    return [f.name for f in folders]


def build_link_bundle(root: Path, destination: Path, *, router: str | None = None) -> list[str]:
    """Like build_bundle, but _shared/ and dayz-*/ are symlinks into the repo.

    SKILL.md stays a real file: it is generated, not part of the repo.
    """
    root = Path(root).resolve()
    router = render_router(root) if router is None else router
    folders = skill_folders(root)
    for folder in [root / "skills" / "_shared", *folders]:
        try:
            os.symlink(folder, Path(destination) / folder.name, target_is_directory=True)
        except OSError as error:
            raise InstallError(
                f"cannot create a symlink ({error}). On Windows symlinks need Developer Mode"
                " or an elevated shell; install without --link to copy the files instead."
            ) from error
    (Path(destination) / "SKILL.md").write_text(router, encoding="utf-8", newline="\n")
    return [f.name for f in folders]


def _marker_text(name: str, skills: list[str], source_commit: str, **extra: object) -> str:
    data = {
        "installer": "packctl install",
        "name": name,
        "source_commit": source_commit,
        "skills": skills,
        **extra,
    }
    return json.dumps(data, indent=2, sort_keys=True) + "\n"


def _remove_tree(path: Path) -> None:
    """Remove a bundle without ever following a symlink into the repo."""
    if path.is_symlink() or path.is_file():
        path.unlink()
        return
    for entry in path.iterdir():
        if entry.is_symlink():
            try:
                entry.unlink()
            except OSError:
                entry.rmdir()  # Windows directory symlink / junction
    shutil.rmtree(path, ignore_errors=True)


def _busy(action: str, error: OSError) -> InstallError:
    return InstallError(
        f"could not {action} ({type(error).__name__}: {error}). Close Claude Code and any other"
        " program using the skills folder (editors, antivirus scans, file explorers), then retry."
    )


def install(
    root: Path,
    target: Path,
    *,
    name: str = "dayz",
    force: bool = False,
    dry_run: bool = False,
    link: bool = False,
) -> dict[str, object]:
    root = Path(root).resolve()
    target = Path(target)
    if not SKILL_NAME_RE.fullmatch(name) or len(name) > 64:
        raise ValueError(f"invalid bundle name: {name!r}")
    router = render_router(root)
    folders = skill_folders(root)
    skill_names = [f.name for f in folders]
    destination = target / name
    previous = "none"
    if destination.exists() or destination.is_symlink():
        marker = destination / MARKER
        if marker.is_file():
            previous = "bundle"
        elif force:
            previous = "foreign"
        else:
            raise FileExistsError(
                f"{destination} exists and was not created by packctl install; use --force to replace it"
            )
    result: dict[str, object] = {
        "destination": str(destination),
        "skills": skill_names,
        "router_bytes": len(router.encode("utf-8")),
        "replaced": previous,
        "dry_run": dry_run,
        "mode": "link" if link else "copy",
        "leftovers": _leftovers(target, name, skill_names),
    }
    if dry_run:
        return result

    target.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{name}.new-", dir=target))
    try:
        (build_link_bundle if link else build_bundle)(root, staging, router=router)
        (staging / MARKER).write_text(
            _marker_text(
                name,
                skill_names,
                git_commit(root),
                installed_at=_dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                mode="link" if link else "copy",
            ),
            encoding="utf-8",
            newline="\n",
        )
        if destination.exists() or destination.is_symlink():
            old = Path(tempfile.mkdtemp(prefix=f".{name}.old-", dir=target))
            old.rmdir()
            try:
                destination.rename(old)
            except OSError as error:
                raise _busy(f"move the existing {destination} aside", error) from error
            try:
                staging.rename(destination)
            except OSError as error:
                try:
                    old.rename(destination)
                except OSError:
                    raise InstallError(
                        f"could not install the new bundle and could not restore the old one;"
                        f" it is at {old}. Close Claude Code and any other program using the"
                        " folder, then rename it back."
                    ) from error
                raise _busy(f"move the new bundle to {destination}", error) from error
            _remove_tree(old)
        else:
            try:
                staging.rename(destination)
            except OSError as error:
                raise _busy(f"move the new bundle to {destination}", error) from error
    finally:
        if staging.exists():
            _remove_tree(staging)
    return result


FIXED_ZIP_TIME = (1980, 1, 1, 0, 0, 0)


def _executable_paths(root: Path) -> set[str]:
    out = git_output(root, "ls-files", "-s", "-z", "skills")
    paths = set()
    for item in out.split("\0"):
        meta, _, path = item.partition("\t")
        if meta.startswith("100755"):
            paths.add(path)
    return paths


def write_bundle_zip(root: Path, output: Path, *, name: str = "dayz") -> dict[str, object]:
    """Write a reproducible ZIP holding exactly the bundle tree under <name>/.

    Same inputs, same bytes: members sorted, fixed timestamps, stored (no
    compression), mode 0644 (0755 where git records the executable bit), no
    timestamp in the marker. Requires a clean worktree, like `packctl build`;
    the working tree is LF (`.gitattributes`: `* text eol=lf`).
    """
    root = Path(root).resolve()
    output = Path(output).resolve()
    if not SKILL_NAME_RE.fullmatch(name) or len(name) > 64:
        raise ValueError(f"invalid bundle name: {name!r}")
    if git_is_dirty(root):
        raise InstallError("the bundle needs a clean Git worktree (git status --porcelain is non-empty)")
    try:
        output.relative_to(root)
    except ValueError:
        pass
    else:
        raise InstallError(f"the bundle output must be outside the source tree: {output}")
    executable = _executable_paths(root)
    scratch = Path(tempfile.mkdtemp(prefix="dayz-bundle-"))
    temporary: Path | None = None
    try:
        skills = build_bundle(root, scratch)
        (scratch / MARKER).write_bytes(
            _marker_text(name, skills, git_commit(root), mode="copy").encode("utf-8")
        )
        members = sorted(
            p.relative_to(scratch).as_posix() for p in scratch.rglob("*") if p.is_file()
        )
        output.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            prefix=output.name + ".", suffix=".tmp", dir=output.parent, delete=False
        ) as handle:
            temporary = Path(handle.name)
        with zipfile.ZipFile(temporary, "w", zipfile.ZIP_STORED, allowZip64=True) as archive:
            for rel in members:
                info = zipfile.ZipInfo(f"{name}/{rel}", date_time=FIXED_ZIP_TIME)
                info.compress_type = zipfile.ZIP_STORED
                info.create_system = 3
                mode = 0o755 if f"skills/{rel}" in executable else 0o644
                info.external_attr = (0o100000 | mode) << 16
                info.flag_bits |= 0x800
                archive.writestr(info, (scratch / rel).read_bytes())
            archive.comment = b""
        os.replace(temporary, output)
        temporary = None
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
        shutil.rmtree(scratch, ignore_errors=True)
    return {"output": str(output), "members": len(members), "skills": skills}
