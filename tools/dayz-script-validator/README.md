# dayz-script-validator

Offline linter for DayZ Enforce Script, `.layout`, `config.cpp`, `inputs.xml`
and `.rvmat` files. It turns silent compile/runtime failures into a JSON
report before a PBO is packed.

This is the pack OFFLINE layer. It does not launch DayZ. In-game verification
belongs to DayZ-MCP.

It is a rule linter, not a compiler: a PASS means no rule fired, not that the
script compiles. The engine compile is the only full syntax gate.

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

Most rules read a single file. Eight read the tree, and five of them need roots
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
| a `requiredAddons[]` entry that is not a string literal (a macro, a number) | SKIP: that dependency is unknown |
| no `config.cpp` in the tree lists any `requiredAddons[]` entry | SKIP: dependencies unknown |
| code under `#ifdef`/`#ifndef` of a macro that vanilla does not test and no scanned script `#define`s or `CfgMods defines[]` lists | not judged: usually another mod's flag |
| the `#ifndef` or `#else` branch of a macro that a scanned script `#define`s, or a scanned `CfgMods defines[]` lists, on a line the preprocessor always keeps (outside every block, or under an `#ifdef` of a macro the same file defines first) | not judged: that branch never compiles |

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
2026-10-03, after the fixes from two rounds of cross-family review, the
vanilla tree gave the same 33 003 references and no finding; the 161 roots
were not measured again.

- `ES-VARIABLE-NAMED-AS-TYPE` (FAIL): a variable, member or parameter whose
  name is a class, enum or typedef declared in the addon, the vanilla tree or
  an `--external-scripts` root. `bool Debug;` in a 4_World settings class
  made DayZDiag 1.29 refuse the module with `Variable name 'Debug' already
  used as type name` (inbox fb-20260928-025254-35c1); a local `Widget map`
  failed the same way (enforce-script-reference `pitfalls-advanced.md`,
  SP-317). Only a member and a local are on record; a parameter, an enum and
  a typedef are judged the same way without a failure on record. The match
  is exact case, so a member `debug` passes: identifiers are case-sensitive
  and no case-only failure is on record. A name is judged against the types
  of its own module and the modules below it (a 4_World local may be named
  like a 5_Mission class). A file outside any `N_Module` folder may compile
  in any module, so it is judged only against the types of 1_Core and those
  of its own file; in a mod recovered without its module folders the rule
  had reported a member against a 5_Mission class (mods pass of 2026-10-17).
  Positions are those of `ES-RESERVED-WORD-IDENTIFIER`;
  code that never compiles is not judged, and a type the addon or an external
  root declares only there is no type. Nor is a name judged against a type its
  own file declares only in another branch of the same `#ifdef` block, or only
  under the opposite test of a macro the file never `#define`s or `#undef`s
  (`#ifdef X` type, a later `#ifndef X` name): the two never compile together.
  Without a vanilla tree the addon's
  and the external roots' types are still judged, and the vanilla part is
  listed as SKIP in `info.skipped_checks` and in `--terse`.
- `ES-CAST-UNRELATED-TYPES` (FAIL): `X.Cast(y)` where neither X nor the
  declared type of `y` derives from the other. `Mission mission =
  GetGame().GetMission(); hud = IngameHud.Cast(mission);` made DayZDiag 1.29
  refuse the Mission module with `Types 'IngameHud' and 'Mission' are not
  related` (inbox fb-20261009-122148-c852). Judged only when everything is
  known: `y` is a plain name declared once, with a plain type, as a local
  still open at the cast or a parameter of the same function, or else as a
  member of the enclosing class itself (an inherited member is not looked
  up); both are classes, not a typedef, an enum, a template or a primitive;
  and the `extends` chain of both resolves in the addon, the vanilla tree or
  an `--external-scripts` root, through declarations that are not `modded`
  and agree on one parent (a header that a directive splits, `class D` /
  `#ifdef X` / `: B` / `#endif`, does not resolve). `Class` is related to
  everything. Anything else,
  a call's result included, is skipped without a SKIP line; without a
  vanilla tree that means every cast whose chain reaches a vanilla class.
- `ES-UNDECLARED-STATIC-MEMBER` (FAIL): `ClassName.Member` or
  `ClassName.Member(` where no declaration of the class names `Member`. A
  lane deleted `ANIM_SWAP_ENABLED` and its sibling consts from its own class
  `LFSK_Constants` while seven call sites still read
  `LFSK_Constants.ANIM_SWAP_ENABLED`, and DayZ refused the World module on
  the first boot (inbox fb-20261006-002741-28fa). Judged only for a class
  the addon owns end to end: declared in the addon, not modded and not a
  template there, declared nowhere (modded or not) in the vanilla tree or an
  `--external-scripts` root, with every ancestor the same through
  declarations that agree on one parent. A name counts as declared when it
  appears at the top level of the body of any addon declaration of the class
  or an ancestor, `modded class` and `#ifdef` branches included; the methods
  of `Class` (`Cast`, `CastTo`, `StaticType`, `StaticGetType`...) always
  count. A class whose
  chain reaches a vanilla or another mod's class is not judged, so it runs
  without a vanilla tree; a class-like name declared as a variable in the
  addon is not judged either.
