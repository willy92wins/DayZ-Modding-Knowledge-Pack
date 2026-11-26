# Atomic-to-phased conversion traps

Trigger this audit whenever a correctness-critical synchronous rebuild or
recount becomes multi-tick/incremental over shared live structures.

[EXACT][CLAIM-R21-RDA-INCREMENTAL-REBUILD] Enumerate the following three defect
classes before approving the conversion:

1. **Lost update through a non-gateable mutator.** Classify every concurrent
   mutator as gateable (for example an RPC handler) or non-gateable (for example
   an engine lifecycle hook). A non-gateable mutator touching a partially
   rebuilt live structure requires either retaining the synchronous rebuild or
   shadow-building and atomically swapping. A gate that postpones an entity
   death/deletion lifecycle is not a valid fix.
2. **Non-idempotent retry.** If a batch can throw before its cursor commits and
   its per-item effect is a raw increment, retry re-applies the completed
   prefix. Commit per item, make the effect a set, or re-clear before retry.
3. **Stuck-flag blast radius.** Grep every consumer of the in-progress flag. A
   stuck flag can freeze unrelated synchronization or maintenance paths, not
   only the phased job.

Also audit iteration stability. A phased job that keeps a cursor into a live
map can skip or repeat keys when concurrent deletion shifts enumeration. A key
snapshot plus per-key lookup avoids that cursor drift; a shadow structure plus
atomic swap is stronger when the rebuilt index itself is authoritative.

Do not misclassify this automatically as on-disk data loss. Session-only maps
that self-heal after restart are correctness corruption/degradation with an
explicit recovery horizon; persisted structures can raise the severity.

## Evidence

- `AI/20_Knowledge/lessons-learned.md:3209-3215`
- `AI/10_Projects/LF_PowerGrid/bug-ledger.md:367-374`
- `AI/30_Sessions/2026-07-23-lfpowergrid-T4-implementation-gates.md:20-27`

The case produced all three defects after converting an atomic reverse-index
rebuild into 16-owner batches. The accepted correction restored the critical
index rebuild to synchronous atomic operation and retained phased work only
over a key snapshot.
