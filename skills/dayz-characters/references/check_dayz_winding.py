#!/usr/bin/env python3
r"""
check_dayz_winding.py - OFFLINE winding and normal gate for the visual LODs of a DayZ source MLOD .p3d.

WHY THIS EXISTS
  A Blender/Three.js preview is double-sided, so it never shows DayZ's single-sided culling: faces wound the
  wrong way only surface in game (inside-out: textures on the interior), and a wrong normal sign only as
  inverted lighting. This reads both offline, before AddonBuilder.

THE CONVENTION IT CHECKS (dayz-model-pipeline Rule 12, measured in game 2026-10-01; dayz-p3d-audit "Absolute
winding check", engine verdict 2026-09-07)
  In a DayZ MLOD the vertex-order cross product cross(v1-v0, v2-v0) and the stored shading normals both point
  away from the side meant to be seen: into the material, inward on a solid. py3d.blender_to_dayz() writes
  that. Per visual LOD:
  (1) WINDING, per closed shell: its signed volume by winding, the sum of dot(v0, cross(v1, v2)) / 6 over the
      fan triangles of its faces, is NEGATIVE, the production sign. Positive: the cross product points out
      of the material, inside-out for a model seen from outside (a room meant to be seen from inside reads
      positive by design; this gate is not for those). A shell is a set of faces linked only through edges
      that exactly two faces use, once points are welded by position; it is closed when each of its edges is
      used by exactly two of its faces, and its volume counts only when it is coherent (the two faces of
      each edge run it in opposite directions). Never the sum over the LOD: it can hide an inverted part
      (dayz-p3d-audit references/winding-diagnostics.md, Check A).
  (2) NORMALS: the share of faces whose first corner's stored normal agrees with the face's cross product,
      counted as py3d _pct_normal_agreement counts it (dayz-p3d-audit's absolute check), read after the
      winding fix this gate asks for. Above 90 % they agree. Below 10 % they disagree: with the winding
      right that means the normals point out of the material, and the fix is to negate the normal pool,
      never to reverse the faces.
  The fixes come in the order of the table in winding-diagnostics.md and of the py3d README ("Winding"): the
  winding first, normals untouched; then the normals against the settled winding.

WHAT IT CANNOT SEE
  - A mirror. A det=+1 export with its faces reversed and its normals negated passes
    (winding_fixtures/mirror_a.p3d rendered solid and mirrored in game). Check chirality on an asymmetric
    feature (Rule 12).
  - The direction of an open part (a sheet, an open tube) or a flat one (a face welded to its reversed
    twin): no volume sign decides there. Their faces are reported as not scored; dayz-p3d-audit's
    visibility battery covers them. A visual LOD with no closed shell is not measurable (exit 2), unless
    its normals disagree with its winding (exit 1, without saying which of the two is wrong).
  - Collision LODs: dayz-model-pipeline Rule 18's per-component check.
  - A debinarized model: the ODOL->MLOD converter's winding handling inverts the comparison.

HISTORY
  The version of 2026-06-25 (LFInfectedBig S6) encoded that build's det=+1 recipe: stored normals OUTWARD
  and cross . normal < 0. It failed all three MLODs of the Rule 12 in-game test, the correct one included
  (measured 2026-10-01), and passed the outward-normal state (dayz-characters SKILL.md, OFFLINE GATE).

USAGE
  python check_dayz_winding.py path\to\model.p3d
  python check_dayz_winding.py path\to\model.p3d --py3d path\to\py3d
  exit code 0 = PASS, 1 = model defect (winding or normals), 2 = invalid input, ODOL, or not measurable
  Fixtures and test: winding_fixtures/ and test_check_dayz_winding.py, next to this script.
"""
import argparse
import math
import os
import struct
import sys
from collections import defaultdict

AGREE_ABOVE = 90.0       # % of voting faces; above it the normals agree (py3d _check_winding_absolute)
DISAGREE_BELOW = 10.0    # below it they disagree (where py3d raises ERR_WINDING_VS_NORMALS)
WELD_DECIMALS = 5        # points equal to 5 decimals are one point (winding-diagnostics.md, Check B)
MIN_THICKNESS = 1e-4     # m; a closed shell with 3*|volume|/area below it is flat (welded twins): no sign

