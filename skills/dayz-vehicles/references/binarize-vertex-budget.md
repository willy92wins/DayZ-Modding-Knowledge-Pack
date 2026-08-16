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

Tool: `C:\Users\<you>\VehicleImport\scripts\p3d_vertex_gate.py` - `count` reports resolved per LOD
as `INFORMATIVE_ONLY`; only `binarize` runs the authoritative three-state adjudication.
