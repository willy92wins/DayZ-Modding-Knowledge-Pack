# Track record — estrenos reales y lo que enseñó cada uno

El valor de esta skill está aquí: cada sección es una corrida real con su
lección operativa. Antes de un encargo, lee la del rol que vas a usar. Cuando
una corrida nueva falle o enseñe algo, se añade aquí — como en
`codex-handoff-template`, cuyo valor está en sus ~15 casos.

## Research ciego — LFThermalCore (2026-08-11)

3 lanes ciegas (Fable/Codex/Grok) sobre «visión térmica DayZ
server-load-first». Consenso 3/3 tras **ronda de conciliación** con tres
retiradas motivadas: Grok retiró su primario de luces, Fable su escena cálida,
Codex su LUT-como-cimiento. Coste Grok: $0.50 research (16 turnos) + $0.19
conciliación vía `-r`.

- **La ronda de conciliación post-ciega funciona** y es barata: conflictos en
  neutro (sin atribuir posiciones) + permiso explícito de retirar. Las
  retiradas motivadas son la señal de éxito. Patrón completo en
  `prompt-patterns.md` §Research.
- Handoff: `AI/30_Sessions/2026-08-11-lfthermal-research-triple-spec-v1.md`.

## Reconciliación / plan — dos casos

### Mercedes v2 (2026-08-03, patrón secuencial de la época)

Plan que YA había pasado research dual + un R21 con 4 BLOCKER aplicados. Grok
devolvió SOUND-CON-FIXES con **1 BLOCKER nuevo**, 5 MAJOR y 5 MINOR; el
receptor verificó 4 hallazgos contra fichero: los 4 correctos.

1. **La lane extra rinde sobre material ya revisado dos veces.** El BLOCKER:
   el plan citaba `_wheel_position` como «precedente verificado del centrado»,
   pero esa función además permuta Y/Z respecto de la transform canónica.
   Reutilizar un helper exige verificar su SEMÁNTICA, no solo que existe
   (`LL-222`).
2. **Pedir «qué NO pudiste verificar» funciona**: devolvió 10 puntos honestos.
3. **El gate del plan no podía detectar el defecto**: `|centro bbox| < 1e-4`
   es invariante a permutar ejes. Un gate que no puede fallar por la causa que
   te preocupa no es un gate; es decoración. Pregúntalo en cada revisión.

### LFCOM slice-2 (2026-08-12) — la lane final sobre material revisado CUATRO veces

Plan tras 4 rondas Codex (19, 11, 10, 3 hallazgos; APPROVE-WITH-MINOR en la
4ª). Grok: **UNSOUND con 1 BLOCKER real** (GRK-S2-001): la medida M0.1 daba
verde sin probar la GEOMETRÍA de red del panel-réplica — componer 3 hechos ya
verificados de `verified-apis.md` contra el diseño «staging remoto» produce una
contradicción que la consistencia documental no ve. Clase de defecto:
**razonamiento espacial de dominio**, no verificación de citas. El follow-up de
calibración retiró 1 de 11 hallazgos y añadió una banda geométrica que el
orquestador no había visto. Coste: $0.64 + $0.17.

- Evidencia: `P:\_LFCOM_Planning\reviews\2026-08-12-grok-r22-plan-slice2.md` ·
  `AI\30_Sessions\2026-08-12-LFCOM-plan-slice2-council.md`.

## R21 código — método adversarial calibrado

### bridge_status (2026-08-07)

R21 ciego sobre código en producción sin revisar. BLOCKER confirmado por el
receptor con las 3 citas verificadas abriendo el archivo. Review íntegra:
`DayZ_MCP_dev\reviews\2026-08-07-r21-bridge-status-grok.md`.

### Corrida 22 del scorecard (2026-08-13) — las preguntas temporal y de género

Sobre MercedesAMGLF: **13/13 CONTRADICTED refutados** — 9 cayeron por la
pregunta TEMPORAL (historia fechada que el árbol posterior desplazó =
OVERSTATED/STALE, no CONTRADICTED) y 2 por el GÉNERO del criterio (un AC en
⏳/❓ describe destino, no as-built). 4/4 spot-checks del orquestador exactos.
Las dos preguntas están integradas en el esqueleto §R21. Prompt de origen:
`DayZ Projects\_linter_memory_layer\ext_mercedes\prompt-lane-b.txt` (4 y 5).

### Arbitraje expuesto — LFPowerGrid A4a (2026-08-13)

Al adjudicar NO-APLICAR un hallazgo (N2) con evidencia de otras lanes, la
repregunta expuso el arbitraje y sus fundamentos e invitó a rebatir con cita.
Resultado: cierre explícito con verificación propia del revisor en 1 turno
(~43% del coste de la revisión, misma sesión con resume). La alternativa
—cerrar en silencio— cría hallazgos zombie. Patrón en `prompt-patterns.md`
§Follow-up.

## Peer — cuatro corridas, dos posturas, dos hosts

### GunRacks C5 (2026-08-06) — estreno postura B

Candidato DayZ completo —builder py3d, repunte de materiales, 8 gates offline,
dos PBO con AddonBuilder, comparador ODOL semántico, manifest— en **29 turnos /
2,66 M tokens / $1,38 / ~7 min**, con **24/24 criterios en verde** y
`stopReason=end_turn`. Aportó un hecho que nadie tenía: midió que AddonBuilder
empaqueta el `.rvmat` sin estar en `include.lst`.

