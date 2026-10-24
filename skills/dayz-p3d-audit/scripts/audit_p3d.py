#!/usr/bin/env python3
"""
DayZ P3D Audit Script - Complete model validator (fork-delegated).

S2 rollout (plan py3d-fork F2-12 + Paso 3.4): los checks de modelo viven
ahora en py3d (fork DayZ >= 1.6.0) via P3D.validate(); este script
conserva el CLI, el escaneo de LODs requeridos y los chequeos de archivos
de texto. Depuracion aplicada (R22-P2-04):
  - ids LOD normalizados a DayZ: ViewGeo=6e15, FireGeo=7e15; el slot
    GeoPhys/2e13 y las menciones FireGeo~3e13 (stale) se RETIRAN;
  - check de winding por centroide absoluto RETIRADO (D8): el fork aplica
    el check RELATIVO vs Visual (cross-product);
  - severidades: ERROR->CRITICAL, WARN->WARNING.

Usage:
    python audit_p3d.py model.p3d [model2.p3d ...]
    python audit_p3d.py model.p3d --config path/to/config.cpp
    python audit_p3d.py model.p3d --model-cfg path/to/model.cfg
    python audit_p3d.py --scan-dir path/to/mod/

Requires: py3d DayZ fork >= 1.6.0 (`pip install -e tools/py3d`;
NUNCA `pip install py3d` - el paquete PyPI es otra libreria).
"""

import sys, os, re, glob, argparse, math

try:
    import py3d
except ImportError:
    print("ERROR: py3d (DayZ fork) not installed.")
    print("Install the pack fork: pip install -e tools/py3d")
    sys.exit(1)

if not getattr(py3d, "IS_DAYZ_FORK", False) or \
        tuple(int(x) for x in py3d.__version__.split(".")) < (1, 6, 0):
    print("ERROR: wrong py3d (%r, %s). This audit requires the DayZ fork "
          ">= 1.6.0 - NEVER `pip install py3d` (PyPI = point-cloud lib). "
          "Install the pack fork: pip install -e tools/py3d."
          % (getattr(py3d, "__version__", "?"),
             getattr(py3d, "__file__", "?")))
    sys.exit(1)

_SEV = {"ERROR": "CRITICAL", "WARN": "WARNING"}


def classify_lod(resolution):
    """Delegado al fork (mapa canonico DayZ, tolerancia relativa unica)."""
    kind = py3d.classify_lod_resolution(resolution)
    if kind is None:
        return "Other(%.1e)" % resolution
    return {
        "visual": "Visual", "shadowvolume": "ShadowVolume",
        "geometry": "Geometry", "memory": "Memory",
        "landcontact": "LandContact", "roadway": "Roadway",
        "paths": "Paths", "hitpoints": "HitPoints",
        "view_geometry": "ViewGeo", "fire_geometry": "FireGeo",
    }[kind]


def check_required_lods(lod_map):
    """LODs minimos (ids normalizados DayZ; GeoPhys retirado)."""
    issues = []
    if "Geometry" not in lod_map:
        issues.append(("CRITICAL", "Missing Geometry LOD (res ~1e13). No collision or action targeting possible."))
    if "Memory" not in lod_map:
        issues.append(("CRITICAL", "Missing Memory LOD (res ~1e15). No animation axes, no bounding data."))
    if "Visual" not in lod_map:
        issues.append(("CRITICAL", "Missing Visual LOD (res 0.0). Object will be invisible."))
    if "ViewGeo" not in lod_map:
        issues.append(("NOTE", "Missing ViewGeo LOD (res ~6e15). Action cursor raycasts (ObjIntersectView) have nothing to hit."))
    if "FireGeo" not in lod_map:
        issues.append(("NOTE", "Missing FireGeo LOD (res ~7e15). No ballistic damage zones."))
    return issues


