# Weapon fire modes (single / burst / full-auto)

Extracted from `enforce-script-reference/SKILL.md` on 2026-07-07 (F3 sectioning).

Config-side fire-mode inheritance for DayZ weapons: when to inherit vs override `class SemiAuto`/`FullAuto`, and the `Mode_*` root-scope forward-declaration trap (SP-031). Cross-ref: SP-038 troubleshooting row in `dayz-pbo-build`.

---

## (added 2026-06-26) Fire modes en armas DERIVADAS: heredar, no redeclarar sobre una base que ya los define

En un arma que hereda de OTRA arma que YA define sus modos (`class SemiAuto`/`class FullAuto`), NO redeclarar las subclases de modo con parent explícito (`class FullAuto: Mode_FullAuto`): eso re-deriva desde la base abstracta `Mode_*` y el engine puede quedarse con 1 modo válido. Síntoma in-game: el arma solo dispara semi, la tecla de modo (X por defecto) no cicla, y no aparece el nombre del modo en el HUD. En su lugar:
- Heredar los modos sin tocarlos (no declarar `modes[]` ni las subclases), o
- Override SIN parent: `class FullAuto { soundSetShot[]=...; reloadTime=...; }` → MODIFICA la heredada (conserva su autofire), solo cambia lo que pongas.

Redeclarar CON `: Mode_*` solo es correcto cuando heredas de `Rifle_Base` (que no predefine los modos), como hacen las AK del pack A6 (a6_ak_config.cpp:354-390).

Mecanismo verificado (vanilla 1.2x, `P:\scripts`):
- Conteo de modos = config `modes[]` + subclases válidas.
- Cambio de modo = input nativo `IsFireModeChange()` (tecla X por defecto) → `GetWeaponManager().SetNextMuzzleMode()` (`4_world\entities\dayzplayerimplement.c:1088`).
- Nombre de modo en HUD = `GetCurrentModeName()` (`4_world\classes\weapons\weaponmanager.c:1335` → `5_mission\gui\itemactionswidget.c:584`); cadena vacía = el engine ve 1 modo.
- El perfil de animación del player (`pType.AddItemInHandsProfileIK(class, .asi, behaviorCfg, ik.anm, weaponStates.anm)` en `dayzplayercfgbase.c:408+`) y el `behaviorCfg` (`SetFirearms`/`SetPistols`/`SetToolsOneHanded` → `ItemBehaviorType`, def. `dayzplayercfgbase.c:167-239`) NO controlan el conteo de modos; pero registrar un arma con `RegisterOneHanded` sí la hace comportarse como herramienta de una mano (sin selector).

Anti-confabulación: una "base protegida" cuyo `config.bin` "no se puede leer" debe VERIFICARSE desrapificando con `CfgConvert -txt` antes de asumirlo. Caso A6_PP19 (2026-06-26): el config.bin se desrapifica entero y ya traía `modes[]={"SemiAuto","FullAuto"}` — la suposición "protegido/single-mode" era falsa.

### `Mode_*` (Mode_SemiAuto/FullAuto/Burst) van en scope RAÍZ, NO dentro de `class CfgWeapons` (SP-031, added 2026-06-29)

Caso de fallo distinto del anterior (no es redeclarar la subclase, es declarar mal el `Mode_*` base). Las clases de modo vanilla (`WeaponMode_Base`{autoFire=0}, `Mode_SemiAuto`, `Mode_Burst`, `Mode_FullAuto: Mode_SemiAuto` con `autoFire=1`) se definen en **scope RAÍZ** del config (vanilla `bin.pbo` config.cpp:260/273/307/310), ANTES de `class CfgWeapons` (l.347) — son **hermanas** de CfgWeapons, no están dentro. Forward-declarar `class Mode_FullAuto;` **dentro de `class CfgWeapons`** crea un `CfgWeapons.Mode_FullAuto` vacío que **eclipsa** al real → cualquier `class FullAuto: Mode_FullAuto` hereda ese stub **sin `autoFire`** → el engine descarta el modo → arma single-mode (solo semi, sin selector ni nombre de modo en HUD).

- **Cómo reconocerlo**: arma con `modes[]={"SemiAuto","FullAuto"}` correcto que in-game SOLO dispara semi, pese a config byte-idéntica a otra que sí cicla. Engañoso: CfgConvert/binarize NO se queja (un forward-decl es un external válido) y el de-rap se ve perfecto. La verdad está en el source vanilla (`bin.pbo`), no en comparar configs de mods.
- **Fix**: forward-declarar `class Mode_SemiAuto;` / `class Mode_FullAuto;` en **scope RAÍZ** (encima de `class CfgWeapons`, igual que `class OpticsInfoRifle;`). Entonces `class FullAuto: Mode_FullAuto` resuelve al real (`autoFire=1`). Discriminador de diagnóstico: un clon que hereda de un arma-base YA-resuelta cicla, mientras tu base que referencia `Mode_*` no → aísla la causa a la resolución de `Mode_*` (NO al modelo).

Origen: A6_SR2M bug#10, 2026-06-28, confirmado in-game (~12 ciclos sin la lección). Cross-ref: SP-038 (fila de troubleshooting en `dayz-pbo-build`), LL-174, `20_Knowledge/dayz-weapon-config-crossproject.md` INV-W1.
