---
name: rip-vehicle-import
description: "Use when importing a new ripped racing-game Grub vehicle into DayZ, resuming the vehicle import pipeline, or diagnosing a ripped-vehicle import contract. Assets already in flight keep their frozen project runbooks."
---

# Ripped racing-game vehicle → DayZ — adaptador de familia B (CAMBIO-2)

> Ruta crítica day-0 para el próximo coche Grub del juego fuente, proxy-split y con partes móviles.
> Si el asset está en vuelo, usa su runbook congelado. Si falta una entrada aplicable: **STOP**.
> El runbook anterior está en `history/pre-cambio-1-family-b-runbook.md` y no es ejecutable.

## Seis deltas obligatorios

| Campo | Contrato de familia B |
|---|---|
| Ejes / unidades | Source `<vehicle-import>\rip\media\cars\<car>\`. Transform neto `DayZ=(-Fx, Fy+Y0, -Fz)`, metros, sin permutar ejes y `det=+1`; `Y0` se mide y se sella en la ficha, nunca se hereda de otro coche. Contrato verificado en `<vehicle-import>/tools/fit_transform.py:5-15,107-108`. |
| Monolítico vs proxy-split | Host/shell con LODs estructurales; piezas visuales que superen presupuesto y attachments se instancian como submodelos proxy. No usar un monolito como fallback silencioso. |
| Partes móviles | Puertas, capó, maletero y rueda/item conservan identidad propia, pivote medido y wiring item↔slot↔proxy; no se funden en el shell. |
| Autoridad de frame | El frame del donor/golden manda para estructura; el frame del source manda para visual importado. Toda conversión se prueba con anclas independientes. Nunca validar una pieza contra un punto producido por el mismo transform. |
| Golden | `<vehicle-import>\goldens\family-b\civiliansedan\r1\q1-structure.json`, revisión `family-b-civiliansedan-r1`, 3.219.555 bytes, SHA-256 `3174D511F2761EE2F4E003694F566D7D92180BB30CE3479A8FA5F1EAA7C45AEB`; donor hashes en `golden-manifest.json`. Es estructural, no clone-ready: `mass_array` vacío y avisos de proxies obligan a STOP antes de copiar masa por vértice o declarar paridad completa. |
| Allowlist de checks | Solo B1-B7 de la tabla siguiente. Ningún gate legacy, snapshot o copia de workspace amplía el carril. |

## Inventario de puertas del source (medido 2026-08-06 sobre la biblioteca de 651 rips)

- El contenedor bilateral de puerta puede venir de CUALQUIER lado: el BRZ entrega solo `doorlf`, `SUB_WRXSTi_04` entrega solo `doorRF_a`, `FOR_BroncoRaptor_22` mezcla lados (`doorLF_a`, `doorLF_b`, `doorLR_b`, `doorRF_a`). La regla real es «un solo lado por contenedor, el que sea» — no asumir LF al clasificar, contar puertas ni sintetizar el espejo.
- Variantes `_a`/`_b` del mismo contenedor de puerta = plataformas intercambiables (puertas desmontables del Bronco): la sentada A elige UNA variante como INCLUDE y justifica el resto como EXCLUDE.
- jamb/handle/card de una puerta SIN su panel `door<lado>_<x>` = puerta fundida en la carrocería (`BMW_M4_14`, `FOR_2_GT40_66`): no es otra convención de nombres; la pieza abrible no existe en el rip.

## Ficha única y checkpoint de identidad

- Plantilla completa: `<vehicle-import>\contracts\asset-contract.json`; schema de revisión: `<vehicle-import>\contracts\asset-contract.schema.json`.
- La copia por asset se llama exactamente `asset-contract.json`; es el tercer y último fichero day-0. Sustituye inventario/decisiones paralelos: no produzcas `source_inventory.json`, `manifest_decisions.json`, tombstones aparte ni otra lista.
- Export sentadas A/B: el humano ejecuta `<vehicle-import>\scripts\blender_export_asset_contract.py` sobre collections `DZ_INCLUDE` / `DZ_EXCLUDE` / `DZ_MOVABLE`. El JSON es evidencia de import; después manda la ficha.
- Primitive única: `<vehicle-import>\scripts\asset_contract_checkpoint.py`, versión declarada en stdout. Está prohibido copiarla a una corrida.
- Sentada A/B se importa con `import-blender`; tras convertir, `check` es el único `capability=LINEAGE_CHECKPOINT`.
- `PASS` permite continuar solo dentro de la capability emitida. `DECISION_REQUIRED` vuelve al humano. `TOOL_FAIL` bloquea y no autoriza tocar geometría ni se registra como fallo del asset.
- La cobertura es N:M: todo `INCLUDE`/`MOVABLE` aparece en un `derived_from` dentro de una operación autorizada; cada `EXCLUDE` justificado es el tombstone. No se exige igualdad source/output.

## Allowlist B1-B6 y ubicación canónica

| ID | Contrato / ubicación | Estado para un B nuevo |
|---|---|---|
| `B1_BINARIZE_LOAD` | Oráculo de tres estados `PASS / CAPACITY_FAIL / OTHER_FAIL`: `<vehicle-import>\scripts\p3d_vertex_gate.py`. | Disponible; autoridad demostrada con known-good, `CAPACITY_FAIL`, `OTHER_FAIL` y ODOL residual. |
| `B2_DEPLOY_IDENTITY` | `<vehicle-import>\scripts\rip_build_identity.py --stage` (`:420-442`). | Disponible. |
| `B3_VEHICLE_PARITY` | `<vehicle-import>\tools\verify_rip_car.py` en modo contractual (`:1538-1546,1734-1736,1817`), nunca `build_checks()` legacy. | Disponible. |
| `B4_CREW_ACTIONS` | `<vehicle-import>\scripts\rip_action_contract_gate.py` por su CLI real (`:732-742`). | Disponible. |
| `B5_DOOR_ALIGNMENT` | `<vehicle-import>\scripts\rip_door_engine_alignment_gate.py` por su CLI real (`:513-515`). | Disponible. |
| `B6_NATIVE_DOOR` | `<vehicle-import>\scripts\rip_native_door_contract_gate.py` por su CLI can?nica (`--profile`, `--mlod-stage`, `--odol-stage`, `--debinarizer-scripts`, `--out`); W2 (`--matrix-authority` + `--matrix-out`) es una extensi?n opcional, no la autoridad base. | Disponible; autoridad de familia B demostrada con perfil no BRZ, golden vanilla, mutaci?n estructural y aver?a instrumental. |
| `B7_VISUAL_SIGNOFF` | Render: `<vehicle-import>\scripts\rip_assembled_viewer.py`. Veredicto: `<vehicle-import>\scripts\rip_visual_signoff.py` (`--render` / `--verdict` / check con `--out`). | Disponible; estrenado con sub_wrxsti_04 el 2026-08-16, cuando el ojo del usuario encontro en minutos cuatro defectos que B1-B6 habian dado por buenos. |

**Ubicación única:** cada primitive/gate se ejecuta solo desde su ruta canónica anterior. Está prohibido
copiarlo a `work\`, `sNN\`, `_validation\`, `.superpowers\sdd\` o cualquier workspace de corrida.
Las copias existentes son snapshots de evidencia: se conservan, se pueden hashear y **no se ejecutan**.
Si la ruta canónica falta, el resultado es STOP, nunca “usar la copia más nueva”.

## Visor de clasificación (revisión de sentada A sin Blender)

`assets/classify-viewer/` — visor Three.js para revisar/reclasificar la sentada A por clic
(GLB con extras + deltas que el agente aplica al `.blend` por script headless). Consultivo:
la autoridad sigue siendo `.blend` → export → ficha. Uso y contrato de datos en su `README.md`.
Estrenado con sub_wrxsti_04 (2026-08-06).

## B7 — visto bueno visual antes del build (estrenado 2026-08-16, sub_wrxsti_04)

B1-B6 miden nombres, conteos de caras, hashes y matrices logicas. **Ninguno puede ver un color
ni la orientacion de un proxy.** El 2026-08-16 el usuario abrio el WRX en un visor por primera
vez y encontro en minutos cuatro defectos que el allowlist entero habia dado por buenos:

- el 64% del coche en UN material y el interior entero en otro — la importacion registro
  `material_map: null` y mando 37 piezas con nombre (emblemas, espejos, escape, jambas,
  faldones, bajos, brazos de suspension) al cubo de pintura de carroceria;
- los cuatro proxies de rueda escritos con la matriz IDENTIDAD, iguales los cuatro, cuando
  vanilla escribe DOS frames espejados, uno por lado. Mismo frame + anclajes espejados =
  un lado montado del reves por obligacion matematica;
- rueda de berlina vanilla de 176 mm en vez de la del coche;
- un color de carroceria que nadie habia verificado.

El instrumento existia a medias: `rip_visual_sheet.py` ya renderiza los artefactos y su
propio docstring dice «renderiza, no juzga» — pero dibuja geometria GRIS y por separado, asi
que no podia enseñar ninguno de los cuatro. B7 es la otra mitad.

**Como se corre**, en este orden y sin saltarse el medio. RUTAS ABSOLUTAS: este proyecto
tiene DOS arboles — `<vehicle-import>` (scripts, profiles, work) y
`C:\Users\<you>\OneDrive\Documentos\DayZ Projects` (= `P:\`, el mod desplegado) — y un
comando relativo solo corre desde uno. El estreno real de B7 murio con
`can't open file ... No such file or directory` justo por eso.