def check_p_drive_paths_in_file(filepath):
    """Paths P:\\ en archivos de texto (config.cpp, .rvmat, model.cfg)."""
    issues = []
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
        for i, line in enumerate(lines, 1):
            matches = re.findall(r'["\']?(P:[\\\/][^"\';\s]+)', line, re.IGNORECASE)
            for m in matches:
                issues.append(("WARNING",
                    f"Line {i}: Absolute P:\\ path '{m}' - breaks on other machines. "
                    f"Use game-relative path (remove 'P:\\' prefix)."))
    except Exception as e:
        issues.append(("ERROR", f"Cannot read {filepath}: {e}"))
    return issues


# --- Tema B additive checks (SP-009 verts / SP-027 class=vehicle / SP-017 / SP-023b) ---
# Standalone helpers; complement the fork's p.validate(), do not alter its flow.

_DAMPER_RE = re.compile(r'damper', re.I)
_WHEEL_OR_DAMPER_RE = re.compile(r'wheel|damper', re.I)

def _is_vehicle_body(p):
    """A wheeled-vehicle BODY carries suspension 'damper' selections (wheelHub
    'wheel_X_X_damper_land' and/or anim 'wheel_X_X_damper'); a standalone wheel
    proxy .p3d does not. Anchoring on 'damper' avoids false positives on wheel
    proxies that merely carry a 'wheel_*' selection."""
    for lod in p.lods:
        for name in lod.selections:
            if _DAMPER_RE.search(name):
                return True
    return False

def _is_vehicle_related(p):
    """Vehicle-domain (body OR standalone wheel proxy): any 'wheel'/'damper'
    selection. Scopes the wheel-collision material check (SP-023b) to vehicle
    parts so it never changes a non-vehicle model's result (no regression)."""
    for lod in p.lods:
        for name in lod.selections:
            if _WHEEL_OR_DAMPER_RE.search(name):
                return True
    return False

def check_lod0_vertex_budget(p):
    """SP-009: the fork already warns on the per-LOD facenormals budget
    (WARN_NORMALS_BUDGET, 32768). This complements it with the 16-bit VERTEX
    ceiling (65536) on Visual LOD0, and a heavier warning for vehicle/proxy
    hosts whose LOD0 is already large before proxy INSTANCES are summed in.
    The hard ceilings are on the RESOLVED LOD0 (body + each proxy instance);
    a single-file pass cannot sum instances, so it flags the per-file risk.
    See dayz-model-pipeline/references/lods-and-geometry.md budget section."""
    issues = []
    body = _is_vehicle_body(p)
    for i, lod in enumerate(p.lods):
        if classify_lod(lod.resolution) != "Visual" or abs(lod.resolution) > 1e-9:
            continue
        nverts = len(lod.points)
        nidx = lod.num_vertices
        nnorm = len(lod.facenormals)
        # DX9 ceiling is on RESOLVED unique vertices (point x normal x uv),
        # not on raw point/face-index counts (SUB_BRZ 2026-06-24: 96585
        # face-indices resolved to 22143 unique vertices and loaded fine).
        resolved = set()
        for fa in lod.faces:
            for v in fa.vertices:
                resolved.add((v.point_index, v.normal_index, tuple(v.uv)))
        nres = len(resolved)
        if nres > 65535:
            issues.append(("CRITICAL",
                "LOD[%d] Visual LOD0 resolves to %d unique vertices "
                "(point x normal x uv) > 65535 (DX9 16-bit ceiling): model "
                "fails to load or renders invisible (points=%d, "
                "face-indices=%d)." % (i, nres, nverts, nidx)))
        elif nverts > 65536 or nidx > 65536:
            issues.append(("WARNING",
                "LOD[%d] Visual LOD0 raw counts exceed 65536 (points=%d, "
                "face-indices=%d) but resolved unique vertices=%d is under "
                "the DX9 ceiling; raw counts alone are not the limit." % (
                    i, nverts, nidx, nres)))
        elif body and (nnorm > 16384 or nverts > 32768):
            issues.append(("WARNING",
                "LOD[%d] Visual LOD0 is heavy on a vehicle/proxy host "
                "(points=%d, facenormals=%d): budget the RESOLVED LOD0 (body + "
                "each proxy INSTANCE) against 32768 normals / 65536 verts before "
                "generating proxies (SP-009)." % (i, nverts, nnorm)))
        break
    return issues

