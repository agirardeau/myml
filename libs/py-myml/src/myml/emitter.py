from __future__ import annotations

import json
import math
import re
from typing import Any

from .modes import is_special_float, validate_mode
from .nodes import DocumentNode, MappingEntry, MappingNode, Node, ScalarNode, SequenceItem, SequenceNode
from .roundtrip import RoundTripMapping, RoundTripSequence, coerce_node

_SAFE_KEY_RE = re.compile(r"^[\w./$()~\-]+$", re.UNICODE)


def infer_scalar_kind(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int) and not isinstance(value, bool):
        return "number"
    if isinstance(value, float):
        return "number"
    return "string"


def dump_to_text(value: Any, *, mode: str = "standard") -> str:
    mode = validate_mode(mode)
    document = _as_document(value, mode=mode)
    if isinstance(value, (RoundTripMapping, RoundTripSequence)) and document.original_text and document.mode == mode and not document.dirty:
        return document.original_text
    pieces = [*document.leading_lines]
    pieces.extend(_render_node(document.root, indent=0, mode=mode, roundtrip=True, in_sequence=False))
    pieces.extend(document.trailing_lines)
    text = "\n".join(pieces)
    return text if not text or text.endswith("\n") else f"{text}\n"


def _as_document(value: Any, *, mode: str) -> DocumentNode:
    if isinstance(value, RoundTripMapping):
        return value._document
    if isinstance(value, RoundTripSequence):
        return value._document
    node = coerce_node(value)
    return DocumentNode(node, "", mode)


def _render_node(node: Node, *, indent: int, mode: str, roundtrip: bool, in_sequence: bool) -> list[str]:
    if isinstance(node, ScalarNode):
        if node.style in {"literal", "folded"}:
            indicator = "|" if node.style == "literal" else ">"
            lines = [indicator]
            lines.extend("  " + segment for segment in _render_block_scalar_lines(str(node.value)))
            return lines
        return [_render_scalar(node, mode=mode, in_flow=False, preserve_style=roundtrip and not node.dirty)]
    if isinstance(node, MappingNode):
        if node.style == "flow" and roundtrip:
            return [_render_flow_mapping(node, mode=mode)]
        return _render_mapping(node, indent=indent, mode=mode, roundtrip=roundtrip, in_sequence=in_sequence)
    if isinstance(node, SequenceNode):
        if node.style == "flow" and roundtrip:
            return [_render_flow_sequence(node, mode=mode)]
        return _render_sequence(node, indent=indent, mode=mode, roundtrip=roundtrip)
    raise TypeError(f"Unsupported node type: {type(node)!r}")


def _render_mapping(node: MappingNode, *, indent: int, mode: str, roundtrip: bool, in_sequence: bool) -> list[str]:
    lines: list[str] = []
    for entry in node.entries:
        lines.extend(entry.before)
        key = _render_key(entry.key)
        value = entry.value
        prefix = " " * indent
        if isinstance(value, ScalarNode) and value.style in {"literal", "folded"}:
            indicator = "|" if value.style == "literal" else ">"
            header = f"{prefix}{key}: {indicator}"
            if entry.inline_comment:
                header = f"{header} {entry.inline_comment}"
            lines.append(header)
            for segment in _render_block_scalar_lines(str(value.value)):
                lines.append(" " * (indent + 2) + segment)
            continue
        if isinstance(value, MappingNode) and value.compact and len(value.entries) == 1:
            compact_entry = value.entries[0]
            scalar = _render_scalar(
                compact_entry.value if isinstance(compact_entry.value, ScalarNode) else coerce_node(None),
                mode=mode,
                in_flow=False,
                preserve_style=roundtrip and not compact_entry.value.dirty if isinstance(compact_entry.value, ScalarNode) else False,
            )
            line = f"{prefix}{key}: {compact_entry.key}: {scalar}"
            if entry.inline_comment:
                line = f"{line} {entry.inline_comment}"
            lines.append(line)
            continue
        if isinstance(value, (MappingNode, SequenceNode)):
            if roundtrip and value.style == "flow":
                rendered = _render_flow_mapping(value, mode=mode) if isinstance(value, MappingNode) else _render_flow_sequence(value, mode=mode)
                line = f"{prefix}{key}: {rendered}"
                if entry.inline_comment:
                    line = f"{line} {entry.inline_comment}"
                lines.append(line)
            else:
                line = f"{prefix}{key}:"
                if entry.inline_comment:
                    line = f"{line} {entry.inline_comment}"
                lines.append(line)
                lines.extend(_render_node(value, indent=indent + 2, mode=mode, roundtrip=roundtrip, in_sequence=False))
            continue
        line = f"{prefix}{key}: {_render_scalar(value, mode=mode, in_flow=False, preserve_style=roundtrip and not value.dirty)}"
        if entry.inline_comment:
            line = f"{line} {entry.inline_comment}"
        lines.append(line)
    lines.extend(node.trailing_lines)
    return lines


