# AnswerOverflow community findings — Model pipeline (mined 2026-05-17)

Source: DayZ Modders Discord (serverId 452035973786632194), via AnswerOverflow MCP. All findings here are MEDIUM-confidence community reports — flag in audit reports, do not treat as canonical.

---

## MDL-1. Binarize misaligns p3d meshes tagged as `personality`

**[OPEN BUG — community-reported, unresolved]**

Symptom (Zen, bracelet in glove slot):
- Mesh attached to glove slot, marked as `personality` in the p3d's named selections.
- Looks correct un-binarized (in Object Builder / Buldozer).
- After running through DayZ Tools binarize: mesh misaligns with the body arm — translated/rotated relative to its un-binarized position.
- `model.cfg` extracted from the binarized p3d matches the original — issue is downstream of model.cfg, in the binarizer itself.

Likely candidates:
- BiTools binarizer 1.29 regression (see PBO-1 about Mikero's tools).
- Bone weight or pivot data being recomputed incorrectly during binarization.

**Action when auditing a misaligned clothing/accessory mod:**
1. Open the binarized `.p3d` (via `dayz-p3d-debinarizer`) and compare bone weights vs source.
2. Try packing with an older DayZ Tools build (community baseline: Aug 14 exp patch — see `mdl-3` in FINDINGS.md, low confidence).
3. Repack with AddonBuilder rather than Mikero's tools.

Source: Zen — https://www.answeroverflow.com/m/1498490570996322315

---

## MDL-2. Nested proxies on binarized models can disappear in-game

**[OPEN BUG / ENGINE LIMITATION — community-reported]**

KOPYkAT's case: modded car part armor system.
- Car door `.p3d` is binarized (vanilla shipped).
- Custom armor `.p3d` (unbinarized) declares the binarized car door as a proxy.
- In-game: the proxy disappears — only the armor renders, no door physics.

Workarounds tried that did NOT fix it:
- Using `proxy:` declaration in the unbinarized model.
- Attaching the door .p3d as a proxy with manual placement.

Workaround that DID work (but with caveats):
- Use the car door's attachment slot system — declare the armor as an attachment.
- BUT: this doesn't transfer the physics/collision of the original door; behaves as cosmetic attachment.

**Open question** in the thread: how to "bake" a proxy into a new `.p3d` without an attachment slot. No resolution.

**Hypothesis:** Engine restricts nested proxies referencing binarized roots — likely because the binarized child cannot reflow its bounding/collision metadata when wrapped in an unbinarized parent.

**Action when auditing:** if a mod has missing visual parts AND uses proxies on binarized vanilla models, flag this issue.

Sources:
- KOPYkAT — https://www.answeroverflow.com/m/1502157615390658560
- KOPYkAT (earlier Q) — https://www.answeroverflow.com/m/1498549372726677646

---

## MDL-3. Maya Object Builder alternative — community plugin

**[COMMUNITY TOOL — Maya 2027]**

targaryen built an Object Builder replacement for Autodesk Maya 2027, open-sourced at https://github.com/SXDIST/Maya-ObjectBuilder. PySide 6 UI. Useful for modelers already working in Maya who want to skip the Object Builder round-trip.

Key design choices (taken from targaryen's notes):

- **Memory points** implemented as Maya Locators, converted to MLOD Memory points on export. (Maya has no native equivalent of OB Memory points.)
- **Named selection → bone assignment** via Maya groups (one group per selection).
- **No Workbench dependency** for the p3d export step.

Status as of 2026-05: alpha. Bugs being actively fixed. May not handle all vanilla LOD edge cases yet.

Useful when:
- User's primary 3D software is Maya (e.g. ex-game-industry modelers).
- Wanting to avoid Blender's add-on / Object Builder round-trip.

Source: targaryen — https://www.answeroverflow.com/m/1502200911387431075

---

## Mining metadata

- Server: DayZ Modders (id 452035973786632194), 14498 members.
- The two open-bug findings (MDL-1, MDL-2) are useful as **red flags during p3d audit** — if a user reports misalignment after binarize or missing proxies on binarized models, point them at these threads.
- One LOW-confidence finding from the mining run (DayZ Tools build stability — Aug 14 vs Oct 31 vs Dec 1) was dropped from this reference per user instruction (HIGH+MED only). See `FINDINGS.md` in the mining tmp dir if needed.
