from __future__ import annotations

import json
import math
import re
from decimal import Decimal
from typing import Any

from .errors import ParseError
from .modes import is_special_float, validate_mode
from .nodes import DocumentNode, MappingEntry, MappingNode, Node, ScalarNode, SequenceItem, SequenceNode
from .parser import Parser, _is_allowed_raw
from .roundtrip import RoundTripMapping, RoundTripSequence, coerce_node

_SAFE_KEY_RE = re.compile(r"^[\w./$()~\-]+$", re.UNICODE)

# Fixed-point zeros beyond which a finite float is written in exponential notation instead.
_MAX_PADDING_ZEROS = 3


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
        if (segments := _block_scalar_lines(node)) is not None:
            indicator = "|" if node.style == "literal" else ">"
            return [indicator, *_indent_block_lines(segments, 2)]
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
    for index, entry in enumerate(node.entries):
        # A sequence item's first entry shares the item's line, so its comments align with the `-`.
        comment_indent = indent - 2 if in_sequence and index == 0 else indent
        lines.extend(_indent_comment_lines(entry.before, comment_indent))
        key = _render_key(entry.key)
        value = entry.value
        prefix = " " * indent
        if isinstance(value, ScalarNode) and (segments := _block_scalar_lines(value)) is not None:
            indicator = "|" if value.style == "literal" else ">"
            header = f"{prefix}{key}: {indicator}"
            if entry.inline_comment:
                header = f"{header} {entry.inline_comment}"
            lines.append(header)
            lines.extend(_indent_block_lines(segments, indent + 2))
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
        lines.extend(_indent_comment_lines(item.before, indent))
        prefix = " " * indent + "-"
        value = item.value
        if isinstance(value, ScalarNode) and (segments := _block_scalar_lines(value)) is not None:
            indicator = "|" if value.style == "literal" else ">"
            header = f"{prefix} {indicator}"
            if item.inline_comment:
                header = f"{header} {item.inline_comment}"
            lines.append(header)
            lines.extend(_indent_block_lines(segments, indent + 2))
            continue
        if isinstance(value, MappingNode) and value.compact and len(value.entries) == 1 and not _is_block_scalar(value.entries[0].value):
            entry = value.entries[0]
            lines.extend(_indent_comment_lines(entry.before, indent))
            scalar = _render_scalar(entry.value, mode=mode, in_flow=False, preserve_style=roundtrip and isinstance(entry.value, ScalarNode) and not entry.value.dirty)
            line = f"{prefix} {_render_key(entry.key)}: {scalar}"
            if item.inline_comment:
                line = f"{line} {item.inline_comment}"
            lines.append(line)
            continue
        if isinstance(value, MappingNode) and len(value.entries) == 1 and isinstance(value.entries[0].value, ScalarNode) and not _is_block_scalar(value.entries[0].value):
            entry = value.entries[0]
            lines.extend(_indent_comment_lines(entry.before, indent))
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
        if isinstance(value, MappingNode):
            rendered = _render_mapping(
                value,
                indent=indent + 2,
                mode=mode,
                roundtrip=roundtrip,
                in_sequence=True,
            )
            first_content = len(value.entries[0].before) if value.entries else None
            if first_content is not None:
                rendered[first_content] = f"{prefix} {rendered[first_content][indent + 2:]}"
                if item.inline_comment:
                    rendered[first_content] = f"{rendered[first_content]} {item.inline_comment}"
                lines.extend(rendered)
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


def _indent_comment_lines(lines: list[str], indent: int) -> list[str]:
    # Comments without indentation, such as those supplied through the format-aware API, align with their entry.
    prefix = " " * indent
    return [f"{prefix}{line}" if line and not line[0].isspace() else line for line in lines]


def _render_flow_mapping(node: MappingNode, *, mode: str) -> str:
    parts = [f"{_render_key(entry.key)}: {_render_flow_value(entry.value, mode=mode)}" for entry in node.entries]
    return "{%s}" % ", ".join(parts)


def _render_flow_sequence(node: SequenceNode, *, mode: str) -> str:
    return "[%s]" % ", ".join(_render_flow_value(item.value, mode=mode) for item in node.items)


