#!/usr/bin/env python3
"""
proxy_frame.py - DayZ/Arma MLOD proxy frame convention (source-verified).

A proxy is a 1-triangle named selection. The engine derives the attachment
orientation from the triangle by ANGLE-SORT, not face-vertex order:

  sort the 3 verts by interior angle, descending:
    center = largest-angle vertex   (anchor / position)
    vert_y = middle-angle vertex     (-> local +Y)
    vert_z = smallest-angle vertex   (-> local +Z)
  y = normalize(vert_y - center); z = normalize(vert_z - center)
  x = normalize(y x z); z = normalize(x x y)        # re-orthogonalize
  R = rows [x, y, z]                                 # local->world orientation

Source (read 2026-05-31): Arma3ObjectBuilder utilities/proxy.py
find_axis_vertices / get_transform_rotation / create_proxy ; doc
https://mrcmodding.gitbook.io/home/documents/proxy-coordinates .
Coords are raw MLOD (what py3d reads); vanilla worn clothing is authored in this
same character space, so the IDENTITY frame == item shown worn upright.

WHY ROTATION USED TO LOOK "approximate": if the two edges from the anchor are
EQUAL length (the 90/45/45 isosceles triangle the mannequin shipped with), the
middle & smallest angles TIE -> y/z get assigned by raw vertex order -> a rotated,
usually-wrong frame. A canonical triangle has three DISTINCT angles so the
assignment is unambiguous. Any rotation of a canonical triangle is still canonical
(rotation preserves angles), so we emit canonical triangles to bake an exact frame.

RESOLVED 2026-06-24 (A6_SR2M, confirmed in-game): the engine reads the triangle as h(R) = P'.R with
P' = [[-1,0,0],[0,0,1],[0,1,0]] relative to this derive_frame. derive_frame is left as-is (callers
rely on it as the skill frame); bake canonical_triangle(anchor, P') when you want the engine to
render IDENTITY. (Historical: an earlier same-day WARNING suspected the Y/Z assignment and
handedness were swapped vs the engine — a ~90deg roll about the long axis, invisible on
cylindrical attachments; superseded by this in-game-confirmed P' convention.) Full convention +
the muzzle-view method for custom weapon-attachment models:
SKILL.md "Weapon attachment proxies + the engine-vs-skill convention map".
"""
import numpy as np

def _angle(u, v):
    nu = float(np.linalg.norm(u)); nv = float(np.linalg.norm(v))
    if nu < 1e-12 or nv < 1e-12:
        return 0.0
    c = float(np.dot(u, v)) / (nu * nv)
    return float(np.arccos(max(-1.0, min(1.0, c))))

def derive_frame(tri):
    """tri: 3 x (x,y,z) MLOD coords. Returns (anchor[list], R 3x3 rows[x,y,z],
    ambiguous: bool, angles_deg_desc: list)."""
    P = [np.asarray(p, float) for p in tri]
    ang = [ _angle(P[(i+1) % 3] - P[i], P[(i+2) % 3] - P[i]) for i in range(3) ]
    order = sorted(range(3), key=lambda i: ang[i], reverse=True)  # largest angle first
    center, vy, vz = P[order[0]], P[order[1]], P[order[2]]
    deg = sorted([float(np.degrees(a)) for a in ang], reverse=True)
    ambiguous = abs(deg[1] - deg[2]) < 1.0   # middle vs smallest within 1 deg => tie
    y = vy - center; ny = np.linalg.norm(y); y = y/ny if ny > 1e-12 else np.array([0.,1.,0.])
    z = vz - center; nz = np.linalg.norm(z); z = z/nz if nz > 1e-12 else np.array([0.,0.,1.])
    x = np.cross(y, z); nx = np.linalg.norm(x); x = x/nx if nx > 1e-12 else np.array([1.,0.,0.])
    z = np.cross(x, y); z = z/(np.linalg.norm(z) + 1e-12)
    R = np.array([x, y, z])  # rows = world dirs of local x,y,z
    return center.tolist(), R, bool(ambiguous), deg

def canonical_triangle(anchor, R=None, scale=0.001):
    """Unambiguous triangle at `anchor` whose derived frame == R (identity if None).
    Point order: [anchor, vert_y(+Y short leg), vert_z(+Z long leg, 2x)]."""
    anchor = np.asarray(anchor, float)
    R = np.eye(3) if R is None else np.asarray(R, float)
    vy = anchor + scale * R[1]          # local +Y (short leg) -> middle angle -> vert_y
    vz = anchor + 2.0 * scale * R[2]    # local +Z (long  leg) -> smallest angle -> vert_z
    return [anchor.tolist(), vy.tolist(), vz.tolist()]
