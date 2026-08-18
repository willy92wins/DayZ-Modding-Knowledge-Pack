# Proxies, get-in y partes desmontables: el contrato

Extraido de `SKILL.md` (corte 3, 2026-08-15). Aqui vive el DETALLE; el enunciado
corto y cuando leer esto estan en el indice `## ARCHIVO DE LECCIONES` del SKILL.md.
Nada de este fichero esta derogado: son lecciones vigentes, ordenadas por tema en
vez de por fecha.

---

## REGEN-FROM-glTF BODY + PROXY-SPLIT / GET-IN RADIAL + LOD LADDER -> `references/vehicle-structural-parity.md`

Regenerating a high-poly body from glTF/FBX and splitting it into proxies to beat the 65535 resolved-vertex ceiling (glTF->DayZ winding tautology, proxy-placement identity-frame trap, the confirmed model-space + no-`.p3d` + measured-frame convention), and the proxy-body **get-in radial + LOD ladder** (script-module binding, the geometric get-in blocker, the DECISIVE inward-wound seat ComponentNN + point flags `0x0000003F`, reversed-wheel `angle1`, shell+proxy LOD ladder) are structural parity and now live in **`references/vehicle-structural-parity.md`** (Appendix "REGEN-FROM-glTF + GET-IN RADIAL / LOD ladder"). That file is their declared source of truth.

## Proxy placement convention - measured on a working reference car (SP-091, added 2026-07-26)

Two full build+test cycles were burned on LFHeli OH-1 guessing this from the broken model alone.
The answer was one probe away: read a car that WORKS. Reference used:
`SUB_BRZ_dev\_references\Tyson89-Landrover` (MLOD v257, py3d reads it directly, no debinarize).

MEASURED on Landrover.p3d LOD0 (18 proxies):
- **NOT ONE has its anchor at the origin.** Every anchor sits at the real target position:
  `Landrover_Wheel [0.8746, 0.4513, -1.5638]`, `Landrover_Driver_Door [0.888, 0.6492, -0.8629]`,
  `Landrover_Trunk [0.0021, 1.1487, 2.5139]`.
- **NOT ONE has an identity frame (0 of 18).** The standard frame is `[[-1,0,0],[0,0,1],[0,1,0]]`;
  the opposite side mirrors it as `[[1,0,0],[0,0,-1],[0,1,0]]`; the spare wheel uses its own rotation.
- Sub-models are authored in **proxy-local space**, origin at the attachment point:
  `Landrover_Wheel |center| = 0.000 m`, `Landrover_Trunk 0.000 m`,
  `Landrover_Hood 0.726 m` and `Landrover_Driver_Door 0.821 m` (they pivot on their hinge).

RULES:
1. Proxy anchor = target position in HOST coordinates. Anchor at origin is a defect.
2. Sub-model geometry authored near ITS OWN origin (< ~1 m). A sub-model whose bbox center sits
   2-7 m away is authored in host coordinates - that is the defect, and it is the one worth gating.
3. The frame `[[-1,0,0],[0,0,1],[0,1,0]]` is the NORMAL neutral, not a smell: the crew proxies that
   work carry it too. Numerical identity NEVER appears in a working model - forcing it makes
   placement WORSE (verified in-game on OH-1).
4. A zero-size crew marker proxy (~463 bytes) is immune to any frame rotation because its geometry
   sits at the origin. Do not infer the convention from those - use a geometry-bearing proxy.
5. Doors on a working vehicle are PROXIES with their own .p3d anchored at the hinge, not baked
   geometry driven by a bone. Consider that before designing bone-driven doors.

METHOD RULE (the expensive lesson): calibrate every gate rule against a model that WORKS before
trusting it. Three rules were written from the broken model; two were false positives that would
have red-flagged every correct model. The reference car killed both in one probe.

Gates implementing this: `LFHeli_dev\tools\import_gates\proxy_placement_gate.py` (P1 anchor at
origin, P8 sub-model authored in host space, P9 normal/winding coherence) plus
`texture_binding_gate.py` (one .rvmat must not carry two base textures).

## Detachable parts (doors/hood/trunk): the FOUR-layer contract, and three rules it corrects (SP-098, added 2026-07-28)

Measured on a working control, `SUB_BRZ_dev\_references\Tyson89-Landrover` (MLOD v257, py3d reads it
directly). LFHeli OH-1 spent weeks on "the door does not animate" with the full script+model contract
verified, because the project only ever knew layer 3 below.

### The contract is four layers, not one

