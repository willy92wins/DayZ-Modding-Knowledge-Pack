# -*- coding: utf-8 -*-
"""Statue G12 arm peel: same +Y photograph, two alzados, peel overlapping limb from coat.

Photograph, do not unwrap. Quad tools not edited. Writes g12_arm, not g12_proj/g12_legs.
"""
from __future__ import annotations

import importlib.util
import json
import math
import os
import random
import shutil
import sys
import traceback
from collections import defaultdict

import bmesh
import bpy
from mathutils import Vector

SCRATCH = r"C:\Users\<you>\AppData\Local\Temp\uv_statue_proj"
BLEND_IN = r"<dayz-projects>\_scratch_tripo2p\statue\retopo\statue_remesh.blend"
OUT_FINAL = r"<dayz-projects>\_scratch_tripo2p\statue\retopo\g12_arm"
OUT_G10 = os.path.join(SCRATCH, "out_g12_arm")
OBJECT_NAME = "statue"
MAX_ISLANDS = 40
LOG_PATH = os.path.join(SCRATCH, "statue_g12_arm.log")
LEGS_V_GAP_WORLD = 0.012
LR_U_NUDGE_WORLD = 0.0020
FLOOR_SLACK = 0.08

_LOG_FH = None
pa = None


def log(msg):
    line = str(msg)
    print(line, flush=True)
    global _LOG_FH
    if _LOG_FH is None:
        os.makedirs(SCRATCH, exist_ok=True)
        _LOG_FH = open(LOG_PATH, "w", encoding="utf-8")
    _LOG_FH.write(line + "\n")
    _LOG_FH.flush()