POOL_FIX = ("negate the normal pool in place: lod.facenormals[j] = (-x, -y, -z) for every j "
            "(not through Vertex.normal).")
CORNER_FIX = ("negate the corner normals of the listed shells, corner by corner: each one that points "
              "against its face; a pool entry that a corner you keep also uses gets a negated copy "
              "(py3d README, \"Winding\", step 3).")
BATTERY = ("no volume sign decides an open or flat part: check them with the visibility battery "
           "(dayz-p3d-audit references/winding-diagnostics.md, \"From Check B to fix\").")


def load_py3d(extra):
    for p in ([extra] if extra else []) + [
        os.path.join(os.path.dirname(__file__), "py3d")]:
        if p and os.path.isdir(p) and p not in sys.path:
            sys.path.insert(0, p)
    try:
        import py3d
    except ImportError as exc:
        print(f"invalid environment: cannot import py3d ({exc}); install the py3d DayZ fork or pass --py3d")
        sys.exit(2)
    version = tuple(map(int, py3d.__version__.split(".")))
    if not getattr(py3d, "IS_DAYZ_FORK", False) or version < (1, 6, 0):
        print(f"invalid environment: py3d {py3d.__version__} from {py3d.__file__} is not the DayZ fork >= 1.6.0")
        sys.exit(2)
    return py3d


def _sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1],
            a[2] * b[0] - a[0] * b[2],
            a[0] * b[1] - a[1] * b[0])


def _dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _plural(n, word):
    return f"{n} {word}" if n == 1 else f"{n} {word}s"


def _ranges(indices):
    """Sorted face indices as '12-23' or '0-3, 7, 9-11'."""
    out = []
    for i in sorted(indices):
        if out and i == out[-1][1] + 1:
            out[-1][1] = i
        else:
            out.append([i, i])
    return ", ".join(str(a) if a == b else f"{a}-{b}" for a, b in out)


def _pct(part, whole):
    return 100.0 * part / whole if whole else 0.0


def _agrees(face, points):
    """py3d _pct_normal_agreement's vote for one face: True, False, or None when it cannot vote."""
    v = [points[x.point_index].coords for x in face.vertices]
    c = _cross(_sub(v[1], v[0]), _sub(v[2], v[0]))
    if c[0] == 0.0 and c[1] == 0.0 and c[2] == 0.0:
        return None
    n = face.vertices[0].normal
    if n is None or (n[0] == 0.0 and n[1] == 0.0 and n[2] == 0.0):
        return None
    d = c[0] * n[0] + c[1] * n[1] + c[2] * n[2]
    if d == 0.0:
        return None
    return d > 0


class Shell:
    """Faces linked through edges that exactly two faces use, with what the gate reads on them."""

    def __init__(self, members):
        self.members = members        # indices into lod.faces
        self.closed = False
        self.bad_edges = 0            # edges both of whose faces run them the same way (Check B)
        self.groups = None            # orientation group sizes, when bad_edges
        self.conflicts = 0            # edges no orientation of the groups satisfies (not orientable)
        self.volume = 0.0
        self.flat = False
        self.centre = (0.0, 0.0, 0.0)
        self.votes = 0
        self.agree = 0

    def kind(self):
        if self.bad_edges:
            return "incoherent"
        if not self.closed or self.flat:
            return "unscored"
        return "positive" if self.volume > 0 else "negative"

    def where(self):
        return f"shell at lod.faces {_ranges(self.members)}"


