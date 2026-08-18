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
7. **Promote only a green commit.** `~\.claude\skills\` is the working
   copy (where agents edit and load). The public repo is a publication
   snapshot harvested by UNION, never a wipe. Plugin trees are ephemeral.

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