1. **`CfgSlots`** (`Tyson89-Landrover\scripts\config.cpp:65-77`)
   ```cpp
   class Slot_Landrover_Driver_Door {
       name = "Landrover_Driver_Door";
       displayName = "...";
       selection = "doors_driver";        // <-- the ANIMATION BONE selection
       ghostIcon = "set:dayz_inventory image:doorfront";
   };
   ```
   `selection` is the binding between "the attachment is mounted" and "the proxy is drawn".

2. **`CfgNonAIVehicles` / `ProxyVehiclePart`** (`Tyson89-Landrover\scripts\config.cpp:80-100`) —
   THE LAYER PEOPLE MISS.
   ```cpp
   class ProxyAttachment;
   class ProxyVehiclePart : ProxyAttachment {
       scope=2; simulation="ProxyInventory"; autocenter=0; animated=0; shadow=1; reversed=0;
   };
   class ProxyLandrover_Driver_Door : ProxyVehiclePart {
       Model = "\Landrover\proxy\Landrover_Driver_Door.p3d";
       inventorySlot = "Landrover_Driver_Door";
   };
   ```
   Without it the engine does not resolve the host's `proxy:\...` as an attachment proxy. Note
   `autocenter=0` appears HERE too: vanilla declares it in THREE places - the sub-model's visual
   LOD, the sub-model's Geometry LOD, and this config class.

3. **Item class** `Landrover_Driver_Door : CarDoor` with `Model`, `inventorySlot`, `hiddenSelections`,
   `weight`, `itemSize[]`, `physLayer`, `DamageSystem` (`Tyson89-Landrover\config.cpp:70-95`).

4. **Vehicle**: the slot name inside `attachments[]`, plus `class Doors` in the vehicle DamageSystem.

**Host proxy triangle: DOUBLE membership.** Measured on `Landrover.p3d` LOD0, the 3 points of
`proxy:\Landrover\proxy\Landrover_Driver_Door.001` belong 3/3 to `doors_driver` (the bone) AND 3/3
to `Landrover_Driver_Door` (the slot name). A proxy wired only to the bone animates but is not
attachment-aware.

**A detachable part is a physical ITEM.** It can be dropped on the ground, so its `.p3d` needs real
special LODs, not an empty Geometry. Measured: `Landrover_Driver_Door.p3d` = visual `463/754`,
Geometry `32/24`, Memory `7/0`, ViewGeo `32/24`, FireGeo `72/56`, with `autocenter=0` on the visual
LOD and on Geometry. Budget the item LODs before promising the feature.

Custom inventory slots are the T148506 family (`enforce-script-reference`): if the slot name and the
`inventorySlot` string diverge, the item never attaches and the proxy never draws.

> REDIRECT CAMBIO-1: la corrección de SP-093 ocupa ahora el sitio original de SP-093.

> REDIRECT CAMBIO-1: la corrección de SP-097 ocupa ahora el sitio original de SP-097.

### `binarize` is NOT deterministic - never gate on ODOL byte identity

Two runs of `binarize.exe -always` over the same source, same flags: the shell came out
`2,886,719 b` / `8C290530214C...` and `2,763,097 b` / `0705207DB7F0...`; the interior `1,062,412 b`
vs `1,062,417 b`. The two small rotor models were byte-identical, so the effect scales with model
size. Semantically the two shells match (66/66 `model_info` fields, same faces/selections/properties
per LOD); the divergence is encoding/compression order.

Rule: gates over ODOL compare SEMANTICS (per-LOD counts, selections, properties, proxies, centres),
never bytes. Hash identity is still valid for MLOD, which the pipeline writes itself. Re-read any
historical "the ODOL came out byte-identical" claim with this in mind.

Origin: LFHeli OH-1 2026-07-28, the session that converted doors to proxied attachments after the
user pointed out that a vanilla car only draws the door proxy when the door is attached.

### Two traps that follow immediately from converting a baked part into an attachment

Both bite the moment the part becomes an attachment, and both look like "my model change
broke the vehicle".

**1. A detachable part is INVISIBLE on every debug/admin spawn until something attaches it.**
`CreateObject`, VPP/admin-tool spawns and MCP-style bridge spawns do not populate attachment
slots - that is why a VPP-spawned vanilla car has no wheels. The moment you move a door from
baked hull geometry to an attachment, a spawned vehicle shows an empty doorway, and it reads as
a regression when it is the contract working.

The hook is `OnDebugSpawn()` (`P:\scripts\3_game\entities\entityai.c:3902-3907`, with
`OnDebugSpawnEx(DebugSpawnParams)` delegating to it). Two source-verified patterns:

