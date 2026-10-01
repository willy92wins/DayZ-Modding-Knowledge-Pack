# Framing checklist format

An entry is `{"q": "<question>", "view": "<framing>"}` and may declare `"skip": "<reason>"`. Framing is the name of the image against which that question is evaluated, not a hint inside a contact sheet. An entry with `skip` remains visible as data, but is not sent to model or scored.

## Minimal example

```json
[
  {"q": "Are cylindrical parts smooth and round rather than visibly faceted polygons?", "view": "zoom_muzzle__front_iso", "skip": "Requires a deterministic facet report."},
  {"q": "Is the object sitting on the ground plane rather than floating above it or sunk into it?", "view": "assembled__profile_L"}
]
```

`q` is the text that the model sees and what is written to `answers[].q` of shadow-log when entry is active. `skip` is a non-empty reason and excludes entry from both consumers; does not substitute one question for another or delete it from file.

The `view` token is **subject+view** (`assembled__iso`, `zoom_muzzle__front_iso`), the first two segments of the file `<subject>__<view>__<subject>__<version>.png`. It is not just the view (`iso`, `profile`). Reason: `profile` exists as view of `zoom_mag` (`zoom_mag__profile__zoom_mag__v1.png`) and lateral views of assembly are `profile_L` / `profile_R`. A `profile` or `iso` token does not distinguish `assembled__profile_L` from `zoom_mag__profile` (nor `assembled__iso` from `body__iso` / `hg__iso`) and reintroduces the original bug: question would be evaluated against wrong framing.

This checklist uses four tokens, all taken from real inventory (none invented):

| view | fichero |
|---|---|
| `assembled__iso` | `assembled__iso__assembled__v1.png` |
| `assembled__profile_L` | `assembled__profile_L__assembled__v1.png` |
| `zoom_receiver__right_iso` | `zoom_receiver__right_iso__zoom_receiver__v1.png` |
| `zoom_muzzle__front_iso` | `zoom_muzzle__front_iso__zoom_muzzle__v1.png` |

The file retains **8 entries** with intact text: **3** declare `skip` and **5** remain active for sending and scoring. `assembled__iso` covers connections, gaps, and "does it look like a finished object?"; `zoom_receiver__right_iso`, bevels; `assembled__profile_L`, ground contact. Excluded entries retain their documentary views: `assembled__profile_R` for inverted faces, `zoom_muzzle__front_iso` for cylinders, and `assembled__profile_L` for proportions.

## How to pass multiple views to CLI

`--view NAME PATH` repeatable. `NAME` must match question `view`. `PATH` is the PNG of that framing. Positional `render` ceases to be mandatory in `ask` if there is at least one `--view`.

```
python vr_score.py ask --view assembled__iso assembled__iso__assembled__v1.png --view assembled__profile_L assembled__profile_L__assembled__v1.png --view zoom_receiver__right_iso zoom_receiver__right_iso__zoom_receiver__v1.png --view zoom_muzzle__front_iso zoom_muzzle__front_iso__zoom_muzzle__v1.png --checklist checks_hardsurface.json
```

Resolution rules:

- Without any `--view` (the `vr_calibrate.py run` sweep remains this): all active questions go to positional PNG in **one** call. The `view` field is recorded in response but does not route. Thus an already-migrated checklist does not break `ask foo.png` nor multiply calibrator GPU cost.
- With `--view`: name is mandatory. Missing `zoom_muzzle__front_iso` → error, not silent fallback. The `render` token is alias of positional PNG, for mixed checklists.
- Each framing is an Ollama call of **one** image. All three views are not sent in the same message.

`--reference` does not change: remains comparison photo/render, and is not just another framing. Its guard DID change (SP-266): no longer checks model name but dimensions of both images. Two images of the SAME pixel size collapse into one on `qwen3.x` —and whichever survives is unpredictable, follows prompt cache—, so call is rejected and a single pixel difference suffices to prevent it. Old guard by model name blocked `qwen3.5`, which works with different sizes, and let pass `qwen3.8`, which has the same collision.

## Alternativa simple descartada

The simplest was not touching the CLI: a single PNG (the usual three-panel sheet) and writing the framing in prompt ("answer looking at foreground").

That does not cover the measured case. In EVIDENCIA.md questions 1 and 3 have different answers depending on panel of **the same sheet**, and that is exactly where the three models disagree. The diagnosis is that the unit of work is (question, image), not (question, instruction on a region). A hint in prompt still sends all three panels together.

The other simple one that does change work unit — `ask img0.png img1.png img2.png` and `"view": 2` — covers a three-file capture in fixed order. Broken by omitting or reordering a file: index 2 ceases to be muzzle zoom and bevel question is evaluated against another view. It is the same failure (question against wrong framing), only in argv. `--view zoom_muzzle__front_iso zoom_muzzle__front_iso__zoom_muzzle__v1.png` fails loud if that PNG is missing.

## Backward compatibility and migration

The old format (flat array of strings) continues loading. Each string is `{q: that string, view: null}` and is scored against positional PNG. There is no `skip` or `version` field. No need to migrate an old checklist for `ask` and `vr_calibrate.py` to work. Reading still uses `utf-8-sig`, which accepts both BOM-less JSON and PowerShell 5.1 BOM.

