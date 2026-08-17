# Weapon in hands — grip, ADS and the weapon-side memory-point contract

How a custom weapon sits in the player's hands is decided by THREE things, only
one of which lives in the weapon `.p3d`:

1. **Player-side `.anm` IK** (via the weapon's ASI — `player_main_rifle.asi`,
   `weapons/player_main_akm.asi`, …) poses the hands. A weapon `.p3d` carries
   **NO hand memory points** — verified against debinarized vanilla
   `DZ\weapons\firearms\akm\akm.p3d` memory LOD (2026-06-11): zero hand/grip
   selections present. Cross-ref `player-skeleton.md` (`RightHand_Dummy`, IK
   helpers) and `anim-graph.md` (ASI catalog).
2. **The weapon's frame**: the engine anchors the model's ORIGIN to the hand
   (`RightHand_Dummy` / `Weapon_Root` chain). The origin→grip and
   origin→handguard relations of the vanilla weapon whose anims the custom
   weapon inherits ARE the grip contract. If the custom grip/handguard occupy
   the same model-space region as the reference's, the inherited `.anm` hands
   land correctly.
3. **The memory-point pattern** in the weapon `.p3d` (fire/eject/axes/ADS).

So grip verification = geometric parity vs the reference weapon, in the same
model space. That is what `scripts/weapon_grip_viewer.py` renders and checks.

## Vanilla rifle memory-point catalog [VERIFIED-vanilla, AKM]

Source: memory LOD of debinarized `akm.p3d` (coords rounded, model space,
muzzle towards −X, Y up). Semantics marked [TBD-verify] are pattern-consistent
but not confirmed in engine docs — keep the vanilla shape unless verified.

| Name | Pts | AKM data | Semantics |
|---|---|---|---|
| `eye` | 1 | (0.23, 0.15, −0.01); **5.2 cm above bore, on bore Z** | ironsights/ADS camera anchor |
| `usti hlavne` | 1 | (−0.4331, 0.0976, −0.0102) | muzzle tip (Czech "barrel mouth"); muzzle flash + projectile exit |
| `konec hlavne` | 1 | (−0.0252, 0.0976, −0.0102) | rear end of barrel. **Same Y/Z as usti** — together they define the bore/fire line |
| `nabojnicestart` / `nabojniceend` | 1+1 | dir = up+right+REAR | shell ejection path |
| `bolt_axis` | 2 | **parallel to bore** | bolt/charging-handle travel |
| `trigger_axis` | 2 | lateral (±Z) axis at trigger | trigger anim axis |
| `magazine_axis` | 2 | vertical-ish (−Y) | mag anim axis [TBD-verify exact use] |
| `recoil` | 2 | duplicates magazine_axis coords | recoil axis [TBD-verify] |
| `weapon back` | 1 | (0.0712, 0.0976, −0.0102) — ON the bore line | rear anchor [TBD-verify — back-holster?] |
| `ce_center` / `ce_radius` | 1+1 | — | central economy placement sphere |
| `invview` | 1 | — | inventory preview camera |
| `boundingbox_min/max` | 1+1 | — | bounds |

Invariants worth enforcing on any custom rifle (each was violated by a real
AI-generated build, MK47 2026-06-11, and caught by the checker):

- `usti hlavne` and `konec hlavne` must share Y and Z (level bore). The MK47
  had konec 4.6 cm high → fire line tilted 6.3°.
- `bolt_axis` parallel to the bore.
- `magazine_axis`/`recoil` orientation should match the reference family
  (vertical-ish on AKM; the MK47 had them lateral = 90° off).
- eject direction within ~25° of the reference (MK47: 42° off, no rearward
  component).
- `eye` height over bore close to the reference (~5 cm for AKM irons); a
  rail-height eye changes the ADS camera.

## The grip viewer / validator

```bash
python3 scripts/weapon_grip_viewer.py \
  --weapon MyRifle.p3d --ref ref_mlod/akm_mlod.p3d \
  --ref-label "AKM vanilla" --out grip_viewer.html --report grip_report.json
```

- Inputs MUST both be MLOD and in final model space (offsets applied). If the
  reference is binarized, run `dayz-p3d-debinarizer` first.
