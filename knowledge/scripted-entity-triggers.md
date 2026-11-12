# ScriptedEntity and trigger events (build 119356)

`ScriptedEntity` is the script-side base for entities that carry their own
collision/trigger volume, and `TriggerEvents` is the vanilla scripted trigger
built on it. This note maps that API: the shape setters, the object-level
enter/leave callbacks, and the server/client event hooks of `TriggerEvents`.
Everything below is source-verified against build `119356`; no runtime
behaviour is claimed, and no vanilla code is copied beyond short signatures.
For placed underground areas see `skills/dayz-underground`; for area hazards
built on synced triggers see `skills/dayz-environment-hazards`. This note is
the API underneath both, not a replacement for either.

## The class

[EXACT][CLAIM-SCRIPTED-ENTITY-CLASS] `ScriptedEntityType : EntityAIType` is declared at `scripts/3_game/entities/scriptedentity.c:8` and `ScriptedEntity : EntityAI` at `scripts/3_game/entities/scriptedentity.c:12`. A scripted entity is therefore an `EntityAI`: it has inventory, networking and persistence machinery whether a given use wants them or not. It is not a bare engine trigger volume, and spawning one means spawning a full entity.

## Collision and trigger shapes

[EXACT][CLAIM-SCRIPTED-ENTITY-SHAPES] The shape enum is `TriggerShape { BOX, SPHERE, CYLINDER }` at `scripts/3_game/entities/scriptedentity.c:1-6`. The shape is selected explicitly; nothing in the class infers it from a model. The setters split into `proto native` declarations and one script wrapper:

| Method | Kind | Effect shown in source |
|---|---|---|
| `SetClippingInfo(vector mins, vector maxs, float radius)` (`scriptedentity.c:21`) | `proto native` | Marked obsolete in its doc comment (`scriptedentity.c:19`); use `SetCollisionBox` instead |
| `SetCollisionBox(vector mins, vector maxs)` (`scriptedentity.c:35`) | `proto native` | Automatically sets `TriggerShape.BOX` (`scriptedentity.c:27`) |
| `SetCollisionSphere(float radius)` (`scriptedentity.c:46`) | `proto native` | Automatically sets `TriggerShape.SPHERE` (`scriptedentity.c:40`) |
| `SetCollisionCylinder(float radius, float height)` (`scriptedentity.c:58`) | `proto native` | Cylinder from the origin up to a positive height (`scriptedentity.c:49`); sets `TriggerShape.CYLINDER` |
| `SetCollisionCylinderTwoWay(float radius, float negativeHeight, float positiveHeight)` (`scriptedentity.c:84`) | script wrapper | Validates, then calls the private native (below) |
| `SetTriggerShape(TriggerShape shape)` (`scriptedentity.c:102`) | `proto native` | Default shape is `TriggerShape.BOX` (`scriptedentity.c:101`) |
| `GetTriggerShape()` (`scriptedentity.c:105`) | `proto native` | Returns the current `TriggerShape` |

[EXACT][CLAIM-SCRIPTED-ENTITY-TWOWAY] `SetCollisionCylinderTwoWay` is the one setter with script-side validation: the wrapper at `scripts/3_game/entities/scriptedentity.c:84-99` rejects `radius <= 0` and `negativeHeight > positiveHeight` with `ErrorEx` and returns early, and only then calls the private `proto native` `SetCollisionCylinderTwoWayNative` declared at `scriptedentity.c:71`. The other setters go straight to native code, so the scripts show no equivalent guard for them; any validation they have lives in the engine and is not visible here.

[EXACT][CLAIM-SCRIPTED-ENTITY-INVENTORY] `ScriptedEntity` overrides `IsInventoryVisible()` to return `false` (`scripts/3_game/entities/scriptedentity.c:107-110`): a scripted entity does not present an inventory in the UI by default, even though it inherits the `EntityAI` inventory machinery.

## Who hears about entry and exit: the entering object

[EXACT][CLAIM-OBJECT-TRIGGER-CALLBACKS] The enter/leave callbacks live on `Object`, not on the trigger: `void OnEnterTrigger(ScriptedEntity trigger) {}` at `scripts/3_game/entities/object.c:92` and `void OnLeaveTrigger(ScriptedEntity trigger) {}` at `scripts/3_game/entities/object.c:95`. Both are empty in the base class, and the parameter is the trigger entity that was entered or left. So the notification direction is "the object that moved is told which trigger it crossed", the inverse of the `TriggerEvents` hooks below, which fire on the trigger itself. A mod that overrides these on the trigger class will never be called through this path.