```
set FZ=<vehicle-import>

python "%FZ%\scripts\rip_visual_signoff.py" --car "%FZ%\profiles\<car>.json" ^
       --render "%FZ%\work\<car>_viewer.html"
   REM  (el humano lo abre y lo mira -- este paso no lo puede hacer el agente)
python "%FZ%\scripts\rip_visual_signoff.py" --car "%FZ%\profiles\<car>.json" ^
       --verdict pass^|fail --by "human:<quien>" --note "<que viste>"
python "%FZ%\scripts\rip_visual_signoff.py" --car "%FZ%\profiles\<car>.json" ^
       --out "%FZ%\work\_gates\b7.json"
```

**Tres reglas que hacen que sea un gate y no un sello de goma:**

1. **El render va MONTADO y con materiales.** Casco + chunks + interior + desmontables en sus
   proxies + ruedas en los suyos, con los colores de los rvmat que ship. Las puertas flotando
   y las llantas invertidas SOLO aparecen ensamblado; en piezas sueltas y en gris, no.
2. **El veredicto se ata a los bytes.** Lleva el sha256 de cada artefacto que se miro, y el
   check los vuelve a hashear. Reconstruir una pieza deja el visto bueno STALE, no viejo, y el
   gate se pone rojo hasta que alguien vuelva a mirar. Es la misma leccion que ya pago el
   `positive_control`: un control apuntando a una ruta que el siguiente build sobreescribe es
   una tautologia.