- CLI prints the checklist + findings (usable headless / in CI); HTML adds:
  custom mesh + translucent reference ghost, both memory-point sets, bore and
  ADS lines with deviations, world-origin axes (the hand anchor), and
  **estimated** hand zones derived from the reference (grip = below/behind
  `trigger_axis` mid; support hand = handguard proxy anchor or 55% along the
  bore). Hands are estimates — the real pose is the player `.anm`; the honest
  check is grip/handguard overlap with the ghost.
- Viewer follows LL-overlay-vs-lighting (unlit overlays) and strips proxy
  triangles from LOD0 (they render as giant spikes otherwise).
- Three.js 0.147 UMD from jsdelivr (proven offline-tolerant in this pipeline);
  self-test with Puppeteer per R1 before delivering to the user.

## Hand-fit / global-offset pattern (worked example: A6_MK47)

When the custom weapon inherits a vanilla base (e.g. `A6_AKM_Base` → AKM
anims), parity is achieved by translating the WHOLE model (geometry + memory
points + proxies) by a single global offset so its bore/grip match the
reference's relation to the origin — never by moving the grip alone. The MK47
assembler applies `GLOBAL_OFFSET` (+0.0326 Y, −0.0102 Z, derived from
usti-hlavne parity with the AKM) exactly once at assembly. Verify offsets are
applied ONCE (double-offset is the classic failure; see the project HANDOFF
guard pattern) and re-run the grip viewer on the final `.p3d` out of the PBO.

## ikpose wrist rotation does NOT override the geometric grip [VERIFIED-SR2M 2026-06-17]

The grip contract above is geometric. A corollary proven in-game on the A6_SR2M (a custom SMG with no
hand memory points, inheriting AKS74U anims): **rotating the `LeftHand` wrist bone in the ikpose does
NOT reorient the support hand.** The ASI/IK realigns the hand to the weapon and absorbs the wrist
rotation. Tested with 4 ikpose variants rotating `LeftHand` 90° on different local axes (120–180°
apart): all render identically in-game; a pixel-diff of the hand region gave a 180° wrist roll = RMS
7.8, LESS than a finger-curl change (RMS 11). What the ikpose DOES drive visibly is the **finger curl**
(`LeftHand{Thumb,Index,Middle,Ring,Pinky}*`), not wrist orientation.

Implication: to change how the support hand is ORIENTED on a custom weapon you cannot just rotate
`LeftHand` in the ikpose — pursue geometric parity instead (an anim-of-reference whose hand already
sits that way, checked with `weapon_grip_viewer.py`; or adjust weapon geometry/offset). A diff of two
vanilla ikposes (e.g. OTS-14 `normal` vs `barrelhandle`) can show a `LeftHand` delta, but that delta
exists because both poses were authored against a weapon that HAS grip parity — it does not mean
rotating `LeftHand` on a non-parity weapon reproduces it. Do not over-generalize that diff.

## Testing ikpose / grip variants in-game without confounds [SR2M 2026-06-17]

- **Compare grades on the SAME weapon.** Clone the real weapon (a `CfgWeapons` class deriving from it)
  once per ikpose variant and register each clone to its own `.anm` via `AddItemInHandsProfileIK`.
  Comparing variants across DIFFERENT weapons confounds the hand — each weapon's balance/handguard moves
  it, swamping the pose difference you want to read.
- **When the visual difference is subtle, don't trust the eye — pixel-diff it.** RMS-diff the hand
  region between variants and against a known-visible change (e.g. a finger-curl change) to separate
  signal from capture noise (lighting/timing). On the SR2M a 180° wrist roll diffed LESS than a
  finger-curl change → the wrist wasn't moving the render.
- **Capture conditions:** fully overcast scene (`overcast=1.0`) kills the specular glint that washes
  the weapon white; capture all variants quickly (short give-weapon cycle) so exposure doesn't drift
  between them; in a multi-weapon cycle keep the per-weapon settle timeout < the cycle period or
  captures desync (land on the next weapon).

## Geometric parity IS the grip fix — raise the weapon to the hand (added 2026-06-23) [VERIFIED-SR2M in-game]

