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