def check_geometry_class_vehicle(p):
    """SP-027: a wheeled vehicle's Geometry LOD must carry the named property
    class=vehicle (verified 6/6 vanilla cars). PARITY only - its absence does
    NOT cause wheelPresent=0 (refuted in-game 2026-05-27); the wheel-sim gate is
    the CfgSlots.selection <-> FireGeometry consistency (SP-017)."""
    issues = []
    if not _is_vehicle_body(p):
        return issues
    for i, lod in enumerate(p.lods):
        if classify_lod(lod.resolution) != "Geometry":
            continue
        props = dict(lod.properties) if lod.properties else {}
        if (props.get("class") or "").strip().lower() != "vehicle":
            issues.append(("CRITICAL",
                "LOD[%d] Geometry of a wheeled vehicle is missing named property "
                "class=vehicle (parity gap: 6/6 vanilla cars carry it; replicate "
                "via geo_lod.properties['class']='vehicle'). PARITY only, NOT the "
                "wheel-sim gate (that is CfgSlots.selection <-> FireGeometry, "
                "SP-017)." % i))
    return issues

_COLLISION = ("Geometry", "FireGeo", "ViewGeo")

def check_collision_face_material(p):
    """SP-023b: wheel/vehicle collision-LOD faces with an empty material degrade
    ballistic penetration resolution (model-pipeline Rule 17). Scoped to
    vehicle-related models (wheel proxy or body) so it never changes a
    non-vehicle model's audit result."""
    issues = []
    if not _is_vehicle_related(p):
        return issues
    for i, lod in enumerate(p.lods):
        k = classify_lod(lod.resolution)
        if k not in _COLLISION:
            continue
        empty = sum(1 for fa in lod.faces if not (fa.material or "").strip())
        if empty:
            issues.append(("WARNING",
                "LOD[%d] %s has %d/%d face(s) with empty material - penetration/"
                "ballistic surface unresolved (assign a penetration .rvmat; "
                "SP-023b / model-pipeline Rule 17)." % (i, k, empty, len(lod.faces))))
    return issues

# --- ddce: needle triangles in the collision components -----------------------

NEEDLE_MIN_AREA = 1e-6   # m^2
NEEDLE_MIN_RATIO = 1e-4  # area / longest edge^2
_COMPONENT_RE = re.compile(r"component\d+", re.I)

def triangle_area_ratio(a, b, c):
    """Area of the triangle a, b, c (each an (x, y, z)) and that area over the
    square of its longest edge: sqrt(3)/4 = 0.433 for an equilateral triangle,
    the most it can be, and 0.0 when the three points coincide."""
    ab = [b[i] - a[i] for i in range(3)]
    ac = [c[i] - a[i] for i in range(3)]
    bc = [c[i] - b[i] for i in range(3)]
    cross = (ab[1] * ac[2] - ab[2] * ac[1],
             ab[2] * ac[0] - ab[0] * ac[2],
             ab[0] * ac[1] - ab[1] * ac[0])
    area = 0.5 * math.sqrt(sum(x * x for x in cross))
    longest = max(sum(x * x for x in e) for e in (ab, ac, bc))
    return area, (area / longest if longest > 0.0 else 0.0)

