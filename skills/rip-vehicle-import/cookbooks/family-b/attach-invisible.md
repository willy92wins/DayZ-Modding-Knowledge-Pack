# Cookbook B — attachment invisible

> Familia B. Este cuerpo se movió sin reescritura en CAMBIO-1; las notas de estado y las rutas permanecen tal como estaban en el origen.

<!-- MOVED-EXACT source="dayz-vehicles/SKILL.md:669" sha256="9EAB1E902D741923EDFF9CEDE1469D619DB11CEB5083705BA4D49DAA8727F9D7" -->
21. **Attachment (wheel/door/part) renders FROM the shell's visual-LOD proxy FRAME — an identity frame hides the piece with the sim intact (SUB_BRZ B1, s37).** The engine instances the attached item's model on the proxy of the visual LOD being drawn, oriented by that proxy's frame. py3d `add_proxy(rotation=None)` writes an identity frame: the attached wheel renders rotated ~90 deg, tucked inside the arch — invisible from outside, no raycast hit at the hub, while attach/sim/damage all work (the exact "attached but invisible" signature). Contract, measured against the civiliansedan control (5 wheel proxies in EVERY visual LOD 1/2/3/4/6 + VG + FG): (a) the attachment proxy exists in EVERY visual LOD of the shell, not just the finest; (b) each carries the per-side lateral frame (x>0 `((1,0,0),(0,0,-1),(0,1,0))`, x<0 mirrored) or, for doors, the UNIFORM measured door frame `((-1,0,0),(0,0,1),(0,1,0))`; (c) proxy point flags 63 like the control (identity-frame proxies also had flags 0); (d) `CfgNonAIVehicles` class name must match the proxy file BASENAME case-insensitively (`sub_brz_wheel_ruined.p3d` -> `ProxySUB_BRZ_Wheel_ruined`; a `_destroyed`-named class over a `_ruined` file correlated with a native client CRASH on the damage swap — B5). Mechanical gate: `derive_proxy_frame` of every visual attachment proxy == expected frame, with a negative fixture (identity MUST fail). Diagnosis shortcut: "attached but invisible" is NOT a missing item LOD 0.0 (refuted in-game s37) and NOT a bone/companion issue if anchors+companions match — measure the FRAMES first. RCA: `<vehicle-import>\work\s37_b1_rca\B1_RCA_findings.md`. Fix verified offline (double-measured); in-game gate pending as of 2026-07-18.

<!-- END MOVED-EXACT -->

## El gate in-game de arriba está CERRADO desde el 2026-08-24

Fuera del bloque MOVED-EXACT, igual que la nota del 22-08 y por el mismo motivo: el
cuerpo de arriba se movió sin reescritura y su `sha256` de procedencia certifica
exactamente esos bytes, notas de estado incluidas. Editarlo en sitio para actualizar un
estado rompe el sello, y ningún check lo detecta — `packctl validate` no mira dentro de
los bloques `MOVED-EXACT`.

El gate que la línea 21 deja «pending as of 2026-07-18» se **cerró en partida el
2026-08-24**: la pieza adjunta renderiza en su sitio. La corrección del frame de proxy
queda por tanto verificada in-game, no solo offline.

## El frame por lado va atado a SU control, y el de arriba es el civiliansedan

Añadido 2026-08-22, fuera del bloque MOVED-EXACT para no romper su sha de procedencia.

La constante de (b) —x>0 `((1,0,0),(0,0,-1),(0,1,0))`, x<0 espejada— **no es universal**:
se midió sobre `civiliansedan_mlod`, y vale para geometría derivada de ese control. El
propio cuerpo de la invariante lo dice al nombrar el control, y `dayz-vehicles`
lo remacha: «copy the **VANILLA** frame (NOT kt's — its mirror differs because its wheel
geometry differs)» (`references/rip-import.md:684-685`), con la doctrina general en
`references/vehicle-structural-parity.md:939`: el frame depende de e1/e2 **y de la
orientación base del modelo**.

Consecuencia práctica, que es donde se pierde el tiempo: **medir estos literales contra un
control de otra familia da «invertido» sin que haya nada roto.** Ocurrió — una nota del
ledger (SP-156) registró la constante como medida al revés comparándola contra un
Landrover. Antes de creer que la constante está mal:

1. Mide el frame de TU control, el que renderiza, con `derive_proxy_frame`.
2. Compara contra él, no contra estos literales.
3. Si tu control es de otra geometría, que difiera es lo esperado, no un bug.

La fixture mecánica que acompaña a la invariante solo exige que el frame identidad FALLE.
Una fixture que intercambie los lados y exija fallo sigue **pendiente**, y es la que
convertiría «invertido» en un rojo automático en vez de en una discusión.
