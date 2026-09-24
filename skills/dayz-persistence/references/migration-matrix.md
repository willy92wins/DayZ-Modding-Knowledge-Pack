# Persistence Migration Matrix

## Normative seven cells

Every reader result exposes four outputs: verdict, bytes consumed, state
preserved, and action. The case name is the input class, not a fifth output.

| Case | Verdict | Bytes consumed | State preserved | Action |
|---|---|---:|---|---|
| `fresh` | `ok` | `0` | defaults | write current header |
| `legacy-no-header` | `ok_legacy` | all bytes in the old format | fully migrated | read legacy, write new after backup |
| `known-version` | `ok` | bytes declared by the header | complete | none |
| `future-version` | `reject` | `0` | intact | do not write; log rate-limited |
| `truncated` | `reject` | `0` applied | intact | discard partial; preserve evidence |
| `same-dayz-build-new-mod-version` | `ok_migrate` | bytes declared by the old header | migrated | migrate by mod version, not game build |
| `rollback-old-reader` | `reject_forward` | `0` | intact | old reader rejects; do not delete |

The bytes-consumed field reports bytes accepted into the result contract, not
how far a low-level cursor moved before detecting failure. A truncated parser may
inspect or consume bytes internally, but it reports `0` applied and commits no
staged values.

## Cell contracts

### `fresh`

No persisted record exists. Initialize defaults and write the current header on
the next explicit save. Do not describe malformed or empty existing bytes as
fresh.

### `legacy-no-header`

Recognize the old grammar explicitly, read it completely into staged state,
validate it, then migrate. Rewriting is permitted only after a backup. A parse
failure is not legacy success.

### `known-version`

Read exactly the fields and lengths declared by the recognized header. Apply
only after the complete record validates. Trailing, missing, or wrongly typed
bytes are not known-version success.

### `future-version`

Reject fail-closed before applying state. Preserve the bytes unchanged, write
nothing over them, and emit at most one reasoned diagnostic per rate-limit
window. A future record is degradation by rejected compatibility, not proof of
corruption.

### `truncated`

Reject the entire record. Discard every staged field, preserve the pre-load
state, and retain the source as recovery evidence. Consuming a valid prefix does
not make the prefix valid state.

### `same-dayz-build-new-mod-version`

The DayZ build can remain unchanged while the mod payload changes. Select the
migration using the mod's own header or CF `storageVersion`, consume the complete
recognized old payload, validate it, and then apply migrated state.

### `rollback-old-reader`

Declare the old reader's behavior against data emitted by the new writer. It
returns `reject_forward`, applies no bytes, preserves the new record, and does
not delete or rewrite it. A format proposal without this downgrade behavior is
incomplete.

## Transversal write rule

`reject`, `reject_forward`, and any other rejecting verdict never write. They do
not auto-save defaults, repair in place, delete the source, or overwrite the
record with the current version. `ok_legacy` and `ok_migrate` may schedule a
rewrite only after the full migration validates and a recoverable backup exists.

Before changing a format, present an equivalent design that leaves the format
unchanged when one provides the same value. If a change remains necessary,
declare legacy read behavior and rollback behavior in the same proposal.

## Mutation check

A fixture is evidence only if the test can be made to fail:

1. Record the expected four outputs for each of the seven cells.
2. Mutate one byte that controls classification, version, length, or payload
   validity.
3. Run the same reader without changing the expected result.
4. Confirm the verdict changes for all seven mutated fixtures.
5. Read each changed result to ensure the mutation reached the intended parser
   boundary rather than causing an unrelated harness error.

An error, distance, or mismatch of exactly `0.000` against an unmutated fixture
is suspicious. It can mean the fixture and oracle share a source, the mutation
never reached the reader, or the verifier measured nothing. It is not proof of
correctness.

## Release checklist

