---
name: blender-visual-review
description: 'Disciplined visual review of 3D models in Blender via the Blender MCP — render the model from several angles, actually look at the images, and catch what numbers miss. Use whenever you have built, imported, modified, or are about to export or finish a model and want to confirm it really looks right: wrong orientation, off proportions, inverted or black normals, shading artifacts, exploded or floating parts, scale drift, or mismatch against a reference image. Complements blender-assembly, which only checks bounding boxes and transforms numerically and never renders. Trigger it even when the user just says a model "looks off", or asks you to "check the model", "look at it", or "review the render", and before burning an in-game test cycle on a DayZ model (orientation, scale, and ride-height parity vs a vanilla reference). Invoke proactively after any non-trivial Blender geometry work — eyes catch what verify_bounds cannot.'
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

### B. DayZ parity vs a vanilla reference

Import a known-good vanilla model into the same scene at 1:1 and compare side by side (the import path lives in `dayz-model-pipeline`). Anchor each check to the reference, not to taste:

- **Orientation / scale** — same forward axis and roughly the same footprint as the vanilla equivalent.
- **Ride-height (measurable)** — for ground items, the lowest vertex (`result["lowest_z"]`) sits at ≈ the ground plane (z≈0); for vehicles, the wheel contact is ≈ ground and the chassis belly clears it well (a vanilla sedan's belly clearance is ~0.43 m; a too-small wheel sinks the body). Measure it — don't eyeball "looks grounded" (LL-062; `vehicle-structural-parity`).
- **Proxy / slot presence** — wheels, FireGeo bulk, and lights are visibly where the vanilla has them.

### C. Reference-image comparison

When matching a photo or concept: load the reference as a camera background image (`cam_data.show_background_images = True`, then `cam_data.background_images.new().image = bpy.data.images.load(path)`), match the camera to the reference's angle, render, and compare **named landmarks** — roofline, wheel arch, handle position — not overall impression. Report silhouette deviation, missing or extra masses, and proportion drift by pointing at specific points.

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

Measured 2026-07-30 (RTX 3090, n=2 renders — provisional): `gemma4:26b` ≈15 s warm per 8-question checklist, `qwen3.5:27b` ≈132 s for comparable quality, so gemma is the default. **⚠ Esa brecha de 9x quedó REFUTADA en su causa el 2026-08-16: no era el modelo, era el `num_ctx` de fábrica** tirando a qwen el 37% a CPU. Con `think:false` + `num_ctx=8192` son 8,3 s y 17,2 s — brecha de 2x, y qwen vuelve a ser viable como segunda opinión de otra familia. Ver §Pre-filtro más abajo. Both correctly flagged a faceted circle and both answered "unsure" rather than guessing when the view could not decide — but they gave **opposite** bevel verdicts on the same renders, so treat bevel/chamfer questions as agent-side until calibration says otherwise. Judge fine surface questions on a native-res crop, never a full-frame render (LL-153).

Setup notes: models live wherever `OLLAMA_MODELS` points (here `E:\Ollama\models`); a 17 GB model fills a 24 GB card, so models load one at a time and compete with Blender for VRAM — unload before a heavy render. Always address the server as `127.0.0.1`, never `localhost`: on Windows that resolves to IPv6 first and a stray IPv6-bound `ollama serve` will answer from a different model library.

## Output / evidence convention

Render into a folder you can also read (the helper defaults to a `_review/` folder next to the .blend, or the OS temp dir if the file is unsaved) and name files `<model>__<angle>__<iter>.png`. Keep the before/after pair for any angle you changed, so the diagnosis is auditable and you can prove the fix actually landed.

## Pre-filtro: cinco preguntas ascendidas de sombra, dos excluidas (added 2026-08-16, SP-277; datos de calibrado en SP-270)

La sección de sombra de arriba manda para cualquier pregunta que no esté en esta tabla. Para las
cinco de aquí, el ascenso está pagado con medidas y **cambia lo que hay que hacer en el bucle**.

**El filtro RECHAZA, nunca APRUEBA.** Un «no» dispara un arreglo antes de enseñar nada; un pase
limpio **no** significa «está bien», significa «ya merece tus ojos». La regla de que el modelo
local nunca es juez final sigue intacta: se le ha delegado el poder de parar, no el de aprobar.

### Qué está calibrado y qué no

Medido sobre `mk47_mutant`, con el par roto/arreglado del MISMO objeto, tres modelos, el agrupado
real de `vr_score.py`. El checklist entero saca **77,8% contra un suelo de respuesta constante del
58,3%**:

| pregunta | acierto | en el bucle |
|---|---|---|
| conectividad / piezas flotando | **12/12** | **pre-filtro** — la más fuerte con diferencia |
| huecos o agujeros en la superficie | 10/12 | **pre-filtro** |
| caras negras, del revés o mal sombreadas | 10/12 | **pre-filtro** (tras moverla a `assembled__profile_R`) |
| objeto acabado vs cajas peladas | 10/12 | **pre-filtro** |
| proporciones consistentes | 10-12/12 | **pre-filtro** |
| **biseles / chamfered edges** | **6/12** | **NO delegar** — está en el suelo de la respuesta constante. Confirma el aviso de 2026-07-30: los dos modelos daban veredictos opuestos de bisel |
| **cilindros facetados** | **al azar en los 8 encuadres** | **NO delegar** — la pregunta está rota de redacción, no mal enrutada: permite leer un guardamanos poligonal, plano por diseño, como un cilindro facetado |

### Dónde entra en el bucle

Entre el paso 2 (capturar ángulos) y el paso 3 (mirar) de §The loop:

    python references/vr_score.py ask --checklist references/checks_hardsurface.json \
      --model gemma4:26b --json \
      --view assembled__iso  _review/m__iso__iter3.png \
      --view assembled__profile_R _review/m__profile_R__iter3.png \
      --view assembled__profile_L _review/m__profile_L__iter3.png \
      --view zoom_receiver__right_iso _review/m__receiver__iter3.png \
      --view zoom_muzzle__front_iso _review/m__muzzle__iter3.png

Si dispara alguna de las cinco: arreglar y re-renderizar **antes** de gastar los ojos del usuario.
Si no dispara ninguna: mirar igualmente — el filtro no ha aprobado nada. Las dos excluidas se
contestan a ojo; sus respuestas del modelo se ignoran, no se ponderan.

### El gate de calibración cambia: por pregunta, con par roto/arreglado

La sección de sombra pide **≥15 renders ya juzgados** antes de delegar una pregunta. Eso es
calibrar por acumulación y **no habría encontrado nada de esto**: la misma pregunta pasa de 7/12 a
11/12 solo cambiando el encuadre, y de 9/12 a 18/18 solo cambiando con qué otras preguntas viaja
en la llamada. Se sustituye por un gate más barato y que además atribuye:

**Coge dos renders del MISMO objeto, uno con el defecto y otro con el defecto arreglado, y haz la
misma pregunta a los dos.** No necesita oro. Mide dos cosas que no son la misma:

- **sensibilidad** — ¿cambia la respuesta donde debe cambiar?
- **especificidad** — ¿se queda quieta donde no debe cambiar?

Un juez que contesta igual a las dos versiones no está leyendo el modelo, tenga el marcador que
tenga. Cualquier mod con un antes/después sirve de banco: no hay que fabricar nada.

### Tres cosas que invalidan una comparación de encuadres

1. **El lote de la llamada cambia la respuesta.** Misma pregunta, misma imagen, mismo modelo:
   **18/18** en una llamada con otras cuatro de sombreado, **9/12** en la llamada con las ocho del
   checklist. Comparar encuadres exige mantener el lote fijo. Y **no es el tamaño**: sacar una
   pregunta del lote empeoró a las dos que se quedaron.
2. **Un encuadre sin render arreglado no es comparable** con uno que lo tenga: puntúa sobre la
   mitad de las celdas y ahí una respuesta constante saca 6/6.
3. **La temperatura está fijada a 0,1** en el payload, así que dos muestras de la misma celda salen
   casi idénticas: el `n` efectivo es el número de celdas, no el de muestras. No confundir repetir
   con medir.

### Alcance, para no repetir el error que originó esto

Todo lo anterior sale de **un solo objeto**. El día antes registré que estos modelos «no detectan
defectos geométricos» — y era falso: medía mi arnés, no los modelos, y cerró una línea de trabajo
que funcionaba. Antes de escribir que un modelo no sabe hacer algo, haber variado **redacción,
encuadre y lote**, y decir cuál de los tres se varió. Origen y evidencia en `LL-289`.

## Reglas promovidas del corpus de lecciones (added 2026-07-27)

Promovidas desde `AI/20_Knowledge/lessons-learned.md` para que lleguen por trigger en vez
de depender de que alguien recuerde buscarlas. Cada regla cita su `LL-NNN` de origen;
la entrada completa (síntoma, origen, evidencia) vive allí. No quites la cita: el índice
`lessons-index.md` detecta la promoción buscando esa referencia dentro de las skills.

- **LL-153** — Juzga toda zona visual crítica en un crop a resolución nativa. Usa RMS y scores solo como filtro de cambio; nunca como veredicto de corrección, y conserva el crop full-res como evidencia.

