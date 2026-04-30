from __future__ import annotations

import codecs
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
_UNQUOTED_KEY_RE = re.compile(r"^[\w./$()~\-]+$", re.UNICODE)


@dataclass
class Line:
    number: int
    text: str


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
        line = self.lines[self.index]
        actual = self._indentation(line)
        if actual != indent:
            self._error("Invalid indentation.", code="invalid-indentation", line=line.number, column=actual + 1)
        stripped = line.text[indent:]
        body, _comment = self._split_comment(stripped)
        if body.startswith("- "):
            return self._parse_sequence(indent)
        if self._find_mapping_separator(body) is not None:
            return self._parse_mapping(indent)
        return self._parse_root_scalar(indent)

    def _parse_root_scalar(self, indent: int):
        line = self.lines[self.index]
        body, comment = self._split_comment(line.text[indent:])
        token = body.strip()
        if not token:
            self._error("Expected a scalar value.", code="missing-value", line=line.number, column=indent + 1)
        node = self._parse_inline_value(token, line.number, indent + body.index(token) + 1, in_flow=False)
        self.index += 1
        if comment:
            if isinstance(node, ScalarNode):
                node.raw = token
        return node

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
                self._error("Invalid indentation.", code="invalid-indentation", line=line.number, column=actual + 1)
            raw = line.text[indent:]
            if raw.startswith("- "):
                self._error("Sequence item is not valid in a mapping position.", code="malformed-mapping", line=line.number, column=indent + 1)
            body, comment = self._split_comment(raw)
            separator = self._find_mapping_separator(body)
            if separator is None:
                self._error("Malformed mapping entry.", code="malformed-mapping", line=line.number, column=indent + 1)
            key_text = body[:separator].rstrip()
            value_text = body[separator + 1 :].lstrip()
            key = self._parse_key(key_text, line.number, indent + body.index(key_text) + 1)
            if key == "<<":
                self._error("Merge keys are not supported.", code="unsupported-merge-key", line=line.number, column=indent + 1, category="unsupported_feature")
            if key in seen_keys:
                self._error("Duplicate mapping key.", code="duplicate-key", line=line.number, column=indent + 1, category="semantic_error")
            seen_keys.add(key)
            self.index += 1
            inline_comment = comment
            if value_text in {"|", ">"}:
                value = self._parse_block_scalar(value_text, indent, line.number)
            elif not value_text:
                if self._peek_significant_indent() <= indent:
                    self._error("Mapping entries must have a value.", code="missing-value", line=line.number, column=indent + separator + 2)
                value = self._parse_block(self._peek_significant_indent())
            else:
                start_column = indent + separator + 2 + (len(body[separator + 1 :]) - len(body[separator + 1 :].lstrip()))
                value = self._parse_inline_value(value_text, line.number, start_column, in_flow=False)
            entries.append(MappingEntry(key=key, value=value, before=pending_before, inline_comment=inline_comment))
            pending_before = []
        node = MappingNode(entries, style="block", trailing_lines=pending_before)
        return node

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
                self._error("Invalid indentation.", code="invalid-indentation", line=line.number, column=actual + 1)
            raw = line.text[indent:]
            if not raw.startswith("- "):
                break
            item_body, comment = self._split_comment(raw[2:])
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
                    value = self._parse_inline_mapping(token, line.number, indent + 3)
                else:
                    value = self._parse_inline_value(token, line.number, indent + 3, in_flow=False)
            items.append(SequenceItem(value=value, before=pending_before, inline_comment=comment))
            pending_before = []
        return SequenceNode(items, style="block", trailing_lines=pending_before)

    def _parse_inline_mapping(self, text: str, line: int, column: int):
        separator = self._find_mapping_separator(text)
        if separator is None:
            self._error("Malformed mapping entry.", code="malformed-mapping", line=line, column=column)
        key_text = text[:separator].rstrip()
        value_text = text[separator + 1 :].lstrip()
        key = self._parse_key(key_text, line, column)
        if key == "<<":
            self._error("Merge keys are not supported.", code="unsupported-merge-key", line=line, column=column, category="unsupported_feature")
        if not value_text:
            self._error("Inline mapping entries must have a value.", code="missing-value", line=line, column=column + separator + 1)
        value = self._parse_inline_value(value_text, line, column + separator + 1, in_flow=False)
        return MappingNode([MappingEntry(key=key, value=value)], style="block", compact=True)

    def _parse_block_scalar(self, indicator: str, parent_indent: int, header_line: int):
        next_indent = self._peek_significant_indent()
        if next_indent <= parent_indent:
            self._error("Block scalar requires indented content.", code="missing-value", line=header_line, column=parent_indent + 1)
        lines: list[str] = []
        while self.index < len(self.lines):
            line = self.lines[self.index]
            if self._is_blank(line.text):
                lines.append("")
                self.index += 1
                continue
            actual = self._indentation(line)
            if actual < next_indent:
                break
            if actual < parent_indent:
                break
            segment = line.text[next_indent:]
            lines.append(segment)
            self.index += 1
        if indicator == "|":
            value = "".join(f"{piece}\n" for piece in lines)
            return ScalarNode(value, kind="string", style="literal", raw="|")
        paragraphs: list[str] = []
        current: list[str] = []
        for piece in lines:
            if piece == "":
                if current:
                    paragraphs.append(" ".join(current))
                    current = []
                paragraphs.append("")
            else:
                current.append(piece)
        if current:
            paragraphs.append(" ".join(current))
        text = "\n".join(paragraphs).rstrip("\n") + "\n"
        return ScalarNode(text, kind="string", style="folded", raw=">")

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
        if not token.endswith("]"):
            self._error("Flow sequences must stay on one line.", code="malformed-sequence", line=line, column=column)
        inner = token[1:-1].strip()
        if not inner:
            return SequenceNode([], style="flow")
        parts = self._split_flow_items(inner, line, column + 1)
        items: list[SequenceItem] = []
        for part, part_column in parts:
            if part.startswith("{") or part.startswith("["):
                self._error("Flow containers may contain scalar values only.", code="flow-non-scalar-element", line=line, column=part_column, category="unsupported_feature")
            items.append(SequenceItem(self._parse_inline_value(part, line, part_column, in_flow=True)))
        return SequenceNode(items, style="flow")

    def _parse_flow_mapping(self, token: str, line: int, column: int):
        if not token.endswith("}"):
            self._error("Flow mappings must stay on one line.", code="malformed-mapping", line=line, column=column)
        inner = token[1:-1].strip()
        if not inner:
            return MappingNode([], style="flow")
        parts = self._split_flow_items(inner, line, column + 1)
        entries: list[MappingEntry] = []
        seen_keys: set[str] = set()
        for part, part_column in parts:
            separator = self._find_mapping_separator(part)
            if separator is None:
                self._error("Malformed flow mapping entry.", code="malformed-mapping", line=line, column=part_column)
            key_text = part[:separator].rstrip()
            value_text = part[separator + 1 :].lstrip()
            key = self._parse_key(key_text, line, part_column)
            if key in seen_keys:
                self._error("Duplicate mapping key.", code="duplicate-key", line=line, column=part_column, category="semantic_error")
            seen_keys.add(key)
            if value_text.startswith("{") or value_text.startswith("["):
                self._error("Flow containers may contain scalar values only.", code="flow-non-scalar-element", line=line, column=part_column + separator + 1, category="unsupported_feature")
            entries.append(MappingEntry(key, self._parse_inline_value(value_text, line, part_column + separator + 1, in_flow=True)))
        return MappingNode(entries, style="flow")

    def _parse_key(self, token: str, line: int, column: int) -> str:
        if token == "<<":
            return token
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
        return token

    def _parse_quoted_scalar(self, token: str, line: int, column: int):
        if len(token) < 2 or token[-1] != token[0]:
            self._error("Quoted scalar is not terminated.", code="malformed-string", line=line, column=column)
        if token[0] == "'":
            inner = token[1:-1].replace("''", "'")
            return ScalarNode(inner, kind="string", style="single", raw=token)
        try:
            inner = codecs.decode(token[1:-1], "unicode_escape")
        except Exception as exc:  # pragma: no cover - defensive
            self._error(str(exc), code="malformed-string", line=line, column=column)
        return ScalarNode(inner, kind="string", style="double", raw=token)

    def _parse_plain_scalar(self, token: str, line: int, column: int, *, in_flow: bool):
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
        if token.startswith(".") and len(token) > 1 and token[1:].isdigit():
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
        if "@" in token or "^" in token:
            self._error("Unquoted string scalars may not contain `@` or `^`.", code="unquoted-string-invalid-char", line=line, column=column, category="lexical_error")
        if self.mode == "strict":
            self._error("Strict mode requires quoted string scalars.", code="strict-mode-unquoted-string", line=line, column=column, category="mode_restriction")
        first = token[0]
        if first in "!\"'`*%&>|,[]{}#":
            self._error("Unsupported unquoted string syntax.", code="invalid-string", line=line, column=column, category="lexical_error")
        if first in "-?" and len(token) > 1 and token[1] == " ":
            self._error("Unsupported unquoted string syntax.", code="invalid-string", line=line, column=column, category="lexical_error")
        if token.endswith(":") or ": " in token:
            self._error("`:` is not permitted at the end of or before a space in unquoted string scalars.", code="unquoted-colon", line=line, column=column, category="lexical_error")
        if in_flow and any(c in token for c in ",[]{}"):
            self._error("Unquoted strings in flow containers may not contain `,`, `[`, `]`, `{`, or `}`.", code="flow-unquoted-comma", line=line, column=column, category="lexical_error")
        return ScalarNode(token, kind="string", style="plain", raw=token)

    def _split_flow_items(self, text: str, line: int, column: int):
        parts: list[tuple[str, int]] = []
        start = 0
        part_column = column
        quote: str | None = None
        for index, char in enumerate(text):
            if quote:
                if char == quote:
                    quote = None
                elif char == "\\" and quote == '"':
                    continue
                continue
            if char in {'"', "'"}:
                quote = char
                continue
            if char == ",":
                part = text[start:index].strip()
                if not part:
                    self._error("Malformed flow container.", code="malformed-flow", line=line, column=part_column)
                parts.append((part, part_column + (len(text[start:index]) - len(text[start:index].lstrip()))))
                start = index + 1
                part_column = column + index + 1
        tail = text[start:].strip()
        if not tail:
            self._error("Malformed flow container.", code="malformed-flow", line=line, column=part_column)
        parts.append((tail, part_column + (len(text[start:]) - len(text[start:].lstrip()))))
        return parts

    def _find_mapping_separator(self, text: str) -> int | None:
        quote: str | None = None
        depth = 0
        for index, char in enumerate(text):
            if quote:
                if char == quote:
                    quote = None
                elif char == "\\" and quote == '"':
                    continue
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
                return index
        return None

    def _split_comment(self, text: str) -> tuple[str, str | None]:
        quote: str | None = None
        for index, char in enumerate(text):
            if quote:
                if char == quote:
                    quote = None
                elif char == "\\" and quote == '"':
                    continue
                continue
            if char in {'"', "'"}:
                quote = char
                continue
            if char == "#" and (index == 0 or text[index - 1] == " "):
                return text[:index].rstrip(), text[index:]
        return text.rstrip(), None

    def _peek_significant_indent(self) -> int:
        probe = self.index
        while probe < len(self.lines):
            line = self.lines[probe]
            if self._is_blank(line.text) or self._is_comment(line.text):
                probe += 1
                continue
            return self._indentation(line)
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
