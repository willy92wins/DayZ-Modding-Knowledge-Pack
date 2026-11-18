"""Whether the vanilla index in use was built from the vanilla tree being read.

scripts/shared/vanilla_index.json is generated from one vanilla tree and
holds that tree's members and signatures. Four rules read it, through
shared/vanilla_reference.py: ES-MEMBER-REDECLARE-BASE,
ES-OVERRIDE-PARAM-NAME-MISMATCH, ES-METHOD-NAME-COLLIDES-VANILLA-CLASS and
ES-OVERRIDE-OF-PLATFORM-GATED-METHOD. The other vanilla rules read the tree
itself, so when the tree moves to another build and the index stays, one run
judges against two builds and nothing says so. On 2026-11-18 an index of
DayZ 1.30.164289 read with the 1.30.164393 tree gave five false
ES-MEMBER-REDECLARE-BASE findings on cctliquidsyntheticcursor.c, a new
subclass that takes those members from CCTLiquid; before that, a 1.29 index
turned the vanilla control red on 1.30 (inbox 4c83).

The index records the count and the total bytes of the .c files of its
tree, and a digest of their contents. Only the two numbers are compared.
The README's "Which tree the vanilla index is" has the measured cost of
both and what the numbers cannot tell apart. A folder's path is not
compared: the same path holds another build after a refresh. Read-only.
"""

import pathlib

from shared.vanilla_reference import loaded_index_path, loaded_index_tree


VANILLA_INDEX_TREE_RULE_ID = "VANILLA-INDEX-TREE-MISMATCH"

# The rules that call shared/vanilla_reference.py's index-backed lookups.
INDEX_RULES = (
    "ES-MEMBER-REDECLARE-BASE, ES-OVERRIDE-PARAM-NAME-MISMATCH, "
    "ES-METHOD-NAME-COLLIDES-VANILLA-CLASS and "
    "ES-OVERRIDE-OF-PLATFORM-GATED-METHOD"
)

_GENERATOR = pathlib.Path(__file__).resolve().parents[1] / "build_vanilla_index.py"

VANILLA_INDEX_TREE_MESSAGE = (
    "[WARN] the vanilla index {index} was not built from the vanilla tree "
    "{root}: the index records {index_files} .c files and {index_bytes} "
    "bytes (built from {index_root}, tree_digest {digest}), and the tree has "
    "{tree_files} .c files and {tree_bytes} bytes. {rules} read the index, "
    "so they judge the addon with the members and signatures of the tree it "
    "was built from: they can report what this tree does not declare and "
    "miss what it does (2026-11-18: an index of DayZ 1.30.164289 read with "
    "the 1.30.164393 tree gave five false ES-MEMBER-REDECLARE-BASE "
    "findings). Rebuild it from the tree being read: {rebuild}; or move it "
    "away, and those rules use only their curated tables."
)


def collect_c_files(vanilla_root):
    """The .c files the index covers, in the order its digest reads them.

    build_vanilla_index.py imports this one: the generator and the
    comparison below must count the same files.
    """
    files = sorted(
        path
        for path in vanilla_root.rglob("*.c")
        if path.is_file()
    )
    return files


def _skip(reason):
    return {
        "rule_id": VANILLA_INDEX_TREE_RULE_ID,
        "status": "SKIP",
        "reason": reason,
    }


def _is_count(value):
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def _rebuild_command(vanilla_root, index_path):
    return 'python "%s" --vanilla-root "%s" --out "%s"' % (
        _GENERATOR, vanilla_root, index_path
    )


def compare_index_tree(vanilla_root):
    """Return (warnings, skipped, info) for the vanilla index in use.

    Without an index nothing reads one, so nothing is compared and nothing
    is reported. info is None whenever nothing was compared; otherwise it
    holds the numbers of both sides and `matches`. What cannot be compared
    is a SKIP line, never a match.
    """
    index_path = loaded_index_path()
    if index_path is None:
        return [], [], None
    if vanilla_root is None:
        return [], [_skip(
            "no vanilla tree to compare the vanilla index %s with" % index_path
        )], None
    recorded = loaded_index_tree()
    index_files = recorded["file_count"]
    index_bytes = recorded["total_bytes"]
    rebuild = _rebuild_command(vanilla_root, index_path)
    if not (_is_count(index_files) and _is_count(index_bytes)):
        return [], [_skip(
            "the vanilla index %s does not record the file count and bytes "
            "of the tree it was built from, so it is not compared with %s; "
            "rebuild it: %s" % (index_path, vanilla_root, rebuild)
        )], None
    parsed = recorded["parsed_file_count"]
    if _is_count(parsed) and parsed != index_files:
        # total_bytes leaves out the files the generator could not read.
        return [], [_skip(
            "the vanilla index %s parsed %d of the %d .c files of its tree, "
            "so its byte count is not the tree's and it is not compared "
            "with %s; rebuild it: %s"
            % (index_path, parsed, index_files, vanilla_root, rebuild)
        )], None
    try:
        files = collect_c_files(pathlib.Path(vanilla_root))
        tree_bytes = sum(path.stat().st_size for path in files)
    except OSError as error:
        return [], [_skip(
            "the vanilla tree %s was not read (%s), so the vanilla index %s "
            "is not compared with it" % (vanilla_root, error, index_path)
        )], None

    index_root = recorded["vanilla_root"]
    if not isinstance(index_root, str) or not index_root:
        index_root = None
    info = {
        "index": str(index_path),
        "index_tree": index_root,
        "index_files": index_files,
        "index_bytes": index_bytes,
        "tree_files": len(files),
        "tree_bytes": tree_bytes,
        "compared": ["file_count", "total_bytes"],
        "matches": index_files == len(files) and index_bytes == tree_bytes,
    }
    if info["matches"]:
        return [], [], info
    digest = recorded["tree_digest"]
    if not isinstance(digest, str) or not digest:
        digest = "unknown"
    message = VANILLA_INDEX_TREE_MESSAGE.format(
        index=index_path, root=vanilla_root, index_files=index_files,
        index_bytes=index_bytes,
        index_root=index_root or "a tree it does not name",
        digest=digest[:12], tree_files=len(files), tree_bytes=tree_bytes,
        rules=INDEX_RULES, rebuild=rebuild,
    )
    warning = {
        "check": VANILLA_INDEX_TREE_RULE_ID,
        "file": str(index_path),
        "line": None,
        "message": message,
        "severity": "WARN",
        "rule_id": VANILLA_INDEX_TREE_RULE_ID,
    }
    return [warning], [], info
