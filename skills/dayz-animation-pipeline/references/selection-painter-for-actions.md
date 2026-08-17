# Selection painter for action raycasts (sandbox tooling pattern)

Pattern for producing `.p3d` named selections whose surface coverage is precise enough to satisfy in-game action raycasts. The motivating case: `seat_driver` / `seat_codriver` selections that must be visible from both sides of the vehicle so the "Subir" action can be triggered from either approach (dual-entry pattern, `dual-entry-action-pattern.md`). The same pattern applies to any selection that drives an action raycast or a hit-zone: handlebar grip area, door handle, hood latch, tank cap.

## When heuristic bounds are not enough

The straightforward way to produce a selection is to script a bounds-based filter: "every face whose centroid is inside this Y/Z range belongs to `seat_driver`". For flat-topped shapes this works. For real vehicle geometry it leaks:

- A wedge-shaped seat with sloped sides: bounds-only includes the visible top but misses the side panels a player rays at from outside.
- A complex curved fender that wraps around the seat: bounds-only either over-includes (paints the wheel arch) or under-includes (leaves a stripe of bare metal between seat and fender).
- A handlebar with mirrors and levers: bounds-only paints the mirror housings.

Worse, when the heuristic fails you don't know **which** face leaked — you just know the action raycast misses sometimes. Iteration is slow and frustrating.

## The pattern — interactive painter

Build (or reuse — see LL-baked-viewer-reuse below) a Three.js viewer that:

1. Loads the `.p3d` geometry — ideally from a baked HTML viewer's `const DATA = ...` block (the LL-baked-viewer-reuse trick), NOT by re-running py3d in the sandbox.
2. Renders one mesh per material so face indices map cleanly to the model's groups.
3. Listens for `mousedown` on the canvas, raycasts against the mesh, and uses `intersection.faceIndex` to **toggle the face into the current brush set**.
4. Exposes 2–3 brushes (one per selection being painted, e.g. `handlebar`, `seat_driver`, `seat_codriver`). Color the active brush prominently.
5. `Shift+click` removes a face from the brush set; right-click rotates between brushes (so users can paint different selections without moving the mouse).
6. Exports a JSON file: one array per brush, each item `{material_index, face_index}` or just `face_index` if the model is single-material.

Key implementation details from the LFQuad case (LL-painter-vs-sliders):

- **Color faces in the brush set with `MeshBasicMaterial`, NOT `MeshStandardMaterial`.** PBR lighting + environment map dims unlit colors enough that yellow brush over a chrome handlebar becomes invisible (LL-overlay-vs-lighting).
- **Inflate brush-colored faces 5 mm along their normal** to win the z-fight against the base geometry. Without this, the brush color flickers in and out as the camera moves.
- **Seed each brush with a heuristic guess** so the user is refining, not painting from scratch. The heuristic just needs to be in-the-right-ballpark; the painter handles the gap.
- The viewer must run from `file://` because the user opens it locally. UMD Three.js (`r147` or earlier — `r148`+ dropped UMD), no ESM imports — see the standalone-HTML-delivery section in `skill-conventions` if you have not seen this bite yet.

## The refiner — adjacency dilation with a distance cap

The painter export is point-accurate where the user clicked, but real selections want coverage. Painting every face on a seat would take 10 minutes. The refiner does the second 90% automatically:

```
INPUT: painter export (face index list per brush)
       mesh geometry (positions, indices)
       cap_cm = 6 for small parts (handlebar grips), 10 for big surfaces (seat)
       optional Y / Z / radial filters per brush

For each brush:
  seeds = set(faces in brush)
  for dilation_step in range(N):   # N = 1 for handlebar, 2 for seats
    new_faces = set()
    for face in current_brush_set:
      for neighbor in adjacency[face]:           # share an edge with face
        if neighbor in current_brush_set: continue
        # cap distance from ANY seed (not from current face) to prevent runaway dilation
        if min(distance(neighbor_centroid, seed_centroid) for seed in seeds) > cap_cm:
          continue
        # apply user filters
        if not passes_filter(neighbor, brush.filters): continue
        new_faces.add(neighbor)
    current_brush_set |= new_faces

OUTPUT: refined per-brush face sets
```

