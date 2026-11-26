# Path-naming matrix — mechanical check #1

Catches the bug class where a path-helper function and a recovery/cleanup site
disagree on the on-disk filename. The reader looks for a file the writer never
wrote, or vice versa.

Reasoning agents miss this because each helper looks correct in isolation —
the bug is the inconsistency, not any one site.

## Worked example: VULN-003 (LF_VStorage 1.4.6)

`GetContainerTmpPath(sid)` returned `container_<sid>.tmp`. The recovery
boot scan looked for `container_<sid>.lfv.tmp`. Either file naming was
defensible; the bug was that they disagreed. Result: a crash mid-virtualize
left a `.tmp` on disk that recovery never noticed. Six reasoning agents read
both functions and signed off.

## Procedure

### Step 1 — Inventory path helpers

Grep every function that returns a string ending in a recognized extension.
Record name, signature, and exact return template.

```powershell
Grep "function.*Path" --type c --output_mode content -n true
Grep "return.*\.lfv|return.*\.tmp|return.*\.bak|return.*\.json|return.*\.manifest" --type c --output_mode content -n true
```

Build table:

| Helper | Signature | Returns template | File:Line |
|---|---|---|---|
| `GetContainerLfvPath` | `(string sid)` | `<dir>/container_<sid>.lfv` | persistence.c:120 |
| `GetContainerTmpPath` | `(string sid)` | `<dir>/container_<sid>.tmp` | persistence.c:128 |
| `GetContainerBak1Path` | `(string sid)` | `<dir>/container_<sid>.lfv.bak1` | persistence.c:135 |
| `GetContainerBak2Path` | `(string sid)` | `<dir>/container_<sid>.lfv.bak2` | persistence.c:142 |

Inconsistency in the third column is a flag. In the example above, `.tmp`
breaks the `.lfv.<suffix>` pattern.

### Step 2 — Inventory all extension concatenations

Grep every literal that ends in one of the recognized extensions. This
finds places that build the path inline without going through a helper.

```powershell
Grep "\".*\.lfv\"|\".*\.tmp\"|\".*\.bak1\"|\".*\.bak2\"|\".*\.manifest\.json\"|\".*\.virtualizing\"|\".*\.restoring\"|\".*\.quarantine\.json\"" --type c --output_mode content -n true
```

For each hit, record the file/line and what extension is being constructed.
Compare against the helper table. Any mismatch is a finding.

### Step 3 — Cross-reference reader sites against writer paths

For each helper, find every callsite. Group by intent: writers vs readers
(recovery, cleanup, admin commands, boot scan).

```powershell
Grep "GetContainerTmpPath|GetContainerLfvPath|GetContainerBak1Path|GetContainerBak2Path" --type c --output_mode content -n true
```

For each writer/reader pair, the path they construct must be byte-identical.
If the writer uses `helper_A` and the reader uses an inline literal, that is
a flag.

### Step 4 — Output

Findings table:

| Site | Path constructed | Expected (per helper) | File:Line |
|---|---|---|---|
| RecoverFromTmp | `container_<sid>.lfv.tmp` | `container_<sid>.tmp` | recovery.c:84 |
| ... | | | |

Each row is a P0 if the path is on the data-loss recovery branch, P1 otherwise.

## Heuristics for what counts as "extension"

Treat as one extension family per file (so the helper table groups them):

- **Authoritative data**: `.lfv` (or your equivalent main format)
- **Atomic temp**: `.tmp`, `.lfv.tmp`, `.partial`
- **Backups**: `.bak`, `.bak1`, `.bak2`, `.lfv.bak1`
- **Markers**: `.virtualizing`, `.restoring`, `.locked`, `.in-progress`
- **Sidecars**: `.manifest.json`, `.quarantine.json`, `.meta`, `.health`

Pick the family for your codebase and run the matrix once per family.

## Time budget

~5–10 minutes per family on a mod the size of LF_VStorage (≤30 path callsites).
If it takes longer, the codebase has too many inline path constructions —
the audit finding is "consolidate path construction through helpers" before
even checking consistency.