- `ES-PROTECTED-METHOD-CROSS-CLASS` (WARN): `recv.Method(` where `Method`
  is `protected` or `private` in the declared type of `recv` (or the addon
  ancestor that declares it) and the calling class is neither that class nor
  derived from it. Shape of inbox fb-20261006-002741-28fa: `PlayerBase.OnRPC`
  called `cmd.LFSK_OnServerState(...)`, protected in `LFSK_RideCommand`, in
  the same module. WARN because the refusal is measured for a protected
  field (`Variable '...' is protected`, `ES-PROTECTED-CROSS-MODULE`) and not
  for a method. The receiver's type is looked up as in
  `ES-CAST-UNRELATED-TYPES`; every class from it up to the one that declares
  the method must be the addon's own, and the first declaration found decides
  (any public declaration of that name in the addon clears it). A caller whose
  chain leaves the addon and the external roots counts as unrelated: a
  vanilla class cannot derive from an addon class. A caller or an ancestor
  whose header a directive splits is not read, and the call is skipped.
- `ES-PROTO-ARGUMENT-DOWNCAST` (FAIL): a name passed to a parameter of a
  `proto` method where the parameter's class derives from the class the
  name is declared as. `DayZPhysics.RaycastRV(from, to, pos, dir, comp,
  hits, hitEntity, m_Human, true, false, ObjIntersectGeom)`, with
  `hitEntity` an `IEntity` at the `Object` parameter 6, made DayZ
  1.30.164014 server refuse the World module with `Cannot convert 'IEntity'
  to 'Object' for argument '6' to method 'RaycastRV'` (inbox
  fb-20261006-030019-e074; the compiler counts arguments from 0). Judged
  only when everything is known: the receiver is a class, or a name looked
  up as in `ES-CAST-UNRELATED-TYPES`; the first class up its chain that
  declares the method (a `modded class` included) declares it `proto` every
  time, with one parameter list; the argument is a plain name looked up the
  same way; and the parameter is not `out` or `inout` and has a plain class
  type whose chain holds the argument's class above its own. `Class` is not
  judged as the argument's class. A call whose arguments hold `<`, `>` or a
  directive is skipped, and so is one with more arguments than parameters.
  Protos are read from the addon, the `--external-scripts` roots and the
  vanilla tree, so without a vanilla tree no vanilla proto is judged, with
  no SKIP line. Only a proto's refusal is measured: an argument of a script
  method and a down-cast in an assignment are not judged.

## Compile errors read from one file

These rules come from script modules that did not compile, each with its
log, or from a broken file the validator passed:

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
- `ES-UNBALANCED-BRACKETS` (FAIL): the first `(`, `[` or `{` never closed,
  or closed by another kind of bracket, and the first closer with nothing
  to close. `m_Objects.Clear();` sabotaged to `m_Objects.Clear(;` got PASS
  (inbox fb-20261004-040148-403a). Brackets are counted on the text without
  comments and strings; this is no parser, so a file it passes can still
  fail to compile. Each branch of an `#ifdef`/`#ifndef`/`#if` block starts
  from the brackets open before it, so a header written once per branch
  with one `{` after the block counts once. When the branches of a block
  end with different brackets open, or an `#ifdef` is never closed, the
  file is not judged. A file with an unterminated string or block comment
  is not judged either: the stripper's warning is the finding there.
- `ES-MODDED-ENGINE-CLASS` (FAIL): `modded class Transport`. DayZDiag
  1.29.163709 refused it with `Engine class 'Transport' cannot be modded.`
  and `Can't compile "Game" script module!` (inbox
  fb-20261005-233046-89d1). Transport is the only class listed: another
  engine class goes in only after a compile refuses it. Mod the script
  bases in 4_World instead, `CarScript` or `BoatScript`.
- `ES-MULTILINE-CONDITION-OPERATOR` (FAIL): a line inside the parentheses
  of an `if (` or `while (` that ends in `&&` or `||`, once per header.
  DayZ 1.30.164014 server refused `if ((t >= A && t < B) ||` followed by
  `(t >= C && t < D))` with `Invalid statement ')'` and `Syntax error` at the
  continuation (inbox fb-20261006-030019-e074). One measurement; FAIL since
  the vanilla control found nothing for it on 1.29.0.163451 and on
  1.30.164078 stable. The operator leading the next line is
  the same parser rule (enforce-script-reference SKILL.md, SP-386) and is not
  reported here; neither is a call's argument list over two lines.

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

One compile error filed with these has no rule here yet:

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

A full run on DayZ 1.30 takes two to four minutes. It is a gate, not a unit
test — do not put it in `unittest discover`.

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