3. **Fail-closed.** Sin veredicto es `NO_EVIDENCE`, nunca PASS. Un veredicto que cubra menos
   artefactos de los que el coche tiene ahora es FAIL: no se puede aprobar una pieza que no se
   enseño.

Firmar tu por el humano invalida el gate entero. El comando `--verdict` existe para que la
firma tenga nombre y fecha; usarlo en su lugar es falsificarla.

Dos trampas que el render encapsula, pagadas el mismo dia: DayZ es ZURDO y three.js DIESTRO,
asi que pasar las coordenadas tal cual **es una reflexion** — un coche espejado se ve
perfectamente plausible hasta que lees un emblema, y el calibrador es texto de marca. Y la
colocacion de proxy es `vertices @ effective_frame.T + anchor` con
`effective_frame = MLOD_PROXY_CONVENTION_FRAME @ raw_frame`
(`rip_detachable_doors.py:55-61,171-176`): deducirla a ojo del triangulo puso cada puerta a
un metro del coche.

## Único índice síntoma → cookbook

| Síntoma | Cookbook movido |
|---|---|
| Get-in ausente | `cookbooks/family-b/get-in-ausente.md` |
| `wheelPresent=0` | `cookbooks/family-b/wheelpresent-0.md` |
| Coche blanco / sin textura | `cookbooks/family-b/coche-blanco.md` |
| Attachment invisible con sim intacta | `cookbooks/family-b/attach-invisible.md` |
| Radial de puerta ausente | `cookbooks/family-b/radial-puerta-ausente.md` |

