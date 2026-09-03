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