def read_shells(lod, faces):
    """Split *faces* (indices into lod.faces) into shells and read each one."""
    points = lod.points
    weld = {}
    wid = [weld.setdefault(tuple(round(c, WELD_DECIMALS) for c in p.coords), len(weld)) for p in points]

    def edges(fi):
        w = [wid[v.point_index] for v in lod.faces[fi].vertices]
        for i in range(len(w)):
            a, b = w[i], w[(i + 1) % len(w)]
            if a != b:
                yield (a, b, 1) if a < b else (b, a, -1)

    users = defaultdict(list)
    for fi in faces:
        for a, b, _ in edges(fi):
            users[(a, b)].append(fi)
    parent = {fi: fi for fi in faces}

    def root(fi):
        while parent[fi] != fi:
            parent[fi] = parent[parent[fi]]
            fi = parent[fi]
        return fi

    for us in users.values():
        if len(us) == 2:
            ra, rb = root(us[0]), root(us[1])
            if ra != rb:
                parent[ra] = rb
    members = defaultdict(list)
    for fi in faces:
        members[root(fi)].append(fi)

    shells = []
    for ms in members.values():
        shell = Shell(ms)
        runs = defaultdict(list)
        for fi in ms:
            for a, b, d in edges(fi):
                runs[(a, b)].append((fi, d))
        shell.closed = all(len(r) == 2 for r in runs.values())
        pairs = [r for r in runs.values() if len(r) == 2]
        shell.bad_edges = sum(1 for (_, d1), (_, d2) in pairs if d1 == d2)
        if shell.bad_edges:
            # flood-fill the faces into orientation groups: across an edge run the same way by both
            # faces the orientation changes, across one run in opposite directions it does not
            nbrs = defaultdict(list)
            for (f1, d1), (f2, d2) in pairs:
                nbrs[f1].append((f2, d1 == d2))
                nbrs[f2].append((f1, d1 == d2))
            side = {}
            for start in ms:
                if start in side:
                    continue
                side[start] = 0
                stack = [start]
                while stack:
                    f = stack.pop()
                    for g, turn in nbrs[f]:
                        if g not in side:
                            side[g] = side[f] ^ turn
                            stack.append(g)
            ones = sum(side[f] for f in ms)
            shell.groups = sorted((len(ms) - ones, ones), reverse=True)
            shell.conflicts = sum(1 for (f1, d1), (f2, d2) in pairs if (side[f1] ^ side[f2]) != (d1 == d2))
        ids = sorted({v.point_index for fi in ms for v in lod.faces[fi].vertices})
        centre = tuple(sum(points[i].coords[k] for i in ids) / len(ids) for k in range(3))
        shell.centre = centre
        # the volume of a closed shell does not depend on the origin; its centre keeps the terms small
        volume = area = 0.0
        for fi in ms:
            q = [_sub(points[v.point_index].coords, centre) for v in lod.faces[fi].vertices]
            for k in range(1, len(q) - 1):
                volume += _dot(q[0], _cross(q[k], q[k + 1])) / 6.0
                c = _cross(_sub(q[k], q[0]), _sub(q[k + 1], q[0]))
                area += math.sqrt(_dot(c, c)) / 2.0
        shell.volume = volume
        shell.flat = area == 0.0 or 3.0 * abs(volume) / area < MIN_THICKNESS
        shells.append(shell)
    shells.sort(key=lambda s: min(s.members))
    return shells