def needle_triangles(points, faces, min_area=NEEDLE_MIN_AREA,
                     min_ratio=NEEDLE_MIN_RATIO):
    """ddce: the needle triangles of `faces`, as (face, corners, area, ratio).

    points is a sequence of (x, y, z) and faces a sequence of faces, each a
    sequence of indices into points. Each face is split into triangles from
    its first corner, so a quad (a, b, c, d) reads as (a, b, c) and (a, c, d),
    the split of py3d's LOD.triangulate(). A triangle is a needle when its
    area is under min_area or its area over the square of its longest edge,
    the ratio, is under min_ratio. Needles come in the order of faces: face
    is a needle's position in faces and corners its three point indices."""
    found = []
    for n, face in enumerate(faces):
        for j in range(1, len(face) - 1):
            corners = (face[0], face[j], face[j + 1])
            area, ratio = triangle_area_ratio(*[points[k] for k in corners])
            if area < min_area or ratio < min_ratio:
                found.append((n, corners, area, ratio))
    return found

def _opposite_longest_edge(points, corners):
    """The corner of a triangle that faces its longest edge."""
    def d2(i, j):
        return sum((points[i][k] - points[j][k]) ** 2 for k in range(3))
    a, b, c = corners
    return max((d2(b, c), a), (d2(a, c), b), (d2(a, b), c))[1]

# py3d's proxy name: PROXY_NAME_RE, tools/py3d/py3d/__init__.py:200-201.
_PROXY_NAME_RE = re.compile(r"^proxy:(?P<path>.+)\.(?P<index>\d+)$",
                            re.IGNORECASE)

def _proxy_triangles(lod):
    """ids of the proxy triangles of a LOD, by py3d's rule: a selection named
    proxy:<path>.<index> (proxy: in any case) that holds exactly one face, a
    triangle, and as its points exactly that triangle's three corners. A
    selection under a proxy name with any other shape is not a proxy, and
    its faces are read. This is py3d's _proxy_triangle_faces
    (tools/py3d/py3d/__init__.py:1274-1296 in py3d 1.10.1, the same in 1.9.0
    and 1.10.0) written out here, not called: py3d keeps it private, and this
    script accepts py3d from 1.6.0. py3d reads a corner as vx.point, which is
    lod.points[vx.point_index]. tests/test_needle_triangles.py checks that the
    two agree on a LOD that py3d wrote and read back."""
    out = set()
    for name, sel in lod.selections.items():
        if not _PROXY_NAME_RE.match(name):
            continue
        if len(sel.points) != 3 or len(sel.faces) != 1:
            continue
        face = next(iter(sel.faces))
        if len(face.vertices) != 3:
            continue
        try:
            corners = {id(lod.points[vx.point_index]) for vx in face.vertices}
        except (IndexError, TypeError):
            continue
        if len(corners) == 3 and corners == set(map(id, sel.points)):
            out.add(id(face))
    return out

def check_collision_needle_triangles(p):
    """ddce: a needle triangle in a component of a collision LOD (Geometry,
    View or Fire). Measured in DayZ 1.29.163709 (SecretRock, 2026-10-02): two
    convex hulls built with Qhull that held one each took no ray in geom, view
    or fire, and binarize said nothing; built again without the point opposite
    each needle's longest edge, they took them. Every face of every ComponentNN
    selection (any case; a face at weight 0 is not in it, and proxy triangles,
    by py3d's rule, are left out) is read with needle_triangles(), at the
    project's thresholds: the engine's own limit lies between a ratio of
    4.6e-7 (no hit) and 1.19e-4 (hit). A face in no component is py3d's
    coverage check. See dayz-model-pipeline
    references/py3d-direct-generation.md, "Needle triangles"."""
    issues = []
    for i, lod in enumerate(p.lods):
        k = classify_lod(lod.resolution)
        if k not in _COLLISION:
            continue
        points = [pt.coords for pt in lod.points]
        index = {id(fa): n for n, fa in enumerate(lod.faces)}
        proxies = _proxy_triangles(lod)
        for name, sel in lod.selections.items():
            if not _COMPONENT_RE.fullmatch(name):
                continue
            faces = sorted(((index[id(fa)], fa) for fa, w in sel.faces.items()
                            if w and id(fa) in index and id(fa) not in proxies),
                           key=lambda item: item[0])
            corners = [[v.point_index for v in fa.vertices] for _, fa in faces]
            for n, tri, area, ratio in needle_triangles(points, corners):
                issues.append(("CRITICAL",
                    "LOD[%d] %s, %s, face %d: needle triangle (points %d, %d, "
                    "%d), area %.2e m^2, area/longest edge^2 %.2e (this check "
                    "fails a triangle under %.0e m^2 or %.0e). In game a convex "
                    "hull holding one took no ray in geom, view or fire, and "
                    "binarize said nothing: build the hull again without point "
                    "%d, the corner opposite the longest edge (ddce; "
                    "dayz-model-pipeline references/py3d-direct-generation.md)."
                    % (i, k, name, faces[n][0], tri[0], tri[1], tri[2], area,
                       ratio, NEEDLE_MIN_AREA, NEEDLE_MIN_RATIO,
                       _opposite_longest_edge(points, tri))))
    return issues

