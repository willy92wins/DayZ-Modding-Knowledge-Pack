# Contributing

Contributions are welcome when they preserve the pack's evidence, licensing
and privacy contracts.

## Required workflow

1. **Discover before generating.** Search the current pack, vanilla scripts,
   official documentation and relevant upstream projects before creating a
   competing rule or tool.
2. **Map the source.** Add or update the corresponding entry in
   `sources/source-map.json`. Pin revisions and hashes; never use modification
   time as authority.
3. **Register executable claims.** A new API, signature, command, schema field
   or engine claim needs a `claim_id` in `sources/claims.json`, with exact
   evidence and verification level.
4. **Label examples.** Use `[EXACT]` only for content verified against the
   cited source. Use `[DESIGN]` for pseudocode or a proposal that still needs
   implementation-specific verification.
5. **Test the smallest contract first.** Add positive and negative fixtures
   before implementation. Then run `python -m packctl gate --root .`.
6. **Check licensing and privacy.** Do not add third-party payload until its
   license is known and compatible. Never commit secrets, personal identities,
   machine-specific absolute paths, private PBOs or proprietary game data.
7. **Promote only a green commit, and edit at the source.** For any skill listed in
   `promotions/promotion-map.json`, **this repo is the editable source**: edit
   `skills/<name>/`, reseal `sources/source-map.json`, and land a commit with
   `packctl validate` green. The live user tree and the plugin trees are promotion
   TARGETS — a hand-edit there is exactly what `PROMOTION-TARGET-UNEXPLAINED` exists to
   catch, and it blocks the next promotion for every session, not just yours. Skills
   absent from the map are unaffected: edit those in the live tree.

   *Direction fixed 2026-09-04.* This point used to call the live tree "the working copy
   where agents edit", which contradicted the workflow doc and left every session to guess.
   The tie-breaker is that `packctl` enforces this direction with executable gates
   (`SOURCE-HASH-MISMATCH`, `PROMOTION-TARGET-UNEXPLAINED`) and nothing enforces the other:
   a document without a gate loses to a gate. The public repo is still a publication
   snapshot harvested by UNION, never a wipe; plugin trees remain ephemeral.

## Evidence rules

- Verify DayZ/Enforce APIs in the real source for the targeted build and cite
  `path:line`; a search result alone is not evidence.
- Distinguish `runtime_verified`, `source_verified`, `offline_tested`,
  `cross_checked`, `historical` and `unverified`.
- Record unknowns as unknowns. Do not turn project history into a current
  runtime guarantee.
- Keep crash, exception, corruption, degradation and cosmetic findings
  distinct.
- Persistent or network-format changes must document legacy reads, rollback
  behavior and a non-format-changing alternative when one exists.

## Licensing boundary

Original contributions are accepted under the repository MIT license.
Preserve the upstream py3d MIT notice. GPL, DPL-ND, CC-NC, proprietary
Workshop content and Bohemia game data may be cited or studied, but are not
accepted as release payload in this repository.

## Privacy boundary

Use public aliases such as `VANILLA`, `VAULT` and `SKILL_SOURCE` in versioned
files. Physical roots belong only in ignored local configuration. The request
to avoid redistributing private paths is a contribution and release policy,
not an additional restriction on the MIT license.

## Change discipline

Keep each change traceable to a product criterion and avoid adjacent
refactors. Update `CHANGELOG.md`, the compatibility matrix and durable
evidence when the change affects them. A release candidate must build twice
to a byte-identical ZIP before promotion.

## Concurrent governed-skill maintenance

This section is the unique authority for authoring, validating, promoting,
session versioning and rolling back skills listed in
`promotions/promotion-map.json`. It does not repeat the seven required-workflow
steps above; those still apply.

Governed skills have one editable source: this repository. Skills present in a
user tree but absent from the promotion map are non-governed. They keep their
own authority. Do not add them to this pack silently.

### Isolate the change

Give each skill change its own branch and Git worktree. Do not share a dirty
index across concurrent edits of governed skills.

### Review, validate, then commit