def read_lod(lod, index):
    """Print one visual LOD's verdict. Returns 'PASS', 'FAIL' or 'ERROR' (not measurable)."""
    proxy = set()
    for name, sel in lod.selections.items():
        if str(name).lower().startswith("proxy:"):
            proxy.update(id(face) for face in sel.faces)
    faces = [fi for fi, face in enumerate(lod.faces) if id(face) not in proxy and len(face.vertices) >= 3]
    left_out = len(lod.faces) - len(faces)
    shells = read_shells(lod, faces)
    for shell in shells:
        for fi in shell.members:
            vote = _agrees(lod.faces[fi], lod.points)
            if vote is not None:
                shell.votes += 1
                # read against the winding this gate settles: a positive shell gets reversed
                shell.agree += vote != (shell.kind() == "positive")

    by = defaultdict(list)
    for shell in shells:
        by[shell.kind()].append(shell)
    neg, pos, bad, uns = by["negative"], by["positive"], by["incoherent"], by["unscored"]
    nfaces = lambda group: sum(len(s.members) for s in group)
    nsum = lambda group: sum(s.volume for s in group)
    lines = []
    fixes = 0
    fail = error = False

    if bad:
        fail = True
        closed = "closed " if all(s.closed for s in bad) else ""
        noun = "shell has" if len(bad) == 1 else "shells have"
        lines.append(f"  winding: INCOHERENT. {len(bad)} {closed}{noun} faces wound against their neighbours, "
                     f"so {'its' if len(bad) == 1 else 'their'} volume is not read:")
        for s in bad:
            text = (f"    {s.where()}: {len(s.members)} faces, {s.bad_edges} edges run the same way by both of "
                    f"their faces; orientation groups of {s.groups[0]} and {s.groups[1]} faces")
            if not s.closed:
                text += " (an open shell)"
            if s.conflicts:
                text += f"; {s.conflicts} edges fit neither grouping: not orientable"
            lines.append(text)
        fixes += 1
        lines.append(f"  fix {fixes}: make each listed shell coherent: reverse the vertex order of one "
                     "orientation group, normally the smaller, normals untouched; then run this gate again, "
                     "which reads a closed shell's volume only once it is coherent (py3d README, \"Winding\", "
                     "step 1).")
    reversal = None
    if pos:
        fail = True
        if neg:
            lines.append(f"  winding: INSIDE-OUT. {len(pos)} of {_plural(len(pos) + len(neg), 'closed shell')} "
                         f"({nfaces(pos)} faces) read a positive signed volume by winding, sum "
                         f"{nsum(pos):+.4g}; the other {len(neg)} ({nfaces(neg)} faces) read negative, sum "
                         f"{nsum(neg):+.4g}. The sum over all of them, {nsum(pos) + nsum(neg):+.4g}, "
                         + ("hides it." if nsum(pos) + nsum(neg) < 0 else "would turn the right ones too."))
            for s in pos:
                lines.append(f"    {s.where()}: {len(s.members)} faces, volume {s.volume:+.4g}, centre "
                             f"({s.centre[0]:.3f}, {s.centre[1]:.3f}, {s.centre[2]:.3f})")
            fixes += 1
            reversal = fixes
            lines.append(f"  fix {fixes}: face.vertices.reverse() on every face of the listed shells, and only "
                         "those (the winding first, normals untouched): the other shells are right, and "
                         "reversing the whole LOD would move the inversion onto them.")
        else:
            lines.append(f"  winding: INSIDE-OUT. {len(pos)} of {_plural(len(pos), 'closed shell')} "
                         f"({nfaces(pos)} faces) read a positive signed volume by winding, sum "
                         f"{nsum(pos):+.4g}: the cross product points out of the material.")
            fixes += 1
            reversal = fixes
            if uns:
                lines.append(f"  fix {fixes}: face.vertices.reverse() on every face of these closed shells (the "
                             "winding first, normals untouched). This reading cannot check the faces not scored "
                             "below; if they came out of the same export call (blender_to_dayz(), transform()), "
                             "they are in the same state.")
            elif bad:
                lines.append(f"  fix {fixes}: face.vertices.reverse() on every face of these closed shells (the "
                             "winding first, normals untouched).")
            else:
                scope = "this LOD" if not left_out else "this LOD except its proxy:* triangles"
                lines.append(f"  fix {fixes}: face.vertices.reverse() on every face of {scope} (the winding "
                             "first, normals untouched; never a vertices[1]/[2] swap, which turns a quad into a "
                             "crossed face).")
    elif neg:
        lines.append(f"  winding: RIGHT. {len(neg)} of {_plural(len(neg), 'closed shell')} ({nfaces(neg)} faces) "
                     f"read a negative signed volume by winding, sum {nsum(neg):+.4g}: the cross product points "
                     "into the material, the MLOD order of Rule 12.")
    elif not bad:
        error = True
        lines.append("  winding: UNSCORED. No closed shell to read: the volume sign means nothing on an open or "
                     "flat part.")

    read = [s for s in shells if s.kind() != "incoherent"]
    votes = sum(s.votes for s in read)
    agree = sum(s.agree for s in read)
    pct = _pct(agree, votes)
    after = f" after fix {reversal}" if reversal else ""
    would = "would agree" if reversal else "agree"
    skipped = f"; the {nfaces(bad)} faces of incoherent shells are read once those are coherent" if bad else ""
    reading = f"{agree} of {votes} faces ({pct:.1f} %) {would} with their winding"
    odd = [s for s in read if s.votes and _pct(s.agree, s.votes) <= AGREE_ABOVE]
    if not votes:
        error = True
        lines.append(f"  normals: UNSCORED. No face has both a non-degenerate winding and a non-zero "
                     f"normal{skipped}.")
    elif pct < DISAGREE_BELOW:
        fail = True
        if reversal:
            lines.append(f"  normals: DISAGREE{after}. {reading}{skipped}.")
            fixes += 1
            lines.append(f"  fix {fixes}: {POOL_FIX}")
        elif neg:
            lines.append(f"  normals: DISAGREE. {reading}: the stored normals point out of the material (the "
                         f"older outward-normal convention){skipped}.")
            fixes += 1
            lines.append(f"  fix {fixes}: {POOL_FIX} Keep every face as it is: reversing faces on this reading "
                         "turns the model inside-out.")
        else:
            lines.append(f"  normals: DISAGREE. {reading}; with no closed shell this gate cannot say which of the "
                         f"two is wrong{skipped}.")
    elif pct > AGREE_ABOVE and not any(_pct(s.agree, s.votes) < DISAGREE_BELOW for s in odd):
        keep = ": keep the normals" if reversal else ""
        lines.append(f"  normals: AGREE{after}. {reading}{keep}{skipped}.")
    else:
        fail = True
        lines.append(f"  normals: MIXED{after}. {reading}{skipped}.")
        for s in sorted(odd, key=lambda s: -len(s.members)):
            note = "" if s.kind() in ("positive", "negative") else " (direction not scored)"
            lines.append(f"    {s.where()}: {s.agree} of {s.votes} faces {would}{note}")
        fixes += 1
        lines.append(f"  fix {fixes}: {CORNER_FIX}")

    if uns:
        flat = [s for s in uns if s.closed]
        opened = [s for s in uns if not s.closed]
        parts = " and ".join(p for p in (_plural(len(opened), "open shell") if opened else "",
                                         _plural(len(flat), "flat closed shell") if flat else "") if p)
        lines.append(f"  not scored: {nfaces(uns)} of {len(faces)} faces ({_pct(nfaces(uns), len(faces)):.1f} %) "
                     f"in {parts}; {BATTERY}")

    tag = "FAIL" if fail else ("ERROR" if error else "PASS")
    print(f"[{tag}] LOD {index} res={lod.resolution:.1f}: {len(faces)} faces, {left_out} proxy faces left out")
    for line in lines:
        print(line)
    return tag


