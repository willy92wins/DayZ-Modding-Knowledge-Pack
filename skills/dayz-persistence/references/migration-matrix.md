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
