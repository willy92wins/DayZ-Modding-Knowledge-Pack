# Materiales y selecciones: dos diagnosticos que enganan

Extraido de `SKILL.md` (corte 3, 2026-08-15). Aqui vive el DETALLE; el enunciado
corto y cuando leer esto estan en el indice `## ARCHIVO DE LECCIONES` del SKILL.md.
Nada de este fichero esta derogado: son lecciones vigentes, ordenadas por tema en
vez de por fecha.

---

## Two diagnoses that look solid and are not: identical textures, and server co-move (SP-094, added 2026-07-26)

Both cost real cycles on LFHeli OH-1. Both are one cheap measurement away.

**A. "One .rvmat bound to two base textures" is NOT automatically the cause of a texture defect.**
On OH-1, `oh1_fuselage.rvmat` resolved to `rd_oh1_fuselage_co.paa` (10403 faces) and
`rd_oh1_hs_fuselage_basecolor_co.paa` (6420 faces), UVs perfectly inside [0,1]. It reads like a
smoking gun. **Hashing the files killed it**: all four .paa were byte-identical
(`16B0FD978AAD7552...`, 6822200 bytes) - the same image under two names, so reassigning the faces
would not change a single pixel. Rule: before concluding a texture-binding split explains anything
visible, **hash the referenced textures**. If they are identical, the split is hygiene, not a cause,
and the real defect is elsewhere (runtime/VFS, material stage, UV layout vs atlas content).
This applies directly to the T1 rule of `texture_binding_gate.py` - the gate is right to flag it,
but a FAIL there is not a diagnosis.

**B. Server-authoritative co-movement does NOT prove the client renders it that way.**
The user reported the hull staying behind while rotors and interior climbed. The instrumented
measurement over a 28 m ascent said the opposite: `ratio shell/root = 1.000`, `proxy/root = 1.000`,
separation constant at 0.626 m - hull and proxy co-move exactly. Both statements were true: the
authoritative transform is coherent and the client still renders the part detached. Rule: when a
part "does not follow", measure BOTH sides before designing a fix. A perfect server-side ratio with
a visible mismatch points at render/replication/perception, and it rules out the physics and
cohesion branches - which is worth a lot, because those are the expensive ones to chase.

## Parent-driven selections (hiddenSelections / config anims) do NOT reach a PROXY - host them in the SHELL (SP-192, added 2026-08-07, SUB_BRZ + LFVehicleUI)

Any named selection the CAR's config must drive - hiddenSelections swaps
(SetObjectTexture/SetObjectMaterial), model.cfg Animations declared on the parent,
sections[] entries - must live in the PARENT model, never only inside a proxy sub-p3d.
Evidence, both measured on SUB_BRZ: (a) dashboard needle anims declared over the interior
proxy = needles STATIC in-game (s45 falsification); (b) the selections that DO work
(light_dashboard idx 8; screen_nav idx 9 for the nav screen) are faces hosted in the shell
- light_dashboard ships duplicated shell+proxy with identical coords and works FROM the
shell copy. MercedesAMGLF carries the same latent defect (interior selections in proxy).

Rules for a proxy-split car (day-1 for car #2, surgery for cars in flight):
1. Every hiddenSelections entry needs its faces in the SHELL, in LOD0 AND the ViewPilot
   1100 (SP-189: 1100 mirrors LOD0 content).
2. MOVE the faces out of the proxy instead of duplicating when the selection can carry a
   DIFFERENT material than the base (a swap on the shell copy z-fights the proxy copy).
   A duplicate is only tolerable while both copies always share the same material - the
   light_dashboard duplicate is a latent z-fight for the dashboard-light swap.
3. Copy vertex order and stored normals VERBATIM when moving (SP-190/191): faces that
   render correctly from the proxy keep rendering correctly from the shell (empirical
   control: the instrument cluster).
4. Reference surgery with asserts (component pick by aspect+centre, per-LOD face deltas,
   selection cardinality, proxies/bones untouched):
   <vehicle-import>/work/lfvui_f2/surgery_screen_nav.py.
