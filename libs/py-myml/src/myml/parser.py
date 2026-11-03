from __future__ import annotations

import re
from dataclasses import dataclass

from .errors import ParseError
from .modes import validate_mode
from .nodes import DocumentNode, MappingEntry, MappingNode, ScalarNode, SequenceItem, SequenceNode
from .roundtrip import to_plain_data, wrap_node

_INT_RE = re.compile(r"^(?:0|-?[1-9][0-9]*)$")
_HEX_RE = re.compile(r"^0x[0-9A-Fa-f]+$")
_DECIMAL_RE = re.compile(r"^-?(?:0|[1-9][0-9]*)\.[0-9]+$")
_EXP_RE = re.compile(r"^-?(?:[1-9](?:\.[0-9]+)?)e-?[0-9]+$")
_NUMERIC_UNDERSCORE_RE = re.compile(r"^-?(?:0x[0-9A-Fa-f_]+|[0-9][0-9_]*(?:\.[0-9_]+)?(?:e-?[0-9_]+)?)$")
_LEADING_ZERO_DECIMAL_RE = re.compile(r"^-?0[0-9]+\.[0-9]+$")
_SCI_RE = re.compile(r"^-?(?:[0-9]+(?:\.[0-9]+)?|\.[0-9]+)e-?[0-9]+$")
# Plain scalars that the YAML 1.2 core schema resolves to integers or floats.
_CORE_NUMBER_RE = re.compile(r"^(?:[-+]?[0-9]+|0o[0-7]+|[-+]?(?:\.[0-9]+|[0-9]+(?:\.[0-9]*)?)(?:[eE][-+]?[0-9]+)?|[-+]?\.(?:inf|Inf|INF))$")
_UNQUOTED_KEY_RE = re.compile(r"^[\w./$()~\-]+$", re.UNICODE)


@dataclass
class Line:
    number: int
    text: str


def _fold_block_lines(lines: list[str]) -> str:
    """Join `>` block scalar lines as YAML folding does.

    A single line break between two lines becomes a space, each empty line between them becomes a
    line break, and breaks next to more-indented lines are kept.
    """
    parts: list[str] = []
    breaks = 0
    previous: str | None = None
    for line in lines:
        if line == "":
            breaks += 1
            continue
        if previous is None:
            parts.append("\n" * breaks)
        elif previous[0] in " \t" or line[0] in " \t":
            parts.append("\n" * (breaks + 1))
        else:
            parts.append("\n" * breaks if breaks else " ")
        parts.append(line)
        previous = line
        breaks = 0
    return "".join(parts) + "\n"


