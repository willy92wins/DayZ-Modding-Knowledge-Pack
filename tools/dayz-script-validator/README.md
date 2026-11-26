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

Most rules read a single file. The ones below read the tree:
`ES-PROTECTED-CROSS-MODULE` the addon's modules, `ES-EXTERNAL-CONSUMER-MISSING`
the addon and the `--external-scripts` roots, and the others the addon, those
roots and the vanilla tree:

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
  failed the same way (dayz-enforce-script-reference `pitfalls-advanced.md`,
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
- `ES-PROTO-ARGUMENT-DOWNCAST` (FAIL or WARN): a name passed to a parameter
  of a `proto` method where the parameter's class derives from the class
  the name is declared as. `DayZPhysics.RaycastRV(from, to, pos, dir, comp,
  hits, hitEntity, m_Human, true, false, ObjIntersectGeom)`, with
  `hitEntity` an `IEntity` at the `Object` parameter 6, made DayZ
  1.30.164014 server refuse the World module with `Cannot convert 'IEntity'
  to 'Object' for argument '6' to method 'RaycastRV'` (inbox
  fb-20261006-030019-e074; the compiler counts arguments from 0). DayZDiag
  1.30.164289 refused that call again, and an `Object` passed to the
  `EntityAI` parameter 0 of `ItemPreviewWidget.SetItem`, the shape the rule
  had found in a mod, with `Cannot convert 'Object' to 'EntityAI' for
  argument '0' to method 'SetItem'` (inbox e074; a retail build is not
  measured for it). Those two pairs, an `IEntity` where an `Object` is
  taken and an `Object` where an `EntityAI` is, are FAIL; any other is
  WARN, because no refusal of it is measured. Judged only when everything is
  known: the call is in a method the validator reads (not one whose return
  type has template arguments, `array<T> F(`); the receiver is a class, or a
  name looked up as in `ES-CAST-UNRELATED-TYPES` or else as a member of
  another body of the enclosing class or of the nearest class up its chain
  that declares it; the first class up the receiver's chain that declares
  the method (a `modded class` included) declares it `proto` every time,
  with one parameter list, where a declaration whose `(` is on a line that
  never compiles does not count; the argument is a plain name looked up the
  same way; and the parameter is not `out` or `inout` and has a plain class
  type whose chain holds the argument's class above its own. `Class` is not
  judged as the argument's class. A member in a body of another file counts
  when that file's script module is not later than the call's (a later one
  is compiled after it), and leaves the name unknown when either file is
  under no `N_Module` folder. A declaration under `#if`, `#ifdef` or
  `#ifndef` leaves a name unknown unless it is in the call's file under
  blocks that are all around the call, and a method whose declaration has a
  line up to its `(` under such a block is unknown. A name that the method
  declares before the call only where that declaration is no longer open at
  the call (a `for` or `foreach` variable, for a call in the loop's body or
  after it, or a local of a block closed before the call) is unknown too,
  also where a member has that name; a call in that `for`'s own header, as
  in its condition, takes the variable's type. A call whose arguments hold
  `<`, `>` or a directive is skipped, and so is one with more arguments than
  parameters. Protos are read from the addon, the `--external-scripts` roots
  and the vanilla tree, so without a vanilla tree no vanilla proto is
  judged, with no SKIP line. Only a proto's refusal is measured here: an
  argument of a script method is judged by `ES-SCRIPT-ARGUMENT-DOWNCAST`,
  and a down-cast in an assignment is judged by neither rule.
- `ES-SCRIPT-ARGUMENT-DOWNCAST` (FAIL or WARN): a name, or a member through a
  name (`rec.m_RefEnt`), passed to a parameter of a script method (not a
  `proto`) where the parameter's class derives from the class the argument
  is declared as. A mod's `SubtreeBornInInventory(rec.m_RefEnt)`, with
  `Object m_RefEnt` and `protected bool SubtreeBornInInventory(EntityAI
  root)`, made DayZDiag 1.30.164289 refuse the Mission module with `Cannot
  convert 'Object' to 'EntityAI' for argument '0' to method
  'SubtreeBornInInventory'` (inbox fb-20261122-205419-250d); with
  `EntityAI.Cast(rec.m_RefEnt)` the mod compiled, and
  `ES-PROTO-ARGUMENT-DOWNCAST` had said nothing. That pair, an `Object`
  where an `EntityAI` is taken, is FAIL; any other is WARN, because no
  refusal of it is measured. Judged only when everything is known: the call
  is in a method the validator reads, on a line that compiles, and is
  `recv.Method(`, `this.Method(` or `Method(` with no receiver inside a
  class body (a `modded class` included), the receiver read as in
  `ES-PROTO-ARGUMENT-DOWNCAST` or, for `this` and no receiver, as the class
  of the body around the call; the first class up the receiver's chain that
  declares the method declares it as a script method every time, with one
  parameter list; the argument is a plain name read the same way, or
  `x.m` with the member read up the chain of the type of `x` (`this.m`
  reads the enclosing class, never a local of that name); and the parameter
  is not `out` or `inout` and has a plain class type whose chain holds the
  argument's class above its own. `Class` is not judged as the argument's
  class. A proto there is the proto rule's; a proto beside a script method
  and two parameter lists (overloads) are skipped by both rules; for this
  rule, that covers two lists in one class or along the receiver's chain.
  Skipped:
  `super.Method(` and `super.m`, a receiver that is not a plain name, an
  unknown receiver, a name preceded by a dot or by an identifier other
  than `return` or `else` (so `new Method(` and `thread Method(` and a
  method header are no call), a call outside every class body, a bare name
  that is also a global function, two levels of members (`x.y.z`), calls
  and anything else as an argument, a call whose arguments hold `<`, `>` or
  a directive, and one with more arguments than parameters. Script methods
  are read from the addon, the `--external-scripts` roots and the vanilla
  tree, so without a vanilla tree no vanilla script method is judged.
- `ES-UNDEFINED-BUILTIN-METHOD` (FAIL): a call to a method that the vanilla
  tree's class of a built-in type does not declare. `vector gU =
  gF.Cross(gR);`, with `gF` and `gR` vector locals, made a DayZ 1.30.164200
  server refuse the World module with `Undefined function 'vector.Cross'`
  (inbox fb-20261103-150432-9f93): the 1.30.164014 Exp scripts declare
  `vector.Cross` (`1_Core/proto/EnConvert.c:239-246`), the 1.30.164200 ones
  do not, and the validator had passed the call against either tree. The
  built-in types are `bool`, `int`, `float`, `vector`, `string`, `typename`,
  `array`, `set` and `map`. Their members are the names at the top level of
  every declaration of that class in the vanilla tree, the addon and the
  `--external-scripts` roots (`modded` included, any `#ifdef` branch,
  comments and strings dropped), and every name written before a `(` from
  such a header to the next class header, plus those of `Class`; a type the
  vanilla tree does not declare is not judged. Judged: `T.Method(` with `T` one of
  them or a typedef of one (`TStringArray`), unless a variable of the file is
  named `T` (`Widget map`, which `ES-VARIABLE-NAMED-AS-TYPE` reports); and
  `name.Method(` where `name` is looked up as in `ES-CAST-UNRELATED-TYPES`
  (a declaration under an `#ifdef` that is not around the call leaves it
  unknown) and declared as one of them, a template of one (`array<string>
  names`) or a typedef of one. A typedef counts when its name has one
  target, no `[]` (`typedef int[] Physics` is a handle) and no class
  declaration anywhere (`ResourceName` is also `class ResourceName :
  string`). A call's result, a member access (`this.m_X.`), an index, a
  `for` or `foreach` variable inside its loop, a local of a block closed
  before the call, a name a later declarator declares (`vector a, x;`), a
  member declared in a parent class, `value` inside a `modded class vector`
  and a parameter whose template arguments the lookup reads across other
  parameters are not judged. Lines that never
  compile are not judged, nor lines that need a DayZ version macro defined:
  the engine defines one `DAYZ_<major>_<minor>` (`1_Core/defines.c:11-14`)
  and the tree does not say which, so `#ifdef DAYZ_1_29`, and the `#else` of
  `#ifndef DAYZ_1_29`, are left out, while the `#ifndef DAYZ_1_29` branch,
  the code of every later build, is judged. Without a usable vanilla tree
  the rule is a SKIP line. A verdict holds for the build the vanilla tree
  comes from: see `--game-root` below.

  Measured on 2026-11-03 against the 1.30.164200 scripts: on the
  LFSkateboard tree before its fix the rule reports `lfsk_playerbase.c:1957`
  and `:1959` and nothing else (390 calls judged), and nothing on the fixed
  tree (388 judged). Nothing on the vanilla tree itself (8 870 calls judged),
  and the vanilla control still matches its baseline; nothing either on the
  1.30.164014 Exp tree or a 1.29 tree, each against itself (8 878 and 8 059
  calls judged). Over 236 addon roots
  under `P:\` (2 019 files, 23 885 calls judged) it reports one call,
  `text.StartsWith(` on a string in an old copy of a bench mod: no tree
  declares `StartsWith` (1.29, 1.30.164014 and 1.30.164200), and the shipped
  copy of that mod uses `IndexOf` instead. Before two fixes the same pass
  gave 19 false positives: 18 where the lookup read `map<string, int> m` as
  an array, its `<...>` running from an earlier parameter's `<`, and one on
  `map.ClearFlags(` with a `Widget map` local. A cross-family review (Grok
  4.7, 2026-11-03) built a third on a synthetic tree: a `(` that only one
  branch of an `#ifdef` opens hid every later member of `vector`, hence the
  names written before a `(`. It also listed the unjudged receivers above as
  missed calls; they stay unjudged. The rule takes about 1 s on
  the 11-file LFSkateboard addon (about 2.5 s on the first call of a
  process) and about 6 s on the 3 056 files of the vanilla tree.

## Which build the vanilla tree is

The rules that read the vanilla tree judge the addon against that tree, not
against the game. A gate that read the 1.30.164014 Exp extract while the
game was 1.30.164200 passed `vector.Cross`, which only the extract declares
(inbox fb-20261103-150432-9f93). `--game-root`, or `DAYZ_GAME_ROOT`, names
the DayZ install folder (or its `dta\scripts.pbo` itself), and the vanilla
tree is compared with that PBO, `.c` file by `.c` file, by content, with
names compared without case:

```powershell
python tools/dayz-script-validator/scripts/script_validator.py <addon_root> `
    --vanilla-root <tree> --game-root <DayZ install folder>
```

When they differ, `VANILLA-ROOT-BUILD-MISMATCH` gives the counts (files that
differ, files the tree lacks, files only the tree has), the first five names
and the PBO header's `version`; `info.vanilla_build` holds the counts either
way, with `matches`. A folder carries no build number, and the header's
`version` or the exe's version only name a build, so the comparison is by
content. The PBO is read with the fail-closed reader of
`tools/dayz-vehicle-proxy-contract` (a compressed entry is refused): a PBO
that cannot be read, a folder without `dta\scripts.pbo` or a missing vanilla
tree gives a SKIP line, never a match. Without `--game-root` or
`DAYZ_GAME_ROOT` nothing is compared. With `--game-root` on the command line,
a mismatch is FAIL (in `errors`, exit 1) so a gate fails on a stale tree;
with `DAYZ_GAME_ROOT`, it is WARN (in `warnings`, exit 2), which a gate that
accepts WARN lets through.

Measured on 2026-11-03: the 1.30.164014 Exp extract against a 1.30.164200
game gives 111 `.c` files that differ and 14 that the tree lacks
(`1_Core/proto/EnConvert.c` first); `P:\scripts` and an extract of the same
`scripts.pbo` both match (3 056 files). The comparison takes about 1.7 s.

## Which tree the vanilla index is

`scripts/shared/vanilla_index.json` is local and optional. It is generated
from one vanilla tree (`scripts/build_vanilla_index.py`) and gives four
rules that tree's members and signatures: `ES-MEMBER-REDECLARE-BASE`,
`ES-OVERRIDE-PARAM-NAME-MISMATCH`, `ES-METHOD-NAME-COLLIDES-VANILLA-CLASS`
and `ES-OVERRIDE-OF-PLATFORM-GATED-METHOD`. The other vanilla rules read
the tree itself, so when the tree moves to another build and the index
stays, one run judges against two builds. On 2026-11-18 an index of
1.30.164289 read with the 1.30.164393 tree gave five false
`ES-MEMBER-REDECLARE-BASE` findings (see "Vanilla control"); a 1.29 index
had already turned the control red on 1.30 (inbox 4c83).

With an index in use and a vanilla tree, each run compares them. The index
records the count and the total bytes of the `.c` files of the tree it was
built from, and the tree being read is counted with the generator's own
walk. When either number differs, and no index kept beside it is of that
tree (below), `VANILLA-INDEX-TREE-MISMATCH` (WARN)
names the index file, the tree it was built from (the folder the generator
read, its two numbers and the start of its `tree_digest`), the tree being
read with its two numbers, and the command that rebuilds the index from
that tree:

```powershell
python tools/dayz-script-validator/scripts/build_vanilla_index.py --vanilla-root <tree>
```

`info.vanilla_index` holds both pairs of numbers either way, with
`matches`. Moving the index away also clears the warning: the four rules
then use only their curated tables. Without an index nothing is compared
and nothing is reported. What cannot be compared is a SKIP line, never a
match, and leaves the verdict as it was: an index with no vanilla tree, an
index that does not record the two numbers or did not parse every file of
its tree, a tree that cannot be read. The folder's path is not compared:
the same path holds another build after a refresh, and the generator
writes the resolved path, which a `subst` drive spells another way. WARN
exits 2, so what the section above says of a gate that accepts WARN holds
here too. The vanilla control never gets this far: it SKIPs when an index
is in use.

[EXACT][CLAIM-DSV-VANILLA-INDEX-BESIDE-OUT] A PC with more than one vanilla tree (the stable build's and an
Experimental one, say) keeps an index of each: the default file for one
and, for each other, a file beside it named
`scripts/shared/vanilla_index.json.<name>`. The name is free; the build
number serves. It is built with `--out`:

```powershell
python tools/dayz-script-validator/scripts/build_vanilla_index.py --vanilla-root <tree> `
    --out tools/dayz-script-validator/scripts/shared/vanilla_index.json.<name>
```

Each run reads the default index from disk again, whatever an earlier run
in the same process read. When that index is not known to be of the tree
being read (a number differs, or it cannot be compared), the files beside
it are tried in name order, and the first that is a whole index of that
tree is read instead: the four rules judge with it,
`info.vanilla_index.index` names it, `info.vanilla_index.compared` adds
`tree_digest`, and the run has no `VANILLA-INDEX-TREE-MISMATCH` warning. A
whole index is what the generator writes: a JSON object of this
`schema_version` holding the four tables the rules read (`base_members`,
`override_params`, `global_class_names` and `platform_gated_methods`, each
an object), a `parsed_file_count` equal to its `file_count`, a
`tree_digest` and, from indexes written since 2026-11-19, a
`tree_digest_casefold_v1` (each digest 64 lower-case hex digits; the
second may be null or missing). It is of the tree when its count and its
bytes are the tree's and one of its digests is one of the tree's (below).
Anything else beside the default index is passed over. When no file beside
it is of the tree, the default index is read and the run warns, or gives
its SKIP line, as above; the warning then also offers `--out` with such a
name. The default file alone says whether there is an index: without one
that loads, nothing beside it is read, so an index moved away under
another name in the same folder stays away, for a later run and for the
vanilla control in the same process too. Like the default index, those
files are derived from Bohemia's scripts, and git ignores them. Index
selection is process-wide state, so `validate_addon` does not support
concurrent calls in the same process.

For the default index the two numbers are compared and its `tree_digest`,
a sha256 over the relative paths and the contents of the same files, is
not, because hashing the tree on every run costs several times the count.
The price is one blind spot: a tree with the same count and the same bytes
but other contents is taken for the default index's tree. A file beside
the default index is not taken on those two numbers: two trees can share
them (one identifier renamed to another of the same length is enough), and
taking one for the other would silence `VANILLA-INDEX-TREE-MISMATCH` and
report a match. Its digest is compared too, and the tree is hashed only
when a file beside the default index has the tree's two numbers.

That digest is compared up to the capitals of the paths, as the comparison
with the PBO above takes them: `collect_c_files` matches `.c` regardless of
case on POSIX as well as Windows, so an extraction that keeps the PBO's own
capitals (`4_World/...` or `.C`) and one in lower case are one tree. Each
file is read once for two digests of the tree: as spelt, which is
`tree_digest`, and with each relative path casefolded and the files in the
order of their casefolded parts, which the generator records as
`tree_digest_casefold_v1`. For a tree whose paths are lower-case ASCII the
two are one, so an index written before `tree_digest_casefold_v1` from such
a tree, as `P:\scripts` and the extractions this pack describes are, is read
for a copy in any ASCII capitals. One written from a copy with capitals is
read for that spelling only, provided the older index recorded the same `.c`
files (an older POSIX index of a tree with upper-case `.C` files omitted
them, so its counts and digest do not match) and, across POSIX and Windows
path-part orders, no two paths share the same lower-case spelling (when two
paths tie in lower case, Windows `Path` sorting preserves directory traversal
order and is not guaranteed to match across platforms), until it is rebuilt;
likewise, for a non-ASCII lower-case letter whose
`casefold` differs from its lower case (`ß` folds to `ss`), `tree_digest`
and `tree_digest_casefold_v1` differ, so an older index without
`tree_digest_casefold_v1` does not match another spelling (`ẞ`) until it is
rebuilt. A tree with two paths that casefold alike, two files on a file
system that tells capitals apart, has no casefolded digest and is compared
as spelt. A path that UTF-8 cannot write (an unpaired surrogate, which NTFS
keeps) or a file that cannot be read while hashing leaves the tree's
digest uncompared: no file beside the default index matches, so the
default index is read and the index check returns its warning or SKIP line,
as before files beside it were read (when `--game-root` or `DAYZ_GAME_ROOT`
is also active, `compare_vanilla_build` opens matching `.c` files from the
tree without catching `OSError`, so an unreadable file can abort the run
before any warning, SKIP line or result is produced). `casefold` also folds
a few letters that are not ASCII (`ß` and `ss`, say); DayZ's script paths
are ASCII.

Two limits remain:

- Only the outer form of the four tables is checked: a file beside the
  default index with the tree's digest and a table emptied, or a value of
  another type inside one, is read, and gives a false PASS or an
  exception. Rebuild an index that was damaged.
- The tree is walked once (`collect_c_files`) before it is counted and
  hashed, and the generator parses each file before it hashes that list: a
  file added after the walk is not in the list (so an index of the prior
  tree can still match), and a file edited during generation after being
  parsed leaves the index with tables from the earlier content and digests
  from the later content. A file already in the list whose bytes change
  between the count and the hash produces a different digest and does not
  match the prior sibling index. Do not change a tree while it is validated
  or indexed.

Measured on the owner's PC on 2026-11-18 (Python 3.14.3, other work
running on the PC), on the 1.30.164393 tree in `P:\scripts` (3 059 `.c`
files, 14 001 771 bytes):

- Count against digest, ten rounds of one after the other: the count took
  0.28 to 0.49 s (median 0.36 s), and reading and hashing every file 1.66
  to 2.44 s (median 2.01 s), 4.6 to 6.6 times as long. On the 1.30.164289
  tree: 0.33 to 1.31 s against 1.76 to 3.40 s.
- Inside six runs of the validator over a 114-file addon with
  `--game-root`, the comparison took 0.32 to 5.81 s, 1.5 to 9.0 % of each
  run (10.8 to 64.9 s). The `--game-root` comparison, which hashes those
  files and the PBO's entries, took 1.40 to 20.4 s in those runs.
- The three trees the owner's index has been built from differ in both
  numbers: 1.29 (2 805 files, 12 566 266 bytes), 1.30.164289 (3 056,
  13 952 124) and 1.30.164393 (3 059, 14 001 771).
- With an index of the 164289 tree, that addon goes from PASS to WARN on
  this rule alone, and 164393's `targetconditionscomponents` folder gives
  the five `ES-MEMBER-REDECLARE-BASE` findings with this warning beside
  them. With the index rebuilt from the 164393 tree both runs report
  `matches`, the addon is PASS and the five findings are gone.
- A walk with `os.scandir`, which reads the sizes from the directory
  listing, gave the same two numbers on both trees in 0.03 to 0.09 s. It
  is not used: the generator and the comparison count with one function,
  `collect_c_files` in `scripts/shared/vanilla_index_tree.py`.

Measured there on 2026-11-19, with the 1.30.164289 tree back in
`P:\scripts` and the 164393 tree in a folder of its own, the default index
built from the 164289 tree and, beside it, `vanilla_index.json.164393` and
an index of 1.29, all three written before `tree_digest_casefold_v1` (other
work running on the PC):

- Three addons of 114, 77 and 3 files, validated against the 164393 tree
  with `--game-root` naming the Experimental install, go from WARN on
  this rule alone to PASS, with `info.vanilla_index.index` naming the
  `.164393` file; each run took 10.9 to 11.7 s, against 8.7 to 10.4 s
  before. Against the default tree, with the stable install, they are PASS
  on the default index before and after.
- A copy of the 164393 tree whose paths keep the PBO's capitals (the same
  3 059 files, bytes and contents) has another `tree_digest` and the same
  casefolded one: against it the 114-file addon goes from WARN to PASS,
  reading the `.164393` file.
- 164393's `targetconditionscomponents` folder, validated against its own
  tree, goes from the five `ES-MEMBER-REDECLARE-BASE` findings and this
  warning to neither.
- Ten rounds of the choice alone: against the 164393 tree 1.50 to 2.53 s
  (median 1.87 s), hashing the tree included; against the 164289 tree,
  whose numbers the default index has, 0.25 to 0.39 s (median 0.32 s). The
  count alone took 0.24 to 0.43 s, and reading one index file 0.014 to
  0.045 s.
- The generator, run on both trees, writes the same document as before
  plus `tree_digest_casefold_v1`, equal to `tree_digest` for both.

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
- `ES-FORMULA-TOO-COMPLEX` (WARN): one statement that holds a string
  literal and joins 18 or more terms with binary `+`. On DayZDiag
  1.30.164289 (inbox 7b9e/7ce1) a statement on one line alternating
  string literals with an `int` and a float's `ToString()`
  (`string s = "a" + i0 + " b" + f0.ToString() + ...`) compiled with 14
  and 17 terms and failed with 18 and 20: `Formula too complex` on its
  line, then `Incompatible parameter 'i0'` there as a cascade, and
  `Can't compile "World" script module!`. The limit is that pattern's:
  other operand types and a statement over several lines are not
  measured, so the rule warns. `++`, `+=` and a unary `+` join nothing.
  Every binary `+` of the statement counts, one inside parentheses or a
  call's arguments too, and whether the compiler counts those is not
  measured. A chain with no string literal adds numbers and is not
  judged. Build the string in steps (`s = s + part;`).
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
  the same parser rule (dayz-enforce-script-reference SKILL.md, SP-386) and is not
  reported here; neither is a call's argument list over two lines.

Each finding is wrong wherever the code compiles, so code under another
mod's `#ifdef` is judged too. A branch that never compiles is not: `#if`
blocks, and the `#ifndef` or `#else` branch of a macro the same file
`#define`s first (`scripts/shared/dead_branches.py`). An expression is never
read through a branch that never compiles, nor from the branch that holds
the `%` into another branch of the same block. Blocks are not compared by
their macros: `#ifdef X` and a later `#ifndef X` count as unrelated, so
their lines can still meet in one expression. The terms of a statement
are counted outside every block and along one branch of nested blocks at
a time: two branches of one block, or two blocks side by side, are never
counted together.

Measured on 2026-10-03: nothing on vanilla 1.29.0.163451 (69 `%` judged) or
on vanilla 1.30.164014 Exp (94 `%`), and on the source that failed in game,
`vector local;`, the reserved-word rule fires on that line. Vanilla
compiles a statement with 14 `+`. On 2026-11-10 the vanilla control found
no `ES-FORMULA-TOO-COMPLEX` on vanilla 1.30.164289 (3057 files).

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

A full run on DayZ 1.30 takes about six minutes (340 s when the baseline was
measured, on 2026-11-10). It is a gate, not a unit test — do not put it in
`unittest discover`.

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
SKIP (no tree, no baseline, unreadable, or a local
`scripts/shared/vanilla_index.json` that the validator loads: the baseline
measures the validator without one, so move that file away first; another
name in the same folder will do, since nothing beside a default index that
is not there is read).

The baseline is measured on one build, the stable one: `tree.dayz_build`
names it and `tree.digest` identifies its tree. A tree of another build
fails the control on the digest whatever the validator finds in it, so when
the default tree holds another build (an Experimental extract in
`P:\scripts`, say), keep a tree of the baseline's build beside it and name
it. An Experimental build is not a reason to `--update`: the baseline moves
when a stable patch lands.

```powershell
python scripts/vanilla_control.py --vanilla-root <tree of the baseline's build>
```

Measured on the owner's PC on 2026-11-18, with DayZ 1.30.164393 Experimental
in `P:\scripts` and the 1.30.164289 stable tree in
`P:\scripts_164289_20261105`: the control passes on the stable tree (8
errors, 431 warnings) and, with no argument, fails on the Experimental one,
on the digest and on `ES-EMPTY-IFDEF-UNSUPPORTED-PATTERN 263 > 260`. That
tree (3 060 files, 96 changed and 3 new) gives the same 8 errors and 434
warnings; the three more are one `#else` each, which the rule does not
analyse, in `constructionbase.c`, `actionmanagerclient.c` and `cctliquid.c`.

A local `scripts/shared/vanilla_index.json` holds the members and
signatures of the tree it was built from, so rebuild it when the vanilla
tree changes build (`python scripts/build_vanilla_index.py`). That day an
index of 1.30.164289 read with the 164393 tree gave five false
`ES-MEMBER-REDECLARE-BASE` findings, at
`4_world/classes/useractionscomponent/targetconditionscomponents/cctliquidsyntheticcursor.c:26-28`
and `:37-38`: 164393 moves those members of `CCTLiquid` into that new
subclass. An index built from the 164393 tree gives none. A run of the
validator with an index of another tree now warns: see "Which tree the
vanilla index is".

Every baseline entry carries the reason it is tolerated. `--update` keeps
the reasons already written and cannot invent the missing ones, so it names
every entry left without a note: an allowlist entry nobody triaged is a
finding hiding behind a gate.
