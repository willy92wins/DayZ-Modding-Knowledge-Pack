from __future__ import annotations

import importlib.util
import inspect
import json
import sys
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).parents[1] / "dayz_ui_lab" / "parse.py"
SPEC = importlib.util.spec_from_file_location("dayz_layout_phase1_parse", MODULE_PATH)
assert SPEC is not None
assert SPEC.loader is not None
parse = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = parse
SPEC.loader.exec_module(parse)


class Phase1ParserTests(unittest.TestCase):
    def test_multiroot_bom_block_comments_and_float_edges(self) -> None:
        text = """\ufeff/* block comment */
FrameWidgetClass Root {
    position .5 1.
    size 1 .25
    visible 0
    {
        TextWidgetClass Label {
            scriptclass "ViewBinding"
            "text halign" center
            text "Hello"
            {
                ScriptParamsClass {
                    Binding_Name "HeaderTitle"
                }
            }
        }
    }
}
FrameWidgetClass Other {
    {
    }
}
"""
        doc = parse.parse_text(text, source_path="fixture.layout", canvas_width=200, canvas_height=100)
        data = doc.to_dict()

        self.assertEqual(data["stats"]["rootCount"], 2)
        self.assertEqual(data["stats"]["widgetCount"], 3)
        self.assertEqual(data["stats"]["geometryWidgetCount"], 3)
        self.assertEqual(data["stats"]["renderedWidgetCount"], 1)
        self.assertEqual(data["stats"]["visualWidgetCount"], 1)
        self.assertEqual(data["stats"]["metadataCount"], 1)
        self.assertEqual(data["roots"][0]["geometry"]["raw"]["position"], [0.5, 1.0])
        self.assertFalse(data["roots"][0]["geometry"]["visible"])
        label = data["roots"][0]["children"][0]
        self.assertEqual(label["bindingName"], "HeaderTitle")
        self.assertEqual(label["attrs"]["text halign"], ["center"])

    def test_layout_json_snapshot_shape(self) -> None:
        text = """FrameWidgetClass Root {
    position 0 0
    size 100 50
    hexactpos 1
    vexactpos 1
    hexactsize 1
    vexactsize 1
    {
    }
}
"""
        doc = parse.parse_text(text, source_path="snapshot.layout", canvas_width=200, canvas_height=100)
        actual = json.loads(doc.to_json())
        expected = {
            "schemaVersion": 1,
            "generator": "renderer/parse.py phase1",
            "source": {"path": "snapshot.layout"},
            "canvas": {"width": 200, "height": 100},
            "renderState": {"mode": "raw-layout"},
            "stats": {
                "rootCount": 1,
                "nodeCount": 1,
                "widgetCount": 1,
                "geometryWidgetCount": 1,
                "renderedWidgetCount": 0,
                "visualWidgetCount": 0,
                "metadataCount": 0,
            },
            "roots": [
                {
                    "class": "FrameWidgetClass",
                    "name": "Root",
                    "source": {"line": 1, "column": 1},
                    "isMetadata": False,
                    "attrs": {
                        "position": [0, 0],
                        "size": [100, 50],
                        "hexactpos": [1],
                        "vexactpos": [1],
                        "hexactsize": [1],
                        "vexactsize": [1],
                    },
                    "children": [],
                    "geometry": {
                        "status": "resolved",
                        "notes": [],
                        "anchor": {"horizontal": "left_ref", "vertical": "top_ref"},
                        "flags": {
                            "hexactpos": 1,
                            "vexactpos": 1,
                            "hexactsize": 1,
                            "vexactsize": 1,
                        },
                        "position": {"x": 0.0, "y": 0.0},
                        "offset": {"x": 0.0, "y": 0.0},
                        "size": {"width": 100.0, "height": 50.0},
                        "raw": {"position": [0.0, 0.0], "size": [100.0, 50.0]},
                        "visible": True,
                        "ignorePointer": False,
                        "clipChildren": False,
                        "alpha": None,
                    },
                }
            ],
        }
        self.assertEqual(actual, expected)

    def test_error_reports_line_and_column(self) -> None:
        text = """FrameWidgetClass Root {
    position 0 0
"""
        with self.assertRaises(parse.LayoutSyntaxError) as raised:
            parse.parse_text(text, source_path="broken.layout")
        self.assertIn("broken.layout:3:1", str(raised.exception))

    def test_widgetclass_leaf_without_child_block_is_valid(self) -> None:
        text = """FrameWidgetClass Root {
    {
        TextWidgetClass Label {
            text "No child block"
        }
    }
}
"""
        doc = parse.parse_text(text, source_path="missing-child-block.layout")
        data = doc.to_dict()
        self.assertNotIn("diagnostics", data)
        self.assertFalse(doc.roots[0].children[0].has_child_block)

    def test_false_strict_child_block_contract_is_not_exposed(self) -> None:
        self.assertNotIn("strict_child_blocks", inspect.signature(parse.Parser).parameters)
        self.assertNotIn("strict_child_blocks", inspect.signature(parse.parse_text).parameters)
        self.assertNotIn("strict_child_blocks", inspect.signature(parse.parse_file).parameters)
        self.assertNotIn(
            "--strict-child-blocks",
            parse.build_arg_parser()._option_string_actions,
        )

    def test_out_dir_preserves_layout_root_relative_path(self) -> None:
        root = Path("C:/layouts")
        out_dir = Path("C:/out")
        medium = Path("C:/layouts/inventory_new/medium/cargo_container.layout")
        narrow = Path("C:/layouts/inventory_new/narrow/cargo_container.layout")

        medium_out = out_dir / parse.layout_json_relative_path(medium, [root])
        narrow_out = out_dir / parse.layout_json_relative_path(narrow, [root])

        self.assertEqual(
            medium_out,
            Path("C:/out/inventory_new/medium/cargo_container.layout.json"),
        )
        self.assertEqual(
            narrow_out,
            Path("C:/out/inventory_new/narrow/cargo_container.layout.json"),
        )
        self.assertNotEqual(medium_out, narrow_out)

    def test_source_display_path_can_be_relative(self) -> None:
        root = Path("C:/layouts")
        layout = Path("C:/layouts/gui/day_z_hud.layout")
        self.assertEqual(parse.source_display_path(layout, root), "gui/day_z_hud.layout")


if __name__ == "__main__":
    unittest.main()
