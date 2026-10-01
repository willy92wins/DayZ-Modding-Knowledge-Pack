---
name: blender-visual-review
description: "Use when: looks off, check the model, look at it, review the render, inverted normals, exploded parts, scale drift. Multi-angle Blender MCP render-and-look. Complements blender-assembly (numeric only). Not DayZ winding: dayz-p3d-audit."
---

# Blender Visual Review

`verify_bounds()` and `audit_all()` (from the `blender-assembly` skill) prove a model's *topology* is clean — parts overlap, transforms are applied, nothing is silently double-scaled. They cannot prove the model is *right*. A chair facing backwards, a quad sunk into the ground, a roof at half scale, faces lit from the inside — every one of those passes a numeric audit and fails the instant a human looks. Numbers verify topology; only eyes verify intent.

This skill is the missing half of the loop: **render the model, look at the images, diagnose what you see, fix one thing, re-render the same angles to confirm.** Run the numeric checks in `blender-assembly`; run the visual checks here.

## When to use this

After you build, import, or modify any model; before you call a model "done" or export it; whenever the user says it "looks off" or asks you to "check" / "look at" / "review" a model; and — for DayZ — before you spend an in-game test cycle, because a render is free and an in-game iteration is not.

## The loop

1. **Set up an honest view** — frame the object, add a scale reference, pick diagnostic shading.
2. **Capture from several angles.** One angle hides defects: a gap invisible head-on, a normal only wrong on one side.
3. **Look, against the checklist.** Don't free-associate — walk the categories below so you don't miss a whole class of defect.
4. **Fix one diagnosis at a time.**
5. **Re-render the *same* angles** and compare before/after. A fix you didn't re-capture is a fix you didn't verify.

## Bounded loop: typed outcomes + stop policy (added 2026-07-30, adapted from img2threejs v1.4.3, Apache-2.0 — provenance in `references/NOTICE-img2threejs.md`)

