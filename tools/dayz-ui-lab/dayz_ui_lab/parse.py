"""
DayZ .layout parser -> LayoutDoc JSON (renderer v2, phase 1).

This module is the testable parser/resolver side of the v2 architecture:
.layout text is tokenized and parsed into WidgetNode roots, then exported as a
LayoutDoc JSON document with raw attributes and phase-1 geometry metadata.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


Scalar = int | float | str

SCHEMA_VERSION = 1
DEFAULT_CANVAS_WIDTH = 1920
DEFAULT_CANVAS_HEIGHT = 1080

METADATA_CLASSES = {"ScriptParamsClass"}
VISUAL_CLASS_SUFFIX = "WidgetClass"
NON_RENDERED_WIDGET_CLASSES = {
    "FrameWidgetClass",
    "PanelWidgetClass",
    "ScrollWidgetClass",
    "GridSpacerWidgetClass",
    "WrapSpacerWidgetClass",
    "CanvasWidgetClass",
}


@dataclass(frozen=True)
class Token:
    kind: str
    value: Scalar | str | None
    line: int
    column: int
    index: int


class LayoutSyntaxError(SyntaxError):
    def __init__(self, message: str, token: Token | None = None, source: str = ""):
        self.token = token
        self.source = source
        if token is not None:
            location = f"{token.line}:{token.column}"
            if source:
                location = f"{source}:{location}"
            message = f"{location}: {message}"
        super().__init__(message)


@dataclass
class WidgetNode:
    cls: str
    name: str = ""
    attrs: dict[str, list[Scalar]] = field(default_factory=dict)
    children: list["WidgetNode"] = field(default_factory=list)
    line: int = 1
    column: int = 1
    has_child_block: bool = False


@dataclass
class LayoutDoc:
    source_path: str
    roots: list[WidgetNode]
    canvas_width: int = DEFAULT_CANVAS_WIDTH
    canvas_height: int = DEFAULT_CANVAS_HEIGHT
    diagnostics: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        stats = collect_stats(self.roots)
        result = {
            "schemaVersion": SCHEMA_VERSION,
            "generator": "renderer/parse.py phase1",
            "source": {
                "path": self.source_path,
            },
            "canvas": {
                "width": self.canvas_width,
                "height": self.canvas_height,
            },
            "renderState": {
                "mode": "raw-layout",
            },
            "stats": stats,
            "roots": [
                widget_to_dict(root, self.canvas_width, self.canvas_height)
                for root in self.roots
            ],
        }
        if self.diagnostics:
            result["diagnostics"] = self.diagnostics
        return result

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2, sort_keys=True)


NUMBER_RE = re.compile(r"-?(?:(?:\d+\.\d*)|(?:\.\d+)|(?:\d+))")
IDENT_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


def tokenize(text: str, source: str = "") -> list[Token]:
    tokens: list[Token] = []
    i = 0
    line = 1
    column = 1

    def advance(fragment: str) -> None:
        nonlocal line, column
        for char in fragment:
            if char == "\n":
                line = line + 1
                column = 1
            else:
                column = column + 1

    length = len(text)
    while i < length:
        char = text[i]

        if char == "\ufeff":
            i = i + 1
            column = column + 1
            continue

        if char.isspace():
            start = i
            while i < length and text[i].isspace():
                i = i + 1
            advance(text[start:i])
            continue

        if text.startswith("//", i):
            start = i
            i = i + 2
            while i < length and text[i] != "\n":
                i = i + 1
            advance(text[start:i])
            continue

        if text.startswith("/*", i):
            start_line = line
            start_column = column
            start = i
            end = text.find("*/", i + 2)
            if end == -1:
                token = Token("COMMENT", None, start_line, start_column, start)
                raise LayoutSyntaxError("Unterminated block comment", token, source)
            i = end + 2
            advance(text[start:i])
            continue

        if char == "{":
            tokens.append(Token("LBRACE", char, line, column, i))
            i = i + 1
            column = column + 1
            continue

        if char == "}":
            tokens.append(Token("RBRACE", char, line, column, i))
            i = i + 1
            column = column + 1
            continue

        if char == '"':
            token_line = line
            token_column = column
            token_index = i
            i = i + 1
            column = column + 1
            value_parts: list[str] = []
            while i < length:
                current = text[i]
                if current == '"':
                    i = i + 1
                    column = column + 1
                    break
                if current == "\\":
                    if i + 1 >= length:
                        token = Token("STR", "", token_line, token_column, token_index)
                        raise LayoutSyntaxError("Unterminated string escape", token, source)
                    escaped = text[i + 1]
                    value_parts.append(_decode_escape(escaped))
                    i = i + 2
                    column = column + 2
                    continue
                value_parts.append(current)
                if current == "\n":
                    line = line + 1
                    column = 1
                else:
                    column = column + 1
                i = i + 1
            else:
                token = Token("STR", "", token_line, token_column, token_index)
                raise LayoutSyntaxError("Unterminated string", token, source)

            tokens.append(Token("STR", "".join(value_parts), token_line, token_column, token_index))
            continue

        num_match = NUMBER_RE.match(text, i)
        if num_match:
            raw = num_match.group(0)
            value: Scalar
            if "." in raw:
                value = float(raw)
            else:
                value = int(raw)
            tokens.append(Token("NUM", value, line, column, i))
            i = num_match.end()
            column = column + len(raw)
            continue

        ident_match = IDENT_RE.match(text, i)
        if ident_match:
            raw = ident_match.group(0)
            tokens.append(Token("IDENT", raw, line, column, i))
            i = ident_match.end()
            column = column + len(raw)
            continue

        token = Token("UNKNOWN", char, line, column, i)
        raise LayoutSyntaxError(f"Unexpected character {char!r}", token, source)

    tokens.append(Token("EOF", None, line, column, i))
    return tokens


def _decode_escape(char: str) -> str:
    escapes = {
        "n": "\n",
        "r": "\r",
        "t": "\t",
        '"': '"',
        "\\": "\\",
    }
    return escapes.get(char, char)


class Parser:
    def __init__(
        self,
        tokens: list[Token],
        source: str = "",
    ):
        self.tokens = tokens
        self.index = 0
        self.source = source
        self.diagnostics: list[dict[str, Any]] = []

    def peek(self, offset: int = 0) -> Token:
        idx = self.index + offset
        if idx < len(self.tokens):
            return self.tokens[idx]
        return self.tokens[-1]

    def consume(self) -> Token:
        token = self.peek()
        if token.kind != "EOF":
            self.index = self.index + 1
        return token

    def expect(self, kind: str) -> Token:
        token = self.peek()
        if token.kind != kind:
            raise LayoutSyntaxError(
                f"Expected {kind}, got {token.kind}={token.value!r}",
                token,
                self.source,
            )
        return self.consume()

    def parse_layout(self) -> list[WidgetNode]:
        roots: list[WidgetNode] = []
        while self.peek().kind != "EOF":
            if self.peek().kind == "RBRACE":
                raise LayoutSyntaxError("Unmatched closing brace", self.peek(), self.source)
            roots.append(self.parse_widget())
        return roots

    def parse_widget(self) -> WidgetNode:
        cls_token = self.expect("IDENT")
        cls = str(cls_token.value)
        name = ""

        if self.peek().kind in ("IDENT", "STR") and self.peek(1).kind == "LBRACE":
            name = str(self.consume().value)

        self.expect("LBRACE")
        attrs, children, child_block_count = self.parse_body()
        self.expect("RBRACE")
        return WidgetNode(
            cls=cls,
            name=name,
            attrs=attrs,
            children=children,
            line=cls_token.line,
            column=cls_token.column,
            has_child_block=child_block_count > 0,
        )

    def parse_body(self) -> tuple[dict[str, list[Scalar]], list[WidgetNode], int]:
        attrs: dict[str, list[Scalar]] = {}
        children: list[WidgetNode] = []
        child_block_count = 0

        while True:
            token = self.peek()
            if token.kind == "RBRACE":
                break
            if token.kind == "EOF":
                raise LayoutSyntaxError("Unclosed widget body", token, self.source)

            if token.kind == "LBRACE":
                self.consume()
                child_block_count = child_block_count + 1
                children.extend(self.parse_child_block())
                continue

            if token.kind in ("IDENT", "STR"):
                key_token = self.consume()
                key = str(key_token.value)
                attrs[key] = self.parse_values(key_token.line)
                continue

            raise LayoutSyntaxError(
                f"Unexpected token in widget body: {token.kind}={token.value!r}",
                token,
                self.source,
            )

        return attrs, children, child_block_count

    def parse_child_block(self) -> list[WidgetNode]:
        children: list[WidgetNode] = []
        while True:
            token = self.peek()
            if token.kind == "RBRACE":
                self.consume()
                return children
            if token.kind == "EOF":
                raise LayoutSyntaxError("Unclosed child block", token, self.source)
            children.append(self.parse_widget())

    def parse_values(self, line: int) -> list[Scalar]:
        values: list[Scalar] = []
        while self.peek().kind in ("NUM", "STR", "IDENT") and self.peek().line == line:
            token = self.consume()
            values.append(token.value)  # type: ignore[arg-type]
        return values


def parse_text(
    text: str,
    source_path: str = "<memory>",
    canvas_width: int = DEFAULT_CANVAS_WIDTH,
    canvas_height: int = DEFAULT_CANVAS_HEIGHT,
) -> LayoutDoc:
    tokens = tokenize(text, source_path)
    parser = Parser(tokens, source_path)
    roots = parser.parse_layout()
    return LayoutDoc(
        source_path=source_path,
        roots=roots,
        canvas_width=canvas_width,
        canvas_height=canvas_height,
        diagnostics=parser.diagnostics,
    )


def parse_file(
    path: Path,
    canvas_width: int = DEFAULT_CANVAS_WIDTH,
    canvas_height: int = DEFAULT_CANVAS_HEIGHT,
    source_path_override: str | None = None,
) -> LayoutDoc:
    text = path.read_text(encoding="utf-8-sig")
    return parse_text(
        text,
        source_path=source_path_override or str(path),
        canvas_width=canvas_width,
        canvas_height=canvas_height,
    )


def attr_values(node: WidgetNode, key: str) -> list[Scalar] | None:
    return node.attrs.get(key)


def attr_first(node: WidgetNode, key: str, default: Scalar | None = None) -> Scalar | None:
    values = attr_values(node, key)
    if values is None or len(values) == 0:
        return default
    return values[0]


def attr_int(node: WidgetNode, key: str, default: int | None = None) -> int | None:
    value = attr_first(node, key, default)
    if value is None:
        return None
    return int(value)


def attr_float(node: WidgetNode, key: str, default: float | None = None) -> float | None:
    value = attr_first(node, key, default)
    if value is None:
        return None
    return float(value)


def attr_str(node: WidgetNode, key: str, default: str = "") -> str:
    value = attr_first(node, key, default)
    return str(value)


def attr_pair(node: WidgetNode, key: str, default: tuple[float, float]) -> tuple[float, float]:
    values = attr_values(node, key)
    if values is None:
        return default
    first = float(values[0]) if len(values) > 0 else default[0]
    second = float(values[1]) if len(values) > 1 else default[1]
    return first, second


def is_metadata_node(node: WidgetNode) -> bool:
    return node.cls in METADATA_CLASSES


def is_widget_node(node: WidgetNode) -> bool:
    return node.cls.endswith(VISUAL_CLASS_SUFFIX)


def is_rendered_widget(node: WidgetNode) -> bool:
    return is_widget_node(node) and node.cls not in NON_RENDERED_WIDGET_CLASSES


def find_script_param(node: WidgetNode, key: str) -> str:
    for child in node.children:
        if child.cls != "ScriptParamsClass":
            continue
        value = attr_first(child, key)
        if value is not None:
            return str(value)
    return ""


def widget_to_dict(
    node: WidgetNode,
    parent_width: float,
    parent_height: float,
) -> dict[str, Any]:
    geometry = resolve_geometry(node, parent_width, parent_height)
    child_parent_width = parent_width
    child_parent_height = parent_height
    if geometry is not None:
        child_parent_width = geometry["size"]["width"]
        child_parent_height = geometry["size"]["height"]

    result: dict[str, Any] = {
        "class": node.cls,
        "name": node.name,
        "source": {
            "line": node.line,
            "column": node.column,
        },
        "isMetadata": is_metadata_node(node),
        "attrs": node.attrs,
        "children": [
            widget_to_dict(child, child_parent_width, child_parent_height)
            for child in node.children
        ],
    }

    if geometry is not None:
        result["geometry"] = geometry

    binding_name = find_script_param(node, "Binding_Name")
    if binding_name:
        result["bindingName"] = binding_name

    relay_command = find_script_param(node, "Relay_Command")
    if relay_command:
        result["relayCommand"] = relay_command

    return result


def resolve_geometry(
    node: WidgetNode,
    parent_width: float,
    parent_height: float,
) -> dict[str, Any] | None:
    if not is_widget_node(node):
        return None

    pos_x, pos_y = attr_pair(node, "position", (0.0, 0.0))
    size_w, size_h = attr_pair(node, "size", (0.0, 0.0))

    h_exact_pos = attr_int(node, "hexactpos", 0)
    v_exact_pos = attr_int(node, "vexactpos", 0)
    h_exact_size = attr_int(node, "hexactsize", 0)
    v_exact_size = attr_int(node, "vexactsize", 0)

    width = size_w if h_exact_size == 1 else parent_width * size_w
    height = size_h if v_exact_size == 1 else parent_height * size_h
    offset_x = pos_x if h_exact_pos == 1 else parent_width * pos_x
    offset_y = pos_y if v_exact_pos == 1 else parent_height * pos_y

    halign = attr_str(node, "halign", "left_ref")
    valign = attr_str(node, "valign", "top_ref")

    notes: list[str] = []
    status = "resolved"
    x = offset_x
    y = offset_y

    if halign in ("left_ref", "left", "0"):
        x = offset_x
    elif halign in ("center_ref", "center", "1"):
        x = (parent_width * 0.5) - (width * 0.5) + offset_x
        status = "assumed"
        notes.append("center_ref semantics are carried as a phase-1 assumption")
    elif halign in ("right_ref", "right", "2"):
        x = parent_width - width - offset_x
        status = "assumed"
        notes.append("right_ref offset sign is unverified until phase 2 discovery")
    else:
        status = "unknown-anchor"
        notes.append(f"Unsupported halign {halign!r}; left_ref fallback used")

    if valign in ("top_ref", "top", "0"):
        y = offset_y
    elif valign in ("center_ref", "center", "1"):
        y = (parent_height * 0.5) - (height * 0.5) + offset_y
        status = "assumed"
        notes.append("center_ref semantics are carried as a phase-1 assumption")
    elif valign in ("bottom_ref", "bottom", "2"):
        y = parent_height - height - offset_y
        status = "assumed"
        notes.append("bottom_ref offset sign is unverified until phase 2 discovery")
    else:
        status = "unknown-anchor"
        notes.append(f"Unsupported valign {valign!r}; top_ref fallback used")

    visible_value = attr_int(node, "visible", 1)
    ignorepointer_value = attr_int(node, "ignorepointer", 0)
    clipchildren_value = attr_int(node, "clipchildren", 0)
    alpha_value = attr_float(node, "alpha", None)

    return {
        "status": status,
        "notes": notes,
        "anchor": {
            "horizontal": halign,
            "vertical": valign,
        },
        "flags": {
            "hexactpos": h_exact_pos,
            "vexactpos": v_exact_pos,
            "hexactsize": h_exact_size,
            "vexactsize": v_exact_size,
        },
        "position": {
            "x": round(x, 6),
            "y": round(y, 6),
        },
        "offset": {
            "x": round(offset_x, 6),
            "y": round(offset_y, 6),
        },
        "size": {
            "width": round(width, 6),
            "height": round(height, 6),
        },
        "raw": {
            "position": [pos_x, pos_y],
            "size": [size_w, size_h],
        },
        "visible": bool(visible_value),
        "ignorePointer": bool(ignorepointer_value),
        "clipChildren": bool(clipchildren_value),
        "alpha": alpha_value,
    }


def collect_stats(roots: list[WidgetNode]) -> dict[str, int]:
    stats = {
        "rootCount": len(roots),
        "nodeCount": 0,
        "widgetCount": 0,
        "geometryWidgetCount": 0,
        "renderedWidgetCount": 0,
        "visualWidgetCount": 0,
        "metadataCount": 0,
    }

    def visit(node: WidgetNode) -> None:
        stats["nodeCount"] = stats["nodeCount"] + 1
        if is_metadata_node(node):
            stats["metadataCount"] = stats["metadataCount"] + 1
        if is_widget_node(node):
            stats["widgetCount"] = stats["widgetCount"] + 1
            stats["geometryWidgetCount"] = stats["geometryWidgetCount"] + 1
        if is_rendered_widget(node):
            stats["renderedWidgetCount"] = stats["renderedWidgetCount"] + 1
            stats["visualWidgetCount"] = stats["visualWidgetCount"] + 1
        for child in node.children:
            visit(child)

    for root in roots:
        visit(root)
    return stats


def resolve_layout_path(layout_ref: str, layout_roots: list[Path]) -> Path:
    direct = Path(layout_ref)
    if direct.exists():
        return direct.resolve()

    for root in layout_roots:
        candidate = root / layout_ref
        if candidate.exists():
            return candidate.resolve()

    searched = ", ".join(str(root) for root in layout_roots) or "(none)"
    raise FileNotFoundError(f"layout not found: {layout_ref}; searched roots: {searched}")


def relative_to_any_root(path: Path, roots: list[Path]) -> Path | None:
    resolved_path = path.resolve()
    resolved_roots = sorted(
        (root.resolve() for root in roots),
        key=lambda value: len(str(value)),
        reverse=True,
    )
    for root in resolved_roots:
        try:
            return resolved_path.relative_to(root)
        except ValueError:
            continue
    return None


def fallback_relative_path(path: Path) -> Path:
    path_text = str(path.resolve()).replace("\\", "/")
    path_text = path_text.replace(":", "")
    path_text = path_text.lstrip("/")
    return Path(*path_text.split("/"))


def layout_json_relative_path(path: Path, layout_roots: list[Path]) -> Path:
    relative = relative_to_any_root(path, layout_roots)
    if relative is None:
        relative = fallback_relative_path(path)
    return relative.with_suffix(".layout.json")


def source_display_path(path: Path, source_root: Path | None) -> str:
    if source_root is None:
        return str(path)
    try:
        return path.resolve().relative_to(source_root.resolve()).as_posix()
    except ValueError:
        return str(path)


def write_doc(doc: LayoutDoc, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(doc.to_json() + "\n", encoding="utf-8")


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Parse DayZ .layout files into renderer v2 LayoutDoc JSON.",
    )
    parser.add_argument("layouts", nargs="+", help="layout path(s), or names under --layout-root")
    parser.add_argument(
        "-o",
        "--out",
        help="output JSON path; valid only with one input. If omitted, JSON is printed to stdout",
    )
    parser.add_argument(
        "--out-dir",
        help="output directory for multiple inputs; writes <layout>.layout.json files",
    )
    parser.add_argument(
        "--layout-root",
        action="append",
        default=[],
        help="directory used to resolve relative layout names; can be repeated",
    )
    parser.add_argument(
        "--source-root",
        help="root used to make source.path relative in emitted JSON",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="parse inputs and print OK lines without writing JSON",
    )
    parser.add_argument("--canvas-width", type=int, default=DEFAULT_CANVAS_WIDTH)
    parser.add_argument("--canvas-height", type=int, default=DEFAULT_CANVAS_HEIGHT)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    layout_roots = [Path(value) for value in args.layout_root]
    paths = [resolve_layout_path(value, layout_roots) for value in args.layouts]
    source_root = Path(args.source_root) if args.source_root else None

    if args.out and len(paths) != 1:
        raise SystemExit("--out is only valid with one input")
    if len(paths) > 1 and not args.check and not args.out_dir:
        raise SystemExit("multiple inputs require --check or --out-dir")

    output_paths: dict[Path, Path] = {}
    if args.out_dir:
        seen_outputs: dict[Path, Path] = {}
        out_dir = Path(args.out_dir)
        for path in paths:
            out_path = out_dir / layout_json_relative_path(path, layout_roots)
            if out_path in seen_outputs:
                raise SystemExit(
                    "output collision: "
                    f"{seen_outputs[out_path]} and {path} both map to {out_path}"
                )
            seen_outputs[out_path] = path
            output_paths[path] = out_path

    for path in paths:
        doc = parse_file(
            path,
            canvas_width=args.canvas_width,
            canvas_height=args.canvas_height,
            source_path_override=source_display_path(path, source_root),
        )
        if args.check:
            stats = collect_stats(doc.roots)
            print(f"OK {path} roots={stats['rootCount']} widgets={stats['widgetCount']} nodes={stats['nodeCount']}")
            continue

        if args.out:
            write_doc(doc, Path(args.out))
        elif args.out_dir:
            out_path = output_paths[path]
            write_doc(doc, out_path)
            print(f"WROTE {out_path}")
        else:
            print(doc.to_json())

    return 0


if __name__ == "__main__":
    sys.exit(main())