def main():
    ap = argparse.ArgumentParser(description="Offline winding and normal gate for DayZ source MLOD visual LODs.")
    ap.add_argument("p3d")
    ap.add_argument("--py3d", default=None)
    a = ap.parse_args()
    try:
        with open(a.p3d, "rb") as stream:
            signature = stream.read(4)
    except OSError as exc:
        print(f"invalid input: {exc}")
        sys.exit(2)
    if signature == b"ODOL":
        print("invalid input: this file is ODOL; convert it to MLOD first with an external "
              "ODOL->MLOD converter (not distributed with this pack).")
        sys.exit(2)
    py3d = load_py3d(a.py3d)
    try:
        with open(a.p3d, "rb") as stream:
            m = py3d.P3D(stream)
    except (OSError, AssertionError, EOFError, ValueError, IndexError, struct.error) as exc:
        print(f"invalid input: {exc}")
        sys.exit(2)
    visual = sorted(((i, lod) for i, lod in enumerate(m.lods) if lod.kind() == "visual"),
                    key=lambda item: item[1].resolution)
    if not visual:
        print("invalid input: no visual LOD")
        sys.exit(2)
    tags = []
    for index, lod in visual:
        try:
            tags.append(read_lod(lod, index))
        except IndexError as exc:
            print(f"[ERROR] LOD {index} res={lod.resolution:.1f}: a point or normal index is out of range ({exc})")
            tags.append("ERROR")
    if "FAIL" in tags:
        print("DAYZ WINDING/NORMAL CONVENTION: FAIL (model defect) - do NOT ship")
        if "ERROR" in tags:
            print(f"  ({tags.count('ERROR')} visual LODs not measurable as well)")
        sys.exit(1)
    if "ERROR" in tags:
        print("DAYZ WINDING/NORMAL CONVENTION: INVALID (not measurable)")
        sys.exit(2)
    print("DAYZ WINDING/NORMAL CONVENTION: PASS")
    print("  It cannot see a mirror: a det=+1 export with its faces reversed and its normals negated passes "
          "too (winding_fixtures/mirror_a.p3d, mirrored in game). Check chirality on an asymmetric feature "
          "(dayz-model-pipeline Rule 12).")
    sys.exit(0)


if __name__ == "__main__":
    main()
