"""Install the pack as one routed skill: <target>/<name>/SKILL.md plus siblings."""

from __future__ import annotations

import datetime as _dt
import json
import re
import shutil
import tempfile
from pathlib import Path

from .common import git_commit

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


def install(
    root: Path,
    target: Path,
    *,
    name: str = "dayz",
    force: bool = False,
    dry_run: bool = False,
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
        "leftovers": _leftovers(target, name, skill_names),
    }
    if dry_run:
        return result

    target.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{name}.new-", dir=target))
    try:
        build_bundle(root, staging, router=router)
        (staging / MARKER).write_text(
            json.dumps(
                {
                    "installer": "packctl install",
                    "name": name,
                    "source_commit": git_commit(root),
                    "installed_at": _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "skills": skill_names,
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
            newline="\n",
        )
        if destination.exists() or destination.is_symlink():
            old = Path(tempfile.mkdtemp(prefix=f".{name}.old-", dir=target))
            old.rmdir()
            destination.rename(old)
            try:
                staging.rename(destination)
            except OSError:
                old.rename(destination)
                raise
            if old.is_symlink() or old.is_file():
                old.unlink()
            else:
                shutil.rmtree(old, ignore_errors=True)
        else:
            staging.rename(destination)
    finally:
        if staging.exists():
            shutil.rmtree(staging, ignore_errors=True)
    return result
