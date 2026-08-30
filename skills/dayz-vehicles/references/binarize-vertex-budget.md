# `binarize` as the load oracle — vertex budget, measured

Development of **invariant 24** in `SKILL.md` (`binarize` is the three-state offline load
oracle; `RESOLVED_LIMIT = 65535` is a false friend). The invariant is stated there; this is
the evidence behind it. Read it when a model passes every offline gate and still refuses to
spawn, or when you need to know your headroom before adding geometry.

Everything below is measured on the HH-60G, cross-checked against 25 in-game verdicts.

**1. `Too many vertices` and `Won't simulate, it has no geometry` are the SAME defect.**
The rejection happens while **loading the MLOD**, before conversion, so the engine aborts the
whole model and emits the generic physics message even though the Geometry LOD is perfect.
Chasing it as a collision problem costs days. If a model that passes every offline gate does
not spawn, run binarize on it **before** touching the Geometry LOD.

**2. binarize adjudicates N models per pass, offline, in ~90 s.**
`binarize.exe -always <src under P:\> <out>`, with a `model.cfg` that declares **every**
basename in the source dir (undeclared basenames fall back to Default and change the code
path). Validated on 28 variants against the in-game verdicts of the previous cycle:
**13 PASS/PASS, 12 FAIL/FAIL, zero false greens, zero false reds.** This turns a model
bisection from ~6 min per variant into ~90 s per batch.

**3. The verdict has THREE states. Using two is a bug in your bench.**
- `PASS` - a **new**, non-empty ODOL for the basename under test, in an output dir that did
  not already contain it. Skip the "new" requirement and a residual ODOL gives you a false green.
- `CAPACITY_FAIL` - no new ODOL **and** a `Too many vertices` line attributed to that MLOD.
- `OTHER_FAIL` - any other absence: bad `model.cfg`, undeclared basename, malformed MLOD, I/O,
  aborted tool. **It blocks and does NOT authorize touching geometry.** Without this state you
  decimate a mesh because your bench was misconfigured.

**The verdict is reproducible; the ODOL bytes are NOT.** The same `.p3d` produced 1,725,025 and
1,726,689 bytes with different hashes in two clean consecutive runs. Never gate on the ODOL SHA.

**Noise that does NOT discriminate** (it appears for the known-good control too):
`Material not loaded`, `No entry '.CfgVehicles'`, `Trying to access error value`,
`Error occured: Loading LODShape`, `UV mapping too varied`, `vertices of bone X are shared with
bone Y`, `Too detailed shadow lod`. The word `Error` in the log classifies nothing - attribute
the outcome to a model and a cause, or record `OTHER_FAIL`.

**4. The ceiling in triple units is not 65535, and it is not portable.**
Measured by walking four structurally different bases of the same asset to the cliff:
**46,133 loads, 46,134 does not** - the same integer for all four. The engine's hard cap does
appear to be 65,535 but on **post-split** vertices, and a `(point, normal, uv)` counter
under-counts those by a model-dependent factor: **1.4205** here, **1.46** on the OH-1 (see #24).
An assembler with `RESOLVED_LIMIT = 65535` hardcoded closed its own gate in green, for weeks, on
a model the engine refuses. **Re-measure per model; the hard gate is binarize's verdict.**

**5. Know your headroom, because it can be one edit wide.**
The deployed HH-60G sat at 46,019 of 46,133 - **114 triples of margin**, 99.8 %. Any change that
adds more than 114 resolved vertices kills it: a normal tweak, a UV seam, a texture that forces
another split. Measure resolved before and after **every** visual edit.

**6. When you mint a normal, you are spending budget; when you reverse a corner order, you are not.**
The defect that cost this project a week: a winding-flip block negated the stored normal **per
corner** for the 151 faces (0.43 %) whose source normal disagreed with the source winding. Those
453 corners minted 630 pool entries and +886 resolved. Re-reversing the corner order of those
151 faces reaches **identical** coherence at zero cost. A face's corner order is free; a new
normal is not.

And the identity to have in your head before "fixing" a winding by inverting things:
`dot(-cross, -n) == dot(cross, n)`. Reversing the corners **and** negating the normal is a
no-op for their relationship - it re-parametrizes, it does not flip. A policy that does both
changes nothing.

**7. A perturbation below the consumer's quantum is a null mutation.**
When walking a limit to find where it breaks, the step must survive the consumer's quantization.
Nudging a normal by 1e-4 on one component (~0.006 deg) does not survive DayZ's normal
compression: the estimator counted +120 new triples, the engine saw none, 42 samples "passed",
and the ceiling would have been reported 7 units too high. Use a step that is unambiguously
above the quantum (>= 3 deg for normals) and include a sample past the known-failing value as
a self-check.

Tool: `<vehicle-import>\scripts\p3d_vertex_gate.py` - `count` reports resolved per LOD
as `INFORMATIVE_ONLY`; only `binarize` runs the authoritative three-state adjudication.

## Qualify a capacity warning on the deployed artifact first (SP-182, added 2026-08-31)

Before changing geometry for a numerical warning, run the same counter on the
known-good model extracted from the deployed PBO. If that artifact already exceeds
the proposed threshold, the threshold does not govern that load route. Confirm the
blob rather than the editable tree, and read its magic: `MLOD` proves the engine's
packonly route, while `ODOL` proves a binarized route. Neither result automatically
proves the other.

A discrete tolerance sweep proves only the sampled grid. Powers-of-ten can jump over
the usable interval; refine around the transition and, for unit normals, test an
angular merge rather than only component-wise rounding. The refined instrument must
first reproduce every previously published sample before any new intermediate point
is accepted.

## Read the verdict artifact, not the wrapper exit code (SP-220, added 2026-08-31)

`p3d_vertex_gate.py binarize` and a Python import failure can both exit `1`. Read the
per-model state from a newly written `_verdicts.json`; a missing report or missing
row is `OTHER_FAIL`, never PASS or `CAPACITY_FAIL`. The child process needs the
required module on `PYTHONPATH`, because an in-process `sys.path` edit is not
inherited. Allow for the measured startup cost (about 68 s even for a four-point
control); for a batch, set an explicit larger timeout and include a tiny known-good
model in that same invocation. If the control does not PASS, no product red is
attributable to capacity.

Keep three units separate: a DCC estimator may split one source point by rounded
corner normal/UV; py3d `resolved` counts `(point_index, normal value, uv)` on the
assembled MLOD; the engine enforces post-split vertices. Budget in assembled py3d
units and adjudicate with the three-state binarize result. Count after host proxies
are present; each proxy contributes three points, one face normal, one face and
three resolved entries.

## Source geometry census is a planning bound, not engine authorization (SP-157, added 2026-08-31)

Before sacrificing artist normals, decimating, or repartitioning, compose the source
node world transforms and count `POSITION` accessor vertices per final frozen owner
container. Count every emitted instance; a mesh definition referenced by three nodes
has three costs after emission. The glTF accessor sum is a conservative planning bound
for that routing and is useful before the MLOD exists.

The count chooses where to measure next; it does not authorize a build. Do not compare
it with a fixed 60,000, 65,535, or approximate 32,768 ceiling. Those literals mix
source accessor vertices, assembled resolved triples and engine post-split vertices.
The assembled py3d count remains informative and the three-state `binarize` verdict
remains authoritative. This rule supersedes approximate fixed-ceiling planning advice
elsewhere in this skill without weakening any measured product gate.