- explicit `CreateAttachment` per part - `LFQuad.c:176-189`:
  ```c
  override void OnDebugSpawn()
  {
      EntityAI entity;
      if (Class.CastTo(entity, this))
      {
          entity.GetInventory().CreateAttachment("CarBattery");
          entity.GetInventory().CreateAttachment("SparkPlug");
          entity.GetInventory().CreateAttachment("LFQuad_Wheel_Front");
          // ...
      }
  }
  ```
- vanilla car, `CreateInInventory` per part - `P:\scripts\4_world\entities\vehicles\inheritedcars\civiliansedan.c:407-429`
  (`SpawnUniversalParts(); SpawnAdditionalItems(); FillUpCarFluids();` then one call per door/wheel).

The `EntityAI` base implementation is config-driven instead: it reads the type's `attachments[]`
and scans `CfgVehicles`/`CfgMagazines`/`CfgWeapons` for any class whose `inventorySlot` matches,
then `CreateInInventory`s it (`entityai.c:3907-3958`). Calling `super.OnDebugSpawn()` therefore
attaches per-type from config with no per-airframe code - useful when one script base serves
several models. Note the vanilla cars deliberately do NOT call super; they list parts explicitly.

**2. `attachments[]` depende del límite de PBO; `+=` no es una regla incondicional.**
> Historial del texto superado: `history/cambio-1-superseded-family-b-rules.md` §“attachments[] += como regla incondicional”.
Dentro del mismo árbol de configuración fuente, `+=` puede conservar los slots del padre. Cuando la clase padre procede de otro PBO ya compilado, esa lista no es una base contractual segura: materializa en la clase hija la lista COMPLETA de slots vitales y propios. Esto corrige la regla anterior con el caso verificado en `AI/20_Knowledge/dayz-mod-implementation-checklists.md:234-240` (E28).

El gate no busca un token `+=`: inspecciona la lista efectiva después de compilar/config-dump y comprueba batería, ignición, radiador, ruedas y cada puerta/parte declarada. Un cambio de puertas no puede retirar silenciosamente un slot vital. Mantén además la comprobación independiente de que cada parte declarada aparece en la ruta `OnDebugSpawn`; son contratos distintos.

## In-vehicle actions need TWO registrations, and a proxied part is your placement oracle (SP-123, added 2026-07-28)

### An action offered to a SEATED occupant must be registered in two places

Measured on LFHeli OH-1, which spent a build cycle on "the close-door action does not appear
when seated" with the action class already correct.

1. The action must opt in: `ActionBase.InitConditionMask` only sets `ACM_IN_VEHICLE` when
   `CanBeUsedInVehicle()` returns true (`actionbase.c:113`), and the base returns false
   (`actionbase.c:335`). Any world action inherited from `ActionInteractBase` is therefore
   MASKED OUT the moment the player boards.
2. A seated player has no cursor target on the vehicle carrying them, so the target contract
   is `CCTNone` plus `HasTarget()` false - the shape vanilla uses in `actioncardoors.c:20-27`.
3. **Both registrations are required, and the second one is the one people miss:**
   - `ActionConstructor.RegisterActions` - builds the instance into the global pool.
   - `PlayerBase.SetActions(out TInputActionMap)` - `AddAction(MyAction, InputActionMap)`.
     Vanilla puts `ActionOpenCarDoors`/`ActionCloseCarDoors` right there
     (`playerbase.c:1669-1670`).
   Registering only in the constructor builds an action the manager never offers, because
   `FindContextualUserActions` walks the player's `InputActionMap` per input, not the pool.

Vanilla splits inside/outside into separate classes (`ActionCloseCarDoors` vs
`ActionCloseCarDoorsOutside`); copy that split rather than trying to make one class serve both.

**Ship the opening half too.** If entry/exit is gated on the door being open, an inside-only
CLOSE action traps the occupant. Pair it with an inside OPEN action, and keep one exemption in
the gate: a door that is NOT MOUNTED must leave the seat escapable, because no action can open
what is not there.

### A proxied part is the first correctly-placed reference on the host - use it as an oracle

When a host renders wrong, there is usually nothing trustworthy to measure it against. Parts
drawn through attachment proxies are placed by the engine from the entity transform, so they
ARE trustworthy, and the disagreement localises the fault:

- proxies agree with each other and disagree with the host -> **the host is the broken one**.
  Do not "correct" the proxy anchors to match: you would deform the correct piece, and the
  error changes with the host's state.
- On LFHeli OH-1 the doors, both rotors and the interior all followed the aircraft into the
  air while the fuselage stayed at ground level. The doors had just been migrated to proxies,
  and became the reference that finally localised a render bug open since 2026-07-20.

Corollary: `scene_raycast` in `rvproxy` mode returns the GEOMETRY LOD, not the visual mesh, so
it cannot adjudicate a visual misalignment. On a coarse collision hull it reports a surface
tens of centimetres inside the visible skin. Use it for collision questions only.