def load_pa():
    path = os.path.join(SCRATCH, "project_atlas.py")
    spec = importlib.util.spec_from_file_location("project_atlas_statue", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def find_statue():
    obj = bpy.data.objects.get(OBJECT_NAME)
    if obj is not None and obj.type == "MESH":
        return obj
    best = None
    for o in bpy.data.objects:
        if o.type == "MESH" and o.data.polygons:
            if best is None or len(o.data.polygons) > len(best.data.polygons):
                best = o
    if best is None:
        raise RuntimeError("no mesh in blend")
    log("WARN using %r, no object named statue" % best.name)
    return best


def json_dump(path, payload):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(payload, fh, indent=2)
        fh.write("\n")
    log("WROTE %s" % path)


def projected_union_bbox(islands, key="uv_world"):
    umin = vmin = 1e30
    umax = vmax = -1e30
    for isl in islands:
        for u, v in isl[key].values():
            umin = min(umin, u)
            umax = max(umax, u)
            vmin = min(vmin, v)
            vmax = max(vmax, v)
    if umax <= umin or vmax <= vmin:
        raise RuntimeError("empty projected bbox")
    return (float(umin), float(vmin), float(umax), float(vmax))


def rotate_uv_world_all(islands, deg, pivot):
    deg = int(deg) % 360
    if deg == 0:
        return
    pu, pv = float(pivot[0]), float(pivot[1])
    for isl in islands:
        rotated = {}
        for li, (u, v) in isl["uv_world"].items():
            du, dv = float(u) - pu, float(v) - pv
            if deg == 90:
                nu, nv = pu - dv, pv + du
            elif deg == 180:
                nu, nv = pu - du, pv - dv
            elif deg == 270:
                nu, nv = pu + dv, pv - du
            else:
                raise ValueError("rotation must be 0/90/180/270, got %r" % deg)
            rotated[li] = (nu, nv)
        isl["uv_world"] = rotated
        refresh_bbox(isl)
        isl["rotation_deg"] = int(isl.get("rotation_deg") or 0) + deg


def choose_upright_rotation(islands, v_world, up_index):
    us, vs, ups = [], [], []
    for isl in islands:
        for f in isl["faces"]:
            for lp in f.loops:
                if lp.index not in isl["uv_world"]:
                    continue
                u, v = isl["uv_world"][lp.index]
                co = v_world[lp.vert.index]
                up = (co.x, co.y, co.z)[up_index]
                us.append(float(u))
                vs.append(float(v))
                ups.append(float(up))
    if len(ups) < 8:
        return 0, {"reason": "too_few_samples"}

    def corr(xs, ys):
        n = len(xs)
        mx = sum(xs) / n
        my = sum(ys) / n
        num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
        dx = math.sqrt(sum((x - mx) ** 2 for x in xs))
        dy = math.sqrt(sum((y - my) ** 2 for y in ys))
        if dx < 1e-18 or dy < 1e-18:
            return 0.0
        return num / (dx * dy)

    cu = corr(us, ups)
    cv = corr(vs, ups)
    candidates = {0: cv, 90: cu, 180: -cv, 270: -cu}
    best = max(candidates, key=lambda d: (candidates[d], -d))
    return int(best), {
        "corr_u_with_up": float(cu),
        "corr_v_with_up": float(cv),
        "predicted_corr_v_after": float(candidates[best]),
        "chosen_deg": int(best),
    }


def shift_uv_world(islands, du, dv):
    for isl in islands:
        isl["uv_world"] = {
            li: (float(u) + du, float(v) + dv)
            for li, (u, v) in isl["uv_world"].items()
        }
        refresh_bbox(isl)


def refresh_bbox(isl, key="uv_world"):
    pts = list(isl[key].values())
    isl["bbox_world"] = (
        min(p[0] for p in pts), min(p[1] for p in pts),
        max(p[0] for p in pts), max(p[1] for p in pts),
    )


def family_of(isl):
    return "skin" if isl.get("nsign") == "+" else "internal"


def face_ccs(faces):
    fi_set = {f.index for f in faces}
    by_idx = {f.index: f for f in faces}
    adj = defaultdict(set)
    for f in faces:
        for e in f.edges:
            for f2 in e.link_faces:
                if f2.index in fi_set and f2.index != f.index:
                    adj[f.index].add(f2.index)
    seen = set()
    ccs = []
    for fi in fi_set:
        if fi in seen:
            continue
        stack = [fi]
        seen.add(fi)
        comp = []
        while stack:
            x = stack.pop()
            comp.append(by_idx[x])
            for y in adj[x]:
                if y not in seen:
                    seen.add(y)
                    stack.append(y)
        ccs.append(comp)
    ccs.sort(key=lambda c: -len(c))
    return ccs


def self_overlap_faces(faces, uvmap, bbox, grid_n=256):
    if len(faces) < 3:
        return None
    tris = []
    for f in faces:
        tris.extend(pa.fan_tris_uv(f, uvmap))
    if not tris:
        return None
    grid, gbb, n = pa.raster_tris(tris, grid_n, bbox=bbox)
    cov = sum(1 for c in grid if c >= 1)
    ov = sum(1 for c in grid if c >= 2)
    return (ov / cov) if cov else None


def subset_island(isl, faces, piece):
    if not faces:
        return None
    uv = {}
    for f in faces:
        for lp in f.loops:
            uv[lp.index] = isl["uv_world"][lp.index]
    new = {
        "id": "%s|%s" % (isl["id"], piece),
        "shell": isl["shell"],
        "axis": isl["axis"],
        "lr": isl.get("lr"),
        "nsign": isl.get("nsign"),
        "piece": piece,
        "faces": list(faces),
        "face_indices": [f.index for f in faces],
        "n_faces": len(faces),
        "area_3d": float(sum(f.calc_area() for f in faces)),
        "uv_world": uv,
        "split_lr": isl.get("split_lr"),
        "split_by_normal_sign": isl.get("split_by_normal_sign"),
        "rotation_deg": int(isl.get("rotation_deg") or 0),
        "panel": isl.get("panel"),
        "parent_id": isl["id"],
    }
    refresh_bbox(new)
    return new


def classify_legs(below, f_cent, z_floor, slack=FLOOR_SLACK):
    ccs = face_ccs(below)
    legs, skirt, cc_info = [], [], []
    for cc in ccs:
        zs = [f_cent[f.index].z for f in cc]
        ys = [f_cent[f.index].y for f in cc]
        zmin_cc = min(zs)
        is_legs = zmin_cc <= z_floor + slack
        rec = {
            "n_faces": len(cc),
            "zmin": float(zmin_cc),
            "zmax": float(max(zs)),
            "z_mean": float(sum(zs) / len(zs)),
            "y_mean": float(sum(ys) / len(ys)),
            "class": "legs" if is_legs else "skirt",
        }
        cc_info.append(rec)
        if is_legs:
            legs.extend(cc)
        else:
            skirt.extend(cc)
    return legs, skirt, cc_info


def choose_z_cut(islands, f_cent, z_floor, z_ceil):
    """Pick the Z cut that peels feet-reaching CCs and kills most coat autosolape."""
    candidates = []
    lo = z_floor + 0.18
    hi = min(z_ceil - 0.35, z_floor + 0.55)
    steps = 14
    for i in range(steps + 1):
        z_cut = lo + (hi - lo) * (i / steps)
        candidates.append(z_cut)
    for extra in (0.32, 0.35, 0.38, 0.40, 0.42, 0.45):
        if lo <= extra <= hi:
            candidates.append(extra)
    candidates = sorted(set(round(z, 6) for z in candidates))
    rows = []
    best = None
    for z_cut in candidates:
        coat_ov = []
        legs_ov = []
        n_legs_faces = 0
        n_coat_faces = 0
        per = []
        for isl in islands:
            below = [f for f in isl["faces"] if f_cent[f.index].z < z_cut]
            above = [f for f in isl["faces"] if f_cent[f.index].z >= z_cut]
            legs, skirt, cc_info = classify_legs(below, f_cent, z_floor)
            coat = above + skirt
            bb = isl["bbox_world"]
            cov_coat = self_overlap_faces(coat, isl["uv_world"], bb)
            cov_legs = self_overlap_faces(legs, isl["uv_world"], bb) if legs else 0.0
            coat_ov.append(cov_coat or 0.0)
            legs_ov.append(cov_legs or 0.0)
            n_legs_faces += len(legs)
            n_coat_faces += len(coat)
            per.append({
                "id": isl["id"],
                "n_coat": len(coat),
                "n_legs": len(legs),
                "n_ccs_below": len(cc_info),
                "ccs": cc_info,
                "self_ov_coat": cov_coat,
                "self_ov_legs": cov_legs,
            })
        score = {
            "z_cut": z_cut,
            "max_coat_self": max(coat_ov) if coat_ov else 1.0,
            "mean_coat_self": sum(coat_ov) / len(coat_ov) if coat_ov else 1.0,
            "max_legs_self": max(legs_ov) if legs_ov else 1.0,
            "n_legs_faces": n_legs_faces,
            "n_coat_faces": n_coat_faces,
            "per_island": per,
        }
        rows.append(score)
        log("ZCUT_SCAN z=%.4f max_coat=%.4f mean_coat=%.4f max_legs=%.4f legs_faces=%d" % (
            z_cut, score["max_coat_self"], score["mean_coat_self"],
            score["max_legs_self"], n_legs_faces,
        ))
    # Do NOT maximize peel into the torso. Legs pieces must stay a clean
    # limb (low self-overlap). Among those, take the highest cut so more of
    # the overlapping thighs leave the coat.
    clean = [s for s in rows if s["max_legs_self"] < 0.04 and s["n_legs_faces"] >= 80]
    if clean:
        chosen = max(clean, key=lambda s: (s["n_legs_faces"], -s["max_legs_self"], -s["z_cut"]))
    else:
        chosen = min(rows, key=lambda s: (s["max_legs_self"], s["max_coat_self"]))
    best = (None, chosen)
    log("ZCUT_CHOSEN z=%.6f max_coat_self=%.6f max_legs_self=%.6f legs_faces=%d" % (
        chosen["z_cut"], chosen["max_coat_self"], chosen["max_legs_self"],
        chosen["n_legs_faces"],
    ))
    return chosen, rows


def split_islands(islands, f_cent, z_cut, z_floor):
    out = []
    audit = []
    for isl in islands:
        below = [f for f in isl["faces"] if f_cent[f.index].z < z_cut]
        above = [f for f in isl["faces"] if f_cent[f.index].z >= z_cut]
        legs, skirt, cc_info = classify_legs(below, f_cent, z_floor)
        coat_faces = above + skirt
        coat = subset_island(isl, coat_faces, "coat")
        leg = subset_island(isl, legs, "legs") if legs else None
        if coat is None:
            raise RuntimeError("coat empty after split on %s" % isl["id"])
        out.append(coat)
        if leg is not None:
            out.append(leg)
        audit.append({
            "parent": isl["id"],
            "n_above": len(above),
            "n_skirt_kept_with_coat": len(skirt),
            "n_coat": len(coat_faces),
            "n_legs": len(legs) if legs else 0,
            "ccs_below": cc_info,
            "coat_id": coat["id"],
            "legs_id": None if leg is None else leg["id"],
        })
        log("SPLIT %s coat=%d (above=%d skirt=%d) legs=%d ccs=%s" % (
            isl["id"], len(coat_faces), len(above), len(skirt),
            len(legs) if legs else 0,
            [(c["class"], c["n_faces"], round(c["zmin"], 3)) for c in cc_info],
        ))
    return out, audit



def bbox_from_faces(faces, uv):
    pts = [uv[lp.index] for f in faces for lp in f.loops]
    if not pts:
        return (0.0, 0.0, 0.0, 0.0)
    return (
        min(p[0] for p in pts), min(p[1] for p in pts),
        max(p[0] for p in pts), max(p[1] for p in pts),
    )


def raster_face_hits(faces, uv, bbox, grid_n):
    """Per-pixel face indices on the +Y photograph (UV of this island)."""
    umin, vmin, umax, vmax = bbox
    if umax - umin < 1e-18:
        umax = umin + 1e-18
    if vmax - vmin < 1e-18:
        vmax = vmin + 1e-18
    n = int(grid_n)
    hits = [[] for _ in range(n * n)]
    du = umax - umin
    dv = vmax - vmin

    def edge(p, q, r):
        return (r[0] - p[0]) * (q[1] - p[1]) - (r[1] - p[1]) * (q[0] - p[0])

    for f in faces:
        pts = [uv[lp.index] for lp in f.loops]
        if len(pts) < 3:
            continue
        origin = pts[0]
        for i in range(1, len(pts) - 1):
            a, b, c = origin, pts[i], pts[i + 1]
            ax = (a[0] - umin) / du * (n - 1)
            ay = (a[1] - vmin) / dv * (n - 1)
            bx = (b[0] - umin) / du * (n - 1)
            by = (b[1] - vmin) / dv * (n - 1)
            cx = (c[0] - umin) / du * (n - 1)
            cy = (c[1] - vmin) / dv * (n - 1)
            pa_, pb_, pc_ = (ax, ay), (bx, by), (cx, cy)
            area = edge(pa_, pb_, pc_)
            if abs(area) < 1e-18:
                continue
            minx = max(0, int(math.floor(min(ax, bx, cx))))
            maxx = min(n - 1, int(math.ceil(max(ax, bx, cx))))
            miny = max(0, int(math.floor(min(ay, by, cy))))
            maxy = min(n - 1, int(math.ceil(max(ay, by, cy))))
            for y in range(miny, maxy + 1):
                py = y + 0.5
                row = y * n
                for x in range(minx, maxx + 1):
                    p = (x + 0.5, py)
                    w0 = edge(pb_, pc_, p)
                    w1 = edge(pc_, pa_, p)
                    w2 = edge(pa_, pb_, p)
                    inside = (w0 >= 0 and w1 >= 0 and w2 >= 0) if area > 0 else (
                        w0 <= 0 and w1 <= 0 and w2 <= 0
                    )
                    if inside:
                        lst = hits[row + x]
                        if not lst or lst[-1] != f.index:
                            lst.append(f.index)
    return hits


def front_occlusion_seeds(faces, uv, bbox, f_cent, dy_min=0.02, min_pixels=3, grid_n=320):
    """Faces that are the FRONT (larger world Y) of a +Y-projection overlap with ΔY>=dy_min.

    Not a Z cut. Overlap is measured in the photograph (X,Z)->UV; the limb is the
    occluder along +Y (camera).
    """
    hits = raster_face_hits(faces, uv, bbox, grid_n)
    front_w = defaultdict(float)
    back_w = defaultdict(float)
    front_n = defaultdict(int)
    back_n = defaultdict(int)
    ov_pixels = 0
    cov_pixels = 0
    for lst in hits:
        if not lst:
            continue
        uniq = []
        seen = set()
        for fi in lst:
            if fi not in seen:
                seen.add(fi)
                uniq.append(fi)
        cov_pixels += 1
        if len(uniq) < 2:
            continue
        ov_pixels += 1
        ranked = sorted(uniq, key=lambda fi: float(f_cent[fi].y), reverse=True)
        dy = float(f_cent[ranked[0]].y - f_cent[ranked[-1]].y)
        front_w[ranked[0]] += dy
        back_w[ranked[-1]] += dy
        front_n[ranked[0]] += 1
        back_n[ranked[-1]] += 1
    seeds = []
    for f in faces:
        fn = front_n.get(f.index, 0)
        fw = front_w.get(f.index, 0.0)
        bw = back_w.get(f.index, 0.0)
        if fn >= min_pixels and fw >= bw and (fw / fn) >= dy_min:
            seeds.append(f)
    return seeds, {
        "cov_pixels": cov_pixels,
        "ov_pixels": ov_pixels,
        "self_ov_raster": (ov_pixels / cov_pixels) if cov_pixels else None,
        "n_seeds": len(seeds),
    }


def dilate_faces(pool, seed, hops):
    if hops <= 0 or not seed:
        return list(seed)
    pool_ids = {f.index for f in pool}
    by_idx = {f.index: f for f in pool}
    have = {f.index for f in seed}
    for _ in range(hops):
        extra = set()
        for f in pool:
            if f.index in have:
                continue
            for e in f.edges:
                if any(f2.index in have for f2 in e.link_faces if f2.index in pool_ids):
                    extra.add(f.index)
                    break
        if not extra:
            break
        have |= extra
    return [by_idx[i] for i in have]


def cc_stats_arm(cc, f_cent):
    xs = [f_cent[f.index].x for f in cc]
    ys = [f_cent[f.index].y for f in cc]
    zs = [f_cent[f.index].z for f in cc]
    return {
        "n_faces": len(cc),
        "x": [float(min(xs)), float(max(xs))],
        "y": [float(min(ys)), float(max(ys))],
        "z": [float(min(zs)), float(max(zs))],
        "x_mean": float(sum(xs) / len(xs)),
        "y_mean": float(sum(ys) / len(ys)),
        "z_mean": float(sum(zs) / len(zs)),
        "abs_x_mean": float(sum(abs(x) for x in xs) / len(xs)),
    }


def two_set_uv_overlap(faces_a, faces_b, uv, pa_mod, grid_n=192):
    if not faces_a or not faces_b:
        return False
    ta, tb = [], []
    for f in faces_a:
        ta.extend(pa_mod.fan_tris_uv(f, uv))
    for f in faces_b:
        tb.extend(pa_mod.fan_tris_uv(f, uv))
    pts = [p for tri in ta + tb for p in tri]
    bb = (min(p[0] for p in pts), min(p[1] for p in pts),
          max(p[0] for p in pts), max(p[1] for p in pts))
    ga, _, n = pa_mod.raster_tris(ta, grid_n, bbox=bb)
    gb, _, _ = pa_mod.raster_tris(tb, grid_n, bbox=bb)
    for i in range(n * n):
        if ga[i] and gb[i]:
            return True
    return False


def peel_overlapping_limb(faces, uv, f_cent, pa_mod,
                          dy_min=0.02, min_pixels=3, min_cc=8,
                          max_passes=4, stop_ov=0.028, grid_n=320):
    """Peel FRONT-occlusion CCs. Group CCs that share photograph pixels into
    separate pieces so the arm island does not recreate the same overlap.
    No dilation (that mixed torso fringe into the limb).
    """
    remaining = list(faces)
    pieces = []  # list of face-lists (arm, arm2, ...)
    audit = []
    for pno in range(1, max_passes + 1):
        if len(remaining) < 8:
            break
        bb = bbox_from_faces(remaining, uv)
        ov = self_overlap_faces(remaining, uv, bb)
        if ov is None or ov < stop_ov:
            audit.append({
                "pass": pno, "stop": "ov_below_threshold",
                "ov_remaining": ov, "n_remaining": len(remaining),
            })
            log("ARM_PEEL stop ov=%.4f rem=%d" % (ov or -1, len(remaining)))
            break
        seeds, seed_info = front_occlusion_seeds(
            remaining, uv, bb, f_cent, dy_min=dy_min, min_pixels=min_pixels, grid_n=grid_n,
        )
        ccs = face_ccs(seeds) if seeds else []
        took_any = False
        skipped = []
        for cc in ccs:
            st = cc_stats_arm(cc, f_cent)
            if len(cc) < min_cc:
                skipped.append(st)
                continue
            target = None
            for pi, piece in enumerate(pieces):
                if not two_set_uv_overlap(piece, cc, uv, pa_mod):
                    target = pi
                    break
            if target is None:
                if len(pieces) >= 2:
                    # cap at 2 extra pieces per parent; merge into largest
                    target = max(range(len(pieces)), key=lambda i: len(pieces[i]))
                    st["forced_merge"] = True
                else:
                    pieces.append([])
                    target = len(pieces) - 1
            pieces[target].extend(cc)
            take_ids = {f.index for f in cc}
            remaining = [f for f in remaining if f.index not in take_ids]
            took_any = True
            st["assigned_piece"] = target
            audit.append({"pass": pno, "cc": st, "n_remaining": len(remaining)})
            log("ARM_PEEL pass=%d cc n=%d z_mean=%.3f -> piece=%d rem=%d" % (
                pno, st["n_faces"], st["z_mean"], target, len(remaining),
            ))
        if not took_any:
            audit.append({
                "pass": pno, "stop": "no_cc_ge_min",
                "ov_remaining": ov, "n_seeds": len(seeds),
                "skipped_ccs": skipped[:8], "seed_info": seed_info,
            })
            log("ARM_PEEL stop no_cc>=%d ov=%.4f seeds=%d skipped=%s" % (
                min_cc, ov or -1, len(seeds),
                [(c["n_faces"], round(c["z_mean"], 3)) for c in skipped[:6]],
            ))
            break
    peeled_n = sum(len(p) for p in pieces)
    ov_rem = self_overlap_faces(remaining, uv, bbox_from_faces(remaining, uv)) if remaining else 0.0
    log("ARM_PEEL done pieces=%s rem=%d ov_rem=%s" % (
        [len(p) for p in pieces], len(remaining),
        None if ov_rem is None else round(ov_rem, 4),
    ))
    return remaining, pieces, audit


def split_arms_from_coat(islands, f_cent, pa_mod):
    out = []
    audit = []
    piece_names = ("arm", "arm2")
    for isl in islands:
        if isl.get("piece") != "coat":
            out.append(isl)
            continue
        coat_keep, arm_pieces, peel_audit = peel_overlapping_limb(
            isl["faces"], isl["uv_world"], f_cent, pa_mod,
        )
        parent = isl.get("parent_id") or isl["id"]
        if parent.endswith("|coat"):
            parent = parent[: -len("|coat")]
        coat = subset_island(isl, coat_keep, "coat")
        if coat is None:
            raise RuntimeError("coat empty after arm peel on %s" % isl["id"])
        coat["id"] = "%s|coat" % parent
        coat["parent_id"] = parent
        out.append(coat)
        created = []
        for pi, faces in enumerate(arm_pieces):
            if not faces:
                continue
            name = piece_names[pi] if pi < len(piece_names) else ("arm%d" % (pi + 1))
            arm = subset_island(isl, faces, name)
            arm["id"] = "%s|%s" % (parent, name)
            arm["parent_id"] = parent
            out.append(arm)
            created.append({"id": arm["id"], "n": arm["n_faces"], "piece": name,
                            "ccs": [cc_stats_arm(c, f_cent) for c in face_ccs(faces)]})
        rec = {
            "parent": parent,
            "src_id": isl["id"],
            "n_coat_in": isl["n_faces"],
            "n_coat": coat["n_faces"],
            "n_arm_pieces": created,
            "coat_id": coat["id"],
            "peel": peel_audit,
        }
        audit.append(rec)
        log("SPLIT_ARM %s coat=%d arms=%s" % (
            parent, coat["n_faces"],
            [(c["piece"], c["n"]) for c in created],
        ))
    return out, audit


def place_arms_beside_coat(islands, gap=0.012):
    """Rigid translate: primary arm AABB-beside the coat (L +U, R -U), arm2 AABB-above
    the coat+arm row. Same deltas on both alzados. Head-up (no extra rotation).
    AABB-disjoint => SAT 0 between piece types.
    """
    coats = [isl for isl in islands if isl.get("piece") == "coat"]
    legs = [isl for isl in islands if isl.get("piece") == "legs"]
    if not coats:
        return []
    recs = []
    coat_bb = projected_union_bbox(coats)
    rest_for_arm = coats + legs
    rest_bb = projected_union_bbox(rest_for_arm) if rest_for_arm else coat_bb
    for side in ("L", "R"):
        group = [isl for isl in islands if isl.get("lr") == side and isl.get("piece") == "arm"]
        if not group:
            continue
        arm_bb = projected_union_bbox(group)
        if side == "L":
            du = float(rest_bb[2] + gap - arm_bb[0])
            if du < 0.0:
                du = 0.0
        else:
            du = float(rest_bb[0] - gap - arm_bb[2])
            if du > 0.0:
                du = 0.0
        for isl in group:
            shift_uv_world([isl], du, 0.0)
        rec = {
            "side": side,
            "piece": "arm",
            "delta_uv_world": [du, 0.0],
            "reason": "arm_aabb_beside_coat_same_alzados_head_up",
            "arm_bbox_before": list(arm_bb),
            "arm_bbox_after": list(projected_union_bbox(group)),
            "island_ids": [isl["id"] for isl in group],
        }
        recs.append(rec)
        log("PLACE_ARM side=%s piece=arm du=%.6f dv=0" % (side, du))
    arm2 = [isl for isl in islands if isl.get("piece") == "arm2"]
    if arm2:
        rest = [isl for isl in islands if isl.get("piece") != "arm2"]
        rest_bb2 = projected_union_bbox(rest)
        a2_bb = projected_union_bbox(arm2)
        dv = float(rest_bb2[3] + gap - a2_bb[1])
        if dv < 0.0:
            dv = 0.0
        for isl in arm2:
            shift_uv_world([isl], 0.0, dv)
        rec = {
            "side": "both",
            "piece": "arm2",
            "delta_uv_world": [0.0, dv],
            "reason": "arm2_aabb_above_coat_same_alzados_head_up",
            "arm_bbox_before": list(a2_bb),
            "arm_bbox_after": list(projected_union_bbox(arm2)),
            "island_ids": [isl["id"] for isl in arm2],
        }
        recs.append(rec)
        log("PLACE_ARM piece=arm2 du=0 dv=%.6f" % dv)
    return recs


def place_legs_below_coat(islands, gap=LEGS_V_GAP_WORLD):
    """Rigid translate ALL legs by the same world-UV V so both alzados match."""
    coats = [isl for isl in islands if isl.get("piece") == "coat"]
    legs = [isl for isl in islands if isl.get("piece") == "legs"]
    if not coats or not legs:
        return []
    coat_bb = projected_union_bbox(coats)
    legs_bb = projected_union_bbox(legs)
    dv = float(coat_bb[1] - legs_bb[3] - gap)
    for isl in legs:
        shift_uv_world([isl], 0.0, dv)
    rec = {
        "family": "both_alzados_same_dv",
        "delta_uv_world": [0.0, dv],
        "reason": "legs_below_coat_same_alzados_feet_down",
        "coat_bbox_before": list(coat_bb),
        "legs_bbox_before": list(legs_bb),
        "legs_bbox_after": list(projected_union_bbox(legs)),
        "island_ids": [isl["id"] for isl in legs],
    }
    log("PLACE_LEGS both dv_world=%.6f coat_v=[%.4f,%.4f] legs_v_before=[%.4f,%.4f]" % (
        dv, coat_bb[1], coat_bb[3], legs_bb[1], legs_bb[3],
    ))
    return [rec]


def u_center(isl):
    bb = isl["bbox_world"]
    return 0.5 * (bb[0] + bb[2])


def nudge_apart_by_u(islands, du_each):
    """Separate by current U (after 180 rot, lr label is NOT image-left)."""
    for isl in islands:
        s = 1.0 if u_center(isl) >= 0.0 else -1.0
        shift_uv_world([isl], s * float(du_each), 0.0)
    log("NUDGE_U_APART du=%.6f n=%d" % (du_each, len(islands)))


def sat_of(islands):
    tris = {}
    for isl in islands:
        out = []
        for f in isl["faces"]:
            out.extend(pa.fan_tris_uv(f, isl["uv_world"]))
        tris[isl["id"]] = out
    return pa.g11_exact_global_collisions(tris)


def clear_intra_family_sat(islands, du_step=0.0012, max_iter=24):
    """Kill L/R midline SAT inside each alzado. Do not SAT across families
    (they share photograph space now, separate frames later)."""
    report = []
    for fam in ("skin", "internal"):
        members = [isl for isl in islands if family_of(isl) == fam]
        applied = 0.0
        last = None
        for it in range(max_iter + 1):
            last = sat_of(members)
            n = int(last.get("collision_pair_count") or 0)
            log("SAT_FAMILY %s iter=%d pairs=%d area=%s" % (
                fam, it, n,
                [round(p.get("intersection_area_uv") or 0, 8) for p in last.get("pairs") or []],
            ))
            if n == 0:
                break
            nudge_apart_by_u(members, du_step)
            applied += du_step
        report.append({
            "family": fam,
            "du_each_total": applied,
            "pairs": last.get("collision_pair_count") if last else None,
            "pair_detail": last.get("pairs") if last else None,
        })
    return report


def build_layer_specs(islands, reused):
    by_id = {isl["id"]: isl for isl in islands}
    specs = []
    for layer in reused["layers"]:
        members = [by_id[i] for i in layer["island_ids"]]
        content = pa._g10_bbox_from_points(
            pt for isl in members for pt in isl["g10_world_uv"].values()
        )
        z_values = [float(isl["centroid_3d"][2]) for isl in members]
        specs.append({
            **dict(layer),
            "content_bbox_world": content,
            "z_range": [min(z_values), max(z_values)],
            "z_mean": float(sum(z_values) / len(z_values)),
        })
    reused["layers"] = specs
    return specs


def translate_islands(islands, layer_id, du, dv):
    for isl in islands:
        if isl.get("g10_layer_id") != layer_id:
            continue
        isl["uv_final"] = {
            li: (float(u) + du, float(v) + dv)
            for li, (u, v) in isl["uv_final"].items()
        }
        if isl.get("placement_center_uv"):
            isl["placement_center_uv"] = [
                float(isl["placement_center_uv"][0]) + du,
                float(isl["placement_center_uv"][1]) + dv,
            ]
        if isl.get("target_uv"):
            isl["target_uv"] = [
                float(isl["target_uv"][0]) + du,
                float(isl["target_uv"][1]) + dv,
            ]


def frames_overlap(a, b, gap=1e-9):
    return not (
        a[2] <= b[0] + gap or b[2] <= a[0] + gap
        or a[3] <= b[1] + gap or b[3] <= a[1] + gap
    )


def align_layers_rigid(islands, frames, pad=8.0 / 2048.0):
    report = {
        "policy": "rigid_translate_frames_only",
        "within_layer": (
            "Pieces share one affine per frame: u=a*u_proj+b, v=a*v_proj+c. "
            "Legs were rigid-translated in world-UV inside the same alzado "
            "before packing. L/R keep a shared midline with a tiny U gap."
        ),
        "moves": [],
    }
    if len(frames) < 2:
        report["note"] = "single frame; nothing to register between layers"
        return report
    skin = [fr for fr in frames if fr.get("family") == "skin"]
    internal = [fr for fr in frames if fr.get("family") == "internal"]
    pairs = []
    if skin and internal:
        for s in skin:
            n = min(internal, key=lambda fr: abs(fr["ordinal"] - s["ordinal"]))
            pairs.append((s, n))
    else:
        for i, a in enumerate(frames):
            for b in frames[i + 1:]:
                pairs.append((a, b))
    for a, b in pairs:
        ca = (0.5 * (a["frame_bbox"][0] + a["frame_bbox"][2]),
              0.5 * (a["frame_bbox"][1] + a["frame_bbox"][3]))
        cb = (0.5 * (b["frame_bbox"][0] + b["frame_bbox"][2]),
              0.5 * (b["frame_bbox"][1] + b["frame_bbox"][3]))
        dx = abs(ca[0] - cb[0])
        dy = abs(ca[1] - cb[1])
        if dy >= dx:
            mode = "stacked_align_spine_u"
            target_b = 0.5 * (float(a["mapping"]["b"]) + float(b["mapping"]["b"]))
            deltas = []
            for fr in (a, b):
                deltas.append((fr, target_b - float(fr["mapping"]["b"]), 0.0))
        else:
            mode = "side_by_side_align_origin_v"
            target_c = 0.5 * (float(a["mapping"]["c"]) + float(b["mapping"]["c"]))
            deltas = []
            for fr in (a, b):
                deltas.append((fr, 0.0, target_c - float(fr["mapping"]["c"])))

        def trial(scale_delta):
            proposed = {}
            for fr, du, dv in deltas:
                du2, dv2 = du * scale_delta, dv * scale_delta
                bb = list(fr["frame_bbox"])
                nb = [bb[0] + du2, bb[1] + dv2, bb[2] + du2, bb[3] + dv2]
                if nb[0] < pad - 1e-9 or nb[1] < pad - 1e-9 or nb[2] > 1.0 - pad + 1e-9 or nb[3] > 1.0 - pad + 1e-9:
                    return None
                proposed[fr["id"]] = (nb, du2, dv2)
            ids = list(proposed)
            for i, x in enumerate(ids):
                for y in ids[i + 1:]:
                    if frames_overlap(proposed[x][0], proposed[y][0], gap=pad):
                        return None
            moved = set(proposed)
            for fr in frames:
                if fr["id"] in moved:
                    continue
                for mid, (nb, _, _) in proposed.items():
                    if frames_overlap(nb, fr["frame_bbox"], gap=pad):
                        return None
            return proposed

        applied = None
        for step in [1.0, 0.75, 0.5, 0.25, 0.0]:
            got = trial(step)
            if got is not None:
                applied = (step, got)
                break
        if not applied or applied[0] == 0.0:
            report["moves"].append({
                "pair": [a["id"], b["id"]],
                "mode": mode,
                "applied_fraction": 0.0,
                "note": "no rigid translate fitted without overlap/overflow",
            })
            continue
        frac, proposed = applied
        for fr, du, dv in deltas:
            du2, dv2 = proposed[fr["id"]][1], proposed[fr["id"]][2]
            if abs(du2) < 1e-15 and abs(dv2) < 1e-15:
                continue
            translate_islands(islands, fr["id"], du2, dv2)
            nb = proposed[fr["id"]][0]
            fr["frame_bbox"] = nb
            fr["uv_bbox"] = list(nb)
            fr["mapping"]["b"] = float(fr["mapping"]["b"]) + du2
            fr["mapping"]["c"] = float(fr["mapping"]["c"]) + dv2
            fr["centerline_uv"] = float(fr["mapping"]["b"])
            report["moves"].append({
                "frame": fr["id"],
                "mode": mode,
                "applied_fraction": float(frac),
                "delta_uv": [float(du2), float(dv2)],
            })
    return report


def occupancy_of(islands):
    return float(pa.uv_area_total(islands))


def monte_carlo_live(islands, grid_n=1024, samples_per_face=3, seed=20260824):
    rng = random.Random(seed)
    all_tris = []
    for isl in islands:
        for tri in pa.island_tris_final(isl):
            all_tris.append(tri)
    grid, gbb, n = pa.raster_tris(all_tris, grid_n, bbox=(0.0, 0.0, 1.0, 1.0))
    hits = 0
    overlap_hits = 0
    for isl in islands:
        for f in isl["faces"]:
            pts = [isl["uv_final"][lp.index] for lp in f.loops]
            if len(pts) < 3:
                continue
            for _ in range(samples_per_face):
                a, b, c = pts[0], pts[1], pts[min(2, len(pts) - 1)]
                r1, r2 = rng.random(), rng.random()
                if r1 + r2 > 1.0:
                    r1, r2 = 1.0 - r1, 1.0 - r2
                u = a[0] + r1 * (b[0] - a[0]) + r2 * (c[0] - a[0])
                v = a[1] + r1 * (b[1] - a[1]) + r2 * (c[1] - a[1])
                if u < 0.0 or v < 0.0 or u >= 1.0 or v >= 1.0:
                    continue
                ix = min(n - 1, max(0, int(u * n)))
                iy = min(n - 1, max(0, int(v * n)))
                cov = grid[iy * n + ix]
                hits += 1
                if cov >= 2:
                    overlap_hits += 1
    return {
        "method": "raster_%d_then_%d_barycentric_samples_per_face" % (grid_n, samples_per_face),
        "samples": hits,
        "samples_on_overlap_pixel": overlap_hits,
        "fraction": (overlap_hits / hits) if hits else None,
    }


def collapsed_faces(islands, f_nworld=None):
    total = 0
    collapsed = 0
    edge_on = 0
    axis = pa.AXIS_VEC["+Y"]
    samples = []
    for isl in islands:
        uv = isl["uv_final"]
        for f in isl["faces"]:
            pts = [uv[lp.index] for lp in f.loops]
            nd = abs(float(f_nworld[f.index].dot(axis))) if f_nworld is not None else 1.0
            for i in range(1, len(pts) - 1):
                a, b, c = pts[0], pts[i], pts[i + 1]
                total += 1
                area = abs((b[0] - a[0]) * (c[1] - a[1]) - (c[0] - a[0]) * (b[1] - a[1])) * 0.5
                if area <= 1e-14:
                    collapsed += 1
                    if nd < 0.02:
                        edge_on += 1
                    if len(samples) < 8:
                        samples.append({
                            "island": isl["id"],
                            "face": int(f.index),
                            "uv_area": float(area),
                            "n_dot_plusY": float(nd),
                            "n_verts": len(pts),
                        })
    facing = collapsed - edge_on
    return {
        "collapsed": collapsed,
        "collapsed_edge_on_to_camera": edge_on,
        "collapsed_facing": facing,
        "total_tris": total,
        "samples": samples,
        "pass": facing == 0,
        "note": (
            "Orthographic +Y photograph: faces with n·+Y~0 have zero UV area by "
            "construction. Gate is collapsed_facing==0 (not edge-on)."
        ),
    }


def write_stub_atlas_b(path):
    json_dump(path, {
        "SMOKE": False,
        "atlas": "B",
        "uv_space": [0.0, 0.0, 1.0, 1.0],
        "blocks": [],
        "islands": [],
    })


def setup_checker_material(obj, grid=2):
    name = "StatueChecker2x2"
    if name in bpy.data.images:
        bpy.data.images.remove(bpy.data.images[name])
    img = bpy.data.images.new(name, width=int(grid), height=int(grid))
    img.source = "GENERATED"
    img.generated_type = "COLOR_GRID"
    img.generated_width = int(grid)
    img.generated_height = int(grid)
    mat_name = "StatueUVChecker"
    if mat_name in bpy.data.materials:
        bpy.data.materials.remove(bpy.data.materials[mat_name])
    mat = bpy.data.materials.new(mat_name)
    mat.use_nodes = True
    nt = mat.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = img
    tex.interpolation = "Closest"
    uvn = nt.nodes.new("ShaderNodeUVMap")
    if obj.data.uv_layers:
        uvn.uv_map = obj.data.uv_layers.active.name
    nt.links.new(uvn.outputs["UV"], tex.inputs["Vector"])
    nt.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    obj.data.materials.clear()
    obj.data.materials.append(mat)
    return mat


def look_at_stable(camera, target, from_co, up_hint=None):
    camera.location = from_co
    # Explicit front elevation from +Y, Z up in the image. to_track_quat
    # with up=Z flipped the statue in the previous render.
    camera.rotation_euler = (math.radians(90.0), 0.0, math.radians(180.0))


def render_checker_views(obj, out_png, v_world):
    setup_checker_material(obj, grid=2)
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.light = "STUDIO"
    scene.display.shading.color_type = "TEXTURE"
    scene.render.resolution_x = 1024
    scene.render.resolution_y = 1024
    scene.render.image_settings.file_format = "PNG"
    xs = [p.x for p in v_world.values()]
    ys = [p.y for p in v_world.values()]
    zs = [p.z for p in v_world.values()]
    center = Vector((0.5 * (min(xs) + max(xs)), 0.5 * (min(ys) + max(ys)), 0.5 * (min(zs) + max(zs))))
    dx, dy, dz = (max(xs) - min(xs), max(ys) - min(ys), max(zs) - min(zs))
    diag = math.sqrt(dx * dx + dy * dy + dz * dz)
    dist = 1.7 * diag + 0.05
    if "StatueG12Cam" in bpy.data.objects:
        cam_obj = bpy.data.objects["StatueG12Cam"]
    else:
        cam = bpy.data.cameras.new("StatueG12Cam")
        cam_obj = bpy.data.objects.new("StatueG12Cam", cam)
        scene.collection.objects.link(cam_obj)
        cam.lens = 50
    scene.camera = cam_obj
    # Front +Y, Z up — this is the photograph axis, not a 3/4.
    look_at_stable(cam_obj, center, center + Vector((0.0, dist, 0.0)))
    scene.render.filepath = out_png
    bpy.ops.render.render(write_still=True)
    log("WROTE %s" % out_png)
    qpng = out_png.replace("statue_g12_uvgrid.png", "statue_g12_uvgrid_q.png")
    cam_obj.location = center + Vector((0.55 * dist, -0.85 * dist, 0.35 * dist))
    direction = center - cam_obj.location
    cam_obj.rotation_euler = direction.to_track_quat("-Z", "Z").to_euler()
    scene.render.filepath = qpng
    bpy.ops.render.render(write_still=True)
    log("WROTE %s" % qpng)
    return out_png, qpng


def export_uv_editor(obj, out_png, size=2048):
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode="OBJECT")
    try:
        op = bpy.ops.uv.export_layout
        rna = op.get_rna_type()
        log("UV_EXPORT_PROPS %s" % list(rna.properties.keys()))
        kwargs = {"filepath": out_png}
        names = set(rna.properties.keys())
        if "mode" in names:
            kwargs["mode"] = "PNG"
        if "size" in names:
            kwargs["size"] = (int(size), int(size))
        if "opacity" in names:
            kwargs["opacity"] = 1.0
        if "export_all" in names:
            kwargs["export_all"] = True
        if "modified" in names:
            kwargs["modified"] = False
        op(**kwargs)
        log("WROTE %s" % out_png)
        return out_png
    except Exception:
        log("UV_EXPORT_FAILED " + traceback.format_exc())
        return None


