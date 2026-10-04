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

Most rules read a single file. Two read the tree, and one of them needs a root
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
path exists. `--baseline` defaults to
`tests/baselines/vanilla_control_baseline.json` next to this tool, not the
cwd. `--update` rewrites the baseline on purpose after a DayZ patch or an
accepted change; it prints what moved. Exit 0 is PASS, 1 is FAIL, 2 is
SKIP (no tree, no baseline, unreadable).

Every baseline entry carries the reason it is tolerated. `--update` keeps
the reasons already written and cannot invent the missing ones, so it names
every entry left without a note: an allowlist entry nobody triaged is a
finding hiding behind a gate.