To migrate an old `.json`: each string `s` becomes `{"q": s, "view": "<token>"}`. Choose framing against which question has a single answer. Do not rewrite text. This `checks_hardsurface.json` is already migrated like this.

## Contract with `vr_calibrate.py`

The calibrator does **not** index by question text. Indexes by:

1. `Path(record["render"]).name` to cross with `verdicts.json`
2. position within active list: `verdicts[name]["answers"][i]` vs `record["answers"][i]["answer"]`

That is respected: `answers` remains an array in the order of active checklist entries; entries with `skip` do not occupy a position. Each element still has `q` (string) and `answer`. `view` and `image` are added (the PNG actually sent); calibrator ignores them. Record `render` remains the positional if present, otherwise first PNG of `--view`.

`vr_calibrate.py report` did `questions[qi][:60]` assuming strings. With objects that explodes. `checklist_labels` now reuses same normalization and exclusion as `ask`, so its accumulators only have the five active positions. `run` continues launching `ask <a.png>` without `--view` (legacy routing, one image). A multi-view sweep would call for another folder convention; not this change.

`checklist_labels` delegates reading to `load_checklist`, which retains `encoding="utf-8-sig"`: PowerShell 5.1 writes BOM and `utf-8` kills the report.

## Where the `view` of each question comes from (calibrated 2026-08-16, SP-270)

The `view` field **is not an opinion**: measured with broken/fixed pair of same object,
which needs no gold. Same question is asked about both versions and two things are checked:

- **accuracy** against object gold, across both states;
- **separation** — does response change between broken and fixed, in questions whose
  response MUST change? A framing can score well by always answering the same.

Measured on `mk47_mutant` (8 framings, 3 models), with actual grouping of `vr_score.py`:
the checklist achieves **77.8% against a constant response floor of 58.3%**, and connectivity
question scores **12/12**.

Three traps that cost an entire run and must be avoided when re-calibrating:

1. **Which questions the call travels with changes the response.** Same shading
   question, same image, and same model: **18/18** in a call with four other shading
   questions, **9/12** in call with eight of the checklist. Comparing two framings
   is only valid if batch is kept identical between them. And it is not batch SIZE: removing
   Q5 from `assembled__iso` lowered Q4 and Q6 two points each, with a smaller batch.
2. **A framing without fixed render is not comparable.** `zoom_muzzle__front_iso` scores
   over 6 cells of broken state instead of 12, and there a constant response gets 6/6.
   Sorting by percentage crowns it with half the evidence and zero separation.
3. **What wins under uniform conditions can lose under real ones.** Moving Q1, Q4, and Q5
   together to `assembled__profile_R` won in audit and **worsened** under real
   grouping: Q1 dropped from 12/12 to 8/12. Only Q5 was moved, which is the one that stood up to validation.

**Q3 is not misrouted: it is broken.** "Are cylinders smooth and round?" is at random
across the eight framings (maximum 50%), because its phrasing permits reading polygonal
handguard —flat by design— as a faceted cylinder.

> **RETRACTED 2026-08-22 — not fixed by rewriting it.** This paragraph closed with "it is
> fixed by rewriting it, not moving it". It was tested and came out the opposite (192 cells on
> `mk47_mutant` + synthetic probe with truth set by construction, 2026-08-17):
>
> - **Four phrasings measured and the existing one wins** (6/6 and 6/6 in framings where
>   round piece fills frame). Numerical threshold 5/6, exclusion clause 5/6, angular
>   silhouette 2/6. On full-object framing **all four** drop to 1-2 of 3:
>   framing outweighs phrasing.
> - **A threshold inside statement is not applied as a count**: asking "roughly six or
>   fewer sides", all three models said "yes" to the **12**-sided variant.
> - **Grouping splits sensitivity by two**: 6/6 asked alone, 3/6 within batch of
>   eight built by `vr_score.py`. Third confirmation of batch effect in this skill.
> - **The object cannot answer it.** `hg_tube` is a REGULAR octagon and is correct — reference
>   photo dictates octagonal section (`dossier.md:18,49`). Authentic cylinders
>   (`body_brake` 18-22 sides, `body_barrel` 14, `endplate` 24) have a sagitta
>   `r*(1-cos(pi/N))` of 0.167-0.213 mm, **less than 1 px** in any of the eight
>   framings, against 1.91 mm and ~6.9 px of octagon. The only visibly faceted piece of this
>   weapon is the piece that ought to be.
> - **8 out of 12 cells are false alarms** under real grouping, against gold derived from
>   geometry. A question flagging correct geometry two-thirds of the time cannot go
>   into an automatic gate, and even less into a pre-filter that REJECTS: there a false alarm throws out
>   good work. It is failure mode of winding gate, red in 73% of what is published.
>
> **What to do instead**: remove it from VLM checklist and any pre-filter, and replace it
> with a deterministic report per part (sides, radius, deviation, sagitta) that **reports and does not
> judge** — Q3 problem was that it required guessing modeler's intent, and a row
> "`hg_tube`, 8 sides, r=25.2 mm" returns that decision to who can make it. Prototype
> (`facet_report.py`) is **not yet in this skill**.