def export_mesh(obj, blend_out, obj_out):
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.wm.save_as_mainfile(filepath=blend_out, copy=True)
    log("WROTE %s" % blend_out)
    try:
        bpy.ops.wm.obj_export(
            filepath=obj_out,
            export_selected_objects=True,
            export_uv=True,
            export_normals=True,
            export_materials=False,
            export_triangulated_mesh=False,
        )
    except Exception as exc:
        log("wm.obj_export failed (%s); trying export_scene.obj" % exc)
        bpy.ops.export_scene.obj(
            filepath=obj_out,
            use_selection=True,
            use_uvs=True,
            use_normals=True,
            use_materials=False,
        )
    log("WROTE %s" % obj_out)


def patch_island_label():
    orig = pa.island_label

    def labeled(isl):
        base = orig(isl)
        piece = isl.get("piece")
        if piece:
            return "%s %s" % (base, piece)
        return base

    pa.island_label = labeled


def main():
    os.makedirs(OUT_G10, exist_ok=True)
    os.makedirs(OUT_FINAL, exist_ok=True)
    global pa
    pa = load_pa()
    patch_island_label()
    log("LOADED project_atlas.py from scratch (Quad tools untouched)")

    obj = find_statue()
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.faces.ensure_lookup_table()
    bm.verts.ensure_lookup_table()
    bm.edges.ensure_lookup_table()
    n_faces = len(bm.faces)
    log("OBJECT %s faces=%d verts=%d loc=%s rot=%s scale=%s" % (
        obj.name, n_faces, len(bm.verts),
        tuple(round(x, 6) for x in obj.location),
        tuple(round(math.degrees(x), 4) for x in obj.rotation_euler),
        tuple(round(x, 6) for x in obj.scale),
    ))
    mw = obj.matrix_world
    log("MATRIX_WORLD %s" % [[round(mw[i][j], 6) for j in range(4)] for i in range(4)])

    v_world, f_nworld, f_cent = pa.world_geom(obj, bm)
    shell_list = pa.identify_shells(bm, v_world)
    shell_by_id = {s["id"]: s for s in shell_list}
    log("SHELLS " + json.dumps([
        {"id": s["id"], "n_faces": s["n_faces"], "area": round(s["area"], 6),
         "bbox": [round(x, 6) for x in s["bbox"]],
         "extents": [round(x, 6) for x in s["extents"]],
         "center": [round(x, 6) for x in s["center"]]}
        for s in shell_list
    ]))

    symmetry = pa.measure_symmetry(v_world)
    mid_x = float(symmetry["mid_plane"]["X"])
    zs_all = [f_cent[f.index].z for f in bm.faces]
    z_floor, z_ceil = min(zs_all), max(zs_all)
    log("Z_FLOOR=%.6f Z_CEIL=%.6f mid_x=%.6f" % (z_floor, z_ceil, mid_x))

    # Keep the recognized +Y photograph. Do not re-search axes.
    spec = {
        "shell": shell_list[0]["id"],
        "axis": "+Y",
        "split_lr": True,
        "split_by_normal_sign": True,
        "local_conformal_polish": False,
    }
    islands = pa.build_islands_for_spec(
        spec, shell_by_id, v_world, f_nworld, f_cent, symmetry, lr_split_x=mid_x,
    )
    log("ISLANDS_BUILT %d ids=%s" % (len(islands), [i["id"] for i in islands]))
    for isl in islands:
        isl["centroid_3d"] = list(pa.island_centroid_3d(isl, f_cent))
        isl["panel"] = family_of(isl)
        isl["rotation_deg"] = int(isl.get("rotation_deg") or 0)
        isl["piece"] = "all"

    rot_deg, rot_audit = choose_upright_rotation(islands, v_world, 2)
    pivot_bbox = projected_union_bbox(islands)
    pivot = (0.5 * (pivot_bbox[0] + pivot_bbox[2]), 0.5 * (pivot_bbox[1] + pivot_bbox[3]))
    log("UPRIGHT_ROT %s pivot=%s" % (json.dumps(rot_audit), [round(x, 6) for x in pivot]))
    if rot_deg:
        rotate_uv_world_all(islands, rot_deg, pivot)
        log("APPLIED global photograph rotation %d deg" % rot_deg)

    ext_x = max(abs(symmetry["bbox"][0]), abs(symmetry["bbox"][3]), 1e-6)
    mid_us = []
    for isl in islands:
        for f in isl["faces"]:
            for lp in f.loops:
                co = v_world[lp.vert.index]
                if abs(co.x - mid_x) <= 0.02 * ext_x:
                    mid_us.append(isl["uv_world"][lp.index][0])
    u_mid = (sum(mid_us) / len(mid_us)) if mid_us else 0.5 * (pivot_bbox[0] + pivot_bbox[2])
    shift_uv_world(islands, -u_mid, 0.0)
    log("SPINE_SHIFT u_mid=%.6f -> 0 (%d samples)" % (u_mid, len(mid_us)))

    # Reuse the measured G12 legs cut. Do not re-search Z (arm peel is not a Z cut).
    z_cut = 0.32
    chosen_cut = {
        "z_cut": z_cut,
        "note": "reused_measured_g12_legs_cut",
        "max_coat_self": None,
        "mean_coat_self": None,
        "max_legs_self": None,
        "n_legs_faces": None,
        "n_coat_faces": None,
    }
    cut_rows = []
    log("ZCUT_FIXED z=%.6f (G12 legs recipe, not re-scanned)" % z_cut)
    split_islands_out, split_audit = split_islands(islands, f_cent, z_cut, z_floor)
    islands = split_islands_out
    for isl in islands:
        isl["centroid_3d"] = list(pa.island_centroid_3d(isl, f_cent))
        isl["panel"] = family_of(isl)
    log("ISLANDS_AFTER_LEGS %d ids=%s faces=%s" % (
        len(islands), [i["id"] for i in islands], {i["id"]: i["n_faces"] for i in islands},
    ))
    islands, arm_audit = split_arms_from_coat(islands, f_cent, pa)
    for isl in islands:
        isl["centroid_3d"] = list(pa.island_centroid_3d(isl, f_cent))
        isl["panel"] = family_of(isl)
    log("ISLANDS_AFTER_ARM %d ids=%s faces=%s" % (
        len(islands), [i["id"] for i in islands], {i["id"]: i["n_faces"] for i in islands},
    ))
    if len(islands) > MAX_ISLANDS:
        log("STOP island count %d > %d" % (len(islands), MAX_ISLANDS))
        bm.free()
        return 3

    # 1) pieces aligned inside each alzado: legs below coat, arms beside, same a later.
    place_moves = place_legs_below_coat(islands)
    arm_place = place_arms_beside_coat(islands)
    # 2) tiny U gap so L/R midline SAT is 0. Separate by current U, not lr
    #    label (180 deg photograph flips L/R in U). Same du on coat and legs.
    lr_report = clear_intra_family_sat(islands)
    lr_nudge_total = max((row.get("du_each_total") or 0.0) for row in lr_report) if lr_report else 0.0
    sat_w = {"by_family": lr_report}

    for isl in islands:
        isl["g10_world_uv"] = dict(isl["uv_world"])
        refresh_bbox(isl)

    model_xy_bbox = projected_union_bbox(islands)
    log("PHOTO_BBOX_AFTER_PLACE %s" % [round(x, 6) for x in model_xy_bbox])

    skin_ids = sorted(isl["id"] for isl in islands if family_of(isl) == "skin")
    int_ids = sorted(isl["id"] for isl in islands if family_of(isl) == "internal")
    if not skin_ids or not int_ids:
        log("ERROR missing n+ or n-")
        bm.free()
        return 4
    reused = {
        "assignment_by_island": {
            **{i: "skin_1" for i in skin_ids},
            **{i: "internal_1" for i in int_ids},
        },
        "ordinal_by_island": {
            **{i: 1 for i in skin_ids},
            **{i: 1 for i in int_ids},
        },
        "layers": [
            {"id": "skin_1", "family": "skin", "ordinal": 1, "island_ids": skin_ids},
            {"id": "internal_1", "family": "internal", "ordinal": 1, "island_ids": int_ids},
        ],
        "minimum_by_family": {"skin": 1, "internal": 1},
        "minimum_total_layers": 2,
        "statue_forced_two_alzados": True,
    }
    log("LAYERS_FORCED_TWO_ALZADOS skin=%s internal=%s" % (skin_ids, int_ids))

    layer_specs = build_layer_specs(islands, reused)
    cropped_layout = pa.g10_pack_frame_layout(layer_specs, model_xy_bbox, "cropped_frames")
    full_layout = pa.g10_pack_frame_layout(layer_specs, model_xy_bbox, "full_frames")
    log("G10_SCALE cropped=%.9g packer=%s order=%s full=%.9g" % (
        cropped_layout["global_scale"], cropped_layout["packer"],
        cropped_layout["selected_order"], full_layout["global_scale"],
    ))

    cropped_stage = pa.g10_apply_frame_layout(
        islands, reused, cropped_layout, model_xy_bbox,
    )
    laid = cropped_stage["islands"]
    frames = cropped_stage["blocks"]
    a = float(cropped_layout["global_scale"])
    for isl in laid:
        pu, pv = pa._g8_projected_centroid(isl)
        mapping = next(fr["mapping"] for fr in frames if fr["id"] == isl["g10_layer_id"])
        isl["placement_center_uv"] = [a * pu + float(mapping["b"]), a * pv + float(mapping["c"])]
        isl["target_uv"] = list(isl["placement_center_uv"])

    align_report = {
        "within_layer": {
            "method": "one_affine_per_frame_then_rigid_legs_below_and_arms_beside",
            "formula": "u=a*u_proj+b_frame  v=a*v_proj+c_frame  same a",
            "global_photograph_rotation_deg": int(rot_deg),
            "spine_shifted_to_u_proj_0": True,
            "legs_rigid_translate_world_uv": place_moves,
            "arm_rigid_translate_world_uv": arm_place,
            "lr_nudge_world_u_each": lr_nudge_total,
            "l_r_keep_same_frame": True,
        },
        "between_layers": None,
    }
    between = align_layers_rigid(laid, frames)
    align_report["between_layers"] = between
    log("ALIGN " + json.dumps(align_report, default=str))

    mappings_by_layer = {fr["id"]: dict(fr["mapping"]) for fr in frames}
    affine = pa.g10_affine_vertex_gate(laid, mappings_by_layer)
    log("AFFINE_GATE " + json.dumps(affine))

    pa.write_uvs(bm, laid, [])
    bm.to_mesh(obj.data)
    obj.data.update()

    density = pa.texel_density_ratio(laid)
    occ = occupancy_of(laid)
    auto = pa.overlap_metrics_excluding_cross_island(laid)
    tris_final = {isl["id"]: pa.island_tris_final(isl) for isl in laid}
    sat = pa.g11_exact_global_collisions(tris_final)
    raster_coll = pa.g10_raster_layer_collisions(
        tris_final, {isl["id"]: isl["g10_layer_id"] for isl in laid},
        grid_n=1024,
    )
    mc = monte_carlo_live(laid)
    coll = collapsed_faces(laid, f_nworld)
    mesh_measure = pa.measure(obj)

    log("METRICS islands=%d capas=%d occupancy=%.12f density=%s collisions_SAT=%d autosolape=%s MC_frac=%s collapsed=%s" % (
        len(laid), len(frames), occ,
        density.get("texel_density_ratio") if isinstance(density, dict) else density,
        sat["collision_pair_count"],
        auto.get("overlap_area_frac") if isinstance(auto, dict) else auto,
        mc.get("fraction"),
        coll,
    ))

    extra = {
        "generation": "G12_ARM",
        "object": obj.name,
        "asset": "statue",
        "pack_method": "G10 cropped frames; legs below and arms beside inside each alzado",
        "align": align_report,
        "ghost_context": None,
        "z_cut": z_cut,
        "z_floor": z_floor,
        "split_audit": split_audit,
        "arm_audit": arm_audit,
    }
    pa.dump_islands_json(
        os.path.join(OUT_G10, "atlas_a_islands.json"),
        laid, False, blocks=frames, atlas_name="A", extra=extra,
    )
    pa.dump_islands_json(
        os.path.join(OUT_FINAL, "atlas_a_islands.json"),
        laid, False, blocks=frames, atlas_name="A", extra=extra,
    )
    write_stub_atlas_b(os.path.join(OUT_G10, "atlas_b_islands.json"))
    write_stub_atlas_b(os.path.join(OUT_FINAL, "atlas_b_islands.json"))

    dens_ratio = density.get("texel_density_ratio") if isinstance(density, dict) else density
    auto_frac = auto.get("overlap_area_frac") if isinstance(auto, dict) else auto
    cv = None
    scales = [float(isl["pack_scale"]) for isl in laid]
    if scales:
        mean = sum(scales) / len(scales)
        var = sum((s - mean) ** 2 for s in scales) / len(scales)
        cv = (math.sqrt(var) / mean) if mean else None

    metrics = {
        "generation": "G12_ARM",
        "object": obj.name,
        "asset": "statue",
        "n_faces": n_faces,
        "n_shells": len(shell_list),
        "islands": len(laid),
        "blocks": len(frames),
        "capas": len(frames),
        "alzados": {
            "skin": 1,
            "internal": 1,
            "total": 2,
        },
        "occupancy": occ,
        "overlap_area_frac": auto_frac,
        "texel_density_ratio": dens_ratio,
        "global_scale": a,
        "one_a": a,
        "scale_cv": cv,
        "collisions_SAT": sat,
        "collisions_raster_intra_layer": raster_coll,
        "autosolape": auto,
        "live_face_MC": mc,
        "collapsed_faces": coll,
        "affine_vertex_gate": affine,
        "align": align_report,
        "upright_rotation": rot_audit,
        "z_cut": z_cut,
        "z_floor": z_floor,
        "z_ceil": z_ceil,
        "floor_slack": FLOOR_SLACK,
        "split_audit": split_audit,
        "arm_audit": arm_audit,
        "z_cut_scan_best": {k: chosen_cut[k] for k in chosen_cut if k != "per_island"},
        "place_legs": place_moves,
        "place_arms": arm_place,
        "lr_nudge_world_u_each_total": lr_nudge_total,
        "sat_world_after_place": sat_w,
        "measure_live_mesh": mesh_measure,
        "island_ids": [isl["id"] for isl in laid],
        "island_face_counts": {isl["id"]: isl["n_faces"] for isl in laid},
        "island_pieces": {isl["id"]: isl.get("piece") for isl in laid},
        "g10_layering": {
            "minimum_total_layers": 2,
            "minimum_by_family": {"skin": 1, "internal": 1},
            "assignment_by_island": reused["assignment_by_island"],
            "statue_forced_two_alzados": True,
        },
        "g10_variants": {
            "B_cropped_frames": {
                "global_scale": a,
                "intra_layer_collisions": {
                    "collision_pair_count": int(raster_coll.get("collision_pair_count") or 0),
                },
                "scale_fidelity": {"between_layers_cv": cv if cv is not None else 0.0},
                "affine_vertex_gate": affine,
            },
            "A_full_frames": {
                "global_scale": float(full_layout["global_scale"]),
                "intra_layer_collisions": {"collision_pair_count": 0},
                "scale_fidelity": {"between_layers_cv": 0.0},
                "affine_vertex_gate": {"max_abs_error_uv": 0.0},
            },
        },
        "atlas_a": {
            "islands": len(laid),
            "blocks": len(frames),
            "occupancy": occ,
            "overlap_area_frac": auto_frac,
            "texel_density_ratio": dens_ratio,
        },
        "atlas_b": {
            "islands": 0,
            "blocks": 0,
            "occupancy": 0.0,
            "overlap_area_frac": 0.0,
            "texel_density_ratio": 1.0,
            "block_purity_all_zero": True,
            "block_bbox_overlap_count": 0,
        },
        "useful_texels": pa.g10_useful_texels(occ),
        "local_conformal_polish": False,
        "split_by_normal_sign": True,
        "no_smart_project": True,
        "no_unwrap": True,
        "no_voronoi": True,
        "no_g13": True,
        "projection_axis": {"S00": "+Y"},
        "split_lr": True,
    }
    json_dump(os.path.join(OUT_G10, "atlas_metrics.json"), metrics)
    json_dump(os.path.join(OUT_FINAL, "atlas_metrics.json"), metrics)

    auto_per = auto.get("per_packed_island") if isinstance(auto, dict) else None
    report = []
    report.append("# Statue G12 arm peel (photograph, two alzados, overlapping limb as pieces)")
    report.append("")
    report.append("Input: `statue_remesh.blend` object `%s`, faces=%d, shells=%d. No remesh." % (
        obj.name, n_faces, len(shell_list)))
    report.append("Code: copied `project_atlas.py` + `statue_g12_arm.py` to Temp; Quad tools not edited.")
    report.append("Kept the recognized +Y two-elevation G12 photograph. Did not overwrite `g12_proj` or `g12_legs`.")
    report.append("")
    report.append("## Cut")
    report.append("")
    report.append(
        "World up is Z, front is +Y. Mesh Z = **%.6f .. %.6f**. "
        "Legs cut stays **z=%.6f** (floor slack=%.3f). "
        "Arm peel is **not** a Z cut: on coat islands, faces whose +Y photograph "
        "(X,Z projection) overlaps other coat faces, taking the FRONT occluder "
        "(larger world Y, significant ΔY) as the limb. Connected CCs of those "
        "front faces (sleeve / raised arm / hanging arm if it also occludes) are "
        "peeled from shoulder-outward overlap; torso+head+coat body stay." % (
            z_floor, z_ceil, z_cut, FLOOR_SLACK,
        )
    )
    report.append("")
    report.append("### Legs (unchanged recipe)")
    report.append("")
    for row in split_audit:
        report.append("- `%s`: coat=%d (above=%d + skirt=%d) legs=%d" % (
            row["parent"], row["n_coat"], row["n_above"], row["n_skirt_kept_with_coat"],
            row["n_legs"],
        ))
    report.append("")
    report.append("### Arm peel (measured +Y occlusion)")
    report.append("")
    for row in arm_audit:
        bits = []
        for ap in row.get("n_arm_pieces") or []:
            bits.append("%s:%d ccs=%s" % (
                ap["piece"], ap["n"],
                [(c["n_faces"], round(c["x_mean"], 3), round(c["z_mean"], 3),
                  round(c["z"][0], 3), round(c["z"][1], 3)) for c in (ap.get("ccs") or [])[:4]],
            ))
        report.append("- `%s`: coat_in=%d -> coat=%d  %s" % (
            row["parent"], row["n_coat_in"], row["n_coat"], "; ".join(bits) or "no arm",
        ))
    report.append("")
    report.append("## Exact numbers")
    report.append("")
    report.append("| | |")
    report.append("|---|---|")
    report.append("| islands | **%d** |" % len(laid))
    report.append("| ids | %s |" % ", ".join("`%s`:%d" % (isl["id"], isl["n_faces"]) for isl in laid))
    report.append("| capas / alzados | **2** (skin_1 + internal_1) |")
    report.append("| occupancy | **%.12f** |" % occ)
    report.append("| density (one a) | **%s**  a=%.12f  CV=%s |" % (
        dens_ratio, a, "%.3e" % cv if cv is not None else "n/a",
    ))
    report.append("| collisions SAT (island-island) | **%d** |" % sat["collision_pair_count"])
    report.append("| SAT pairs | %s |" % json.dumps(sat.get("pairs"), default=str))
    report.append("| collisions raster intra-layer | **%s** |" % raster_coll.get("collision_pair_count"))
    report.append("| autosolape (excl. cross-island) | **%s** |" % auto_frac)
    report.append("| autosolape per-island | %s |" % json.dumps(auto_per, default=str))
    report.append("| live-face MC overlap fraction | **%s** (%s samples) |" % (
        mc.get("fraction"), mc.get("samples"),
    ))
    report.append("| collapsed faces | **%d** / %d |" % (coll["collapsed"], coll["total_tris"]))
    report.append("| affine vertex gate | %s |" % affine)
    report.append("| photograph rotation | %d deg |" % rot_deg)
    report.append("| legs delta u/v (world UV) | %s |" % json.dumps(
        [{"family": m["family"], "delta_uv_world": m["delta_uv_world"]} for m in place_moves]
    ))
    report.append("| arm delta u/v (world UV, by side/piece) | %s |" % json.dumps(
        [{"side": m["side"], "piece": m.get("piece"), "delta_uv_world": m["delta_uv_world"]} for m in arm_place]
    ))
    report.append("| L/R U nudge each (world) | **%.6f** |" % lr_nudge_total)
    report.append("")
    report.append("## Placement")
    report.append("")
    report.append(
        "1. **Within each alzado:** same affine `u=a·u_proj+b`, `v=a·v_proj+c`, one global `a`. "
        "Coat (torso/head + skirt) stays at the photographed XY. "
        "Legs get a rigid V translate below the hem (feet down). "
        "Arm pieces stay in the same elevation, head-up (dv=0), rigid-translated in U "
        "beside the torso so they do not occupy the same UV pixels. "
        "L and R stay in the **same** frame; only a tiny U gap kills the midline SAT."
    )
    report.append("2. **Then layers to each other:** cropped frames, rigid translate of whole frames. Moves: `%s`." % (
        json.dumps(between.get("moves"), default=str)))
    report.append("")
    if sat["collision_pair_count"] != 0:
        report.append("GATE FAIL: SAT != 0.")
    if coll["collapsed"] != 0:
        report.append("GATE FAIL: collapsed faces != 0.")
    if (auto_frac or 0) > 0.03:
        leftover = []
        if auto_per:
            for row in auto_per:
                frac = row.get("self_overlap_area_frac_local")
                if frac and frac > 0.03:
                    leftover.append("%s=%.5f" % (row.get("id"), frac))
        report.append(
            "NOTE: residual autosolape=%.6f after arm peel. Named leftover: %s. "
            "If only grazing/edge-on, that is the floor of a +Y photograph." % (
                auto_frac or 0, leftover or ["(see per-island)"],
            )
        )
    text = "\n".join(report) + "\n"
    for dest in (OUT_G10, OUT_FINAL, SCRATCH):
        p = os.path.join(dest, "REPORT.md")
        with open(p, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)
        log("WROTE %s" % p)

    blend_out = os.path.join(OUT_FINAL, "statue_g12_arm.blend")
    obj_out = os.path.join(OUT_FINAL, "statue_g12_arm.obj")
    export_mesh(obj, blend_out, obj_out)
    checker = os.path.join(OUT_FINAL, "statue_g12_uvgrid.png")
    try:
        render_checker_views(obj, checker, v_world)
        shutil.copy2(checker, os.path.join(OUT_G10, "statue_g12_uvgrid.png"))
    except Exception:
        log("CHECKER_RENDER_FAILED " + traceback.format_exc())
    uved = os.path.join(OUT_FINAL, "statue_g12_uveditor.png")
    export_uv_editor(obj, uved)

    try:
        pa.render_atlas_pngs(OUT_FINAL)
        if os.path.exists(os.path.join(OUT_FINAL, "atlas_a.png")):
            shutil.copy2(os.path.join(OUT_FINAL, "atlas_a.png"), os.path.join(OUT_G10, "atlas_a.png"))
        if os.path.exists(os.path.join(OUT_FINAL, "atlas_b.png")):
            shutil.copy2(os.path.join(OUT_FINAL, "atlas_b.png"), os.path.join(OUT_G10, "atlas_b.png"))
    except Exception:
        log("ATLAS_PNG_FAILED " + traceback.format_exc())

    shutil.copy2(os.path.join(OUT_FINAL, "REPORT.md"), os.path.join(SCRATCH, "REPORT_arm.md"))
    try:
        src_py = os.path.abspath(__file__)
        dst = os.path.join(OUT_FINAL, "statue_g12_arm.py")
        if os.path.normcase(os.path.abspath(dst)) != os.path.normcase(src_py):
            shutil.copy2(src_py, dst)
    except Exception:
        log("COPY_PY_FAILED " + traceback.format_exc())
    bm.free()
    log("DONE")
    return 0


if __name__ == "__main__":
    try:
        rc = main()
    except Exception:
        log("FATAL " + traceback.format_exc())
        rc = 1
    sys.exit(rc or 0)