Step 4 of the loop says "fix one diagnosis at a time" — this section bounds how many times. Unbounded visual iteration is a documented failure mode (racing-game rip: N rounds on a red visual before escalating to a human; DZ-R5's in-game hard stop exists for the same reason). Every review iteration ends by choosing exactly one action:

- `continue` — this aspect is good; move to the next check or part.
- `refine-spec` — the plan was wrong or shallow (missing detail row, wrong connection-map entry, wrong route): go back to `blender-assembly` Phase 1/1.5, fix the plan, rebuild from it. Patching geometry around a wrong plan burns iterations without converging.
- `refine-code` — the plan is sound; the build doesn't match it. Fix the geometry/material.
- `request-input` — show the user the evidence (before/after renders, what was tried, what still fails) and stop iterating.
- `stop` — the target is not reachable from this input (unusable reference, wrong approach); say so instead of faking progress.

Keep a per-model iteration history — a JSON list, one entry per iteration: `{"fidelity": <your visual 0-1 score>, "defectTags": ["short-stable-labels"], "reverted": <true if the fix made it worse and was undone>}`, stored next to the renders (`_review/history.json`). After appending each iteration, run the stop policy (always `--json`: the plain output crashes cp1252 consoles):

    python references/correction_loop.py --history _review/history.json --json

| Condition (priority order) | Verdict |
|---|---|
| fidelity ≥ target and no open defect tags | stop — `continue` |
| same defect tag survived 2 consecutive fixes | stop — `refine-spec`: the plan is wrong, not the code |
| oscillating — 2 reverted fixes, or score direction flip | stop — `refine-spec` |
| progress plateaued (Δ < 0.02, below target) | stop — `request-input` |
| 6 iterations | stop — `request-input`, non-bypassable |

The script is the cycle counter nobody keeps under pressure. NEVER argue past its stop verdict with "one more try will fix it" — that is the exact failure it exists to catch. Escalate with the evidence instead.

### Per-feature gates: a global "looks right" cannot rescue a failed critical feature

The detail list from `blender-assembly` Phase 1.5 is this review's contract. Its identity-defining rows — the ones that make the object *this* object (a grille shape, a stock profile, a hinge) — each get their own pass/fail during checklist step 3, judged on a native-res crop (LL-153). A render that reads well overall with one wrong critical feature fails the iteration; record that feature's tag in `defectTags`.

### Report honestly: "improved" is not "done"

Each iteration's note states what changed (with numbers — "guard edge extended −0.56→−0.48"), why, what still doesn't match, and what the current check is blind to ("passes front view; top view not re-rendered"). A feature that got closer is "improved", never "done" — imprecise language here is how a defect survives into the next session.

## Two ways to see — and when to use each

You have two distinct ways to get pixels back, and they answer different questions.

**Quick viewport screenshot** — `get_screenshot_of_area_as_image(area_ui_type="VIEW_3D")` returns the current viewport straight to you in one call, no file step. Use it for "what does it look like right now", and especially for the **Face Orientation overlay** (below), which shows only in the viewport, never in a render.

**Reproducible multi-angle render** — place a camera at canonical angles and render each to a file, then `Read` the files. Use it when you need identical framing every iteration, clean lighting, and before/after evidence. The helper below renders all angles in one call and also returns the measurable numbers (dimensions, lowest vertex, counts), so you get numeric and visual in one shot.

Rule of thumb: **screenshot to glance, render to judge.**

## Setup that keeps captures honest

**Scale reference.** Proportion errors are invisible without a yardstick. Drop a 1 m cube at the origin so every render carries a known unit (size=2 so scale = half-extent, per `blender-assembly`):

```python
import bpy
bpy.ops.mesh.primitive_cube_add(size=2, location=(0, 0, 0.5))
ref = bpy.context.active_object
ref.name = "VR_ScaleRef_1m"
ref.scale = (0.5, 0.5, 0.5)            # a 1 m cube sitting on z=0
bpy.ops.object.transform_apply(scale=True)
ref.display_type = 'WIRE'              # wireframe so it never hides the model
```

**Diagnostic shading.** For shape and topology, Solid + cavity reveals facets and pinching that smooth shading hides. For normal *direction*, the Face Orientation overlay paints front faces blue and back faces red — the fastest inverted-normal detector there is (viewport only). Set it, then take a viewport screenshot:

```python
import bpy
for area in bpy.context.screen.areas:
    if area.type == 'VIEW_3D':
        sp = area.spaces.active
        sp.shading.type = 'SOLID'
        sp.shading.show_cavity = True            # facets / pinching
        sp.overlay.show_face_orientation = True  # front = blue, back = red
        break
```

Workbench needs no scene lights (it has its own studio light), which sidesteps the classic "render came out black because the scene has no lamp" trap. Use Workbench for diagnosis; switch to EEVEE or Cycles only when you are specifically judging materials.

## Multi-angle capture (the workhorse)

Run this via `execute_blender_code`. It renders the object from front / right / top / iso to files you can read, restores the scene's original camera and engine, and returns both the file paths and the measurable diagnostics. Then `Read` each path and actually look.

```python
import bpy, os, tempfile
from mathutils import Vector

def vr_capture(obj_name, tag="iter1", out_dir=None, res=900):
    obj = bpy.data.objects[obj_name]
    scene = bpy.context.scene

    # world-space bounds of the base mesh (good enough to frame and measure)
    vs = [obj.matrix_world @ v.co for v in obj.data.vertices]
    lo = Vector((min(v.x for v in vs), min(v.y for v in vs), min(v.z for v in vs)))
    hi = Vector((max(v.x for v in vs), max(v.y for v in vs), max(v.z for v in vs)))
    center, dims = (lo + hi) * 0.5, (hi - lo)
    max_dim = max(dims.x, dims.y, dims.z) or 1.0

    if out_dir is None:                       # a folder you can also Read afterwards
        base = bpy.path.abspath("//") if bpy.data.filepath else tempfile.gettempdir()
        out_dir = os.path.join(base, "_review")
    os.makedirs(out_dir, exist_ok=True)

    prev = (scene.render.engine, scene.camera, scene.render.filepath,
            scene.display.shading.show_cavity)
    scene.render.engine = 'BLENDER_WORKBENCH'         # fast, self-lit
    scene.display.shading.show_cavity = True          # facets / pinching in the render
    scene.render.image_settings.file_format = 'PNG'
    scene.render.resolution_x = scene.render.resolution_y = res
    scene.render.resolution_percentage = 100

    cam_data = bpy.data.cameras.new("VR_Cam")
    cam = bpy.data.objects.new("VR_Cam", cam_data)
    scene.collection.objects.link(cam)
    scene.camera = cam
    dist = max_dim * 2.2

    views = {"front": (0,-1,0), "right": (1,0,0), "top": (0,0,1), "iso": (1,-1,0.8)}
    renders = []
    for name, off in views.items():
        cam.location = center + Vector(off).normalized() * dist
        cam.rotation_euler = (center - cam.location).to_track_quat('-Z', 'Y').to_euler()
        path = os.path.join(out_dir, f"{obj_name}__{name}__{tag}.png")
        scene.render.filepath = path
        bpy.ops.render.render(write_still=True)
        renders.append(path)

    (scene.render.engine, scene.camera, scene.render.filepath,
     scene.display.shading.show_cavity) = prev        # restore, then drop temp camera
    bpy.data.objects.remove(cam, do_unlink=True)
    if cam_data.users == 0:
        bpy.data.cameras.remove(cam_data)

    return {"renders": renders,
            "dims": [round(c, 4) for c in dims],
            "lowest_z": round(lo.z, 4),
            "center": [round(c, 4) for c in center],
            "counts": {"verts": len(obj.data.vertices), "faces": len(obj.data.polygons)}}

result = vr_capture("YOUR_OBJECT")   # set the object name; optional: tag=, out_dir=, res=
```

`Read` each path in `result["renders"]` and look. Use `result["dims"]`, `result["lowest_z"]`, and `result["counts"]` as the measurable backbone for the checklist. (Bounds come from the base mesh; if a modifier changes the silhouette, apply it or evaluate the dependency graph first.)

## Diagnostic checklist

Walk every category — the point of a checklist is to catch the defect you weren't already worried about. Each item is a concrete, checkable signal, not a vibe: an invariant written as loose prose gets nodded at and skipped (LL-062), so tie each one to a number or a specific visual cue.

### A. General 3D correctness (every model)

- **Orientation** — does "forward" point where it should; is anything upside down or mirrored? Read it against the scale cube and the world axes, not memory.
- **Proportion / scale** — measure against the 1 m cube and `result["dims"]`. "Looks small" is a prompt to check the number, not a conclusion.
- **Inverted / black normals** — Face Orientation overlay: any red facing the camera is a back-face you are seeing through. Also watch for surfaces lit as if from inside.
- **Shading artifacts** — black facets, pinching, smooth shading bleeding across a hard edge, n-gons on curved areas.
- **Exploded / floating parts** — gaps between parts that should touch; a part hovering off its mount. (`blender-assembly`'s `verify_overlap` catches the quantifiable ones; the eye catches the rest.)
- **Doubled geometry** — a shimmer that flickers between angles means two faces occupy the same place (z-fighting).
- **Animated parts: clearance per keyframe, not per render** — presentation renders only show posed frames; impacts hide behind walls or closed doors. Evaluate the depsgraph mesh at every keyframe AND at intermediate points of each travel span: `BVHTree.overlap` between each moving mesh and each fixed mesh, a sweep of fixed-geometry points (vertices, face and edge centres) that fall inside the part's at-rest footprint and travel range, and section cuts on the travel planes. A flush contact also reports as overlap — separate it from a penetration by measuring how deep the geometry enters the footprint, not how many triangles cross. [EXACT] Measured on an animated rock platform (2026-10-01): its 9 presentation cameras showed nothing, while the sweep found a 12 × 14.6 m platform crossing a lip 0.27 m into its footprint and an elevator cabin crossing the top threshold (0.14 m) on every ride, visible only from inside at frame 145.
- **Workbench `color_type = 'TEXTURE'` paints one image of the material, not its shading** [EXACT] — on a vanilla rock the `rock_*_mask` input rendered as flat RGB mask colours and looked like a defect. Judge materials in EEVEE with the file's own lights. (measured 2026-10-01)

### B. DayZ parity vs a vanilla reference

Import a known-good vanilla model into the same scene at 1:1 and compare side by side (the import path lives in `dayz-model-pipeline`). Anchor each check to the reference, not to taste:

- **Orientation / scale** — same forward axis and roughly the same footprint as the vanilla equivalent.
- **Ride-height (measurable)** — for ground items, the lowest vertex (`result["lowest_z"]`) sits at ≈ the ground plane (z≈0); for vehicles, the wheel contact is ≈ ground and the chassis belly clears it well (a vanilla sedan's belly clearance is ~0.43 m; a too-small wheel sinks the body). Measure it — don't eyeball "looks grounded" (LL-062; `vehicle-structural-parity`).
- **Proxy / slot presence** — wheels, FireGeo bulk, and lights are visibly where the vanilla has them.

### C. Reference-image comparison

When matching a photo or concept: load the reference as a camera background image (`cam_data.show_background_images = True`, then `cam_data.background_images.new().image = bpy.data.images.load(path)`), match the camera to the reference's angle, render, and compare **named landmarks** — roofline, wheel arch, handle position — not overall impression. Report silhouette deviation, missing or extra masses, and proportion drift by pointing at specific points.

### D. Photo-resemblance scoring: calibrate the camera first (added 2026-09-25, SP-427)

- **One Blender camera per reference photo, calibrated by silhouette IoU** — maximize the IoU between the Workbench-alpha silhouette and the photo mask (Nelder-Mead over loc/yaw/pitch/roll/focal, initialized from a known-size feature such as the tyres from the spec sheet). Judge only photo|render crops taken with that same camera: with an eyeballed "similar" camera the proportion errors (a wing out of place, a dome floating 5 cm) stay invisible.
- **Poor or partial views** — low-res or off-angle photos converge to a false camera (IoU 0.81 on a brochure front view); solve PnP on 6-8 triangulated points across other photos instead, and reject any refinement that LOWERS silhouette IoU (a 2-anchor bundle shifted the camera 38 cm along the view rays and dropped IoU 0.936 to 0.923).
- **Silhouette renders** — set `render.use_compositing = False`: an Alpha-Over compositor makes the whole silhouette opaque when `film_transparent` is on.
- **Judge blind, cross-family.** [EXACT] Same-family self-scores ran 1-2 checklist points above a blind audit by another model family over the same 27 image sets (measured in Blender 5.1.1 headless against studio photos, 2026-09-25); the working score is the per-criterion minimum of self and blind.

## Hard guardrail: a Blender render cannot judge DayZ winding

Blender (and any Three.js viewer) renders **right-handed**; DayZ culls **left-handed**. A model that looks perfectly solid in Blender can render inside-out in-game. This is not hypothetical — it is a logged self-error: a render was used to declare "normals not inverted", and the exterior turned out transparent in-game (`lessons-learned.md` LL-029-era entry; `dayz-p3d-audit/SKILL.md:474-476`).

- **NEVER conclude that DayZ face winding or normal direction is correct from a Blender render or screenshot.** The render genuinely cannot tell you. Absolute winding is decided by `dayz-p3d-audit` (its edge-pair topology check), not by eye.
- The *only* valid visual winding signal is **relative**: the model winds the same way as a vanilla reference imported beside it. "Same as vanilla" is meaningful; "looks fine to me" is not.
- The Blender→DayZ transform `(x,y,z)→(x,z,-y)` is a proper rotation (det=+1) and **preserves** winding — do not "flip to be safe" (LL-020; authority: `dayz-model-pipeline`).

Everything else here — orientation, proportion, scale, exploded parts, ride-height, reference match — the render judges well. Winding is the one thing it cannot; hand that to `dayz-p3d-audit`.

### Winding-flip detection workflow (added 2026-07-30, applies pending append 2026-06-24; LL-162)

A standard lit render cannot expose a winding flip (the guardrail above) because declared/custom split normals mask it: lighting follows declared normals while engines cull by triangle winding. Reproduced on the MercedesAMGLF Phase 2 shell — all 4 views passed here, in-game only back faces textured (LL-162). Two viewport/render mechanisms DO read winding-derived orientation, unaffected by declared normals:

1. **Face Orientation overlay** (already in Setup above) — from OUTSIDE the model, any red face is winding-flipped. Screenshot the 4 canonical angles with the overlay on; a uniformly red exterior means the whole mesh is flipped.
2. **Backface-culling re-render** — set `mat.use_backface_culling = True` on every material (EEVEE honors it), re-render the same 4 angles, and diff each against its original render (`references/vr_delta.py` per angle). Faces that vanish (holes; silhouette IoU < 0.95 on any view) were winding-flipped ⇒ verdict `FLIPPED_LIKELY` — do not approve the export.

Do NOT "verify" a suspected flip by running `normals_make_consistent` and re-rendering: recalc rewrites the winding itself, so the re-render comes back clean and the check false-negatives. Recalc is a repair tool; the repair decision for a DayZ export belongs to the import-transform rules in `dayz-model-pipeline` (LL-020: the canonical `(x,y,z)→(x,z,-y)` transform preserves winding; a `det=−1` variant is what flips it).

When to run: any import from glTF/FBX/OBJ, any pipeline with a configurable `reverse_winding`, any build destined for a winding-culling engine (DayZ / Arma / BI). Absolute authority on the exported `.p3d` remains `dayz-p3d-audit`'s topology check; this is the free early warning that saves the in-game cycle.

#### Quantified, and why checklist Q5 must never be scored by eye (measured 2026-08-21)

The guardrail above was reproduced from the other direction, on a purpose-built probe whose
winding is reversed by construction (`q5_normals_build.py` pattern: same object, same camera,
same shading, only the winding differs):

| capture | faces reversed | pixels changed |
|---|---|---|
| this skill's own settings (Workbench + `show_cavity`, culling **off**) | 62 (face-0 normal dot **-1.0001**) | **0.00%** |
| identical, backface culling **on** | 62 | **36.92%** |

Two variants at different severities came out byte-identical to each other. The defect is
**absent from the pixels**, so no reviewer can answer from a lit render -- which is exactly
what the section above says, now with a number.

**Consequence for `references/checks_hardsurface.json`.** Its entry 4 -- *"Are there any black,
inside-out or wrongly shaded faces visible?"* -- asks a VLM the one question this skill states
a render cannot answer, over non-culled captures. It carries `skip` and must be routed to the
culling diff above, never sent to or scored by the VLM. A gate that cannot go red for the
cause it targets is decoration.

**And it is not a local-model limitation.** Given the culled pair where the flip changes 36.92%
of the image and the interior of the cylinder is plainly visible, `ornith-1.5:9b`,
`qwen3-vl:30b` and `muse-glimmer:30b` each answered NO on **both** variants across 3 seeds --
0/3 separation, all three -- and justified it fluently: *"the visible faces are the front cap
and the exterior side of the cylinder"*, said of a render where the front cap is culled away
and the interior is what is on screen. The failure mode is a confident green, not a refusal.

#### What the local judges DO and DO NOT hold up on (same tanda)

Whole shipped checklist, over a pair differing only in facet count (48 vs 6 sides), 3 seeds.
Only the faceting question should move; everything else should hold still:

| model | correct | the miss |
|---|---|---|
| `qwen3-vl:30b` | **8/8** | -- |
| `ornith-1.5:9b` | 7/8 | calls the SMOOTH variant holed, 2 of 3 seeds |
| `muse-glimmer:30b` | 7/8 | reads the FACETED variant as bevelled, 3 of 3 seeds |

So the incumbent is the cleanest of the three, and a bigger or newer model did not beat it.
Scope: one object, one pair, one framing where the round part fills the frame -- the condition
where the faceting question is already known to work. It screens models; it does not rank them.


## Deterministic delta check (report-only; added 2026-07-30)

Before judging a fix by eye, run the pixel-math comparator on the before/after pair of the SAME angle:

    python references/vr_delta.py _review/model__front__iter1.png _review/model__front__iter2.png --json

It reports silhouette IoU, bbox scale/aspect deltas, SSIM, edge overlap, tonal/blowout/flat parity, and which signals moved beyond same-camera noise. Two uses:

- **Prove the fix landed** — an intended edit must move at least one signal; `identicalImages: true` after an edit means the old scene got re-rendered (a real reproduced failure mode: the MCP render-depsgraph staleness documented in `blender-assembly`).
- **Catch collateral drift** — signals moving that the edit shouldn't touch (a tonal shift after a pure geometry fix; a silhouette change after a material tweak).

Per LL-153 these numbers are a change filter, NEVER a correctness verdict — correctness is decided by eyes on the renders and native-res crops. Same-camera pairs only: scoring a render against a reference photo is not calibrated here (framing/background mismatch breaks every signal; that comparison stays with §C's named-landmark method).

## Free local second opinion — SHADOW MODE (added 2026-07-30)

A local vision model served by Ollama answers checklist questions about renders at zero credit cost, so agent budget goes to gates and final judgment instead of every inner-loop glance. `references/vr_score.py`:

    python references/vr_score.py ask _review/model__iso__iter3.png --checklist references/checks_hardsurface.json --model gemma4:26b --json
    python references/vr_score.py score _review/model__iso__iter3.png --reference ref.jpg --model gemma4:26b --json

Prefer `ask` over `score`: concrete yes/no questions are measurably easier for a small VLM than open judgment, and each "no" is a specific pointer instead of an opaque number. Derive the questions from the model's own detail list (`blender-assembly` Phase 1.5) — `checks_hardsurface.json` is the generic starter set.

**This is SHADOW MODE and it is not negotiable**: the local model's answers are evidence logged beside your own, NEVER a gate, NEVER a substitute for looking. Every call appends to a JSONL shadow log; that log IS the calibration dataset, built free during real work. Promotion path: shadow → pre-filter (it discards the obviously broken, you judge the survivors) → never final judge. Run `references/vr_calibrate.py report` against ≥15 renders you have judged yourself before delegating any single question; it reports agreement per question, which is the unit that gets delegated — not the model as a whole.

Measured 2026-07-30 (RTX 3090, n=2 renders — provisional): `gemma4:26b` ≈15 s warm per 8-question checklist, `qwen3.5:27b` ≈132 s for comparable quality, so gemma is the default. **⚠ That 9x gap was REFUTED in its cause on 2026-08-16: it was not the model, it was the factory `num_ctx`** offloading 37% of qwen to CPU. With `think:false` + `num_ctx=8192` it is 8.3 s and 17.2 s — 2x gap, and qwen becomes viable again as second opinion from another family. See §Pre-filter below. Both correctly flagged a faceted circle and both answered "unsure" rather than guessing when the view could not decide — but they gave **opposite** bevel verdicts on the same renders, so treat bevel/chamfer questions as agent-side until calibration says otherwise. Judge fine surface questions on a native-res crop, never a full-frame render (LL-153).

Setup notes: models live wherever `OLLAMA_MODELS` points; a 17 GB model fills a 24 GB card, so models load one at a time and compete with Blender for VRAM — unload before a heavy render. Always address the server as `127.0.0.1`, never `localhost`: on Windows that resolves to IPv6 first and a stray IPv6-bound `ollama serve` will answer from a different model library.

## Output / evidence convention

Render into a folder you can also read (the helper defaults to a `_review/` folder next to the .blend, or the OS temp dir if the file is unsaved) and name files `<model>__<angle>__<iter>.png`. Keep the before/after pair for any angle you changed, so the diagnosis is auditable and you can prove the fix actually landed.

## VLM Checklist: five active questions, three excluded (added 2026-08-16, SP-277; calibration data in SP-270)

The shadow section above governs any question not in this table. The JSON preserves
eight entries: five reach the model and three have `skip`; only the **pre-filter** rows change the loop.

**The filter REJECTS, never APPROVES.** A "no" triggers a fix before showing anything; a clean
pass does **not** mean "it is fine", it means "it now deserves your eyes". The rule that the local
model is never the final judge remains intact: it has been delegated the power to stop, not to approve.

### What is calibrated and what is not

Measured on `mk47_mutant`, with the broken/fixed pair of the SAME object, three models, the actual
grouping of `vr_score.py`. The entire checklist achieves **77.8% against a constant response floor of
58.3%**:

| question | accuracy | in the loop |
|---|---|---|
| connectivity / floating parts | **12/12** | **pre-filter** — by far the strongest |
| gaps or holes in the surface | 10/12 | **pre-filter** |
| ~~black, flipped or improperly shaded faces~~ | ~~10/12~~ | **DO NOT delegate** — `skip`: defect is not in capture; use mechanical culling diff |
| finished object vs bare boxes | 10/12 | **pre-filter** |
| ~~consistent proportions~~ | ~~10-12/12~~ | **DO NOT delegate** (retracted 2026-08-22) — that 10-12/12 is an **unfalsified** score: broken/fixed pair against which it was measured contained no proportion defect, so answering "yes" always scores perfect. See note below |
| **bevels / chamfered edges** | **6/12** | **DO NOT delegate** — is at constant response floor. Confirms 2026-07-30 warning: both models gave opposite bevel verdicts |
| **faceted cylinders** | **at random across 8 framings** | **DO NOT delegate, and do not rewrite it** — four phrasings tested (2026-08-17) and the existing one is best: 6/6 in framings where round piece fills frame, 1-2 of 3 in whole object framing. **Framing outweighs phrasing.** Underlying failure is that object cannot answer it, see note below |

### Before believing a high score from this table (2026-08-22)

A yes/no question has two failure modes that its own score hides, and the
proportions row fell into both:

1. **The constant.** If test set gold **never changes value**, constant
   response scores perfect and metric remains *unfalsified*, not validated.
   The question looked 10-12/12 because pair against which it was measured had no
   proportion defect. **The check is one line: does gold change value in the
   set?** If not, you measured nothing.
2. **Confabulation.** When asked for rationale it does not hesitate, it invents. Facing a flange 37%
   wider than expected, one model declared it consistent with "standard fastener
   geometry" and another "appropriately scaled". A confident and false note is worse than
   "unsure".

Measured on 2026-08-17 with `gemma4:26b`, `qwen3.8:27b`, and `qwen3.5:27b`: with two constructed
defects, the question answered **"yes" in all 9 cells** (3 models × 3 variants).
Asking instead for **the measurement** —size and position of each piece as fraction of
frame, scored by direction of change— got **6/6 right on the same renders**.

The measurement substitute **is not yet implemented here**: `probe_truth.py` does not exist
in `references/` and the question remains in `checks_hardsurface.json:29` as-is. Until
it is, this row is checked by eye and not delegated. And when implementing it, the trap that already
bit: **declaring a coordinate convention does not beat the model's up-down
prior** — asking for y=0 at bottom and mirroring its responses reduced vertical error from 0.107 to
0.017 of frame. Use image convention or detect mirror before scoring.

### Where it enters the loop

Between step 2 (capture angles) and step 3 (look) of §The loop:

    python references/vr_score.py ask --checklist references/checks_hardsurface.json \
      --model gemma4:26b --json \
      --view assembled__iso  _review/m__iso__iter3.png \
      --view assembled__profile_R _review/m__profile_R__iter3.png \
      --view assembled__profile_L _review/m__profile_L__iter3.png \
      --view zoom_receiver__right_iso _review/m__receiver__iter3.png \
      --view zoom_muzzle__front_iso _review/m__muzzle__iter3.png

If any of the five active ones triggers: fix and re-render **before** spending user's eyes.
If none triggers: look anyway — filter has not approved anything. The three excluded do
not appear in model responses: inverted faces go to mechanical diff; proportions and
cylinders keep gap declared until `probe_truth.py` and `facet_report.py` exist.

### Calibration gate changes: per question, with broken/fixed pair

The shadow section asks for **≥15 already-judged renders** before delegating a question. That is
calibrating by accumulation and **would have found none of this**: the same question goes from 7/12 to
11/12 just by changing framing, and from 9/12 to 18/18 just by changing which other questions travel
in the call. It is replaced by a cheaper gate that also attributes:

**Take two renders of the SAME object, one with defect and another with defect fixed, and ask
the same question to both.** Needs no gold. Measures two things that are not the same:

- **sensitivity** — does response change where it should change?
- **specificity** — does it stay still where it should not change?

A judge answering identically to both versions is not reading the model, whatever score it
may have. Any mod with a before/after serves as testbench: nothing needs to be manufactured.

### Three things that invalidate a framing comparison

1. **The batch of the call changes the response.** Same question, same image, same model:
   **18/18** in a call with four other shading questions, **9/12** in call with eight of the
   checklist. Comparing framings requires keeping batch fixed. And **it is not size**: removing a
   question from batch worsened the two that stayed.
2. **A framing without fixed render is not comparable** to one that has it: scores over
   half of cells and there a constant response gets 6/6.
3. **Temperature is set to 0.1** in payload, so two samples of same cell turn out
   almost identical: effective `n` is number of cells, not number of samples. Do not confuse repeating
   with measuring.

### Scope, so as not to repeat the error that originated this

All of the above comes from **a single object**. The day before I recorded that these models "do not detect
geometric defects" — and it was false: it measured my harness, not the models, and closed a line of work
that worked. Before writing that a model cannot do something, have varied **phrasing,
framing, and batch**, and state which of the three was varied. Origin and evidence in `LL-289`.

## Rules promoted from the lessons corpus (added 2026-07-27)

Promoted from `AI/20_Knowledge/lessons-learned.md` so that they arrive via trigger instead
of relying on someone remembering to look them up. Each rule cites its source `LL-NNN`;
the full entry (symptom, origin, evidence) lives there. Do not remove the citation: the index
`lessons-index.md` detects promotion by searching for that reference inside the skills.

- **LL-153** — Judge every critical visual zone on a native-resolution crop. Use RMS and scores only as change filter; never as correctness verdict, and keep full-res crop as evidence.

## Q3 closed: do not rewrite or delegate faceting (SP-282, added 2026-08-31)

Current cylinders phrasing is best of four measured, but that does not make it a
gate. Asked alone it got 6/6; within the batch of eight of `vr_score.py` it fell to 3/6. On
actual object it produced 8 false alarms out of 12: visible octagonal piece is intentional and
authentic smoothed cylinders have subpixel sagitta in those framings. Therefore:

- keep question without rewriting, with `skip`; does not enter active checklist or pre-filter;
- do not describe result as chance: failure changes with framing and grouping;
- if asked to count a profile, frame the **section** until it fills the frame. Generic
  distance `max_dim * 2.2` of an elongated object leaves axial view without information;
- correct substitute is deterministic and **reports, does not judge**: part, sides, radius, relative
  deviation, and sagitta, with allowlist for intentional prisms. Intention remains a
  decision of the modeler.

`facet_report.py` continues without being distributed in this skill. This section establishes its contract and its
limits; does not claim that executable is installed.

## Calibrated contract of faceting report (SP-284, added 2026-08-31)

If `facet_report.py` is incorporated, calibrated candidate rule is `sides < 12` and
`radius >= 6 mm`, never provisional 4 mm threshold. Furthermore, requires an almost square
cross section: ratio between sides of transversal bbox `<= 1.30`. That limit admits pentagons and
hexagons, but rejects planar shapes that the 20% outer filter confuses with a cylinder.
An allowlist silences deliberate prismatic profiles.

The **coverage** report is as important as flags. Must publish:

- meshes visible in render and parts with circular profile;
- examined polygons and percentage over visible ones;
- largest unexamined mesh and its percentage.

`0 marked` is **INCONCLUSIVE** if there are no visible meshes or if a single unexamined mesh
concentrates `>=30%` of polygons. Overall percentage covered does not decide verdict: an
asset composed mainly of boxes and rails can have low coverage and be valid for
examined parts.

Declared calibration: 0 false alarms across 41 circular-profile parts from three real assets and
all three parts of synthetic defect remained marked; 12- and 48-sided probes remained
clean. Limits: works per object, does not see tubes inside merged mesh, can miss
thin or heavily slotted profiles, and does not certify that undetected geometry is round. Corpus does
not include a published mod verified in-game; do not elevate this report to final gate.
