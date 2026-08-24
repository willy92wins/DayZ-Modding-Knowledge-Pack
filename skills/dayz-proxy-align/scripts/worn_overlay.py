#!/usr/bin/env python3
"""
worn_overlay.py — attach worn-clothing reference meshes to a proxy recipe.

For each slot, resolves the WORN-on-male model variant, debinarizes ODOL->MLOD if
needed, extracts its LOD0 geometry, and injects it into the recipe as
proxies[i]["worn"]. The viewer shows it as a translucent ghost (alignment target)
and, via the "Resultado final" button, attached to the proxy (assembled preview).

DEFAULTS: one representative vanilla item is mapped to every slot out of the box,
so you immediately see a fully "dressed" mannequin. Override any slot to test a
specific item with --map Slot=<spec> (a slot you map replaces its default). Use
--no-defaults to start empty, or --dry-run to just print the resolved mapping.

MODEL-VARIANT RULE: clothing ships as <item>_m (male worn, USE THIS), <item>_f
(female), <item>_g (ground/dropped — the "default"/floor one, NOT this). _m is
preferred automatically; if several candidates remain they are reported so you
pick explicitly instead of guessing.

Usage:
  python3 worn_overlay.py recipe.json out_recipe.json --dz "/path/DZ" \
      [--odol-backend "/path/to/odol-backend/scripts"] \
      [--map Vest=vests/plate_carrier Legs=pants/cargopants] [--no-defaults] [--dry-run]
  # A --map value may be a full .p3d path, "<subdir>/<stem>" under DZ/characters,
  # or just "<stem>" (searched recursively under DZ/characters). Prefers the _m file.
"""
import sys, os, json, glob, tempfile, argparse
import py3d

# One sensible vanilla _m item per default mannequin/player slot. Stems are
# resolved to the _m variant at run time; override any with --map.
DEFAULT_MAP = {
    "Body":     "tops/long_sleeve_shirt",
    "Vest":     "vests/plate_carrier",
    "Legs":     "pants/bdu_pants",
    "Feet":     "shoes/combatboots",
    "Gloves":   "gloves/leather_gloves",
    "Headgear": "headgear/baseballcap",
    "Mask":     "masks/airborne_mask",
    "Eyewear":  "glasses/skigoggles",
    "Armband":  "tops/armbend_small",
    "Hips":     "belts/belt_leather",
    "Back":     "backpacks/alicebackpack",
}

def find_odol_backend(arg):
    # External ODOL->MLOD backend (not distributed with this pack); same
    # contract as tools/dayz-odol-strict: a scripts dir with odol_to_mlod.py.
    cands = [arg, os.environ.get("DAYZ_ODOL_BACKEND_ROOT")]
    for c in cands:
        if c and os.path.isfile(os.path.join(c, "odol_to_mlod.py")):
            return os.path.abspath(c)
    return None

def to_mlod(path, debin_scripts):
    if open(path, "rb").read(4) == b"MLOD":
        return path
    if not debin_scripts:
        raise RuntimeError("ODOL model needs an external ODOL->MLOD backend; pass --odol-backend <scripts dir> or set DAYZ_ODOL_BACKEND_ROOT")
    sys.path.insert(0, debin_scripts)
    from odol_reader import ODOL
    from odol_to_mlod import convert_odol_to_mlod
    mlod = convert_odol_to_mlod(ODOL.from_file(path))
    tmp = tempfile.NamedTemporaryFile(suffix=".p3d", delete=False).name
    with open(tmp, "wb") as f:
        mlod.write(f)
    return tmp

def lod0_geo(path):
    with open(path, "rb") as f:
        m = py3d.P3D(f)
    lod = min((l for l in m.lods if l.points), key=lambda x: x.resolution)
    pos = [list(p.coords) for p in lod.points]
    faces = []
    for face in lod.faces:
        vi = [v.point_index for v in face.vertices]
        if len(vi) == 3:
            faces.append(vi)
        elif len(vi) == 4:
            faces.append([vi[0], vi[1], vi[2]]); faces.append([vi[0], vi[2], vi[3]])
        elif len(vi) > 4:
            for k in range(1, len(vi) - 1):
                faces.append([vi[0], vi[k], vi[k+1]])
    return pos, faces

def resolve_variant(dz, spec):
    chars = os.path.join(dz, "characters")
    if spec.lower().endswith(".p3d") and os.path.isfile(spec):
        return spec, [spec]
    if "/" in spec or "\\" in spec:
        hits = glob.glob(os.path.join(chars, spec.replace("\\", "/")) + "*.p3d")
    else:
        hits = glob.glob(os.path.join(chars, "**", spec + "*.p3d"), recursive=True)
    male = sorted(h for h in hits if os.path.basename(h).lower().endswith("_m.p3d"))
    return (male[0] if male else (sorted(hits)[0] if hits else None)), hits

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("recipe"); ap.add_argument("out")
    ap.add_argument("--dz", required=True)
    ap.add_argument("--odol-backend", dest="odol_backend", default=None)
    ap.add_argument("--map", nargs="*", default=[], help="Slot=itemspec ... (overrides the default for that slot)")
    ap.add_argument("--no-defaults", action="store_true", help="do not seed every slot with a default item")
    ap.add_argument("--dry-run", action="store_true", help="resolve + print the mapping, do not debinarize/inject")
    a = ap.parse_args()

    rec = json.load(open(a.recipe))
    by_slot = {p["slot"]: p for p in rec["proxies"]}

    # effective map: defaults (for slots present in the recipe) overridden by --map
    eff = {} if a.no_defaults else {s: v for s, v in DEFAULT_MAP.items() if s in by_slot}
    eff.update(dict(kv.split("=", 1) for kv in a.map))

    debin = None if a.dry_run else find_odol_backend(a.odol_backend)
    done = 0
    for slot, spec in eff.items():
        if slot not in by_slot:
            print("WARN slot '%s' not in recipe (have %s)" % (slot, list(by_slot))); continue
        path, cands = resolve_variant(a.dz, spec)
        if not path:
            print("WARN %-9s no model for '%s' under %s/characters" % (slot, spec, a.dz)); continue
        bn = os.path.basename(path)
        tag = "DEFAULT" if (slot in DEFAULT_MAP and eff[slot] == DEFAULT_MAP.get(slot) and not any(k.split("=")[0]==slot for k in a.map)) else "override"
        if not bn.lower().endswith("_m.p3d"):
            print("ASK  %-9s no _m variant; using %s. Candidates: %s" % (slot, bn, [os.path.basename(c) for c in cands]))
        elif len([c for c in cands if c.lower().endswith("_m.p3d")]) > 1:
            print("NOTE %-9s several _m candidates; picked %s. Override: --map %s=<subdir>/<stem>" % (slot, bn, slot))
        if a.dry_run:
            print("DRY  %-9s [%s] -> %s" % (slot, tag, bn)); continue
        ml = to_mlod(path, debin)
        pos, faces = lod0_geo(ml)
        by_slot[slot]["worn"] = {"positions": pos, "faces": faces, "variant": bn,
                                 "source": os.path.relpath(path, a.dz), "default": tag == "DEFAULT"}
        done += 1
        print("OK   %-9s [%s] <- %-26s (%d verts, %d tris)" % (slot, tag, bn, len(pos), len(faces)))

    if not a.dry_run:
        json.dump(rec, open(a.out, "w"))
        print("wrote %s (%d proxies, %d with worn refs)" % (a.out, len(rec["proxies"]), done))

if __name__ == "__main__":
    main()
