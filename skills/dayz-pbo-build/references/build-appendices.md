# DayZ PBO — Build Appendices (session findings)

Extracted from dayz-pbo-build/SKILL.md 2026-07-07 (F3). Dated session appendices (2026-06-11) kept out of the core for length. The core skill links here from its "Build appendices" index line.

---

## Mandatory post-build PBO verification (added 2026-06-11)

Origin: LFSlidingFloor session 2026-06-10 — AddonBuilder reported "Build Successful" with a 613-byte PBO (its internal sync to temp copied 0 files, probably collision with OneDrive); additionally the measured PBO was RESIDUE from a previous build (cf. LL-135) because AddonBuilder names PBO according to source FOLDER, not according to -prefix.

Checklist after EACH build (exit 0 and "Build Successful" are NOT enough):
1. PBO size larger than a reasonable threshold (a script mod is around 15-30 KB; ~600 B = packed empty folder; cf. memory "2 KB PBO = model fell off").
2. Content: binary grep of expected strings (names of .c files, a RECENT code literal to detect residue): PowerShell `[Text.Encoding]::ASCII.GetString([IO.File]::ReadAllBytes($pbo)) -match "my_marker"`.
3. Name: PBO outputs as `<SourceFolderName>.pbo` — if you build from staging, the folder MUST be named exactly like the mod (e.g. `C:\Temp\<Mod>\`), or you will deploy and measure the wrong file.
4. Local staging (outside OneDrive) for build source: AddonBuilder sync against OneDrive paths can copy 0 files without reporting error.
5. PROPERTIES gate after `ExtractPbo` — SHA is not enough: a hash manifest compares the same file on both sides, so gives green even if packed `.p3d` were built BEFORE property entered generators. Measured case (LFHeli HH-60G, 2026-07-29): `autocenter=0` was added to visual LOD of hull in both generators at 01:52/02:07, PBO was packed at 02:15 from previous `.p3d`, and manifest gave green; upon measuring the 48 extracted `.p3d`, the 8 sub-models had it and **the 40 hulls did not**. The gate must read the specific property **per LOD**, with expectations declared in table (property, expected value, reason, explicit exclusions — e.g. Memory LODs, having no geometry to recenter, are excluded). A gate only comparing hashes cannot turn red from this cause.
6. Model-count gate from the PBO ENTRY TABLE — size alone passes a model-less PBO: measured 2026-09-13 (SUB_BRZ s91), a build with exit 0 and "Build Successful" packed an 8.0 MB PBO with 132 entries and ZERO of ten `.p3d`, because the stage path carried the addon folder name higher up (`...\s91_stage0\stage\SUB_BRZ`); renaming only the stage's parent folder produced full PBOs again (21.5 MB, 140/140 entries, 10/10 ODOL). The `<4096 B` size gate misses it, and the SP-069 "`-temp` must stay under the work drive" explanation did not reproduce in four later builds with `-temp` outside the work drive (work drive mounted): re-measure before trusting either explanation of a tiny or model-less PBO. Count the `.p3d`/ODOL entries of the built PBO against the stage before trusting any build. [EXACT] (measured, SP-394]

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
