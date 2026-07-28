# Vanilla Entity Stream Contract

## Scope

Use this contract only when the mod owns both the data and the entity, the data
is naturally part of that entity's save stream, uninstall survival is not
required, and outside-game inspection is not required. Otherwise return to the
router in `../SKILL.md`.

The engine hooks are `EntityAI.OnStoreSave(ParamsWriteContext)` and
`EntityAI.OnStoreLoad(ParamsReadContext, int)` returning `bool`
(`VANILLA/3_game/entities/entityai.c:2925`; `VANILLA/3_game/entities/entityai.c:2989`). The stream has no field names or
random access: correctness is the exact sequence of typed writes and reads.

## Normative write/load order

A subclass writes in this order:

1. Call `super.OnStoreSave(ctx)` so the base class owns the prefix.
2. Write every subclass field in one declared order and with one declared type.
3. If the subclass has an independent mod schema, write its own header inside
   its portion of the stream; do not reinterpret the hook's build version.

A subclass loads in this order:

1. Call `super.OnStoreLoad(ctx, version)` and return `false` if it returns
   `false`.
2. Read subclass fields sequentially in the exact save order and types.
3. Check the boolean result of every `ctx.Read` and return `false` on the first
   failure.
4. Stage values separately. Commit them to entity state only after every read
   and validation succeeds.

This propagation and fail-closed read behavior follows the vanilla contract at
`VANILLA/3_game/entities/entityai.c:2969-2985`. A load that consumed some bytes
before failure is still a failed load; byte consumption does not authorize
partial state.

## Version unit

The `version` argument is the DayZ save/build version produced by
`g_Game.SaveVersion()` (`VANILLA/3_game/global/game.c:434`). Vanilla subsystems
use storage-version gates at
`VANILLA/4_world/classes/playerstomach.c:255` and
`VANILLA/4_world/classes/playermodifiers/modifiersmanager.c:170`. These build
checks describe engine compatibility; they do not version a mod release.

## Variable-width super trap

`EntityAI.OnStoreSave` conditionally writes nine energy-component fields when
`m_EM` exists and writes none when it does not
(`VANILLA/3_game/entities/entityai.c:2928-2959`). Therefore the base prefix width
is a runtime property.

A reader that seeks to a remembered offset, skips a fixed number of fields, or
assumes that `super` always consumed the energy fields is wrong. With the
component absent it reads the subclass's first value as a base value and then
fails or misinterprets later bytes. Let the real `super.OnStoreLoad` advance the
context by the width that the matching base save wrote; begin subclass reads at
the resulting sequential position.

This trap applies even when a fixture with the component present passes. Test
both component-present and component-absent streams against the same reader.

## Failure and ownership boundaries

- A wrong type, truncated field, failed base load, failed subclass `ctx.Read`, or
  trailing-layout mismatch rejects the load and preserves the pre-load state.
- Never convert a failed read into defaults and then report success. Defaults
  are valid only for an explicitly classified fresh or legacy case.
- Saving and loading must call `super` in the same relative position. Reordering
  the subclass prefix changes the wire contract.
- The stream belongs to the entity. If the mod that appended bytes disappears,
  no remaining handler understands or re-emits those bytes. Use CF ModStorage
  when uninstall/reinstall survival is a requirement.

## Verification checklist

- Save and load order and types are identical.
- `super` is propagated before subclass fields.
- Every `ctx.Read` result is checked.
- State mutation happens only after the complete read succeeds.
- Both optional-component widths are exercised.
- The hook build version is not presented as the mod's format version.
- Uninstall behavior is declared rather than implied.