## (added 2026-08-01) A shared vehicle-core source turns "deploy ordering" gates into fiction

When one Enforce core file serves several vehicle lines (LFHeliCore's `LFHeli_Base.c` serves
OH-1 and HH-60G), any patch in it — even gated by `ConfigIsExisting("vehicleProp")` so only one
line executes it — DEPLOYS whenever ANY line rebuilds the core PBO. A sequencing rule like "do
not deploy the core patch until the model ships its matching memory points" does not survive
the sibling line's next rebuild. Case: LFHeli 2026-08-01 — the OH-1 line rebuilt and deployed
the shared core for its own fixes, and the HH-60G get-in patch went live with it, pointing at
ten `lfheli_con_*` memory points the deployed model does not emit (verified by scanning the
deployed PBO bytes for the patch symbols, not by mtime).

1. A core-side patch that requires a model-side contract (memory points, selections, bones)
   must be RUNTIME-TOLERANT: `MemoryPointExists` fallback to the previous mapping, so the
   patch stays inert until the model actually ships the contract. Deploy-order gates across a
   shared source are not enforceable by anyone.
2. Alternatively, land model and core in the same session/build — never leave a
   contract-dependent patch sitting in shared source "waiting" for its model.
3. When auditing what is live, verify the deployed PBO CONTENT (byte scan for the patch's
   symbols). The sibling line's handoff tells you the core changed; only the bytes tell you
   what rode along.

## Phantom vehicle command blocks ALL vanilla get-in after a client crash while seated (added 2026-08-02)

Symptom: the get-in prompt SHOWS but accepting does nothing - both seats, zero RPT/script-log
trace, and it survives rebuilds because nothing in the mod is broken. Mechanism:
'ActionGetInTransport.ActionCondition' runs on BOTH sides; the CLIENT player (clean) shows the
prompt, but the SERVER-side player still carries a non-null 'GetCommand_Vehicle()' restored
from player storage after a client crash while seated. The first server gate
(actiongetintransport.c:45-48) rejects silently, and a null 'StartCommand_Vehicle' in Start()
(actiongetintransport.c:91-92) produces no log either.

Checklist BEFORE suspecting model/proxies/config for a get-in regression:
1. Check the previous run's client profiles for a 'crash_*.log' - a crash while seated is the
   phantom's birth certificate.
2. With dayz-mcp available: 'query_get_in_condition' returning 'first_block=already_in_vehicle'
   with the player standing in the open = phantom confirmed; 'vehicle_get_in_client' (owner-side
   direct, skips the action gates) seating fine = seat contract and model are healthy.
3. The phantom clears on a clean logout cycle. "It fixed itself next session" is the signature
   of THIS bug, not of a flaky model.

Origin: LFHeli OH-1 gate D 2026-08-02 (GD-1): a full regression gate was misattributed to a
model surgery whose Geometry/ViewGeo/FireGeo/Memory LODs were byte-identical pre/post.

## ViewPilot (1100) of a shell+proxy car MUST carry the body geometry, not only proxy tris (SP-189, added 2026-08-06, SUB_BRZ B-3)

Symptom: on entering the vehicle in FIRST person the body goes invisible for
seconds (vanilla never does). Measured root cause: the shell's 1100 LOD held 7
faces = only the proxy triangles (interior/doors/wheels), zero own geometry,
while the vanilla control (civiliansedan MLOD) carries 11,977 REAL faces there
(interior + body + glass) plus its 13 proxies. The engine switches the shell to
the 1100 on mount; with nothing but proxy anchors in it, the body vanishes
until proxies resolve. The generator's "subset lives in the interior file"
design never materialized as a subset (brz_int 1100 = its full visual LOD).

Fix pattern (fix_b3_viewpilot.py, s45): merge the shell LOD0 into the 1100 —
own geometry with remapped point/normal indices, named selections via
get-or-create (camo/light_* keep working in 1PP), plus the LOD0-only chunk
proxies copied VERBATIM (points+face+selection; add_proxy would lose the
frame). Exclude faces AND anchor points of proxies the 1100 already has.
Gates that must pass: original proxy sels intact (1 face/3 pts), proxy set ==
originals + copied, bone companions cardinality unchanged, facenormals <=
32768, resolved-verts printed vs the ~16k design budget. Binarize preserved
the merge exactly (22,849 faces / 11 proxies in the ODOL).

Applies to every car built by this pipeline (MercedesAMGLF has the same
proxy-only 1100 — same latent defect). Day-1 check for car #2: census the
shell 1100 vs civiliansedan BEFORE first in-game (b3_viewpilot_census.py).