Review the branch, run `python -m packctl validate --root <repo> --report
<report-outside-the-repo>` on that worktree, and commit. `python -m packctl
gate --root <repo> --report-dir <dir-outside-the-repo>` is the publish gate;
its report directory must sit outside the repository. Promotion reads a clean
commit. A dirty tree fails `promote --check` with `PROMOTION-DIRTY`. Confirm
the current flags with `python -m packctl promote --help`.

### Isolated schema-2 bootstrap

[EXACT][CLAIM-PACKCTL-PORTABLE-PROMOTION-V2] A first promotion into empty destinations uses `--bootstrap`, not `--check`.
`--bootstrap` is mutually exclusive with `--check`, `--apply` and `--recover`.
Confirm the current flags with `python -m packctl promote --help`.

1. Copy `promotions/local-targets.example.json` to a gitignored contract
   (default path `promotions/local-targets.json`). Keep `schema_version` `2`.
2. Set `installation_id` to a new canonical lowercase UUID v4 (version nibble
   `4`, variant `8`, `9`, `a` or `b`; `uuid.UUID(value)` must round-trip to the
   same string). Do not reuse an id that already has a receipt.
3. Create `backup_root` and each `targets.*.path` as existing empty directories
   you own. Routed artifact destinations may be absent or empty. `--bootstrap`
   rejects non-empty backups (`PROMOTION-BACKUP-NONEMPTY`) and non-empty or
   type-mismatched artifact destinations (`PROMOTION-TARGET-NONEMPTY` /
   `PROMOTION-TARGET-TYPE-MISMATCH`). Linked parents fail closed.
4. `--bootstrap` requires `--plan` and local-target contract v2. It also
   requires zero receipts for that `installation_id`
   (`PROMOTION-INSTALLATION-EXISTS` otherwise). Historical v1 receipts for other
   installations are not that set.

```text
python -m packctl promote --bootstrap --root <repo> --promotion-map promotions/promotion-map.json --local-targets <local-targets.json> --plan <plan.json>
```

Inspect the written plan before apply: `schema_version` `2`, the same
`installation_id`, `bootstrap` true, the full map, and each operation's
`after_digest`. Then apply that same plan of that same commit:

```text
python -m packctl promote --apply --plan <plan.json>
```

`--apply` takes the plan; it does not take a second copy of the map. After
apply, read the new receipt under `promotions/receipts/` and confirm destination
bytes match each `after_digest`. Register that receipt (and any other new
tracked file) in `sources/source-map.json` and land a commit. There is no
`packctl reseal` command; the owner writes the source-map entry.

Later promotions of that installation use `--check` of the full map, then
inspect the plan, then `--apply`. `--bootstrap` is only the genesis of an
installation with no receipts for that UUID.

### Check, then apply

Run `python -m packctl promote --check` with `--promotion-map` and
`--local-targets` set to explicit paths before `--apply`. `--apply` requires
`--plan` from a green check of that same commit. After apply, read the receipt
under `promotions/receipts/` and confirm destination bytes match the plan
`after_digest`. Register the receipt in `sources/source-map.json` and commit;
there is no `packctl reseal` command.

`--recover` (requires `--transaction-root`) restores a failed or interrupted
apply to the preimage recorded in that transaction. It is not a rollback to a
previous skill version.

### Session pin

A promote that overwrites a live skill target does not freeze sessions already
running, and it does not rewrite context the agent has already loaded.

Per session, record the source commit and consume a copy of the **whole**
governed skill tree taken from an immutable snapshot of that commit. A hash
without those files is not a pin. A copy does not make an agent load it.
Consumer procedure for `dayz-mod-workflow`:
`skills/dayz-mod-workflow/references/concurrent-session-snapshot.md`.

### Version rollback

`python -m packctl promote` walks the full `promotions/promotion-map.json`.
There is no per-artifact selector, so a version rollback is a full-map
`--check` then `--apply` of an older commit, recorded as a **new commit**.
Keep the installation's receipts and the same `installation_id`. Do not
`git reset` the promotion history or delete receipts to pretend an apply did
not happen.

Inspect every destination in that plan. Destinations whose planned
`after_digest` equals their current bytes must keep that digest. Do not claim
a per-skill rollback.

`--recover` (requires `--transaction-root`) finishes or aborts one
incomplete apply back to that transaction's recorded preimage. It is not
version rollback.