def _render_sequence(node: SequenceNode, *, indent: int, mode: str, roundtrip: bool) -> list[str]:
    lines: list[str] = []
    for item in node.items:
        lines.extend(item.before)
        prefix = " " * indent + "-"
        value = item.value
        if isinstance(value, ScalarNode) and value.style in {"literal", "folded"}:
            indicator = "|" if value.style == "literal" else ">"
            header = f"{prefix} {indicator}"
            if item.inline_comment:
                header = f"{header} {item.inline_comment}"
            lines.append(header)
            for segment in _render_block_scalar_lines(str(value.value)):
                lines.append(" " * (indent + 2) + segment)
            continue
        if isinstance(value, MappingNode) and value.compact and len(value.entries) == 1:
            entry = value.entries[0]
            scalar = _render_scalar(entry.value, mode=mode, in_flow=False, preserve_style=roundtrip and isinstance(entry.value, ScalarNode) and not entry.value.dirty)
            line = f"{prefix} {_render_key(entry.key)}: {scalar}"
            if item.inline_comment:
                line = f"{line} {item.inline_comment}"
            lines.append(line)
            continue
        if isinstance(value, MappingNode) and len(value.entries) == 1 and all(isinstance(entry.value, ScalarNode) for entry in value.entries):
            entry = value.entries[0]
            scalar = _render_scalar(entry.value, mode=mode, in_flow=False, preserve_style=roundtrip and not entry.value.dirty)
            line = f"{prefix} {_render_key(entry.key)}: {scalar}"
            if item.inline_comment:
                line = f"{line} {item.inline_comment}"
            lines.append(line)
            continue
        if isinstance(value, MappingNode) and value.style == "flow" and roundtrip:
            line = f"{prefix} {_render_flow_mapping(value, mode=mode)}"
            if item.inline_comment:
                line = f"{line} {item.inline_comment}"
            lines.append(line)
            continue
        if isinstance(value, SequenceNode) and value.style == "flow" and roundtrip:
            line = f"{prefix} {_render_flow_sequence(value, mode=mode)}"
            if item.inline_comment:
                line = f"{line} {item.inline_comment}"
            lines.append(line)
            continue
        if isinstance(value, (MappingNode, SequenceNode)):
            line = prefix
            if item.inline_comment:
                line = f"{line} {item.inline_comment}"
            lines.append(line)
            lines.extend(_render_node(value, indent=indent + 2, mode=mode, roundtrip=roundtrip, in_sequence=True))
            continue
        line = f"{prefix} {_render_scalar(value, mode=mode, in_flow=False, preserve_style=roundtrip and not value.dirty)}"
        if item.inline_comment:
            line = f"{line} {item.inline_comment}"
        lines.append(line)
    lines.extend(node.trailing_lines)
    return lines


def _render_flow_mapping(node: MappingNode, *, mode: str) -> str:
    parts: list[str] = []
    for entry in node.entries:
        if not isinstance(entry.value, ScalarNode):
            raise TypeError("Flow mappings may contain scalar values only.")
        parts.append(f"{_render_key(entry.key)}: {_render_scalar(entry.value, mode=mode, in_flow=True, preserve_style=True)}")
    return "{%s}" % ", ".join(parts)


def _render_flow_sequence(node: SequenceNode, *, mode: str) -> str:
    parts: list[str] = []
    for item in node.items:
        if not isinstance(item.value, ScalarNode):
            raise TypeError("Flow sequences may contain scalar values only.")
        parts.append(_render_scalar(item.value, mode=mode, in_flow=True, preserve_style=True))
    return "[%s]" % ", ".join(parts)


def _render_key(key: str) -> str:
    if _SAFE_KEY_RE.match(key):
        return key
    return json.dumps(key, ensure_ascii=False)


def _render_scalar(value: ScalarNode | Node, *, mode: str, in_flow: bool, preserve_style: bool) -> str:
    if not isinstance(value, ScalarNode):
        raise TypeError("Expected a scalar node.")
    if preserve_style and value.raw and value.style not in {"literal", "folded"}:
        if value.kind == "string" and _string_requires_quotes(str(value.value), mode=mode, in_flow=in_flow):
            return _quote_string(str(value.value))
        return value.raw
    if value.kind == "null":
        return "null"
    if value.kind == "boolean":
        return "true" if value.value else "false"
    if value.kind == "number":
        return _render_number(value.value)
    return _render_string(str(value.value), mode=mode, in_flow=in_flow, style=value.style if preserve_style else None)


def _render_number(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if is_special_float(value):
        if math.isnan(value):
            return ".nan"
        return ".inf" if value > 0 else "-.inf"
    if isinstance(value, float):
        text = format(value, "g")
        if "E" in text:
            text = text.lower()
        return text
    return str(value)


def _render_string(text: str, *, mode: str, in_flow: bool, style: str | None) -> str:
    if style == "single":
        return _single_quote_string(text)
    if style == "double":
        return _quote_string(text)
    if "\n" in text:
        return _quote_string(text)
    if mode == "strict":
        return _quote_string(text)
    if _string_requires_quotes(text, mode=mode, in_flow=in_flow):
        return _quote_string(text)
    return text


def _string_requires_quotes(text: str, *, mode: str, in_flow: bool) -> bool:
    if text == "":
        return True
    first = text[0]
    if first in "!\"'`*%&>|,[]{}#":
        return True
    if first in "-?" and len(text) > 1 and text[1] == " ":
        return True
    if text == "~":
        return True
    if "@" in text or "^" in text:
        return True
    if text.endswith(":") or ": " in text:
        return True
    if text.startswith("#") or " #" in text:
        return True
    if in_flow and any(c in text for c in ",[]{}"):
        return True
    if text in {"true", "false", "null", ".inf", "-.inf", ".nan"}:
        return True
    if re.match(r"^(?:0|-?[1-9][0-9]*)$", text):
        return True
    if re.match(r"^0x[0-9A-Fa-f]+$", text):
        return True
    if re.match(r"^-?(?:0|[1-9][0-9]*)\.[0-9]+$", text):
        return True
    if re.match(r"^-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?e-?[0-9]+$", text):
        return True
    return False


def _quote_string(text: str) -> str:
    return json.dumps(text, ensure_ascii=False)


def _single_quote_string(text: str) -> str:
    return "'" + text.replace("'", "''") + "'"


def _render_block_scalar_lines(text: str) -> list[str]:
    if text == "":
        return [""]
    pieces = text.split("\n")
    if pieces and pieces[-1] == "":
        pieces = pieces[:-1]
    return pieces