[EXACT][CLAIM-PLAYERBASE-TRIGGER-DIAG] The one vanilla override is diagnostic only. `PlayerBase` declares `int m_IsInsideTrigger` inside `#ifdef DIAG_DEVELOPER` (`scripts/4_world/entities/manbase/playerbase.c:224-225`), and its overrides `OnEnterTrigger` (`playerbase.c:4772-4777`) and `OnLeaveTrigger` (`playerbase.c:4779-4784`) merely call `super` and increment or decrement that counter, inside the `DIAG_DEVELOPER` block that runs to `playerbase.c:4785`. The counter only feeds a debug draw of the player collision box (`playerbase.c:4733-4742`). In a retail build none of this exists: do not read `m_IsInsideTrigger`, and do not treat the `PlayerBase` overrides as a gameplay hook to copy.

## TriggerEvents: events on the trigger

[EXACT][CLAIM-TRIGGEREVENTS-CLASS] `TriggerEvents : ScriptedEntity` is declared at `scripts/4_world/entities/scriptedentities/triggers/triggerevents.c:3`. Where `Object.OnEnterTrigger` tells the entering object, `TriggerEvents` gives the trigger its own protected event methods plus two invokers other code can subscribe to.

[EXACT][CLAIM-TRIGGEREVENTS-INVOKERS] The invokers are `protected ref ScriptInvoker m_OnEnterInvoker` and `m_OnLeaveInvoker` (`triggerevents.c:5-6`), created lazily by `GetOnEnterInvoker()` and `GetOnLeaveInvoker()` (`triggerevents.c:8-20`): the getter allocates on first use and returns the same instance afterwards. There is no stay invoker; stay is hook-only.

[EXACT][CLAIM-TRIGGEREVENTS-DISPATCH] The dispatchers are `Enter`, `StayStart`, `Stay`, `StayFinish` and `Leave` (`triggerevents.c:26-43`, `:54-68`, `:79-93`, `:104-118`, `:129-146`). Each one runs the same pattern in the same order: first the `Begin` hook, then — for enter and leave only — the matching invoker if it exists, then exactly one side hook chosen by `g_Game.IsServer()` (`OnEnterServerEvent` on the server, `OnEnterClientEvent` otherwise), and finally the `End` hook. `Leave` additionally guards the side test with `g_Game &&` (`triggerevents.c:140`); the other dispatchers test `g_Game.IsServer()` directly. The hook signatures differ by phase: enter and leave hooks take the `TriggerInsider`, stay hooks take the insider plus a `float deltaTime`, `StayStart` hooks take an `int nrOfInsiders`, and `StayFinish` hooks take no arguments (`triggerevents.c:44-47`, `:69-72`, `:94-97`, `:119-122`, `:147-150`). All hooks are empty `protected` methods in the base class, so a subclass overrides only the phases and sides it needs. Because the side is chosen per call, the same trigger instance runs its server hooks on the server peer and its client hooks on each client peer; a hook is not replicated to the other side by this class.

## Vanilla subclasses, as patterns

[EXACT][CLAIM-SCRIPTED-ENTITY-USAGE] Four shipped subclasses show the intended range of the base. `UndergroundTriggerCarrierBase : ScriptedEntity` (`scripts/3_game/triggercarrierbase.c:1`) is the carrier the underground system moves trigger data with; its placed-area behaviour is covered by `dayz-underground`, not here. `DynamicArea_Flare : ScriptedEntity` (`scripts/4_world/classes/contaminatedarea/dynamicarea_flare.c:2`) is a falling dummy entity for contaminated-area announcements, an effect carrier rather than a volume. `SpookyPlayerStalker : ScriptedEntity` (`scripts/4_world/classes/contaminatedarea/spookyareamisc.c:324`) is attached per player inside its area and carries a temperature source; the hazard design around it belongs to `dayz-environment-hazards`. `TestFramework : ScriptedEntity` (`scripts/3_game/systems/testframework.c:212`) uses the base as a plain scripted world object with init/frame event masks, with no trigger shape involved at all. Read together: the base serves as trigger volume, effect carrier and generic scripted object, and only the first of those uses the shape API.

## Gotchas

- `ScriptedEntity` is an `EntityAI` subclass, not a generic trigger volume; spawning costs a full entity.
- Shape selection is explicit: the `SetCollision*` setters set the `TriggerShape` as a side effect, and the default is `BOX`. Picking the wrong setter changes the volume, not just its numbers.
- Only `SetCollisionCylinderTwoWay` validates in script. The native setters show no script-visible guard, so pass them checked values.
- `OnEnterTrigger`/`OnLeaveTrigger` fire on the entering object; `TriggerEvents` hooks fire on the trigger. Overriding the former on a trigger class does nothing through this path.
- The `PlayerBase` trigger overrides are `DIAG_DEVELOPER`-only debug counters, absent in retail.
- Server and client hooks are separate methods selected per call by `g_Game.IsServer()`; implementing only the server hook leaves client peers silent, and vice versa.

## Limits

The scripts show declarations, dispatch order and the one script-side validation; they do not show how the engine detects overlap, how often insiders are evaluated, or whether a `proto native` shape setter is linked in a given build. Those are engine behaviour and are not claimed here. Whether the debug-draw counter or the dispatchers behave as read has not been measured in game.
