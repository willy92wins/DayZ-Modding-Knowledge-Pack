# dayz-script-validator

Offline linter for DayZ Enforce Script, `.layout`, `config.cpp`, `inputs.xml`
and `.rvmat` files. It turns silent compile/runtime failures into a JSON
report before a PBO is packed.

This is the pack OFFLINE layer. It does not launch DayZ. In-game verification
belongs to DayZ-MCP.

## Install

```powershell
python -m pip install -e tools/dayz-script-validator
```

Python 3.9 or newer is required. No third-party dependencies.

## Invoke

From the pack root, without installing:

```powershell
python tools/dayz-script-validator/scripts/script_validator.py <addon_root>
python tools/dayz-script-validator/scripts/ui_reconcile.py <addon_root>
```

After `pip install -e`:

```powershell
python -m dayz_script_validator <addon_root>
```

Exit `0` = PASS, `1` = FAIL, `2` = WARN. Findings are JSON on stdout.

## Checks that need more than one file

Most rules read a single file. Three read the tree, and two of them need roots
outside the addon:

- `ES-PROTECTED-CROSS-MODULE` compares modules against each other. Enforce
  enforces `protected` across script modules, so a `5_Mission` class reading a
  `4_World` class's protected member aborts the whole Mission module. Runs
  automatically.
- `ES-EXTERNAL-CONSUMER-MISSING` compares the addon against script that calls
  into it from outside -- a mission folder, another mod. Pass those roots
  explicitly; the check is inert without them:

```powershell
python tools/dayz-script-validator/scripts/script_validator.py <addon_root> `
    --external-scripts <mission_root> --external-scripts <other_mod_root>
