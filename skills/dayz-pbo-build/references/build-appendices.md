# DayZ PBO — Build Appendices (session findings)

Extracted from dayz-pbo-build/SKILL.md 2026-07-07 (F3). Dated session appendices (2026-06-11) kept out of the core for length. The core skill links here from its "Build appendices" index line.

---

## Verificación post-build obligatoria del PBO (added 2026-06-11)

Origen: sesión LFSlidingFloor 2026-06-10 — AddonBuilder reportó "Build Successful" con un PBO de 613 bytes (su sync interno a temp copió 0 archivos, probablemente choque con OneDrive); además el PBO medido era un RESIDUO de un build anterior (cf. LL-135) porque AddonBuilder nombra el PBO según la CARPETA fuente, no según -prefix.

Checklist tras CADA build (exit 0 y "Build Successful" NO bastan):
1. Tamaño del PBO mayor que un umbral razonable (un mod de scripts ronda 15-30 KB; ~600 B = carpeta vacía empaquetada; cf. memoria "PBO de 2 KB = el modelo se cayó").
2. Contenido: grep binario de strings esperadas (nombres de los .c, un literal de código RECIENTE para detectar residuos): PowerShell `[Text.Encoding]::ASCII.GetString([IO.File]::ReadAllBytes($pbo)) -match "mi_marker"`.
3. Nombre: el PBO sale como `<NombreCarpetaFuente>.pbo` — si construyes desde staging, la carpeta DEBE llamarse exactamente como el mod (p.ej. `C:\Temp\<Mod>\`), o desplegarás y medirás el archivo equivocado.
4. Staging local (fuera de OneDrive) para el source del build: el sync de AddonBuilder contra rutas OneDrive puede copiar 0 archivos sin marcar error.
5. Gate de PROPIEDADES tras `ExtractPbo` — el SHA no basta: un manifiesto de hashes compara el mismo fichero a los dos lados, así que da verde aunque los `.p3d` empaquetados se construyeran ANTES de que la propiedad entrara en los generadores. Caso medido (LFHeli HH-60G, 2026-07-29): `autocenter=0` se añadió al LOD visual del casco en los dos generadores a las 01:52/02:07, el PBO se empaquetó a las 02:15 desde `.p3d` previos, y el manifiesto dio verde; al medir los 48 `.p3d` extraídos, los 8 sub-modelos la llevaban y **los 40 cascos no**. El gate tiene que leer la propiedad concreta **por LOD**, con las expectativas declaradas en tabla (propiedad, valor esperado, motivo, exclusiones explícitas — p.ej. los LOD de Memory, sin geometría que recentrar, quedan fuera). Un gate que solo compara hashes no puede salir en rojo por esta causa.

### Property-gate controls (SP-133)

The expectation table must also name controls that are expected not to change, such as the
control arm of an A/B build or a byte-frozen copy. A blanket "all LODs" requirement rejects
healthy controls and gets disabled; declare the expected value and reason for each control
instead.

## (added 2026-06-11) Model-path resolution gate — validate what the engine will RESOLVE

Origin: A6_MK47 2026-06-11 — `model=` pointed at the PBO root while the
binarized p3d lived in `data\`; dirty-temp builds smuggled a raw MLOD into the
PBO root and the engine loaded that file for 11 versions, so every offline gate
validated a p3d the runtime never resolved (LL-145).

Before declaring any build/deploy good:

1. Extract (or listFiles) the DEPLOYED PBO and read the compiled config.bin
   (classnames and paths survive rapification as plain strings).
2. For every `model=` — and every texture/rvmat path the config references —
   verify the path resolves to an entry INSIDE the PBO under its `$PREFIX$`,
   case-insensitive.
3. A second copy of the main `.p3d` at a non-referenced path (typically the
   PBO root) is NOT dead weight: it is the tell of a dirty AddonBuilder temp
   plus a mis-pointed `model=`. Fix the reference and rebuild with `-clear`.
4. Run this on the artifact the engine loads (the deployed PBO), never only on
   the source tree or the build temp.