Why the cap is **from any seed, not from the current frontier**: dilating from the frontier lets the brush leak across thin necks (the joint between seat and frame would let `seat_driver` pour into `frame`). Capping from the seed keeps the brush bounded by where the user actually painted.

Why Y/Z/radial filters per brush, not global: `handlebar` needs `Y > 0.83` (above the steering column), `seat_driver` needs no filter. Putting a global Y filter would either let handlebar leak below or block seat above.

LFQuad reference numbers (`LFQuad_dev/handoff_2026-05-28.md`):

- handlebar: 1 dilation step, cap 6 cm, `Y > 0.83`, radial 0.40 m from handlebar pivot → 2383 faces final.
- seat_driver: 2 dilation steps, cap 10 cm, no filter → 170 faces final.
- seat_codriver: 2 dilation steps, cap 10 cm, no filter → 36 faces final.

## LL-baked-viewer-reuse — don't re-parse the .p3d in the sandbox

The bash sandbox times out at 45 s. A 10+ MB `.p3d` parsed by py3d easily exceeds that, especially for complex vehicles. But you almost certainly already have a `.p3d` viewer (HTML standalone, from `dayz-3d-viewer` or `dayz-p3d-inspector`) whose `const DATA = "..."` block already contains the geometry base64-encoded.

**Reuse that DATA block.** Decoding the base64 takes ~1 s, vs ~30 s for re-parsing — 10× faster, and it does not blow the timeout. Pattern: read the existing viewer's HTML, regex out the `const DATA = "..."` literal, decode, build the painter on top of it. The geometry is already in the right frame, with materials already separated, ready to use.

## LL-overlay-vs-lighting — unlit + inflated normals beats PBR dim

When the brush color is dim or invisible against a base material:

- Switch the brush mesh from `MeshStandardMaterial` to `MeshBasicMaterial` (no PBR, ignores lights and env map). The brush color stays at its raw value regardless of scene lighting.
- Inflate the brush mesh's vertices 5 mm along their per-vertex normal. This wins the z-fight against the base geometry every time — without it, the brush flickers depending on camera angle.
- Use saturated, high-luminance colors (yellow `0xffe000`, green `0x00ff66`, blue `0x33bbff`) so the eye picks them out instantly even on chrome or dark plastic.

This applies to ANY overlay in a Three.js viewer where the base scene uses PBR, not just selection painters: anchor markers, axis visualizers, debug arrows.

## Pipeline (start to finish)

1. Identify which `.p3d` selections you need to author or fix (the action raycast fails from some angle, the hit-zone is too small, the rotated geometry pivots wrong).
2. Find an existing viewer with the geometry baked in — `dayz-3d-viewer` output or a recent `.p3d` inspector run.
3. Build the painter HTML on top of the baked DATA (one day's work the first time; cut-and-paste the next).
4. User opens it, paints with seed + clicks for the corner cases, exports JSON.
5. Run the refiner on the export with project-specific caps and filters.
6. Apply the refined JSON to the `.p3d` via `dayz-p3d-inspector` (Recipe JSON edit) or a project-specific update script (see `LFQuad_dev/task4_handoff/p3d_update.py` for a reusable shape).
7. Verify the new selection in Object Builder OR re-open the viewer.
8. In-game test: trigger the action from the expected angles. Tweak caps / filters if coverage is wrong.

## What this pattern does NOT do

- It does not change the shape of the geometry. If the seat is shaped wrong, repaint will not save you — fix the geometry first (`dayz-model-pipeline`).
- It does not create new memory points or change the axis of an animation. That is `dayz-p3d-inspector` / `handlebar-and-steering-config.md`.
- It does not validate that the selection works in-game. The painter only ensures coverage; the action raycast still has to physically hit one of those faces, which depends on player position and the action's reach.

## Reference case

`LFQuad_dev/handoff_2026-05-28.md` — `LFQuad_selection_tuner.html` (painter) + inline refiner script + `LFQuad_selections_refined.json` (output). The painter is reusable across vehicles by swapping the baked DATA and re-tuning the heuristic seeds.