- All seven case names exist exactly once.
- Every case asserts verdict, bytes consumed, preserved state, and action.
- Future, truncated, and rollback cases commit no state and perform no write.
- A future-version diagnostic is rate-limited by case and window.
- Legacy and migration rewrites are gated by complete validation and backup.
- Mod payload compatibility is independent from the DayZ build.
- Seven deliberate byte mutations change seven verdicts.

## DayZ 1.30 Exp (build 1.30.164014) — worked cells

The seven cells above stay normative for **mod** formats. Vanilla 1.30 does
not implement all seven for every new field. Classify each 1.29→1.30 input
explicitly; do not infer a migrate from a version bump alone.

| Input | Case | Verdict | Bytes consumed | State preserved | Action |
|---|---|---|---|---|---|
| `CombinationLock` saved on 1.29 (`version` 142) | `legacy-no-header` relative to the third int; engine treats it as known-minus-field | `ok` | two ints after `super` | `m_CombinationInside` stays default | skip `m_CombinationInside` (`version >= 143` false). Verified: `exp\scripts\scripts\4_World\Entities\ItemBase\CombinationLock.c:169-177`. 1.29 writer: `stable-1.29\scripts\scripts\4_World\Entities\ItemBase\CombinationLock.c:90-97`. |
| `CombinationLock` saved on 1.30 (`version` 144) | `known-version` | `ok` | three ints after `super` | complete | read `m_CombinationInside`. Writer always emits the third int (`CombinationLock.c:128-136`). |
| Old CombinationLock reader (1.29 binary) vs 1.30 save | `rollback-old-reader` | `reject_forward` / desync | 1.29 reader never consumes the third int | 1.30 record intact on disk | 1.29 `OnStoreLoad` stops after two ints (`stable-1.29\scripts\scripts\4_World\Entities\ItemBase\CombinationLock.c:99-129`). Later attachments in the same world bin misalign. Do not ship a 1.29 lock subclass against a 1.30 world. |
| `PlayerBase` saved on 1.29, loaded on 1.30 MP | `truncated` (vanilla does **not** gate) | `reject` | thermal `ctx.Read` fails | pre-load player state | print `---- failed to load ThermalBiasHandler, read fail  ----` (`PlayerBase.c:7520-7524`). Not `ok_legacy`. |
| `PlayerBase` saved on 1.30 MP | `known-version` | `ok` | one float after arrow manager | complete | `ThermalBiasHandler.c:67-77`. |
| `DigitalCodeLock` on a 1.29 world | `fresh` | `ok` | `0` | defaults | class did not exist; no legacy record. |
| `BaseBuildingBase` 1.29 fence | `known-version` | `ok` | three ints + bool after `super` | complete | suffix unchanged (`BaseBuildingBase.c:420-429`). |
| `Rebuilding` stored version `< REBUILDING_STORAGE_VERSION` | vanilla rejects as invalid | `reject` | `0` applied after the version int fails the `<` check | intact | `Rebuilding.c:519-525`. |
| `Rebuilding` stored version `>` current | vanilla **accepts** | (violates this matrix's `future-version` cell) | ten ints | applied | `[DESIGN]` do not copy. `m_LastStorageVersion < REBUILDING_STORAGE_VERSION` only. |
| Missing `$mission:BunkerBroadcastPersistenceStorage.bin` | `fresh` | `ok` | `0` | scheduler/handler defaults | `Load()` returns `false` when `Open` fails (`BunkerBroadcastHandler.c:56-68`); constructor still installs empty objects (`:29-34`). |
| Present bunker `.bin` | `known-version` **without a header** | vanilla returns `true` after `Open` even if `Read` fails | whole objects or partial | applied | `file.Read` bool ignored (`:61-65`; `Serializer.c:58`). Classify as vanilla exception, not a model. Schema change has no `legacy`/`future` branch. |

Bodies and `[EXACT]` copies:
[dayz-1-30-persistence.md](dayz-1-30-persistence.md).