# --- SP-017: CfgSlots.selection <-> FireGeometry proxy selection (P1) --------

def _extract_block(text, header_re):
    """Return the brace-matched body of the first class whose header matches
    header_re (regex up to the opening brace). None if not found."""
    m = re.search(header_re, text)
    if not m:
        return None
    i = text.find("{", m.start())
    if i < 0:
        return None
    depth = 0
    for j in range(i, len(text)):
        if text[j] == "{":
            depth += 1
        elif text[j] == "}":
            depth -= 1
            if depth == 0:
                return text[i + 1:j]
    return None

def parse_wheel_selections(config_text):
    """Best-effort wheel-slot selection extraction from a vehicle config.cpp.

    Returns (selections:set, slots:set, note:str). Structure (verified against
    dayz-model-pipeline/references/vehicle-config-and-modelcfg.md):
      SimulationModule.Axles.<Front|Rear>.Wheels.<Left|Right>.inventorySlot="<slot>"
      CfgSlots.Slot_*{ name="<slot>"; selection="<sel>"; }
    Some configs (Landrover) omit CfgSlots (vanilla auto-registration) -> the
    slot->selection mapping cannot be resolved; that is reported, not failed."""
    txt = re.sub(r'//[^\n]*', '', config_text)
    txt = re.sub(r'/\*.*?\*/', '', txt, flags=re.S)
    axles = _extract_block(txt, r'class\s+Axles\b')
    if axles is None:
        return set(), set(), "no 'class Axles' block (not a wheeled-vehicle config or non-standard structure)"
    slots = set(re.findall(r'inventorySlot\s*=\s*"([^"]+)"', axles))
    if not slots:
        return set(), set(), "Axles block has no inventorySlot entries"
    sels = set()
    cfgslots = _extract_block(txt, r'class\s+CfgSlots\b')
    mapped = {}
    if cfgslots is not None:
        for m in re.finditer(r'class\s+\w+\s*\{([^{}]*)\}', cfgslots):
            body = m.group(1)
            nm = re.search(r'name\s*=\s*"([^"]+)"', body)
            sl = re.search(r'selection\s*=\s*"([^"]+)"', body)
            if nm and sl:
                mapped[nm.group(1)] = sl.group(1)
    for slot in slots:
        if slot in mapped:
            sels.add(mapped[slot])
    if not sels:
        if cfgslots is None:
            return set(), slots, "no CfgSlots block: slot->selection mapping unresolved (Landrover-style auto-registration). FireGeo wheel-selection consistency NOT auto-verified - check manually."
        return set(), slots, "CfgSlots present but no Slot.name matched a wheel inventorySlot; mapping unresolved - check manually."
    return sels, slots, ""