def _render_flow_value(node: Node, *, mode: str) -> str:
    if isinstance(node, MappingNode):
        return _render_flow_mapping(node, mode=mode)
    if isinstance(node, SequenceNode):
        return _render_flow_sequence(node, mode=mode)
    if node.style in {"literal", "folded"}:
        raise TypeError("Flow containers may not contain block scalars.")
    return _render_scalar(node, mode=mode, in_flow=True, preserve_style=True)


def _render_key(key: str) -> str:
    if _SAFE_KEY_RE.match(key) and not _string_requires_quotes(key, mode="standard", in_flow=False):
        return key
    return _quote_string(key)


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
        return _render_float(value)
    return str(value)


def _render_float(value: float) -> str:
    """Render a finite float with the fewest significant digits that read back as the same value.

    Fixed-point notation is used unless it would need more than `_MAX_PADDING_ZEROS` zeros between
    the significant digits and the decimal point, in which case normalized exponential notation is
    used. Either way the text reads back as a float, never as an integer.
    """
    sign = "-" if math.copysign(1.0, value) < 0 else ""
    if value == 0:
        return f"{sign}0.0"
    _, digit_tuple, exponent = Decimal(repr(abs(value))).normalize().as_tuple()
    digits = "".join(map(str, digit_tuple))
    count = len(digits)
    exp = count - 1 + exponent
    padding = -exp - 1 if exp < 0 else max(exp - count + 1, 0)
    if padding > _MAX_PADDING_ZEROS:
        mantissa = digits if count == 1 else f"{digits[0]}.{digits[1:]}"
        return f"{sign}{mantissa}e{exp}"
    if exp < 0:
        return f"{sign}0.{'0' * padding}{digits}"
    if exp + 1 >= count:
        return f"{sign}{digits}{'0' * padding}.0"
    return f"{sign}{digits[:exp + 1]}.{digits[exp + 1:]}"


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
    """Whether `text` must be quoted: it is emitted unquoted only if it parses back as itself."""
    if text == "" or text != text.strip():
        return True
    if any(not _is_allowed_raw(char) or char == "\xa0" for char in text):
        return True
    if text.startswith("#") or " #" in text:
        return True
    try:
        node = Parser("", mode="standard")._parse_inline_value(text, 1, 1, in_flow=in_flow)
    except ParseError:
        return True
    return not (isinstance(node, ScalarNode) and node.kind == "string" and node.style == "plain" and node.value == text)


def _quote_string(text: str) -> str:
    quoted = json.dumps(text, ensure_ascii=False)
    return "".join(
        f"\\u{ord(char):04x}" if not _is_allowed_raw(char) or char == "\xa0" else char
        for char in quoted
    )


def _single_quote_string(text: str) -> str:
    return "'" + text.replace("'", "''") + "'"


def _block_scalar_lines(node: ScalarNode) -> list[str] | None:
    """Return the content lines of `node` as a `|` or `>` block scalar, or None if that style cannot represent it.

    Block scalars use clip chomping and take their indentation from the first non-blank line, so the
    value must end with exactly one line break, its first non-blank line may not start with
    whitespace, and the blank lines before that one must be empty. Folded lines are the inverse of parser folding: a line break between two lines needs
    an empty line unless one of them is more indented.
    """
    if node.style not in {"literal", "folded"}:
        return None
    text = str(node.value)
    if not text.endswith("\n") or text.endswith("\n\n"):
        return None
    if any(char != "\n" and not _is_allowed_raw(char) for char in text):
        return None
    segments = text[:-1].split("\n")
    first = next((index for index, segment in enumerate(segments) if segment.strip()), None)
    if first is None or segments[first][0] in " \t" or any(segments[:first]):
        return None
    if node.style == "literal":
        return segments
    lines: list[str] = []
    empty = 0
    previous: str | None = None
    for segment in segments:
        if segment == "":
            empty += 1
            continue
        spaced = previous is not None and (previous[0] in " \t" or segment[0] in " \t")
        lines.extend([""] * (empty + 1 if previous is not None and not spaced else empty))
        lines.append(segment)
        previous = segment
        empty = 0
    return lines


def _is_block_scalar(node: Node) -> bool:
    return isinstance(node, ScalarNode) and _block_scalar_lines(node) is not None


def _indent_block_lines(lines: list[str], indent: int) -> list[str]:
    return [" " * indent + line if line else "" for line in lines]