End-to-end in-game result on the A6_SR2M that confirms the two sections above ("ikpose wrist rotation does
NOT override geometry" + "Hand-fit / global-offset pattern"). After EVERY player-side lever was proven inert
in-game (ikpose IK-target pos/rot, behavior flag, `LeftHand` FK — iter22-32), the grip was fixed by the
GEOMETRY: the SR2M bore sat **2.4 cm LOWER over the weapon origin** than a working reference (KarmaKrew's
SR-2M, bore Y0.090 vs the SR2M's 0.066), so the support hand (lands at a fixed skeleton-space point) fell ON
TOP of the barrel. Translating the WHOLE model +Y0.024 (global-offset pattern) raised the weapon INTO the
hand → the support hand closed on the foregrip. **Idle grip perfect in-game.** Rule: when IK-target moves are
inert, stop tuning the anim — move the WEAPON to the hand (raise/translate geometry to where the ikpose
lands), not the hand to the weapon.

### Working mods use STOCK vanilla ikposes + geometry parity — NOT custom anim mods [RE KarmaKrew]
Reverse-engineered a server pack (workshop 2864245850) showing a closed foregrip grip. The whole technique is
the plain `AddItemInHandsProfileIK(class, rifle-parent-asi, FIREARMS-behavior, VANILLA-ikpose, states)` — the
grip lever is choosing a vanilla IK-driven ikpose (`vikhr.anm`, `pm73_ik.anm`) whose `LeftHandIKTarget` lands
where the weapon PHYSICALLY HAS a handguard. NO custom player-anim mod, NO base-pose override, NO script bone
manipulation. This refutes the "needs a full player-anim mod" pessimism: a custom weapon gets the grip from
(a) firearms behavior, (b) a stock vanilla ikpose, (c) geometry where that ikpose lands.

### The ikpose is SHARED across stances — fixing idle does NOT fix aim [SR2M]
The 4th-arg ikpose applies to ALL stances. The base raised pose differs per stance
(`Locomotion.<stance>Ras.{Idle,Aim,AimingDownSight}`); the aim entries add the aim-space additive
(`p_rfl_erc_aimspace.anm`, shared rifle anm) which OPENS the support hand. So a geometry/ikpose combo that
closes the IDLE grip can still leave the AIM grip open (hand detaches, weapon front "floats"). You cannot
close only-aim by tuning the shared ikpose's wrist roll without also rotating the (already-good) idle.
Per-stance fix = override the weapon's aim/ADS `Locomotion` entries in a custom `.asi` (the parent rifle
`.asi` DOES map them; per-weapon asis can override them — proven in the KarmaKrew/BastardAnims RE).

[RESOLVED 2026-06-23 gate iter37] On the SR2M the worry did NOT materialize: the SAME geometry raise that
closed the idle ALSO closed the aim (forced-raise gate, 3rd-person — support hand closed on the foregrip,
comparable to KK, user-confirmed). The per-stance `.asi` override was NOT needed — lifting the weapon into
the hand feeds BOTH stances because both base poses anchor the support hand to the same weapon-relative
zone. Treat the `.asi` per-stance override as the FALLBACK, only if a future weapon still shows aim-open
after the idle is closed.

### Forcing the aim stance for gate capture — must be CLIENT-side [VERIFIED-SR2M gate iter36→37]
To capture/validate the AIM grip from a scripted/spawned player, force the raise each frame with
`p.GetInputController().OverrideRaise(HumanInputControllerOverrideType.ENABLED, true)` (`scripts\3_game\human.c:249`;
enum `:7-12` — ENABLED persists, ONE_FRAME flickers and drops to idle). CRITICAL: it MUST run CLIENT-side, NOT
in the server mission `init.c`. The captured character is the client's OWN local player; a server-side override
does not move the pose the client renders for it (iter36: server logged `raised=1` but the weapon rendered
LOWERED). Ship it as `modded class MissionGameplay { override void OnUpdate(...) { ...GetGame().GetPlayer()... } }`
in a gate mod (declare a `missionScriptModule`). The 3rd-person aim pose is gated purely on `IsRaised()`
(`dayzplayerimplement.c:1726`, AimingModel) → a held raise is enough; do NOT call `SetIronsights()` (forces the
ironsight camera, fights an MCP free-cam, and server-side left the weapon untextured). `WeaponADS()`
(`human.c:86`) is an INPUT flag with no script override (`human.c:234-255`) → always 0 even when ADS works; the
success signal is `IsRaised()` / the client log, not `WeaponADS()`. Keep a matching server-side OverrideRaise so
the server agrees. Full recipe + drop-in snippet: `dayz-mcp-verify`.

### Refines "RMS-diff it": RMS only on FULL-RES crops; the eye on full-res is the verdict
The "don't trust the eye — RMS-diff it" advice above is RIGHT only if the RMS runs on a FULL-RES hand crop.
On the SR2M a whole-panel RMS over a DOWNSCALED contact sheet (support hand ~30 px) made me wrongly call a
working grip "inert" — the user's eye on the full-res image caught the closed grip the thumbnail hid. RMS is
a coarse "did anything change" filter, NOT a "is it correct" verdict. Always crop the hand zone from the
full-res per-angle grab and LOOK. (See LL-153; the gate now auto-emits a full-res `_handcrop`.)

<!-- a6_sr2m grip: parity-raise fix + KarmaKrew RE + shared-ikpose-stances + force-aim + fullres-review refinement | 2026-06-23 -->

## Cross-references

- `player-skeleton.md` — hand/IK bones the `.anm` poses (`RightHand_Dummy`,
  `LeftHandIKTarget`, `Weapon_Root`).
- `anim-graph.md` — ASI chain that picks the `.anm` per weapon and state.
- `item-ik-and-hide.md` — `AddItemInHandsProfileIK` (the same reuse idea for
  heavy items).
- `dayz-p3d-debinarizer` / `dayz-p3d-inspector` — get MLOD + edit memory
  points when the checker finds anomalies.

## [2026-06-28] The ASI binding path for a custom weapon anim [VERIFIED-vanilla]

A custom WEAPON animation reaches the player through THREE decoupled artifacts bound per-item via Enforce Script — none of which edits the player graph (`.agr`/`.aw`), so the route is conflict-free across mods (the one-anim-mod wall does NOT apply; vehicles excepted):

- `AddItemInHandsProfileIK(itemClass, asi, behavior, ikPose.anm, weaponStates.anm)` — `dayzplayer.c:243` (5-arg). Binds the weapon classname to its `.asi` + a one-time IK pose + a weapon-states `.anm`.
- `AddItemBoneRemap(itemClass, pairs[])` — maps the weapon's p3d/model.cfg part selections to the player skeleton's `Weapon_*` bones.

Do NOT conflate the three artifact kinds (verified frame data, see `references/weapon-anim-blender-complete.md`):

| Artifact | What it is | Vanilla AKM | Where referenced |
|---|---|---|---|
| **IK pose** (`#ikpose`, `ik/weapons/<wpn>.anm`) | ONE distinct static hand/finger placement on the gun | 2 frames @30fps but frame 1 = byte-exact dup of frame 0 (= 1 pose); AKM reuses izh18's pose (`player_main_akm.asi:5`) | `.asi` `#ikpose`; 4th arg of `AddItemInHandsProfileIK` |
| **Weapon-states** (`w_<wpn>_states.anm`) | bolt/bullet driver of only the `Weapon_*` bones | 2 distinct frames @30fps (`Weapon_Bolt` slides, `Weapon_Bullet` ejects) — NOT a fixed 3; Workbench trims to 2–4 keys/channel | 5th arg of `AddItemInHandsProfileIK`; `SetInitState` reads it |
| **Action anims** (reload/fire/chamber/jam) | additive deltas (≈shoulders-down) blended on idle | mag-remove 22f, full swap 55f, reloadAction 44f, chambering 107f, fire 11f, jam 230f — all @30fps | `.asi` `$animations` map |

The `.asi` `$animations` blend ON TOP of the weapon-states `.anm` and override those bone transforms. The IK-pose chain itself is configured in the `AnimNodeWeaponIK` graph node (`combat.agr:24-30`, the `ikpose_*` keys), not in any config file. `reloadAction` (CfgWeapons) is LEGACY/obsolete and NOT how reloads are driven here — omit it (all vanilla rifles do).


## [2026-06-28] Reproducir el agarre en un viewer OFFLINE - los factores + el pipeline Blender [VERIFIED]

Cierre de la sesion WeaponAnimPipeline #8/#9 (visor para AUTORAR anims de arma). Que determina el agarre y como reproducirlo offline sin heuristicar.

### Los factores que fijan el agarre (vanilla + mod) - la lista completa
1. **Anclaje**: el arma se monta por su ORIGEN de modelo en `Weapon_Root`/`RightHand_Dummy` (bone del esqueleto). El `.p3d` del arma NO tiene puntos de mano (verificado arriba contra `akm.p3d`).
2. **Manos = el ikpose del arma** (4 arg de `AddItemInHandsProfileIK`). Verificado extrayendo `sr2m_grip.anm` (DayZATool): 43 huesos que keyean los IK helpers (`RightHandOrigin`/`LeftHandOrigin`/`LeftHandIKTarget`/`*ForeArmDirection`) + los dedos, **NO** los `LeftHand`/`RightHand` crudos (coincide con el caveat de `player-skeleton.md:53`). El SR2M HEREDA el ikpose del aks74u.
3. **Geometria arma<->origen = "mueve el ARMA a la mano"** (geometric parity, documentado abajo). La mano cae en un punto fijo del ikpose; se traslada la geometria del arma (global offset) para que su grip caiga ahi. Un SMG corto (grips pistol<->foregrip ~0.18 m) NO tiene paridad con la mano de RIFLE (~0.33 m) -> la mano de soporte no agarra hasta hacer parity.
4. **Stance/aim**: el aditivo de aim-space (`DZ/anims/anm/player/layered/aim/2handed/p_2hd_erc_aimspace.anm`, 39 frames = grid 2D de direcciones) al **frame CENTER (idx 19) = NEUTRAL** (max 0.7 grados, casi todo 0.0). Implicacion VERIFICADA: NO hay una "pose ADS" aparte que sumar al centro - la pose base `Rifle_Erect_Idle_Ras (Soft_Aim).txa` YA es el aim alzado in-game al centro; el aditivo solo desvia al apuntar arriba/abajo/lados.

### Pipeline Blender VALIDADO para LEER el agarre real offline
Rig con IK bones `_AssetSamples/Poses/Rifle/M4 Rifle IK.blend` (155 huesos; constraints reales `RightHand IK->RightHandOrigin`, `LeftHand IK->LeftHandOrigin`) -> aplicar la pose base `.txa` (plugin) + el ikpose de agarre (accion del plugin, sus bones IK-helper) -> el IK del rig RESUELVE las manos sobre el arma -> leer las transformaciones mundiales (`Weapon_Root`, manos, dedos). Patron en el script `dump_combined.py` de la sesion (combina base+ikpose, lee 155 worlds). La base `Ras (Soft_Aim)` da config de manos de rifle ~0.33 m (M4 ikpose combinado = 0.326 m -> confirma que la base YA es la config de rifle).

### El gate honesto (por que no cierra del todo offline)
Aplicar el ikpose ESPECIFICO de un arma (su `.anm`/SEAnim) directamente offline choca con el gate de convencion bone-frame del proyecto (las ROTACIONES; solo in-game lo cierra). El `Weapon_Root` del rig JD "No IK Bones" da el canon "cruzado"/boca-abajo posado (medido); el rig CON IK bones (M4) lo posa bien -> usar ese. **NO heuristices** (orientar el arma por el eje de dedos, Rx(-90) en la muneca de soporte, nudges forward): probadas ~8 variantes, todas fallan o no generalizan (ver LL-171).

### Herramientas + ground truth
- DayZATool CLI: `--extract-anim <input.anm> <scale=100>` (SIN output path; escribe `.seanim` junto al input; `--generate-anim` el inverso). El aim/ikpose vanilla esta desempaquetado en `DZ/anims/anm/player/layered/aim/{rifle,2handed,...}`.
- Ground truth in-game YA capturado (no re-lanzar a la ligera = ~10-15 min retail + 5 GB): `A6_SR2M_dev/_gate/captures/mcp_s0_proj_ads_orbit_i37.png` + `_handcrop_i37.png` (agarre RESUELTO, support hand cerrada en el foregrip, user-confirmed; fix = geometry raise +Y0.024). Re-correr: `A6_SR2M_dev/_gate/gate-mcp.ps1 -Retail`.

### Reproduccion correcta en el viewer (para PARTIR de la pose correcta y animar)
Modelo: pose base (= aim alzado) + arma en `Weapon_Root` con su geometria de PARIDAD + manos en la config del ikpose (no fit-a-manos heuristico). Para que el viewer sea editable: `applyPose()` debe reconstruir desde la pose base FK (no T-pose) - ver el fix `basePoseQ`/`basePoseP` de la sesion.

## [2026-06-28] The IK-resolved grip is NOT offline-derivable - READ it off the live skeleton [VERIFIED-SR2M]

Closes WeaponAnimPipeline s4. The offline ikpose resolution (sections above) nails the HANDS (the ikpose's IK-target positions are static data), but the ELBOW is engine-IK-resolved at runtime from the forearm-direction pole and is NOT cleanly derivable offline: the plugin's Blender IK pole gives a winged elbow, and a naive swivel guess was the OPPOSITE direction (right elbow guessed +tuck, true measured -81.7 deg OPEN; left +50.4). Do NOT eyeball-iterate it.

Authoritative source = dump the live player skeleton (model space):
- API (verified): `int idx = player.GetBoneIndexByName("RightForeArm")` (`human.c:1387`, used on the player at `dayzplayerimplement.c:625`); `vector p = player.GetBonePositionMS(idx)` + `player.GetBoneRotationMS(idx, float q[4])` (`object.c:243,248`). MS = relative to the player entity -> pose independent of world position/facing.
- Mechanism: a CLIENT-side `modded class MissionGameplay` that force-raises (`OverrideRaise(ENABLED)`, `human.c:249`) and, once `IsWeaponRaiseCompleted()` + ~120 frames settle, Prints each bone MS pos+quat ONCE. The Print lands in `client_profiles\script_*.log` (NOT the `.RPT`). Launch with the retail SR2M gate (`A6_SR2M_dev/_gate/gate-mcp.ps1 -Retail`, slot 0 = production SR2M = pm73_ik).
- Enforce gotcha: build the Print string in single-line statements (`ln = ln + ...`); a multi-line `+` expression is a compile error (R11g family). `-packonly` PBO rebuild + retail (the A6 weapon pack fails DayZDiag strict-compile).
- game-MS -> Three.js viewer: position `(x, y, -z)` (z-flip, Enfusion LH -> Three RH). The quaternion z-flip `(-x,-y,z,w)` rendered MIRRORED -> reconstruct from POSITIONS (solid), not raw quats. Clean fix: keep the offline-resolved pose (perfect hands) and compute the EXACT elbow-swivel angle landing the resolved elbow on the measured in-game elbow (same shoulder+hand => elbow lies on the swivel arc; solve the signed angle about the shoulder->hand axis - lands within ~5 mm, hands untouched).

Reusable for ANY engine-IK-resolved pose (vehicle rider, heavy-item carry, hide-on-attach IK): static config gives positions; the IK-resolved joints get READ from the game. See [[LL-172]].

## (added 2026-07-05) Cross-ref: an ikpose keys synthetic IK-targets; the viewer authors curl + parity

A real ikpose keys 8 IK bones -- LeftHandIKTarget, RightHandIKTarget, LeftHandOrigin, RightHandOrigin, LeftForeArmDirection, RightForeArmDirection plus their Origin -- alongside all fingers and _Dummy. Verified by extracting A6_AnimRTTest\animations\sr2m_grip.seanim (43 bones). It does NOT key the raw Arm-ForeArm-Hand bones; the hand is placed by the IKTarget, the elbow by the ForeArmDirection. The weapon-anim viewer rig ("No IK Bones") lacks those 8, so a native ikpose export must SYNTHESIZE them -- non-trivial; prefer a vanilla ikpose plus geometric parity. Full model and grip-authoring flow: references\weapon-anim-authoring-viewer.md (section added 2026-07-05) and WeaponAnimPipeline_dev\reviews\2026-07-05-flujo-agarre-con-visor.md.