- Lo que lo hizo verificable: **todo a `%TEMP%`** y **foto de hashes ANTES**
  (28 ficheros + PBO + baseline → 0 cambios, medido). Doctrina en
  `write-to-disk-handoff.md` §Disciplina.
- Cuándo repetirlo: ejecución larga, mecánica, con gates objetivos donde el
  plan ya dice qué medir.

### ForzaDayZ WRX T6.4 (2026-08-07) — estreno postura A

Artefacto JSON de configuración (`profiles\wrx.json`, `detachable_doors`) con
`--tools "read_file,grep,list_dir,search_replace"`: 17 turnos, $0.58,
`end_turn`, entregable único en `%TEMP%` y recibo por stdout. Sesión
`019fde2c-59bd`.

1. **Encarga también la verificación del esquema**, no solo la autoría: pedir
   `key_citations` con `ruta:línea` por clave hizo que quitara una clave que
   ningún script lee y la marcara en `not_verified` en vez de inventársela.
2. **Darle las decisiones ya tomadas numeradas y prohibir relitigarlas**
   concentra sus turnos en lo que aporta.
3. El hash-snapshot previo probó **0 cambios en 409 ficheros** — eso convierte
   «no toqué nada» en un hecho. Valor real: dos correcciones que la ejecución
   no podía dar, ambas confirmadas después por la corrida real.

### DayZ_MCP debug-gate (2026-08-07) — tres cosas que solo se aprenden ejecutando

$0.64 total, entrega correcta en lo esencial y dos defectos reales cazados en
revisión:

1. **Al aterrizar trabajo delegado, corre la SUITE COMPLETA, nunca solo el
   vecindario.** Sus 45 tests pasaban; solo la suite entera delató que su
   cambio ponía en rojo un gate de seguridad de OTRO módulo (política
   anti-`getattr` dinámico del repo). Un delegado no puede conocer los gates
   transversales: esa comprobación es del orquestador.
2. **El workspace delegado lleva los artefactos que los tests referencian, o
   el prompt declara qué módulos NO corren ahí.** 5 tests petaron por
   artefactos no copiados — ruido del orquestador que cuesta arbitraje.
3. **Observabilidad que altera el control de flujo del cleanup**: había puesto
   una captura de diagnóstico ANTES de `close_job()` sin proteger — si lanzaba,
   dejaba el árbol de procesos huérfano. Mirar siempre esa costura en entregas
   de peer.

### LFPowerGrid lane 1 + spec B (2026-08-14, portátil) — validación en 2º host

(1) Refactor Enforce `.c` 132→203 líneas, EOL/BOM intactos, baseline y árbol
vivo intocados por hash; 15 turnos, 1,04M tokens; R21 ciego posterior (sesión
nueva, sin memoria): SOUND, 0 hallazgos. (2) Spec Phase B: ronda 2 editando EN
SITIO un doc de 109 KB (840→915 líneas, 25 turnos, 3,0M tokens) + ronda 3
quirúrgica por resume (716K tokens) — **el patrón «resume para rondas de
corrección del MISMO implementador» escala bien**. (3) Caveat aplicado: revisor
SIEMPRE sesión nueva ciega; la convergencia intra-familia se compensó con
revisión final del orquestador línea a línea.

## La auditoría que parió el preflight (2026-08-08)

Backfill del `council-scorecard.md` sobre **~67 corridas de Grok en 14
sesiones** (~$28 equivalente):

1. **Grok (como juez sin shell) no ejecuta**: no corre Python, no calcula un
   SHA, no lanza suites — lo supone. Los dos fallos de ForzaDayZ T5a fueron
   asunciones sobre runtime. Contra-evidencia del mismo período: como revisor
   va bien y barato (T8.0: 2 BLOCKER + 4 MAJOR + 4 MINOR, 4/4 citas correctas,
   $0.665). No es «peor proveedor»: es **un sensor sin acceso al runtime** —
   de ahí la postura C y la regla de preflight.
2. **Grok implementa + Grok revisa = gate degradado, y se declara.** Principio
   del usuario (LFHeli): «si lo hizo grok y lo revisa grok es menos valor»;
   decisión GunRacks `D-09b`.
3. **La corrida que no se vuelca muere con la sesión**: 67 corridas quedaron
   sin arbitraje recuperable — dos días de precisión perdidos. El volcado al
   scorecard se hace en el mismo paso que el arbitraje.

Bonus medido: el follow-up de calibración va **4/4 y nunca ha salido en
blanco** por ~10-12% del coste. Lanzarlo siempre.

## Sondas de re-verificación 1.0.4 (2026-08-15, WILLY)

Tras el bump 1.0.0→1.0.4, tres sondas con baseline de hashes: juez read-only
(no escribió, MCP denegado, $0.010) · postura C (SHA-256 por shell exacto
`-eq` contra medición host-side + `--json-schema` validado, $0.008) · imagen
ACP por `--prompt-file` (número y color exactos, $0.009). Las tres `end_turn`,
baseline intacto. La contención y las capacidades de esta skill están medidas
contra 1.0.4, no heredadas de 1.0.0.
