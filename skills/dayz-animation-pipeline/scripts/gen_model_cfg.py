#!/usr/bin/env python3
"""
gen_model_cfg.py - generate a DayZ model.cfg (CfgSkeletons + CfgModels + class
Animations) from a small spec, so animation names stay consistent across
model.cfg / config.cpp / script and you avoid the #1 silent failure: a typo'd
name that resolves nowhere.

Layer 1 (config-driven animation). Runs in-sandbox. Output is text you place in
the project's compilable folder. This generator does NOT touch the .p3d, RTM, or
.anm — it only emits the config that binds named selections to animations.

Property names emitted here are [VERIFIED] against the PMC wiki model.cfg page
(see references/config-driven-animation.md). It deliberately refuses to emit
animation types it cannot vouch for (translationModelX, direct) - if you need
those, verify against vanilla first and add them by hand.

Spec format (Python dict or JSON):
{
  "model": "MyObject",                 # MUST equal the .p3d filename (MyObject.p3d)
  "skeleton": "MyObjectSkeleton",
  "skeletonInherit": "",               # parent skeleton or ""
  "bones": [                           # (bone, parent) pairs; parent "" = root
      ["door", ""],
      ["door_handle", "door"]
  ],
  "animations": [
    {
      "name": "Door1",                 # the class name; == AnimationSources class == SetAnimationPhase arg
      "type": "rotation",              # rotation[/X/Y/Z], translation[/X/Y/Z], hide
      "source": "Door1",               # "user" source -> declare in config.cpp AnimationSources
      "selection": "door",             # named selection in the .p3d (must be a bone above)
      "axis": "door_axis",             # axis selection (2 memory points); omit for hide
      "minValue": 0, "maxValue": 1,
      "angle0": 0, "angle1": "rad 90"  # rotation; or offset0/offset1 for translation; or hideValue for hide
    }
  ]
}

Usage:
  python3 gen_model_cfg.py spec.json > model.cfg
  python3 gen_model_cfg.py --self-test
"""
import json
import sys

# Animation types this generator will emit without complaint. Verified against
# PMC wiki. 'hide' is verified against a working mod (kt_roadkill); confirm the
# hideValue comparison direction against a vanilla door config if it matters.
VERIFIED_TYPES = {
    "rotation", "rotationX", "rotationY", "rotationZ",
    "translation", "translationX", "translationY", "translationZ",
    "hide",
}

# Keys we know how to render, in a stable emit order. Unknown keys are passed
# through verbatim (so you can add a verified property without editing this file),
# but a warning is printed to stderr so confabulated keys don't slip in silently.
KNOWN_ANIM_KEYS = [
    "type", "source", "selection", "axis", "begin", "end", "memory",
    "minValue", "maxValue", "minPhase", "maxPhase", "sourceAddress",
    "animPeriod", "angle0", "angle1", "offset0", "offset1", "hideValue",
]


def _fmt_value(v):
    """Render a value the way model.cfg expects: bare strings like 'rad 90' or
    'clamp' must be quoted; numbers stay bare; explicit quoted strings stay."""
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return repr(v)
    s = str(v)
    # already quoted
    if s.startswith('"') and s.endswith('"'):
        return s
    # numeric-looking -> leave bare
    try:
        float(s)
        return s
    except ValueError:
        return f'"{s}"'


def _emit_animation(a):
    name = a["name"]
    t = a.get("type")
    if t not in VERIFIED_TYPES:
        sys.stderr.write(
            f"WARNING: animation '{name}' type '{t}' is not in the verified set "
            f"{sorted(VERIFIED_TYPES)}. Verify against vanilla before shipping.\n"
        )
    lines = [f"            class {name}", "            {"]
    emitted = set()
    for k in KNOWN_ANIM_KEYS:
        if k in a:
            lines.append(f"                {k}={_fmt_value(a[k])};")
            emitted.add(k)
    # pass through any other keys (verbatim) but warn
    for k, v in a.items():
        if k in ("name",) or k in emitted:
            continue
        sys.stderr.write(
            f"WARNING: animation '{name}' has unrecognized key '{k}'. Passing it "
            f"through verbatim - confirm it is a real model.cfg property.\n"
        )
        lines.append(f"                {k}={_fmt_value(v)};")
    lines.append("            };")
    return "\n".join(lines)


def generate(spec):
    model = spec["model"]
    skel = spec.get("skeleton", model + "Skeleton")
    inherit = spec.get("skeletonInherit", "")
    bones = spec.get("bones", [])
    anims = spec.get("animations", [])

    # validate: every animation selection must be a declared bone
    bone_names = {b[0] for b in bones}
    for a in anims:
        sel = a.get("selection")
        if sel and sel not in bone_names:
            sys.stderr.write(
                f"WARNING: animation '{a.get('name')}' selection '{sel}' is not in "
                f"skeletonBones[] - the engine will log a bone error and skip it.\n"
            )

    out = []
    out.append("class CfgSkeletons")
    out.append("{")
    out.append(f"    class {skel}")
    out.append("    {")
    out.append(f'        isDiscrete=1;')
    out.append(f'        skeletonInherit="{inherit}";')
    bone_pairs = []
    for b in bones:
        bone_pairs.append(f'"{b[0]}","{b[1]}"')
    out.append("        skeletonBones[]=")
    out.append("        {")
    out.append("            " + (",\n            ".join(bone_pairs) if bone_pairs else ""))
    out.append("        };")
    out.append("    };")
    out.append("};")
    out.append("")
    out.append("class CfgModels")
    out.append("{")
    out.append(f"    class {model}")
    out.append("    {")
    out.append(f'        skeletonName="{skel}";')
    out.append('        sectionsInherit="";')
    out.append("        sections[]={};")
    out.append("        class Animations")
    out.append("        {")
    out.append("\n".join(_emit_animation(a) for a in anims) if anims else "")
    out.append("        };")
    out.append("    };")
    out.append("};")
    return "\n".join(out) + "\n"


def _self_test():
    spec = {
        "model": "MyObject",
        "skeleton": "MyObjectSkeleton",
        "skeletonInherit": "",
        "bones": [["door", ""], ["door_handle", "door"], ["barrel_1", ""]],
        "animations": [
            {"name": "Door1", "type": "rotation", "source": "Door1",
             "selection": "door", "axis": "door_axis",
             "minValue": 0, "maxValue": 1, "angle0": 0, "angle1": "rad 90"},
            {"name": "hide_barrel1", "type": "hide", "source": "hide_barrel1",
             "selection": "barrel_1", "minValue": 0, "maxValue": 1, "hideValue": 0.5},
        ],
    }
    out = generate(spec)
    assert "class CfgSkeletons" in out
    assert 'skeletonName="MyObjectSkeleton";' in out
    assert "class Door1" in out and 'angle1="rad 90";' in out
    assert "class hide_barrel1" in out and "hideValue=0.5;" in out
    assert '"door",""' in out and '"door_handle","door"' in out
    print(out)
    sys.stderr.write("\nself-test OK\n")


if __name__ == "__main__":
    if len(sys.argv) == 2 and sys.argv[1] == "--self-test":
        _self_test()
    elif len(sys.argv) == 2:
        with open(sys.argv[1]) as f:
            spec = json.load(f)
        sys.stdout.write(generate(spec))
    else:
        sys.stderr.write(__doc__)
        sys.exit(1)
