"""Regression tests for extract_empties.py, the rig stage between fbx_extract.py
and build_rig_dayz.py.

extract_empties.py runs inside Blender. These tests run it against stand-in
`bpy` and `mathutils` modules that hold a scene built by hand, so they need
numpy only. Every expected position is worked out in the comment above it.
"""

import json
import os
from pathlib import Path
import runpy
import subprocess
import sys
from types import ModuleType, SimpleNamespace

import numpy as np
import pytest


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
EXTRACTOR = SCRIPTS / "extract_empties.py"
BUILD_RIG = SCRIPTS / "build_rig_dayz.py"


class Matrix:
    """The part of mathutils.Matrix the extractor uses: @, [row][col], Translation."""

    def __init__(self, rows=None):
        self.m = np.identity(4) if rows is None else np.array(rows, dtype=float)

    @classmethod
    def Translation(cls, vector):
        m = np.identity(4)
        m[:3, 3] = vector
        return cls(m)

    def __matmul__(self, other):
        return Matrix(self.m @ other.m)

    def __getitem__(self, row):
        return [float(x) for x in self.m[row]]


def _turn_z(translation=(0.0, 0.0, 0.0)):
    """+90 deg about Z (x -> y, y -> -x), then the translation."""
    m = np.array([
        [0.0, -1.0, 0.0, 0.0],
        [1.0, 0.0, 0.0, 0.0],
        [0.0, 0.0, 1.0, 0.0],
        [0.0, 0.0, 0.0, 1.0],
    ])
    m[:3, 3] = translation
    return Matrix(m)


class _Objects(list):
    """bpy.data.objects: iterable, and indexable by name."""

    def get(self, name, default=None):
        return next((o for o in self if o.name == name), default)

    def __getitem__(self, key):
        if isinstance(key, str):
            found = self.get(key)
            if found is None:
                raise KeyError(key)
            return found
        return super().__getitem__(key)


def _empty(name, parent, parent_type, parent_bone="", inverse=None, basis=None):
    # matrix_world stays at the origin, as on the helpers the BI FBX imports
    # disabled in viewports: the extractor must not read it.
    return SimpleNamespace(
        name=name, type="EMPTY", parent=parent, parent_type=parent_type,
        parent_bone=parent_bone, matrix_world=Matrix(),
        matrix_parent_inverse=inverse or Matrix(), matrix_basis=basis or Matrix(),
    )


def _scene(with_right_hand=True):
    arm = SimpleNamespace(
        name="Armature", type="ARMATURE", parent=None, parent_type="OBJECT", parent_bone="",
        matrix_world=Matrix.Translation((10.0, 0.0, 0.0)),
        matrix_parent_inverse=Matrix(), matrix_basis=Matrix.Translation((10.0, 0.0, 0.0)),
        # pose matrices, armature space: RightHand turned 90 deg about Z, head (0,0,5)
        pose=SimpleNamespace(bones={
            "RightHand": SimpleNamespace(matrix=_turn_z((0.0, 0.0, 5.0))),
            "LeftHand": SimpleNamespace(matrix=Matrix.Translation((0.0, 0.0, 5.0))),
        }),
        data=SimpleNamespace(bones={
            "RightHand": SimpleNamespace(length=2.0),
            "LeftHand": SimpleNamespace(length=3.0),
        }),
    )
    objects = [arm]
    if with_right_hand:
        hand = _empty("RightHand_Dummy", arm, "BONE", "RightHand",
                      basis=Matrix.Translation((0.0, 0.0, 1.0)))
        objects += [hand, _empty("Weapon_Root", hand, "OBJECT",
                                 basis=Matrix.Translation((1.0, 0.0, 0.0)))]
    objects += [
        _empty("LeftHand_Dummy", arm, "BONE", "LeftHand", inverse=_turn_z(),
               basis=Matrix.Translation((4.0, 0.0, 0.0))),
        _empty("Lamp_Helper", arm, "BONE", "LeftHand"),
        SimpleNamespace(name="Male_body", type="MESH", parent=arm, parent_type="OBJECT",
                        parent_bone=""),
    ]
    return _Objects(objects)


def _run_extractor(monkeypatch, scratch, objects):
    """Run the script as Blender would, after the FBX import left `objects`."""
    imported = []
    bpy = ModuleType("bpy")
    bpy.ops = SimpleNamespace(
        wm=SimpleNamespace(read_factory_settings=lambda use_empty=False: None),
        import_scene=SimpleNamespace(fbx=lambda filepath: imported.append(filepath)),
    )
    bpy.context = SimpleNamespace(view_layer=SimpleNamespace(update=lambda: None))
    bpy.data = SimpleNamespace(objects=objects)
    mathutils = ModuleType("mathutils")
    mathutils.Matrix = Matrix
    monkeypatch.setitem(sys.modules, "bpy", bpy)
    monkeypatch.setitem(sys.modules, "mathutils", mathutils)
    monkeypatch.setenv("DAYZ_ANIM_SCRATCH", str(scratch))
    runpy.run_path(str(EXTRACTOR), run_name="__main__")
    return imported


