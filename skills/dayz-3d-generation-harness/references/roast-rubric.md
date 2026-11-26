# Roast Rubric — adversarial review, scored

Objective: find what is wrong, with evidence. Each category scores 0–2:
- **0** = defect(s) with no mitigation, or category not verifiable from the evidence on file
- **1** = minor defects, or verified with partial evidence
- **2** = verified clean, evidence cited

A verdict without cited evidence (render filename + observation, or measured number vs dossier number) scores at most 1, regardless of how good it "looks". UNVERIFIED ≠ PASS.

Gate V: no category at 0, total ≥ 13/16, no open high-severity defects.

## Categories

### 1. Silhouette vs reference
Match the `vr_capture` angles against the dossier views. Compare **named landmarks** (roofline, wheel arch, muzzle, grip curve), not overall impression. Evidence: side-by-side observation per landmark, naming the render file and the dossier view.

### 2. Proportions & dimensions (numeric)
Table: measured dims (`vr_capture` numeric output / `verify_bounds`) vs dossier table, % deviation per row. >5% deviation = defect unless the plan declared tolerance. Evidence: the table itself.

### 3. Orientation & scale
Forward axis correct, nothing mirrored/upside down, plausible against the 1m scale cube (and the vanilla 1:1 reference for DayZ). Evidence: render with the scale reference in frame.

### 4. Detail density vs plan
Every feature in the detail list: PRESENT / MISSING / DEGRADED, one row each. A missing planned feature is automatically a defect; ≥3 feature types visible on a hero object. Evidence: close-up render per detail zone.

### 5. Mesh integrity
`verify_mesh_integrity` output for every part, current geometry. Any FAIL = category 0. Evidence: the gate printouts in the ledger.

### 6. Shading & normals
Face Orientation overlay screenshot (any red facing camera = defect), black facets, pinching, smooth bleeding across hard edges, ngons on curved areas. Evidence: viewport screenshot + render. NOTE: for DayZ, absolute winding is NOT judgeable here — only relative-to-vanilla; absolute winding belongs to `dayz-p3d-audit` (hard guardrail).

### 7. Assembly
Gaps, floating parts, z-fighting shimmer between angles, parts sunk into each other beyond plan. Evidence: `verify_overlap` results + iso render observations.

### 8. Target parity (DayZ or engine-specific)
Tri count inside budget per LOD; ride-height/footprint vs vanilla reference (measured, e.g. lowest_z ≈ 0 for ground items); proxy/slot presence. For non-DayZ targets: export-format requirements. Evidence: counts + measurements vs the vanilla numbers.

## Defect list format

| # | Severity (H/M/L) | Category | Defect | Evidence | Proposed fix |
|---|------------------|----------|--------|----------|--------------|

Severity: **H** = visibly wrong or breaks the target use (wrong proportions, broken mesh, missing major part). **M** = noticeable in normal viewing (gap, missing planned detail, shading artifact). **L** = polish (bevel width, minor texture seam).

## Zero-defect rule

A first roast returning zero defects is suspect, not a success. Re-roast with new camera angles + tighter close-ups before accepting. Two clean passes = accepted.

## Re-roast scope after fixes

Fixes touching 1–2 components: re-score affected categories + mesh integrity on touched parts, same camera angles as the original roast (before/after pairs kept). Fixes touching ≥3 components: full re-roast.
