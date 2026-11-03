from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TextIO

VALID_MODES = ("standard", "strict")

_INT_RE = re.compile(r"^(?:0|-?[1-9][0-9]*)$")
_HEX_RE = re.compile(r"^0x[0-9A-Fa-f]+$")
_DECIMAL_RE = re.compile(r"^-?(?:0|[1-9][0-9]*)\.[0-9]+$")
_EXP_RE = re.compile(r"^-?(?:[1-9](?:\.[0-9]+)?)e-?[0-9]+$")
_NUMERIC_UNDERSCORE_RE = re.compile(r"^-?(?:0x[0-9A-Fa-f_]+|[0-9][0-9_]*(?:\.[0-9_]+)?(?:e-?[0-9_]+)?)$")
_LEADING_ZERO_DECIMAL_RE = re.compile(r"^-?0[0-9]+\.[0-9]+$")
_SCI_RE = re.compile(r"^-?(?:[0-9]+(?:\.[0-9]+)?|\.[0-9]+)e-?[0-9]+$")
_UNQUOTED_KEY_RE = re.compile(r"^[\w./$()~\-]+$", re.UNICODE)


class MymlError(Exception):
    """Base error for caller-facing Myml failures."""

    def __init__(
        self,
        message: str,
        *,
        code: str = "myml-error",
        category: str = "error",
        line: int | None = None,
        column: int | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.category = category
        self.line = line
        self.column = column

    def __str__(self) -> str:
        if self.line is not None and self.column is not None:
            return f"{self.message} (line {self.line}, column {self.column})"
        return self.message


class ParseError(MymlError):
    """Raised when Myml input is invalid."""


class ModeError(MymlError):
    """Raised when a caller supplies an unsupported mode."""


@dataclass
class Line:
    number: int
    text: str


def load(stream: TextIO, *, mode: str = "standard", roundtrip: bool = False):
    return loads(stream.read(), mode=mode, roundtrip=roundtrip)


def loads(text: str, *, mode: str = "standard", roundtrip: bool = False):
    _ = roundtrip
    return Parser(text, mode=mode).parse()


def _validate_mode(mode: str) -> str:
    if mode not in VALID_MODES:
        raise ModeError(
            f"Unsupported mode {mode!r}. Expected one of {', '.join(VALID_MODES)}.",
            code="unsupported-mode",
            category="api_error",
        )
    return mode


class Parser:
    def __init__(self, text: str, *, mode: str = "standard") -> None:
        self.text = text
        self.lines = [Line(index + 1, raw) for index, raw in enumerate(text.splitlines())]
        self.index = 0
        self.mode = _validate_mode(mode)

    def parse(self):
        self._consume_trivia()
        if self.index >= len(self.lines):
            return None
        root = self._parse_block(indent=0)
        self._consume_trivia()
        if self.index < len(self.lines):
            line = self.lines[self.index]
            self._error("Unexpected content after document root.", code="malformed-document", line=line.number, column=1)
        return root

    def _consume_trivia(self) -> None:
        while self.index < len(self.lines):
            line = self.lines[self.index]
            if self._is_blank(line.text) or self._is_comment(line.text):
                self.index += 1
                continue
            break

    def _parse_block(self, indent: int):
        if self.index >= len(self.lines):
            self._error("Expected a value.", code="missing-value", line=self.lines[-1].number if self.lines else 1, column=1)
        # Comment and blank lines may precede a nested block.
        self._consume_trivia()
        line = self.lines[self.index]
        actual = self._indentation(line)
        if actual != indent:
            self._error("Invalid indentation.", code="invalid-indentation", line=line.number, column=actual + 1)
        stripped = line.text[indent:]
        body, _comment = self._split_comment(stripped)
        if body == "-" or body.startswith("- "):
            return self._parse_sequence(indent)
        if self._find_mapping_separator(body) is not None:
            return self._parse_mapping(indent)
        return self._parse_root_scalar(indent)

    def _parse_root_scalar(self, indent: int):
        line = self.lines[self.index]
        body, _comment = self._split_comment(line.text[indent:])
        token = body.strip()
        if not token:
            self._error("Expected a scalar value.", code="missing-value", line=line.number, column=indent + 1)
        if self.index + 1 < len(self.lines):
            next_line = self.lines[self.index + 1]
            if self._indentation(next_line) > indent:
                self._error_if_multiline_scalar_continuation(next_line, indent)
        value = self._parse_inline_value(token, line.number, indent + body.index(token) + 1, in_flow=False)
        self.index += 1
        return value

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
        result: dict[str, object] = {}
        seen_keys: set[str] = set()
        while self.index < len(self.lines):
            self._consume_trivia()
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
            body, _comment = self._split_comment(raw)
            self.index += 1
            key, value = self._parse_mapping_entry(body, indent, line, seen_keys)
            result[key] = value
        return result

    def _parse_mapping_entry(self, body: str, indent: int, line: Line, seen_keys: set[str]):
        """Parse one block mapping entry whose key starts at column `indent` of `line`, the line before `self.index`."""
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
        result: list[object] = []
        while self.index < len(self.lines):
            self._consume_trivia()
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
            item_body, _comment = self._split_comment(raw[1:].lstrip())
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
                    key, entry_value = self._parse_mapping_entry(item_body, key_indent, line, set())
                    value = {key: entry_value}
                    continuation_indent = self._peek_significant_indent()
                    if continuation_indent > indent:
                        continuation = self._parse_mapping(continuation_indent)
                        duplicate_keys = value.keys() & continuation.keys()
                        if duplicate_keys:
                            self._error(
                                "Duplicate mapping key.",
                                code="duplicate-key",
                                line=line.number,
                                column=indent + 3,
                                category="semantic_error",
                            )
                        value.update(continuation)
                else:
                    if self.index < len(self.lines):
                        next_line = self.lines[self.index]
                        if self._indentation(next_line) > indent:
                            self._error_if_multiline_scalar_continuation(next_line, indent)
                    value = self._parse_inline_value(token, line.number, indent + 3, in_flow=False)
            result.append(value)
        return result

    def _parse_block_scalar(self, indicator: str, parent_indent: int, header_line: int) -> str:
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
            lines.append(line.text[next_indent:])
            self.index += 1
        if indicator == "|":
            return "".join(f"{piece}\n" for piece in lines)
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
        return "\n".join(paragraphs).rstrip("\n") + "\n"

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
            return []
        result: list[object] = []
        for part, part_column in self._split_flow_items(token, commas, line, column):
            result.append(self._parse_inline_value(part, line, part_column, in_flow=True))
        return result

    def _parse_flow_mapping(self, token: str, line: int, column: int):
        commas = self._scan_flow_delimiters(token, line, column)
        if not token[1:-1].strip():
            return {}
        result: dict[str, object] = {}
        seen_keys: set[str] = set()
        for part, part_column in self._split_flow_items(token, commas, line, column):
            separator = self._find_mapping_separator(part, in_flow=True)
            if separator is None:
                self._error("Malformed flow mapping entry.", code="malformed-mapping", line=line, column=part_column)
            key_text = part[:separator].rstrip()
            value_text = part[separator + 1 :].lstrip()
            key = self._parse_key(key_text, line, part_column)
            if key in seen_keys:
                self._error("Duplicate mapping key.", code="duplicate-key", line=line, column=part_column, category="semantic_error")
            seen_keys.add(key)
            result[key] = self._parse_inline_value(value_text, line, part_column + separator + 1, in_flow=True)
        return result

    def _parse_key(self, token: str, line: int, column: int) -> str:
        if token == "<<":
            return token
        if token.startswith("'") or token.startswith('"'):
            return self._parse_quoted_scalar(token, line, column)
        if "#" in token:
            self._error("`#` is not permitted within unquoted keys.", code="unquoted-key-hash", line=line, column=column)
        if ":" in token:
            self._error("`:` is not permitted within unquoted keys.", code="unquoted-key-colon", line=line, column=column)
        if not token:
            self._error("Mapping keys must be strings.", code="non-string-key", line=line, column=column)
        if not _UNQUOTED_KEY_RE.match(token):
            self._error("Unsupported unquoted key syntax.", code="invalid-key", line=line, column=column)
        return token

    def _parse_quoted_scalar(self, token: str, line: int, column: int) -> str:
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
        return value

    def _parse_plain_scalar(self, token: str, line: int, column: int, *, in_flow: bool):
        if token in {"true", "false"}:
            return token == "true"
        if token == "null":
            return None
        if token in {".inf", "-.inf", ".nan"}:
            if token == ".inf":
                return float("inf")
            if token == "-.inf":
                return float("-inf")
            return float("nan")
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
            return int(token, 16)
        if _INT_RE.match(token):
            return int(token)
        if _DECIMAL_RE.match(token):
            return float(token)
        if _EXP_RE.match(token):
            number = float(token)
            return int(number) if number.is_integer() else number
        if _SCI_RE.match(token):
            self._error(
                "Scientific notation must use a normalized coefficient with 1 <= m < 10.",
                code="invalid-number-scientific-notation",
                line=line,
                column=column,
                category="lexical_error",
            )
        if self.mode == "strict":
            self._error("Strict mode requires quoted string scalars.", code="strict-mode-unquoted-string", line=line, column=column, category="mode_restriction")
        first = token[0]
        if first in "!\"'`*%&>|,[]{}#@":
            self._error("Unsupported unquoted string syntax.", code="invalid-string", line=line, column=column, category="lexical_error")
        if first in "-?" and len(token) > 1 and token[1] == " ":
            self._error("Unsupported unquoted string syntax.", code="invalid-string", line=line, column=column, category="lexical_error")
        if token.endswith(":") or ": " in token:
            self._error("`:` is not permitted at the end of or before a space in unquoted string scalars.", code="unquoted-colon", line=line, column=column, category="lexical_error")
        if in_flow and any(c in token for c in ",[]{}"):
            self._error("Unquoted strings in flow containers may not contain `,`, `[`, `]`, `{`, or `}`.", code="flow-unquoted-comma", line=line, column=column, category="lexical_error")
        return token

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

    def _split_flow_items(self, token: str, commas: list[int], line: int, column: int) -> list[tuple[str, int]]:
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


__all__ = [
    "ModeError",
    "MymlError",
    "ParseError",
    "load",
    "loads",
]