No crear `INDEX.yaml`, un router de cookbooks ni otra tabla síntoma→cookbook. Este es el único índice.

## Secuencia day-0

1. Abre este adaptador desde el selector de `dayz-vehicles`.
2. Abre una única ficha `asset-contract.json`, creada desde la plantilla canónica, y verifica source revision, `Y0`, golden revision y estado.
3. El humano clasifica en Blender; la primitive captura hash/inventario e importa lists/transforms en esa misma ficha. El agente no abre ni mantiene schema/export como documentos de estado.
4. Comprueba presencia can?nica de B1-B6 sin ejecutar snapshots. **El allowlist B1-B7 est? completo; cualquier ausencia can?nica da STOP.**
5. Convierte preservando procedencia y exige `LINEAGE_CHECKPOINT=PASS`; los otros dos estados bloquean.
6. Ejecuta solo el allowlist; el test vivo final permanece separado del preflight.
7. Si aparece uno de los cinco síntomas, abre solo su cookbook. Para otros síntomas, STOP y diagnóstico explícito.

## Raíl de conversión del paso 5 (SP-363; estrenado sub_wrxsti_04, 2026-08-06)

El profile del coche declara `source.asset_contract` (ruta a la ficha) — eso activa el modo
contract de `rip_p2_import.py`: listas INCLUDE/SHADOW proyectadas de la ficha por
`scripts/rip_contract_source.py` (homogeneidad por contenedor fail-closed), sin
`manifest_decisions.json` jamás, far-shell diferido a la clasificación humana, anclas G0 por
profile (`source.g0_anchors` = pares [part, locator]). Los tres comandos, en orden:

```
blender --background --factory-startup --python-exit-code 1 --python scripts\rip_p2_import.py -- --car profiles\<car>.json
python scripts\asset_contract_checkpoint.py import-conversion --contract <ficha> --import-report <report> --contact-y-m C --hub-y-m H --lift-m L --y0-m Y0 --responsible "machine:rip_p2_import@<car>" --approved-by "human:<quien>" --out <ficha>
python scripts\asset_contract_checkpoint.py check --contract <ficha>
```

- `--python-exit-code 1` es OBLIGATORIO: sin él Blender devuelve exit 0 aunque el script python
  muera (un G0 FAILED pasó por "completado" en el estreno). Aplica a TODO lanzamiento Blender
  headless, no solo a este paso.
- `import-conversion` valida la derivación `Y0 == contact − hub + lift`, la correspondencia
  MULTISET de nombres de objetos por contenedor (report vs inventario, ciega a sufijos Blender
  `.NNN`) y que ninguna parte excluida se importó; sella linaje 1:1 `AXIS_UNIT_TRANSFORM` +
  frame, y es sellado-una-vez (reintento = `CONVERSION_ALREADY_IMPORTED`).
- El profile nuevo nace MÍNIMO (ver `profiles/wrx.json`): source block + anclas + transform
  medido + `WHEEL_R` == radio de rueda montada. Copiar claves de `profiles/brz.json` está
  prohibido: son cicatrices específicas de ese coche.
- Minas conocidas aguas abajo (siguiente cirugía): `rip_p2_group.py:33` IN_BLEND hardcoded
  BRZ; `rip_p3_structural.py:715` cae por defecto a `brz.json`.