def check_wheel_slot_firegeo(p, config_text):
    """SP-017 (P1): for each wheel-slot selection named in config, verify it
    exists in the body's FireGeometry LOD (not only in visual LODs). A selection
    present only in visual LODs binds the slot as inventory but PhysX never seats
    the wheel -> WheelCountPresent()=0, silent (no RPT error). See
    enforce-script-reference 'Wheel attachment to simulation'."""
    issues = []
    if not _is_vehicle_body(p):
        return issues
    sels, slots, note = parse_wheel_selections(config_text)
    fire = [(i, lod) for i, lod in enumerate(p.lods)
            if classify_lod(lod.resolution) == "FireGeo"]
    if not fire:
        issues.append(("CRITICAL",
            "Wheeled vehicle body has no FireGeometry LOD: wheels cannot be "
            "seated by PhysX (SP-017)."))
        return issues
    fi, fl = fire[0]
    fnames = {n.lower(): s for n, s in fl.selections.items()}
    if not sels:
        if note:
            issues.append(("NOTE", "SP-017 wheel-slot/FireGeo check: %s" % note))
        return issues
    for sel in sorted(sels):
        key = sel.lower()
        if key not in fnames:
            issues.append(("CRITICAL",
                "SP-017: wheel-slot selection '%s' (from config CfgSlots) is "
                "ABSENT from the FireGeometry LOD[%d] - wheel will not simulate "
                "(WheelCountPresent=0), silent failure. Alias the FireGeo wheel-"
                "proxy face into selection '%s' (additive py3d fix)." % (sel, fi, sel)))
        elif len(fnames[key].faces) == 0:
            issues.append(("WARNING",
                "SP-017: wheel-slot selection '%s' exists in FireGeometry LOD[%d] "
                "but contains 0 faces - it must hold the wheel-proxy face." % (sel, fi)))
    return issues


def audit_p3d(filepath, config_text=None):
    """Full audit of one P3D file. True si no hay CRITICAL."""
    print(f"\n{'='*70}")
    print(f"AUDITING P3D: {filepath}")
    print(f"{'='*70}")

    try:
        with open(filepath, 'rb') as f:
            sig = f.read(4)
            if sig != b'MLOD':
                print(f"  ERROR: Not MLOD format (sig={sig}). Cannot audit ODOL. Provide source MLOD.")
                return False
            f.seek(0)
            p = py3d.P3D(f)
    except Exception as e:
        print(f"  ERROR: Failed to read: {e}")
        return False

    size = os.path.getsize(filepath)
    print(f"  Size: {size} bytes, LODs: {len(p.lods)}")

    all_issues = []
    lod_map = {}
    for i, lod in enumerate(p.lods):
        lt = classify_lod(lod.resolution)
        lod_map[lt] = (i, lod)
        sels = list(lod.selections.keys())
        props = dict(lod.properties) if lod.properties else {}
        print(f"  LOD[{i}] {lt} (res={lod.resolution:.1e}): "
              f"{len(lod.points)}v {len(lod.faces)}f sels={sels} props={props}")

    all_issues.extend(check_required_lods(lod_map))

    # Checks de modelo: delegados al fork (F2-12, paridad depurada).
    for f in p.validate():
        sev = _SEV.get(f.severity, f.severity)
        lod_tag = "" if f.lod is None else "LOD[%d] " % f.lod
        all_issues.append((sev, "%s[%s] %s" % (lod_tag, f.code, f.msg)))

    # Tema B additive checks (complement the fork; SP-009/027/017/023b), and
    # the needle triangles of the collision components (ddce).
    for sev, msg in check_lod0_vertex_budget(p):
        all_issues.append((sev, msg))
    for sev, msg in check_geometry_class_vehicle(p):
        all_issues.append((sev, msg))
    for sev, msg in check_collision_face_material(p):
        all_issues.append((sev, msg))
    for sev, msg in check_collision_needle_triangles(p):
        all_issues.append((sev, msg))
    if config_text:
        for sev, msg in check_wheel_slot_firegeo(p, config_text):
            all_issues.append((sev, msg))
    for sev, msg in all_issues:
        print(f"  {sev}: {msg}")

    crits = sum(1 for s, _ in all_issues if s == "CRITICAL")
    warns = sum(1 for s, _ in all_issues if s == "WARNING")
    notes = sum(1 for s, _ in all_issues if s == "NOTE")
    print(f"\n  {'='*50}")
    if crits == 0 and warns == 0:
        print(f"  RESULT: ALL CHECKS PASSED ({notes} notes)")
    else:
        print(f"  RESULT: {crits} CRITICAL, {warns} WARNING, {notes} NOTE")
    return crits == 0


