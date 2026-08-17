# Tooling inventory, the seam, and the walls

Where every tool lives on the sandbox/GUI seam, the verified walls, and signing. Sources are the fase-0 research (2026-05-20), labelled [VERIFIED] (primary source read) or [TBD-verify] (secondary/single source).

## Tool inventory

| Tool | Does | Where it runs | Source |
|---|---|---|---|
| `model.cfg` / `config.cpp` editing | config-driven animation (Layer 1) | sandbox (Claude) | [VERIFIED] PMC wiki |
| `scripts/seanim_writer.py` (this skill) | write SEAnim from keyframes | sandbox (Claude) | open SEAnim spec |
| Blender headless (`bpy`) | author/edit keyframes | sandbox (Claude) | [VERIFIED] Blender |
| **DayZATool** (DTZxPorter) | `.anm` extract→SEAnim and SEAnim→`.anm` (`--generate-anim`) | Windows, closed binary, .NET 4.5 | [VERIFIED] dtzxporter.com/tools/dayzatool |
| **Arma3ObjectBuilder** (MrClock8163) | Blender 4.2+ addon, RTM import AND export | Windows, interactive Blender | [VERIFIED] github.com/MrClock8163/Arma3ObjectBuilder |
| ArmAToolbox (Alwarren) | older Blender RTM export | Windows, interactive Blender | [VERIFIED] github.com/AlwarrenSidh/ArmAToolbox |
| **FBXToRTMGui.exe** | FBX → `.rtm` | Windows, ships with DayZ Tools | [VERIFIED] BI wiki FBX_to_RTM |
| `jdfnc24/DayZAnimationPluginDemo` | Blender → `.txa`/`.txo` | Windows, interactive Blender | [VERIFIED] github.com/jdfnc24/DayZAnimationPluginDemo |
| **Workbench** (DayZ Tools) | compile `.txa`→`.anm`, `.txo`→`.xob` | Windows GUI | [VERIFIED] DayZ Tools, Steam 830640 |
| `4d4a5852/rtm_import` | read RTM into Blender (import only, no write) | Windows, Blender 2.80 | [VERIFIED] github.com/4d4a5852/rtm_import |
| SEAnim Blender plugin (SE2Dev) | import/export SEAnim in Blender | Windows, interactive Blender | [VERIFIED] github.com/SE2Dev/io_anim_seanim |
| Addon Builder / Publisher (DayZ Tools) | PBO pack, sign, Workshop upload | Windows GUI | [VERIFIED] DayZ Tools |

## The two formats (do not conflate)

- **RTM** — legacy Real Virtuality. Used for config-driven prop animation and legacy man animations. Binary, reverse-engineered (BI wiki carries an explicit "internal undocumented, use may violate BI rights" notice). Authored via Blender (Arma3ObjectBuilder) or FBX→FBXToRTM.
- **`.anm` / `.txa`** — Enfusion. Used for character/infected/animal and weapon animations. `.txa` is text, compiled by Workbench to binary `.anm`. Bridged from the open **SEAnim** format via DayZATool.

DayZ Standalone runs a hybrid engine — characters go Enfusion (`.anm`), config-driven props go RTM. Most community confusion comes from mixing the two routes.

## The walls [VERIFIED]

1. **One animation mod at a time.** Only one mod modifying player/creature animations can load; two crash the client/server. Enfusion engine limit, not policy. Flag on every character/creature-anim plan. (Confirmed across multiple Workshop mod descriptions.) Does NOT affect config-driven object animation.
2. **RTM is reverse-engineered.** No open-source RTM writer in pure Python exists; only Blender plugins write RTM. The format spec is community RE, not an official contract — it can change between engine versions.
3. **`.anm` is proprietary.** DayZATool writes it but is a closed binary with its own EULA. No open-source `.anm` writer.
4. **Skeleton bone names are exact.** Target is `OFP2_ManSkeleton`; any mismatch logs `Error: Bone X doesn't exist in skeleton OFP2_ManSkeleton` and the bone does not animate. [VERIFIED] BI forums.
5. **Cannot restructure the vanilla skeleton.** You can overlay animations on vanilla bones; adding/removing bones breaks vanilla anim compatibility. [TBD-verify: community consensus, no primary BI doc read.]

## Signing and deploy (Layer 3, user/computer-use)

All mod PBOs must be signed (bikey/bisign) via DayZ Tools. Animation mods are no different. See the vault runbook `AI/20_Runbooks/dayz-mod-build-sign-deploy.md`. None of this runs in the sandbox.

## What to hand the user

When Claude produces a Layer 2 intermediate (a SEAnim file, a `.txa`, a Blender `.blend`), the handoff MUST state:
- the exact converter command/tool the user runs next (e.g. `DayZATool --generate-anim my.seanim`),
- the target skeleton and that bone names must match,
- the one-mod-anim wall if it is a character/creature anim,
- that signing + in-game test are still required.

Never imply Claude ran Workbench / FBXToRTM / DayZATool in-sandbox — it cannot.

## [2026-06-28] Weapon-anim corrections (verified)

### CORRECTION to wall #1 — it is the GRAPH-replacement wall, not a weapon-anim wall [VERIFIED-vanilla]

Wall #1 above ("one animation mod at a time") applies ONLY to mods that REPLACE the player/creature animation GRAPH (`player_main.aw`/`.agr`, e.g. Expansion-Animations). Custom WEAPON animations authored via the ASI route do NOT touch the graph and are **conflict-free across mods** — multiple weapon-anim mods coexist. The ASI route binds per-item through Enforce Script (`AddItemInHandsProfileIK(itemClass, asi, behavior, ikPose.anm, weaponStates.anm)` at `dayzplayer.c:243` + `AddItemBoneRemap`) and a per-weapon `.asi` parent chain — it never edits `.agr`/`.aw`. Do NOT warn about the one-anim-mod wall on a custom-weapon-animation plan; it is a false blocker. (Vehicles are the unsupported exception.)

### Plugin/Blender-version split — the maintained fork inverts the version requirement [VERIFIED]

The tool table lists `jdfnc24/DayZAnimationPluginDemo` (original) which needs **Blender 3.6.8–4.0** (on ≥4.1 it throws `AttributeError: 'Mesh' object has no attribute 'calc_normals_split'`). The **MAINTAINED Sanitoeter05 fork** is the opposite — it calls Blender 4.4+/5.x APIs (`action.fcurve_ensure_for_datablock`, `generate_fcurves_bl51`) and will NOT run on 3.6.8; its `bl_info` `'blender': (2,80,0)` is meaningless, do not trust it. Always check the import code's API calls against your Blender version before choosing. Install = manual folder copy into `…/scripts/addons/DayzAnimationTools` (the download is a plain folder, NOT a zip — "Install from file" fails).

### `.txa` → Workbench is the canonical PLAYER weapon route [VERIFIED]

For a playable-character weapon animation use Route A (`.txa` via the DayZAnimationPlugin → Workbench compiles `.anm`), as the JD demo and community do. SEAnim/DayZATool (Route B) is a fallback — its extracted rig is a reference, NOT a clean round-trip (community: extracted rigs "always wrong" for empties/IK-helper bones). RTM is the #1 wrong turn — never use it for a player weapon anim.