class Parser:
    def __init__(self, text: str, *, mode: str = "standard", roundtrip: bool = False) -> None:
        self.text = text
        self.lines = [Line(index + 1, raw) for index, raw in enumerate(text.splitlines())]
        self.index = 0
        self.mode = validate_mode(mode)
        self.roundtrip = roundtrip

    def parse(self):
        leading = self._consume_trivia([])
        if self.index >= len(self.lines):
            document = DocumentNode(ScalarNode(None, kind="null", style="plain", raw="null"), self.text, self.mode)
            document.leading_lines = leading
            return wrap_node(document.root, document) if self.roundtrip else None
        root = self._parse_block(indent=0)
        trailing = self._consume_trivia([])
        if self.index < len(self.lines):
            line = self.lines[self.index]
            self._error("Unexpected content after document root.", code="malformed-document", line=line.number, column=1)
        document = DocumentNode(root, self.text, self.mode, leading_lines=leading, trailing_lines=trailing)
        return wrap_node(root, document) if self.roundtrip else to_plain_data(root)

    def parse_document(self) -> DocumentNode:
        leading = self._consume_trivia([])
        if self.index >= len(self.lines):
            root = ScalarNode(None, kind="null", style="plain", raw="null")
            return DocumentNode(root, self.text, self.mode, leading_lines=leading)
        root = self._parse_block(indent=0)
        trailing = self._consume_trivia([])
        if self.index < len(self.lines):
            line = self.lines[self.index]
            self._error("Unexpected content after document root.", code="malformed-document", line=line.number, column=1)
        return DocumentNode(root, self.text, self.mode, leading_lines=leading, trailing_lines=trailing)

    def _consume_trivia(self, acc: list[str]) -> list[str]:
        while self.index < len(self.lines):
            line = self.lines[self.index]
            if self._is_blank(line.text) or self._is_comment(line.text):
                acc.append(line.text)
                self.index += 1
                continue
            break
        return acc

    def _parse_block(self, indent: int):
        if self.index >= len(self.lines):
            self._error("Expected a value.", code="missing-value", line=self.lines[-1].number if self.lines else 1, column=1)
        # Comment and blank lines may precede a nested block; the container parsers collect them.
        line = self.lines[self._next_significant_index()]
        actual = self._indentation(line)
        if actual != indent:
            self._error("Invalid indentation.", code="invalid-indentation", line=line.number, column=actual + 1)
        stripped = line.text[indent:]
        body, _comment = self._split_comment(stripped)
        if body == "-" or body.startswith("- "):
            return self._parse_sequence(indent)
        if self._find_mapping_separator(body) is not None:
            return self._parse_mapping(indent)
        self._consume_trivia([])
        return self._parse_root_scalar(indent)

    def _parse_root_scalar(self, indent: int):
        line = self.lines[self.index]
        body, comment = self._split_comment(line.text[indent:])
        token = body.strip()
        if not token:
            self._error("Expected a scalar value.", code="missing-value", line=line.number, column=indent + 1)
        if self.index + 1 < len(self.lines):
            next_line = self.lines[self.index + 1]
            if self._indentation(next_line) > indent:
                self._error_if_multiline_scalar_continuation(next_line, indent)
        node = self._parse_inline_value(token, line.number, indent + body.index(token) + 1, in_flow=False)
        self.index += 1
        if comment:
            if isinstance(node, ScalarNode):
                node.raw = token
        return node

    def _error_if_multiline_scalar_continuation(self, line: Line, parent_indent: int) -> None:
        actual = self._indentation(line)
        raw = line.text[parent_indent:]
        body, _comment = self._split_comment(raw)
        text = body.strip()
        if actual > parent_indent and text and not text.startswith("- ") and self._find_mapping_separator(body) is None:
            self._error(
                "Multiline non-block scalar strings are not supported.",
                code="unsupported-multiline-scalar",
                line=line.number,
                column=actual + 1,
                category="unsupported_feature",
            )

    def _parse_mapping(self, indent: int):
        entries: list[MappingEntry] = []
        pending_before: list[str] = []
        seen_keys: set[str] = set()
        while self.index < len(self.lines):
            pending_before = self._consume_trivia(pending_before)
            if self.index >= len(self.lines):
                break
            line = self.lines[self.index]
            actual = self._indentation(line)
            if actual < indent:
                break
            if actual > indent:
                self._error_if_multiline_scalar_continuation(line, indent)
                self._error("Invalid indentation.", code="invalid-indentation", line=line.number, column=actual + 1)
            raw = line.text[indent:]
            if raw == "-" or raw.startswith("- "):
                self._error("Sequence item is not valid in a mapping position.", code="malformed-mapping", line=line.number, column=indent + 1)
            body, comment = self._split_comment(raw)
            self.index += 1
            key, value = self._parse_mapping_entry(body, indent, line, seen_keys)
            entries.append(MappingEntry(key=key, value=value, before=pending_before, inline_comment=comment))
            pending_before = []
        node = MappingNode(entries, style="block", trailing_lines=pending_before)
        return node

    def _parse_mapping_entry(self, body: str, indent: int, line: Line, seen_keys: set[str]):
        """Parse one block mapping entry whose key starts at column `indent` of `line`, the line before `self.index`."""
        separator = self._find_mapping_separator(body)
        if separator is None:
            self._error("Malformed mapping entry.", code="malformed-mapping", line=line.number, column=indent + 1)
        key_text = body[:separator].rstrip()
        value_text = body[separator + 1 :].lstrip()
        key = self._parse_key(key_text, line.number, indent + body.index(key_text) + 1)
        if key in seen_keys:
            self._error("Duplicate mapping key.", code="duplicate-key", line=line.number, column=indent + 1, category="semantic_error")
        seen_keys.add(key)
        if value_text in {"|", ">"}:
            return key, self._parse_block_scalar(value_text, indent, line.number)
        if not value_text:
            if self._peek_significant_indent() <= indent:
                self._error("Mapping entries must have a value.", code="missing-value", line=line.number, column=indent + separator + 2)
            return key, self._parse_block(self._peek_significant_indent())
        start_column = indent + separator + 2 + (len(body[separator + 1 :]) - len(body[separator + 1 :].lstrip()))
        if self.index < len(self.lines):
            next_line = self.lines[self.index]
            if self._indentation(next_line) > indent:
                self._error_if_multiline_scalar_continuation(next_line, indent)
        return key, self._parse_inline_value(value_text, line.number, start_column, in_flow=False)

    def _parse_sequence(self, indent: int):
        items: list[SequenceItem] = []
        pending_before: list[str] = []
        while self.index < len(self.lines):
            pending_before = self._consume_trivia(pending_before)
            if self.index >= len(self.lines):
                break
            line = self.lines[self.index]
            actual = self._indentation(line)
            if actual < indent:
                break
            if actual > indent:
                self._error_if_multiline_scalar_continuation(line, indent)
                self._error("Invalid indentation.", code="invalid-indentation", line=line.number, column=actual + 1)
            raw = line.text[indent:]
            if raw != "-" and not raw.startswith("- "):
                break
            item_body, comment = self._split_comment(raw[1:].lstrip())
            token = item_body.strip()
            self.index += 1
            if not token:
                next_indent = self._peek_significant_indent()
                if next_indent <= indent:
                    self._error("Sequence items must have a value.", code="missing-value", line=line.number, column=indent + 3)
                value = self._parse_block(next_indent)
            elif token in {"|", ">"}:
                value = self._parse_block_scalar(token, indent, line.number)
            else:
                inline_map_separator = self._find_mapping_separator(token)
                if inline_map_separator is not None and not token.startswith("{"):
                    # The item is a block mapping whose keys align with its first key.
                    key_indent = indent + 1 + len(raw[1:]) - len(raw[1:].lstrip())
                    existing_keys: set[str] = set()
                    key, entry_value = self._parse_mapping_entry(item_body, key_indent, line, existing_keys)
                    first_entry = MappingEntry(key=key, value=entry_value)
                    compact = isinstance(entry_value, ScalarNode) and entry_value.style not in {"literal", "folded"}
                    value = MappingNode([first_entry], style="block", compact=compact)
                    continuation_indent = self._peek_significant_indent()
                    if continuation_indent > indent:
                        continuation = self._parse_mapping(continuation_indent)
                        for entry in continuation.entries:
                            if entry.key in existing_keys:
                                self._error(
                                    "Duplicate mapping key.",
                                    code="duplicate-key",
                                    line=line.number,
                                    column=indent + 3,
                                    category="semantic_error",
                                )
                            existing_keys.add(entry.key)
                        value.entries.extend(continuation.entries)
                        value.trailing_lines = continuation.trailing_lines
                else:
                    if self.index < len(self.lines):
                        next_line = self.lines[self.index]
                        if self._indentation(next_line) > indent:
                            self._error_if_multiline_scalar_continuation(next_line, indent)
                    value = self._parse_inline_value(token, line.number, indent + 3, in_flow=False)
            items.append(SequenceItem(value=value, before=pending_before, inline_comment=comment))
            pending_before = []
        return SequenceNode(items, style="block", trailing_lines=pending_before)

    def _parse_block_scalar(self, indicator: str, parent_indent: int, header_line: int):
        next_indent = self._peek_block_scalar_indent()
        if next_indent <= parent_indent:
            self._error("Block scalar requires indented content.", code="missing-value", line=header_line, column=parent_indent + 1)
        lines: list[str] = []
        while self.index < len(self.lines):
            line = self.lines[self.index]
            if self._is_blank(line.text):
                # Whitespace beyond the content indentation is content, even on an otherwise blank line.
                lines.append(line.text[next_indent:] if line.text.startswith(" " * next_indent) else "")
                self.index += 1
                continue
            if len(line.text) - len(line.text.lstrip(" ")) < next_indent:
                # Tabs may follow the content indentation, but not form part of it.
                self._indentation(line)
                break
            lines.append(line.text[next_indent:])
            self.index += 1
        # Clip chomping: trailing empty lines are not part of the value.
        while lines and lines[-1] == "":
            lines.pop()
        if indicator == "|":
            return ScalarNode("".join(f"{line}\n" for line in lines), kind="string", style="literal", raw="|")
        return ScalarNode(_fold_block_lines(lines), kind="string", style="folded", raw=">")

    def _parse_inline_value(self, token: str, line: int, column: int, *, in_flow: bool):
        if token.startswith("&") or token.startswith("*"):
            self._error("Anchors and aliases are not supported.", code="unsupported-anchor", line=line, column=column, category="unsupported_feature")
        if token.startswith("!"):
            self._error("Tags are not supported.", code="unsupported-tag", line=line, column=column, category="unsupported_feature")
        if token == "~":
            self._error("The `~` null spelling is not supported.", code="unsupported-null-tilde", line=line, column=column, category="unsupported_feature")
        if token.startswith("["):
            return self._parse_flow_sequence(token, line, column)
        if token.startswith("{"):
            return self._parse_flow_mapping(token, line, column)
        if token.startswith("'") or token.startswith('"'):
            return self._parse_quoted_scalar(token, line, column)
        return self._parse_plain_scalar(token, line, column, in_flow=in_flow)

    def _parse_flow_sequence(self, token: str, line: int, column: int):
        commas = self._scan_flow_delimiters(token, line, column)
        if not token[1:-1].strip():
            return SequenceNode([], style="flow")
        parts = self._split_flow_items(token, commas, line, column)
        items: list[SequenceItem] = []
        for part, part_column in parts:
            items.append(SequenceItem(self._parse_inline_value(part, line, part_column, in_flow=True)))
        return SequenceNode(items, style="flow")

    def _parse_flow_mapping(self, token: str, line: int, column: int):
        commas = self._scan_flow_delimiters(token, line, column)
        if not token[1:-1].strip():
            return MappingNode([], style="flow")
        parts = self._split_flow_items(token, commas, line, column)
        entries: list[MappingEntry] = []
        seen_keys: set[str] = set()
        for part, part_column in parts:
            separator = self._find_mapping_separator(part, in_flow=True)
            if separator is None:
                self._error("Malformed flow mapping entry.", code="malformed-mapping", line=line, column=part_column)
            key_text = part[:separator].rstrip()
            value_text = part[separator + 1 :].lstrip()
            key = self._parse_key(key_text, line, part_column)
            if key in seen_keys:
                self._error("Duplicate mapping key.", code="duplicate-key", line=line, column=part_column, category="semantic_error")
            seen_keys.add(key)
            entries.append(MappingEntry(key, self._parse_inline_value(value_text, line, part_column + separator + 1, in_flow=True)))
        return MappingNode(entries, style="flow")

    def _parse_key(self, token: str, line: int, column: int) -> str:
        if token == "<<":
            self._error("Merge keys are not supported.", code="unsupported-merge-key", line=line, column=column, category="unsupported_feature")
        if token.startswith("'") or token.startswith('"'):
            node = self._parse_quoted_scalar(token, line, column)
            if node.kind != "string":
                self._error("Mapping keys must be strings.", code="non-string-key", line=line, column=column)
            return node.value
        if "#" in token:
            self._error("`#` is not permitted within unquoted keys.", code="unquoted-key-hash", line=line, column=column)
        if ":" in token:
            self._error("`:` is not permitted within unquoted keys.", code="unquoted-key-colon", line=line, column=column)
        if not token:
            self._error("Mapping keys must be strings.", code="non-string-key", line=line, column=column)
        if not _UNQUOTED_KEY_RE.match(token):
            self._error("Unsupported unquoted key syntax.", code="invalid-key", line=line, column=column)
        if token == "~" or self._parse_plain_scalar(token, line, column, in_flow=False, mode="standard").kind != "string":
            self._error("Mapping keys must be strings.", code="non-string-key", line=line, column=column)
        return token

    def _parse_quoted_scalar(self, token: str, line: int, column: int):
        if len(token) < 2 or token[-1] != token[0]:
            self._error("Quoted scalar is not terminated.", code="malformed-string", line=line, column=column)
        quote = token[0]
        result: list[str] = []
        index = 1
        while index < len(token) - 1:
            char = token[index]
            if quote == "'":
                if char == "'":
                    if index + 1 >= len(token) - 1 or token[index + 1] != "'":
                        self._error("Apostrophes within single quotes must be doubled.", code="malformed-string", line=line, column=column)
                    result.append("'")
                    index += 2
                    continue
            elif char == '"':
                self._error("Unescaped quote within double quotes.", code="malformed-string", line=line, column=column)
            elif char == "\\":
                index += 1
                if index >= len(token) - 1:
                    self._error("Quoted scalar is not terminated.", code="malformed-string", line=line, column=column)
                escape = token[index]
                escapes = {
                    "0": "\0", "a": "\a", "b": "\b", "t": "\t", "n": "\n",
                    "v": "\v", "f": "\f", "r": "\r", "e": "\x1b", " ": " ",
                    '"': '"', "/": "/", "\\": "\\", "N": "\x85",
                    "_": "\xa0", "L": "\u2028", "P": "\u2029",
                }
                if escape in escapes:
                    result.append(escapes[escape])
                elif escape in "xuU":
                    width = {"x": 2, "u": 4, "U": 8}[escape]
                    digits = token[index + 1:index + 1 + width]
                    if len(digits) != width or any(digit not in "0123456789abcdefABCDEF" for digit in digits):
                        self._error("Invalid Unicode escape.", code="malformed-string", line=line, column=column)
                    point = int(digits, 16)
                    if point > 0x10ffff or 0xd800 <= point <= 0xdfff:
                        self._error("Invalid Unicode code point.", code="malformed-string", line=line, column=column)
                    result.append(chr(point))
                    index += width
                else:
                    self._error("Unknown escape sequence.", code="malformed-string", line=line, column=column)
                index += 1
                continue
            result.append(char)
            index += 1
        value = "".join(result)
        return ScalarNode(value, kind="string", style="single" if quote == "'" else "double", raw=token)

    def _parse_plain_scalar(self, token: str, line: int, column: int, *, in_flow: bool, mode: str | None = None):
        if token in {"true", "false"}:
            return ScalarNode(token == "true", kind="boolean", style="plain", raw=token)
        if token == "null":
            return ScalarNode(None, kind="null", style="plain", raw=token)
        if token in {".inf", "-.inf", ".nan"}:
            if token == ".inf":
                return ScalarNode(float("inf"), kind="number", style="plain", raw=token)
            if token == "-.inf":
                return ScalarNode(float("-inf"), kind="number", style="plain", raw=token)
            return ScalarNode(float("nan"), kind="number", style="plain", raw=token)
        if token.lower() in {"true", "false", "null", ".inf", "-.inf", ".nan"} and token not in {"true", "false", "null", ".inf", "-.inf", ".nan"}:
            self._error("Special scalars must use lowercase spellings.", code="unsupported-non-lowercase-special-scalar", line=line, column=column, category="unsupported_feature")
        if "_" in token and _NUMERIC_UNDERSCORE_RE.match(token):
            self._error(
                "Numeric separators are not supported.",
                code="invalid-number-underscore-separator",
                line=line,
                column=column,
                category="lexical_error",
            )
        if token == "-0":
            self._error("`-0` is not a supported numeric form.", code="invalid-number-negative-zero", line=line, column=column, category="lexical_error")
        if re.match(r"^-?\.[0-9]+$", token):
            self._error("Leading-dot decimals are not supported.", code="invalid-number-leading-dot-decimal", line=line, column=column, category="lexical_error")
        if _LEADING_ZERO_DECIMAL_RE.match(token):
            self._error(
                "Plain fractional decimals may use exactly one `0.` prefix.",
                code="invalid-number-leading-zero-decimal",
                line=line,
                column=column,
                category="lexical_error",
            )
        if _HEX_RE.match(token):
            return ScalarNode(int(token, 16), kind="number", style="plain", raw=token)
        if _INT_RE.match(token):
            return ScalarNode(int(token), kind="number", style="plain", raw=token)
        if _DECIMAL_RE.match(token):
            return ScalarNode(float(token), kind="number", style="plain", raw=token)
        if _EXP_RE.match(token):
            number = float(token)
            value = int(number) if number.is_integer() else number
            return ScalarNode(value, kind="number", style="plain", raw=token)
        if _SCI_RE.match(token):
            self._error(
                "Scientific notation must use a normalized coefficient with 1 <= m < 10.",
                code="invalid-number-scientific-notation",
                line=line,
                column=column,
                category="lexical_error",
            )
        if _CORE_NUMBER_RE.match(token):
            # YAML 1.2 reads these as numbers, so they cannot be strings either.
            if token.startswith("+"):
                message, code = "Numbers may not use a `+` prefix.", "invalid-number-plus-prefix"
            elif token.startswith("0o"):
                message, code = "Octal notation is not supported.", "invalid-number-octal"
            elif re.match(r"^-?0[0-9]+$", token):
                message, code = "Integers may not have leading zeros.", "invalid-number-leading-zero"
            else:
                message, code = "Unsupported numeric form.", "invalid-number-form"
            self._error(message, code=code, line=line, column=column, category="lexical_error")
        if (mode or self.mode) == "strict":
            self._error("Strict mode requires quoted string scalars.", code="strict-mode-unquoted-string", line=line, column=column, category="mode_restriction")
        first = token[0]
        if first in "!\"'`*%&>|,[]{}#@":
            self._error("Unsupported unquoted string syntax.", code="invalid-string", line=line, column=column, category="lexical_error")
        if first in "-?" and (len(token) == 1 or token[1] == " "):
            self._error("Unsupported unquoted string syntax.", code="invalid-string", line=line, column=column, category="lexical_error")
        if token.endswith(":") or ": " in token:
            self._error("`:` is not permitted at the end of or before a space in unquoted string scalars.", code="unquoted-colon", line=line, column=column, category="lexical_error")
        if in_flow and any(c in token for c in ",[]{}"):
            self._error("Unquoted strings in flow containers may not contain `,`, `[`, `]`, `{`, or `}`.", code="flow-unquoted-comma", line=line, column=column, category="lexical_error")
        return ScalarNode(token, kind="string", style="plain", raw=token)

    def _scan_flow_delimiters(self, token: str, line: int, column: int) -> list[int]:
        """Validate the brackets of the flow container `token` and return the indices of its top-level commas."""
        commas: list[int] = []
        quote: str | None = None
        escaped = False
        single_quote_end = False
        open_brackets: list[tuple[str, int]] = []
        for index, char in enumerate(token):
            if quote:
                if quote == '"':
                    if escaped:
                        escaped = False
                        continue
                    if char == "\\":
                        escaped = True
                        continue
                elif single_quote_end:
                    single_quote_end = False
                    if char == "'":
                        continue
                    quote = None
                if quote and char == quote:
                    if quote == "'":
                        single_quote_end = True
                    else:
                        quote = None
                    continue
                if quote:
                    continue
            if char in {'"', "'"}:
                quote = char
                continue
            # Brackets open a nested container only where a value starts and close one only where a
            # value ends; elsewhere they are scalar content, which scalar parsing rejects.
            if char in "[{" and token[:index].rstrip()[-1:] in {"", ",", ":", "[", "{"}:
                open_brackets.append(("]" if char == "[" else "}", index))
                continue
            if not open_brackets:
                if char.isspace():
                    continue
                self._error("Unexpected content after flow container.", code="malformed-flow", line=line, column=column + index)
            if char in "]}" and token[index + 1 :].lstrip()[:1] in {"", ",", "]", "}"}:
                expected = open_brackets[-1][0]
                if char != expected:
                    self._error(
                        f"Mismatched `{char}` in flow container; expected `{expected}`.",
                        code="mismatched-flow-delimiter",
                        line=line,
                        column=column + index,
                    )
                open_brackets.pop()
                continue
            if char == "," and len(open_brackets) == 1:
                commas.append(index)
        if open_brackets:
            is_sequence = open_brackets[-1][0] == "]"
            self._error(
                f"Unclosed `{'[' if is_sequence else '{'}` in flow container; flow containers must stay on one line.",
                code="malformed-sequence" if is_sequence else "malformed-mapping",
                line=line,
                column=column + open_brackets[-1][1],
            )
        return commas

    def _split_flow_items(self, token: str, commas: list[int], line: int, column: int):
        parts: list[tuple[str, int]] = []
        for start, end in zip([0, *commas], [*commas, len(token) - 1]):
            segment = token[start + 1 : end]
            part = segment.strip()
            if not part:
                self._error("Malformed flow container.", code="malformed-flow", line=line, column=column + start + 1)
            parts.append((part, column + start + 1 + len(segment) - len(segment.lstrip())))
        return parts

    def _find_mapping_separator(self, text: str, *, in_flow: bool = False) -> int | None:
        """Find the `:` that separates a key from its value.

        The `:` must be outside quotes and flow containers and followed by whitespace or the end of
        `text`; in a flow mapping it may also directly follow a quoted key, as in `{"a":1}`.
        """
        quote: str | None = None
        escaped = False
        single_quote_end = False
        depth = 0
        for index, char in enumerate(text):
            if quote:
                if quote == '"':
                    if escaped:
                        escaped = False
                        continue
                    if char == "\\":
                        escaped = True
                        continue
                elif single_quote_end:
                    single_quote_end = False
                    if char == "'":
                        continue
                    quote = None
                if quote and char == quote:
                    if quote == "'":
                        single_quote_end = True
                    else:
                        quote = None
                    continue
                if quote:
                    continue
            if char in {'"', "'"}:
                quote = char
                continue
            if char in "[{":
                depth += 1
                continue
            if char in "]}":
                depth -= 1
                continue
            if depth == 0 and char == ":":
                following = text[index + 1 : index + 2]
                if not following or following.isspace() or in_flow and text[:index].endswith(("'", '"')):
                    return index
        return None

    def _split_comment(self, text: str) -> tuple[str, str | None]:
        quote: str | None = None
        escaped = False
        single_quote_end = False
        for index, char in enumerate(text):
            if quote:
                if quote == '"':
                    if escaped:
                        escaped = False
                        continue
                    if char == "\\":
                        escaped = True
                        continue
                elif single_quote_end:
                    single_quote_end = False
                    if char == "'":
                        continue
                    quote = None
                if quote and char == quote:
                    if quote == "'":
                        single_quote_end = True
                    else:
                        quote = None
                    continue
                if quote:
                    continue
            if char in {'"', "'"}:
                quote = char
                continue
            if char == "#" and (index == 0 or text[index - 1] == " "):
                return text[:index].rstrip(), text[index:]
        return text.rstrip(), None

    def _next_significant_index(self) -> int:
        probe = self.index
        while probe < len(self.lines):
            line = self.lines[probe]
            if self._is_blank(line.text) or self._is_comment(line.text):
                probe += 1
                continue
            return probe
        return probe

    def _peek_block_scalar_indent(self) -> int:
        """Leading spaces of the next non-blank line, which may begin with `#` or a tab as block scalar content."""
        probe = self.index
        while probe < len(self.lines) and self._is_blank(self.lines[probe].text):
            probe += 1
        if probe == len(self.lines):
            return -1
        text = self.lines[probe].text
        return len(text) - len(text.lstrip(" "))

    def _peek_significant_indent(self) -> int:
        probe = self._next_significant_index()
        if probe < len(self.lines):
            return self._indentation(self.lines[probe])
        return -1

    def _indentation(self, line: Line) -> int:
        count = 0
        for char in line.text:
            if char == " ":
                count += 1
                continue
            if char == "\t":
                self._error("Tabs are not permitted in indentation.", code="invalid-indentation", line=line.number, column=count + 1)
            break
        return count

    @staticmethod
    def _is_blank(text: str) -> bool:
        return text.strip() == ""

    @staticmethod
    def _is_comment(text: str) -> bool:
        return text.lstrip().startswith("#")

    def _error(
        self,
        message: str,
        *,
        code: str,
        line: int,
        column: int,
        category: str = "structural_error",
    ) -> None:
        raise ParseError(message, code=code, category=category, line=line, column=column)


def parse_text(text: str, *, mode: str = "standard", roundtrip: bool = False):
    parser = Parser(text, mode=mode, roundtrip=roundtrip)
    return parser.parse()


def parse_document(text: str, *, mode: str = "standard") -> DocumentNode:
    parser = Parser(text, mode=mode, roundtrip=False)
    return parser.parse_document()
