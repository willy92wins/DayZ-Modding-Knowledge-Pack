#!/usr/bin/env python3
"""
proxy_canon.py - rewrite every proxy triangle as a CANONICAL unambiguous frame.

Reads recipe.json (proxy_extract) and emits edits.json (for proxy_apply) that
replaces each proxy's triangle with a canonical right-triangle (distinct
90/63.4/26.6 angles) at the SAME anchor, encoding identity orientation by default
(item shown worn upright = vanilla character-space pose) or a per-slot rotation.

Why: the shipped proxies are 90/45/45 isosceles -> the engine's angle-sort ties
and assigns a rotated frame (clothing comes out turned). Canonical triangles make
the derived frame deterministic. See proxy_frame.py for the verified convention.

Usage:
  python3 proxy_canon.py recipe.json edits.json
      [--scale 0.001] [--rot Slot=AXIS:DEG ...]      # e.g. --rot Headgear=Y:90
"""
import sys, json, argparse
import numpy as np
from proxy_frame import canonical_triangle

def rotm(axis, deg):
    base={"X":(1,0,0),"Y":(0,1,0),"Z":(0,0,1)}
    a=np.asarray(base[axis.upper()],float); th=np.radians(float(deg))
    x,y,z=a; c=np.cos(th); s=np.sin(th); C=1-c
    return np.array([[c+x*x*C,x*y*C-z*s,x*z*C+y*s],
                     [y*x*C+z*s,c+y*y*C,y*z*C-x*s],
                     [z*x*C-y*s,z*y*C+x*s,c+z*z*C]])

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("recipe"); ap.add_argument("out")
    ap.add_argument("--scale",type=float,default=0.001)
    ap.add_argument("--rot",nargs="*",default=[],help="Slot=AXIS:DEG (e.g. Headgear=Y:90)")
    a=ap.parse_args()
    rec=json.load(open(a.recipe))
    rotmap={}
    for kv in a.rot:
        slot,spec=kv.split("=",1); ax,dd=spec.split(":"); rotmap[slot]=rotm(ax,dd)
    edits=[]
    for p in rec["proxies"]:
        R=rotmap.get(p["slot"])
        anchor=p["origin"]
        tri=canonical_triangle(anchor,R,a.scale)
        edits.append({"lod":p["lod"],"name":p["name"],"slot":p["slot"],
                      "point_indices":p["point_indices"],"new_triangle":tri})
        print("CANON %-10s anchor=(%+.3f,%+.3f,%+.3f) %s"%(
            p["slot"],anchor[0],anchor[1],anchor[2], "rotated" if R is not None else "identity"))
    json.dump({"edits":edits},open(a.out,"w"),indent=1)
    print("wrote %s (%d proxies canonicalized)"%(a.out,len(edits)))

if __name__=="__main__":
    main()