```

Both only fire when the receiver's declared type resolves inside the addon.
That is deliberate: judging by member name alone produced 164 false positives
on a tree that compiles clean.

- `ES-UNDEFINED-CLASS-REF` (FAIL) flags a class-like name (first letter upper
  case) used where only a type fits -- `Name.Method(`, `Name.Cast(`,
  `new Name`, a template argument, a typed declaration at the start of a line
  -- when no `class`, `enum` or `typedef` of that name exists in the addon,
  in the vanilla scripts tree or in any `--external-scripts` root. Found on
  TransferZ PR #12, which deleted a `4_World` class that `5_Mission` still
  called: a guaranteed Mission compile failure the linter reported as WARN
  with 0 errors. The vanilla tree comes from `--vanilla-root`, then
  `DAYZ_VANILLA_ROOT`, then `P:\scripts`.

```powershell
python tools/dayz-script-validator/scripts/script_validator.py <addon_root> `
    --external-scripts <CF_root>
```

Pass each dependency's root, the folder that holds its `config.cpp`: the rule
reads that file's `CfgPatches` to know which `requiredAddons[]` entry the
root covers, so a root without it leaves the dependency uncovered.

It judges only when it can see every place the type could be declared, and
otherwise lists what it could not judge under `info.skipped_checks` (and as a
`SKIP` line in `--terse`) without changing the status:

| Situation | Result |
|---|---|
| no vanilla tree, or a folder that declares no `class Managed` | SKIP: every vanilla type would look undefined |
| `requiredAddons[]` names an addon that is not a vanilla patch and that no scanned root declares in `CfgPatches`, directly or as the dependency of a scanned dependency | SKIP with the unresolved names; pass that addon's root with `--external-scripts` to get verdicts |
| a `requiredAddons[]` entry that is not a string literal (a macro) | SKIP: that dependency is unknown |
| no `config.cpp` in the tree lists any `requiredAddons[]` entry | SKIP: dependencies unknown |
| code under `#ifdef`/`#ifndef` of a macro that vanilla does not test and no scanned script `#define`s or `CfgMods defines[]` lists | not judged: usually another mod's flag |
| the `#ifndef` or `#else` branch of a macro that a scanned script `#define`s outside any `#if` block, or that a scanned `CfgMods defines[]` lists | not judged: that branch never compiles |

A mod that uses another mod's classes without listing it in `requiredAddons[]`
does get the FAIL; the message names both remedies. "Vanilla patch" means one
of the 211 `CfgPatches` names of `P:\DZ` (1.29.0.163451), the scripts tree and
the 1.30.164014 Exp data, listed in `scripts/shared/vanilla_patches.py`. A
`DZ_` prefix is not enough: four mod patches under `P:\` use it too.

Measured on 2026-09-19 with the first version of the rule: 33 003 references
judged on the vanilla tree with no finding; over 161 addon roots under `P:\`
it left 12 FAILs in 3 roots (one probable real bug, two recovered-source trees
that use a sibling mod they do not declare) and 32 SKIPs whose unresolved
names all belong to mods. Reading the vanilla tree adds about 0.9 s per
invocation (2.6 s against 1.7 s on a 23-file addon, four runs each). On
2026-10-03, after the review fixes (comma-separated variables, dead
preprocessor branches, the dependency closure and the patch inventory), the
vanilla tree gave the same 33 003 references and no finding; the 161 roots
were not measured again.

## Compile errors read from one file

Two rules come from script modules that did not compile, each with its log:

- `ES-RESERVED-WORD-IDENTIFIER` (FAIL): a variable, member or parameter named
  `sealed`, `local`, `owned` or `out`. These four failed as names in a real
  compile: `Expected name, not a keyword 'sealed'` on DayZDiag 1.29.163709,
  and `Broken expression (missing ';'?)` for the others (`local` on DayZDiag
  1.30.164014 Exp). Vanilla uses each only as a keyword. Other modifiers
  vanilla uses the same way (`notnull`, `inout`, `autoptr`, `event`...) are
  not listed until a failure is on record. A name counts after its type,
  on the same line or the next, as a later declarator (`int a = 1, out;`)
  and as a foreach variable; a later use of the variable is not reported
  again. Later declarators are found by counting brackets in the text as
  written, lines that never compile included, so one that follows brackets
  which differ between two branches of an `#ifdef`, or a bracket in a
  branch that never compiles, can go unseen.
- `ES-MODULO-FLOAT-CONTEXT` (FAIL): `%` inside an arithmetic expression that
  also holds a float literal, such as `(n % 4) * 0.7`. Both operands of `%`
  can be integers and it still fails with `Unknown operator '%'` (DayZDiag
  1.29 and DayZ 1.30 Exp); computing the `%` into an int local first
  compiles. The expression stops at a call's or an index's brackets, a
  comparison, an assignment, `;` and `,`, and one that holds a string
  literal anywhere is not judged (there `+` concatenates); quotes inside a
  comment are no string. That includes a string that is only the receiver
  of a method: `"cell".Length() + (n % 4) * 0.5` is not judged, because
  types are not tracked and another method could return a string. A float
  literal under an `(int)` cast, or in a parenthesised condition (only the
  results behind a `?` count), does not reach the expression. A float
  variable is not seen: only the literal case is caught.

Each finding is wrong wherever the code compiles, so code under another
mod's `#ifdef` is judged too. A branch that never compiles is not: `#if`
blocks, and the `#ifndef` or `#else` branch of a macro the same file
`#define`s first (`scripts/shared/dead_branches.py`). An expression is never
read through a branch that never compiles, nor from the branch that holds
the `%` into another branch of the same block. Blocks are not compared by
their macros: `#ifdef X` and a later `#ifndef X` count as unrelated, so
their lines can still meet in one expression.

Measured on 2026-10-03: nothing on vanilla 1.29.0.163451 (69 `%` judged) or
on vanilla 1.30.164014 Exp (94 `%`), and on the source that failed in game,
`vector local;`, the reserved-word rule fires on that line.

Two compile errors filed with these have no rule here yet:

- `Variable name 'X' already used as type name` (a local or member named
  like a vanilla class, such as `bool Debug = false;`) needs the vanilla
  scripts tree to know the class names, and waits for the `--vanilla-root`
  option.
- `Formula too complex`: vanilla compiles a statement with 14 `+`, the one
  that failed had about 20 terms and its source is gone, and the limit
  between them was not measured.

## Tests

```powershell
python -m unittest discover tests
```

Run from `tools/dayz-script-validator/`.

## Vanilla control

Bohemia's vanilla script tree compiles and ships, so a linter finding on
it is a false positive by construction. This control runs the validator
over that tree and fails if the findings differ from a measured baseline.

The vanilla tree is Bohemia's and is not redistributed. Without a local
copy the control SKIPs (exit 2) instead of pretending the tree was clean.

A full run takes about 85 seconds. It is a gate, not a unit test — do not
put it in `unittest discover`.

```powershell
python scripts/vanilla_control.py
```

`--vanilla-root` defaults to `DAYZ_VANILLA_ROOT`, then `P:\scripts` if that
path exists. The control passes the tree as its own vanilla root, so
`ES-UNDEFINED-CLASS-REF` runs instead of skipping, and vanilla's empty
`requiredAddons[]` is not read as "dependencies unknown": a false positive of
that rule fails the control rather than hiding in a SKIP. `--baseline` defaults to
`tests/baselines/vanilla_control_baseline.json` next to this tool, not the
cwd. `--update` rewrites the baseline on purpose after a DayZ patch or an
accepted change; it prints what moved. Exit 0 is PASS, 1 is FAIL, 2 is
SKIP (no tree, no baseline, unreadable).

Every baseline entry carries the reason it is tolerated. `--update` keeps
the reasons already written and cannot invent the missing ones, so it names
every entry left without a note: an allowlist entry nobody triaged is a
finding hiding behind a gate.
