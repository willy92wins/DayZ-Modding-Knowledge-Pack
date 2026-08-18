#!/usr/bin/env python3
"""R26 fixtures for proxy_frame. exit 0 = all pass, 1 = a failure."""
import sys, numpy as np
from proxy_frame import derive_frame, canonical_triangle

def rot(axis, deg):
    a = np.asarray(axis, float); a = a/np.linalg.norm(a); th = np.radians(deg)
    x,y,z = a; c = np.cos(th); s = np.sin(th); C = 1-c
    return np.array([[c+x*x*C, x*y*C-z*s, x*z*C+y*s],
                     [y*x*C+z*s, c+y*y*C, y*z*C-x*s],
                     [z*x*C-y*s, z*y*C+x*s, c+z*z*C]])
fails = 0
def chk(name, cond):
    global fails
    print(("PASS " if cond else "FAIL ") + name); fails += 0 if cond else 1

# pos fixture: canonical identity -> R==I, not ambiguous, anchor preserved
c,R,amb,deg = derive_frame(canonical_triangle([0.1,0.2,0.3]))
chk("canonical identity frame == I", np.allclose(R, np.eye(3), atol=1e-6))
chk("canonical NOT ambiguous", amb is False)
chk("canonical anchor preserved", np.allclose(c, [0.1,0.2,0.3], atol=1e-9))
chk("canonical angles 90/63.4/26.6", abs(deg[0]-90)<0.5 and abs(deg[1]-63.43)<0.5 and abs(deg[2]-26.57)<0.5)

# neg fixture: the shipped 90/45/45 isosceles -> ambiguous
e = 0.00136
c,R,amb,deg = derive_frame([[0,0,0],[0,0,e],[e,0,0]])  # legs +Z and +X equal
chk("shipped 45/45 isosceles flagged ambiguous", amb is True)

# round-trip: emit canonical(R0) -> derive == R0 (no ambiguity), several rotations
ok = True
for ax,dd in [((0,1,0),35),((1,0,0),20),((0,0,1),90),((1,1,0),60),((0,1,0),-50)]:
    R0 = rot(ax,dd)
    c,R,amb,deg = derive_frame(canonical_triangle([0,1,0], R0))
    ok = ok and np.allclose(R, R0, atol=1e-6) and not amb
chk("round-trip canonical(R)->derive==R (5 rotations)", ok)

print("\n%d failure(s)" % fails)
if __name__ == "__main__":
    sys.exit(1 if fails else 0)