def audit_text_file(filepath, label="file"):
    print(f"\n{'='*70}")
    print(f"AUDITING {label}: {filepath}")
    print(f"{'='*70}")
    issues = check_p_drive_paths_in_file(filepath)
    for sev, msg in issues:
        print(f"  {sev}: {msg}")
    if not issues:
        print(f"  OK: No P:\\ paths found.")
    return len([s for s, _ in issues if s in ("CRITICAL", "WARNING")]) == 0


def scan_directory(dirpath):
    print(f"\nScanning directory: {dirpath}")
    all_pass = True
    p3d_files = glob.glob(os.path.join(dirpath, '**', '*.p3d'), recursive=True)
    p3d_files = [f for f in p3d_files if not f.endswith('.bak') and '.bak' not in f]
    cfg_text = None
    _cfgs = sorted(glob.glob(os.path.join(dirpath, '**', 'config.cpp'), recursive=True))
    if _cfgs:
        try:
            cfg_text = open(_cfgs[0], encoding='utf-8', errors='ignore').read()
        except Exception:
            cfg_text = None
    for f in sorted(p3d_files):
        if not audit_p3d(f, cfg_text):
            all_pass = False
    for pattern, label in (('**/config.cpp', 'config.cpp'),
                           ('**/*.rvmat', '.rvmat'),
                           ('**/model.cfg', 'model.cfg')):
        for f in sorted(glob.glob(os.path.join(dirpath, pattern), recursive=True)):
            if not audit_text_file(f, label):
                all_pass = False
    return all_pass


def main():
    parser = argparse.ArgumentParser(description="DayZ P3D Audit - Complete Model Validator (py3d fork)")
    parser.add_argument('files', nargs='*', help='.p3d files to audit')
    parser.add_argument('--config', help='config.cpp to check for path issues')
    parser.add_argument('--model-cfg', help='model.cfg to check')
    parser.add_argument('--scan-dir', help='Scan entire mod directory')
    parser.add_argument('--rvmat', nargs='*', help='.rvmat files to check')
    args = parser.parse_args()

    all_pass = True
    if args.scan_dir:
        all_pass = scan_directory(args.scan_dir)
    else:
        cfg_text = open(args.config, encoding='utf-8', errors='ignore').read() if args.config else None
        for f in (args.files or []):
            if not os.path.exists(f):
                print(f"ERROR: File not found: {f}")
                all_pass = False
                continue
            if f.endswith('.p3d'):
                if not audit_p3d(f, cfg_text):
                    all_pass = False
            else:
                if not audit_text_file(f):
                    all_pass = False
        if args.config and not audit_text_file(args.config, "config.cpp"):
            all_pass = False
        if args.model_cfg and not audit_text_file(args.model_cfg, "model.cfg"):
            all_pass = False
        for rv in (args.rvmat or []):
            if not audit_text_file(rv, ".rvmat"):
                all_pass = False

    print(f"\n{'='*70}")
    print(f"OVERALL: {'ALL PASSED' if all_pass else 'ISSUES FOUND - fix before building PBO'}")
    print(f"{'='*70}")
    sys.exit(0 if all_pass else 1)


if __name__ == "__main__":
    main()