def _positions(empties):
    return {name: [round(m[r][3], 6) for r in range(3)] for name, m in empties.items()}


def test_helpers_are_composed_through_their_parent_chain(tmp_path, monkeypatch):
    """Breaks if the file moves, matrix_world leaks in, or the chain order changes."""
    _run_extractor(monkeypatch, tmp_path, _scene())

    out = json.loads((tmp_path / "empties_armworld.json").read_text(encoding="utf-8"))
    assert sorted(out) == ["LeftHand_Dummy", "RightHand_Dummy", "Weapon_Root"]
    pos = _positions(out)
    # Armature (10,0,0) + head (0,0,5); the bone is turned 90 deg about Z, so
    # its tail (0,2,0) lands at (-2,0,0) while the empty's own (0,0,1) stays.
    assert pos["RightHand_Dummy"] == [8.0, 0.0, 6.0]
    # Child of RightHand_Dummy: its own (1,0,0) turns with it to (0,1,0).
    assert pos["Weapon_Root"] == [8.0, 1.0, 6.0]
    # (10,0,0) + head (0,0,5) + tail (0,3,0); the parent inverse turns the
    # empty's own (4,0,0) to (0,4,0). In the other order it would stay (4,0,0).
    assert pos["LeftHand_Dummy"] == [10.0, 7.0, 5.0]
    turn = [[round(v, 6) for v in row[:3]] for row in out["RightHand_Dummy"][:3]]
    assert turn == [[0.0, -1.0, 0.0], [1.0, 0.0, 0.0], [0.0, 0.0, 1.0]]
    assert out["RightHand_Dummy"][3] == [0.0, 0.0, 0.0, 1.0]


def test_build_rig_dayz_turns_the_file_into_anchors(tmp_path, monkeypatch):
    """Breaks if build_rig_dayz.py stops finding the extractor's file or reading it."""
    _run_extractor(monkeypatch, tmp_path, _scene())
    # Mesh vertices on the bone heads: build_rig_dayz.py aligns at scale 1 with
    # no shift, and only the viewer frame (x, y, z) -> (x, z, -y) is left.
    heads = {
        "Pelvis": (0.0, 0.0, 1.0), "Neck": (0.0, 0.0, 1.8), "Head": (0.0, 0.0, 2.0),
        "RightHand": (-1.0, 0.0, 1.5), "LeftHand": (1.0, 0.0, 1.5),
        "RightFoot": (-0.2, 0.0, 0.0), "LeftFoot": (0.2, 0.0, 0.0),
    }
    rig = {
        "bones": [
            {"name": name, "parent": None if name == "Pelvis" else "Pelvis",
             "world": Matrix.Translation(head).m.tolist(), "length": 0.1}
            for name, head in heads.items()
        ],
        "mesh": {
            "verts": [list(head) for head in heads.values()],
            "faces": [[0, 1, 2]],
            "weights": [[["Pelvis", 1.0]] for _ in heads],
        },
    }
    (tmp_path / "rig_raw.json").write_text(json.dumps(rig), encoding="utf-8")

    done = subprocess.run(
        [sys.executable, str(BUILD_RIG)],
        env=dict(os.environ, DAYZ_ANIM_SCRATCH=str(tmp_path)),
        capture_output=True, text=True,
    )

    assert done.returncode == 0, done.stderr
    anchors = json.loads((tmp_path / "rig_dayz.json").read_text(encoding="utf-8"))["anchors"]
    assert sorted(anchors) == ["LeftHand_Dummy", "RightHand_Dummy", "Weapon_Root"]
    # (8,0,6) -> (8,6,0) and (8,1,6) -> (8,6,-1)
    assert anchors["RightHand_Dummy"]["pos"] == [8.0, 6.0, 0.0]
    assert anchors["Weapon_Root"]["pos"] == [8.0, 6.0, -1.0]


def test_no_file_without_right_hand_dummy(tmp_path, monkeypatch):
    """Breaks if a rig without the weapon anchor still yields a file: build_viewer.py
    would then place the weapon at its fixed (0, 1.3, 0.2) without a word."""
    with pytest.raises(SystemExit) as stopped:
        _run_extractor(monkeypatch, tmp_path, _scene(with_right_hand=False))

    assert "RightHand_Dummy" in str(stopped.value.code)
    assert not (tmp_path / "empties_armworld.json").exists()


def test_both_extractors_ship_the_same_fbx(tmp_path, monkeypatch):
    """Breaks if the default FBX paths drift apart: build_rig_dayz.py pairs
    rig_raw.json with empties_armworld.json, so both come from one FBX."""
    imported = _run_extractor(monkeypatch, tmp_path, _scene())

    assert len(imported) == 1
    assert imported[0] in (SCRIPTS / "fbx_extract.py").read_text(encoding="utf-8")
