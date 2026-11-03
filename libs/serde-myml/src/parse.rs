//! Line-oriented Myml parser producing a `Value`.
use crate::{Error, Mode, Value};
use std::collections::BTreeMap;

pub(crate) fn parse(text: &str, mode: Mode) -> Result<Value, Error> {
    let text = text.strip_prefix('\u{feff}').unwrap_or(text);
    let lines = split_lines(text);
    for (n, line) in lines.iter().enumerate() {
        let body = split_comment(line);
        if body == "---" || body == "..." || body.starts_with("--- ") || body.starts_with("... ") {
            return Err(Error::at("document markers are unsupported", n + 1, 1));
        }
    }
    let mut p = Parser {
        lines,
        index: 0,
        mode,
    };
    p.consume_trivia();
    if p.index >= p.lines.len() {
        return Ok(Value::Null);
    }
    let root = p.parse_block(0)?;
    p.consume_trivia();
    if p.index < p.lines.len() {
        return Err(Error::at(
            "unexpected content after document root",
            p.index + 1,
            1,
        ));
    }
    Ok(root)
}

struct Parser<'a> {
    lines: Vec<&'a str>,
    index: usize,
    mode: Mode,
}

impl<'a> Parser<'a> {
    fn consume_trivia(&mut self) {
        while self.index < self.lines.len() && is_trivia(self.lines[self.index]) {
            self.index += 1;
        }
    }

    /// Indentation of the next non-trivia line, or `None` at end of input.
    fn peek_indent(&self) -> Result<Option<usize>, Error> {
        let mut n = self.index;
        while n < self.lines.len() {
            if !is_trivia(self.lines[n]) {
                return self.indentation(n).map(Some);
            }
            n += 1;
        }
        Ok(None)
    }

    fn indentation(&self, n: usize) -> Result<usize, Error> {
        let line = self.lines[n];
        let count = line.bytes().take_while(|&b| b == b' ').count();
        if line.as_bytes().get(count) == Some(&b'\t') {
            return Err(Error::at(
                "tabs are not permitted in indentation",
                n + 1,
                count + 1,
            ));
        }
        Ok(count)
    }

    fn parse_block(&mut self, indent: usize) -> Result<Value, Error> {
        self.consume_trivia();
        let n = self.index;
        if n >= self.lines.len() {
            return Err(Error::at("expected a value", self.lines.len().max(1), 1));
        }
        let actual = self.indentation(n)?;
        if actual != indent {
            return Err(Error::at("invalid indentation", n + 1, actual + 1));
        }
        let body = split_comment(&self.lines[n][indent..]);
        if is_sequence_item(body) {
            return self.parse_sequence(indent);
        }
        if find_mapping_separator(body, false).is_some() {
            let mut map = BTreeMap::new();
            self.parse_mapping_into(indent, &mut map)?;
            return Ok(Value::Mapping(map));
        }
        let token = body.trim();
        if token.is_empty() {
            return Err(Error::at("expected a scalar value", n + 1, indent + 1));
        }
        self.index += 1;
        self.reject_continuation(indent)?;
        self.inline_value(token, n + 1, indent + 1, false)
    }

    /// Rejects a more-indented line after a scalar that would continue it as a multiline plain scalar.
    fn reject_continuation(&self, parent_indent: usize) -> Result<(), Error> {
        let n = self.index;
        if n >= self.lines.len() {
            return Ok(());
        }
        let actual = self.indentation(n)?;
        if actual <= parent_indent {
            return Ok(());
        }
        let body = split_comment(&self.lines[n][parent_indent..]);
        let text = body.trim();
        if !text.is_empty()
            && !text.starts_with("- ")
            && find_mapping_separator(body, false).is_none()
        {
            return Err(Error::at(
                "multiline non-block scalar strings are unsupported",
                n + 1,
                actual + 1,
            ));
        }
        Ok(())
    }

    fn parse_mapping_into(
        &mut self,
        indent: usize,
        map: &mut BTreeMap<String, Value>,
    ) -> Result<(), Error> {
        loop {
            self.consume_trivia();
            let n = self.index;
            if n >= self.lines.len() {
                return Ok(());
            }
            let actual = self.indentation(n)?;
            if actual < indent {
                return Ok(());
            }
            if actual > indent {
                self.reject_continuation_at(n, indent)?;
                return Err(Error::at("invalid indentation", n + 1, actual + 1));
            }
            let body = split_comment(&self.lines[n][indent..]);
            if is_sequence_item(body) {
                return Err(Error::at(
                    "sequence item is not valid in a mapping position",
                    n + 1,
                    indent + 1,
                ));
            }
            self.index += 1;
            self.parse_mapping_entry(body, indent, n, map)?;
        }
    }

    fn reject_continuation_at(&mut self, n: usize, parent_indent: usize) -> Result<(), Error> {
        let saved = self.index;
        self.index = n;
        let result = self.reject_continuation(parent_indent);
        self.index = saved;
        result
    }

    /// Parses one block mapping entry whose key starts at column `indent` of line `n`.
    fn parse_mapping_entry(
        &mut self,
        body: &str,
        indent: usize,
        n: usize,
        map: &mut BTreeMap<String, Value>,
    ) -> Result<(), Error> {
        let line = n + 1;
        let sep = find_mapping_separator(body, false)
            .ok_or_else(|| Error::at("malformed mapping entry", line, indent + 1))?;
        let key_text = body[..sep].trim_end();
        let value_part = &body[sep + 1..];
        let value_text = value_part.trim_start();
        let key = parse_key(key_text, line, indent + 1)?;
        if map.contains_key(&key) {
            return Err(Error::at(
                format!("duplicate mapping key {key:?}"),
                line,
                indent + 1,
            ));
        }
        let sep_col = indent + chars(&body[..sep]) + 1;
        let value = if value_text == "|" || value_text == ">" {
            self.parse_block_scalar(value_text, indent, line)?
        } else if value_text.is_empty() {
            match self.peek_indent()? {
                Some(next) if next > indent => self.parse_block(next)?,
                _ => {
                    return Err(Error::at(
                        "mapping entries require a value",
                        line,
                        sep_col + 1,
                    ))
                }
            }
        } else {
            self.reject_continuation(indent)?;
            let col = sep_col + 1 + chars(value_part) - chars(value_text);
            self.inline_value(value_text, line, col, false)?
        };
        map.insert(key, value);
        Ok(())
    }

    fn parse_sequence(&mut self, indent: usize) -> Result<Value, Error> {
        let mut items = Vec::new();
        loop {
            self.consume_trivia();
            let n = self.index;
            if n >= self.lines.len() {
                break;
            }
            let actual = self.indentation(n)?;
            if actual < indent {
                break;
            }
            if actual > indent {
                self.reject_continuation_at(n, indent)?;
                return Err(Error::at("invalid indentation", n + 1, actual + 1));
            }
            let raw = &self.lines[n][indent..];
            if !is_sequence_item(split_comment(raw)) {
                break;
            }
            let after = &raw[1..];
            let item_body = split_comment(after.trim_start());
            let token = item_body.trim();
            let line = n + 1;
            self.index += 1;
            let value = if token.is_empty() {
                match self.peek_indent()? {
                    Some(next) if next > indent => self.parse_block(next)?,
                    _ => {
                        return Err(Error::at(
                            "sequence items require a value",
                            line,
                            indent + 2,
                        ))
                    }
                }
            } else if token == "|" || token == ">" {
                self.parse_block_scalar(token, indent, line)?
            } else if find_mapping_separator(token, false).is_some() && !token.starts_with('{') {
                // The item is a block mapping whose keys align with its first key.
                let key_indent = indent + 1 + after.len() - after.trim_start().len();
                let mut map = BTreeMap::new();
                self.parse_mapping_entry(item_body, key_indent, n, &mut map)?;
                if self.peek_indent()?.is_some_and(|next| next > indent) {
                    self.parse_mapping_into(key_indent, &mut map)?;
                }
                Value::Mapping(map)
            } else {
                self.reject_continuation(indent)?;
                self.inline_value(token, line, indent + 3, false)?
            };
            items.push(value);
        }
        Ok(Value::Sequence(items))
    }

    fn parse_block_scalar(
        &mut self,
        indicator: &str,
        parent_indent: usize,
        header_line: usize,
    ) -> Result<Value, Error> {
        // Block scalar content indentation comes from the next non-blank line, which may begin with
        // `#` or, after the indentation, a tab.
        let spaces = |text: &str| text.bytes().take_while(|&b| b == b' ').count();
        let next = self.lines[self.index..]
            .iter()
            .find(|text| !text.trim().is_empty());
        let content_indent = match next.map(|text| spaces(text)) {
            Some(next) if next > parent_indent => next,
            _ => {
                return Err(Error::at(
                    "empty block scalar is unsupported",
                    header_line,
                    parent_indent + 1,
                ))
            }
        };
        let mut pieces: Vec<&str> = Vec::new();
        while self.index < self.lines.len() {
            let text = self.lines[self.index];
            if text.trim().is_empty() {
                // Whitespace beyond the content indentation is content, even on an otherwise blank line.
                pieces.push(if spaces(text) >= content_indent {
                    &text[content_indent..]
                } else {
                    ""
                });
            } else if spaces(text) < content_indent {
                // Tabs may follow the content indentation, but not form part of it.
                self.indentation(self.index)?;
                break;
            } else {
                pieces.push(&text[content_indent..]);
            }
            self.index += 1;
        }
        // Clip chomping: trailing blank lines do not contribute to the value.
        while pieces.last() == Some(&"") {
            pieces.pop();
        }
        let mut out = String::new();
        if indicator == "|" {
            for piece in pieces {
                out.push_str(piece);
                out.push('\n');
            }
            return Ok(Value::String(out));
        }
        let mut breaks = 0;
        let mut prev: Option<&str> = None;
        for piece in pieces {
            if piece.is_empty() {
                breaks += 1;
                continue;
            }
            // Line breaks next to more-indented lines are not folded.
            let spaced = |line: &str| line.starts_with([' ', '\t']);
            match prev {
                Some(p) if spaced(p) || spaced(piece) => out.push_str(&"\n".repeat(breaks + 1)),
                Some(_) if breaks == 0 => out.push(' '),
                _ => out.push_str(&"\n".repeat(breaks)),
            }
            out.push_str(piece);
            breaks = 0;
            prev = Some(piece);
        }
        out.push('\n');
        Ok(Value::String(out))
    }

    fn inline_value(
        &self,
        token: &str,
        line: usize,
        col: usize,
        in_flow: bool,
    ) -> Result<Value, Error> {
        if token.starts_with('&') || token.starts_with('*') {
            return Err(Error::at("anchors and aliases are unsupported", line, col));
        }
        if token.starts_with('!') {
            return Err(Error::at("tags are unsupported", line, col));
        }
        if token == "~" {
            return Err(Error::at("the `~` null spelling is unsupported", line, col));
        }
        if token.starts_with('[') {
            return self.flow_sequence(token, line, col);
        }
        if token.starts_with('{') {
            return self.flow_mapping(token, line, col);
        }
        if token.starts_with('\'') || token.starts_with('"') {
            return quoted_scalar(token, line, col).map(Value::String);
        }
        plain_scalar(token, self.mode, in_flow, line, col)
    }

    fn flow_sequence(&self, token: &str, line: usize, col: usize) -> Result<Value, Error> {
        let commas = scan_flow_delimiters(token, line, col)?;
        if token[1..token.len() - 1].trim().is_empty() {
            return Ok(Value::Sequence(Vec::new()));
        }
        split_flow_items(token, &commas, line, col)?
            .into_iter()
            .map(|(part, part_col)| self.inline_value(part, line, part_col, true))
            .collect::<Result<_, _>>()
            .map(Value::Sequence)
    }

    fn flow_mapping(&self, token: &str, line: usize, col: usize) -> Result<Value, Error> {
        let commas = scan_flow_delimiters(token, line, col)?;
        let mut map = BTreeMap::new();
        if token[1..token.len() - 1].trim().is_empty() {
            return Ok(Value::Mapping(map));
        }
        for (part, part_col) in split_flow_items(token, &commas, line, col)? {
            let sep = find_mapping_separator(part, true)
                .ok_or_else(|| Error::at("malformed flow mapping entry", line, part_col))?;
            let key = parse_key(part[..sep].trim_end(), line, part_col)?;
            if map.contains_key(&key) {
                return Err(Error::at(
                    format!("duplicate mapping key {key:?}"),
                    line,
                    part_col,
                ));
            }
            let value_col = part_col + chars(&part[..sep]) + 1;
            let value = self.inline_value(part[sep + 1..].trim_start(), line, value_col, true)?;
            map.insert(key, value);
        }
        Ok(Value::Mapping(map))
    }
}

/// Splits `text` at YAML 1.2 line breaks: CRLF, CR, and LF.
fn split_lines(text: &str) -> Vec<&str> {
    let mut lines = Vec::new();
    let bytes = text.as_bytes();
    let (mut start, mut i) = (0, 0);
    while i < bytes.len() {
        if bytes[i] == b'\n' || bytes[i] == b'\r' {
            lines.push(&text[start..i]);
            if bytes[i] == b'\r' && bytes.get(i + 1) == Some(&b'\n') {
                i += 1;
            }
            start = i + 1;
        }
        i += 1;
    }
    if start < text.len() {
        lines.push(&text[start..]);
    }
    lines
}

fn chars(s: &str) -> usize {
    s.chars().count()
}

fn is_trivia(line: &str) -> bool {
    let t = line.trim_start();
    t.is_empty() || t.starts_with('#')
}

fn is_sequence_item(body: &str) -> bool {
    body == "-" || body.starts_with("- ")
}

/// Yields the characters of `text` that lie outside quoted scalars, with byte offsets.
/// Opening and closing quote characters are not yielded.
fn outside_quotes(text: &str) -> impl Iterator<Item = (usize, char)> + '_ {
    let mut quote: Option<char> = None;
    let mut escaped = false;
    let mut single_quote_end = false;
    text.char_indices().filter(move |&(_, c)| {
        match quote {
            Some('"') => {
                if escaped {
                    escaped = false;
                } else if c == '\\' {
                    escaped = true;
                } else if c == '"' {
                    quote = None;
                }
                return false;
            }
            Some(_) if single_quote_end => {
                single_quote_end = false;
                if c == '\'' {
                    return false;
                }
                quote = None;
            }
            Some(_) => {
                single_quote_end = c == '\'';
                return false;
            }
            None => {}
        }
        if c == '"' || c == '\'' {
            quote = Some(c);
            return false;
        }
        true
    })
}

/// Strips a trailing comment and trailing whitespace.
fn split_comment(text: &str) -> &str {
    for (i, c) in outside_quotes(text) {
        if c == '#' && (i == 0 || text.as_bytes()[i - 1] == b' ') {
            return text[..i].trim_end();
        }
    }
    text.trim_end()
}

/// Finds the `:` separating a mapping key from its value: outside quotes and flow containers, and
/// followed by whitespace or the end of the text. In a flow mapping it may also directly follow a
/// quoted key, as in `{"a":1}`.
fn find_mapping_separator(text: &str, in_flow: bool) -> Option<usize> {
    let mut depth = 0i32;
    for (i, c) in outside_quotes(text) {
        match c {
            '[' | '{' => depth += 1,
            ']' | '}' => depth -= 1,
            ':' if depth == 0 => {
                let next = text[i + 1..].chars().next();
                if next.is_none_or(char::is_whitespace)
                    || in_flow && text[..i].ends_with(['"', '\''])
                {
                    return Some(i);
                }
            }
            _ => {}
        }
    }
    None
}

/// Validates the brackets of flow container `token` and returns the byte offsets of its top-level commas.
fn scan_flow_delimiters(token: &str, line: usize, col: usize) -> Result<Vec<usize>, Error> {
    let mut commas = Vec::new();
    let mut open: Vec<(char, usize)> = Vec::new();
    let at = |i: usize| col + chars(&token[..i]);
    for (i, c) in outside_quotes(token) {
        // Brackets open a nested container only where a value starts and close one only where a
        // value ends; elsewhere they are scalar content, which scalar parsing rejects.
        let before = token[..i].trim_end().chars().last();
        if (c == '[' || c == '{') && matches!(before, None | Some(',' | ':' | '[' | '{')) {
            open.push((if c == '[' { ']' } else { '}' }, i));
            continue;
        }
        let Some(&(expected, _)) = open.last() else {
            if c.is_whitespace() {
                continue;
            }
            return Err(Error::at(
                "unexpected content after flow container",
                line,
                at(i),
            ));
        };
        let after = token[i + c.len_utf8()..].trim_start().chars().next();
        if (c == ']' || c == '}') && matches!(after, None | Some(',' | ']' | '}')) {
            if c != expected {
                return Err(Error::at(
                    format!("mismatched `{c}` in flow container; expected `{expected}`"),
                    line,
                    at(i),
                ));
            }
            open.pop();
            continue;
        }
        if c == ',' && open.len() == 1 {
            commas.push(i);
        }
    }
    if let Some(&(closer, i)) = open.last() {
        let opener = if closer == ']' { '[' } else { '{' };
        return Err(Error::at(
            format!("unclosed `{opener}` in flow container; flow containers must stay on one line"),
            line,
            at(i),
        ));
    }
    Ok(commas)
}

fn split_flow_items<'t>(
    token: &'t str,
    commas: &[usize],
    line: usize,
    col: usize,
) -> Result<Vec<(&'t str, usize)>, Error> {
    let starts = std::iter::once(0).chain(commas.iter().copied());
    let ends = commas
        .iter()
        .copied()
        .chain(std::iter::once(token.len() - 1));
    starts
        .zip(ends)
        .map(|(start, end)| {
            let segment = &token[start + 1..end];
            let part = segment.trim();
            let part_col =
                col + chars(&token[..start + 1]) + chars(segment) - chars(segment.trim_start());
            if part.is_empty() {
                return Err(Error::at("malformed flow container", line, part_col));
            }
            Ok((part, part_col))
        })
        .collect()
}

fn parse_key(token: &str, line: usize, col: usize) -> Result<String, Error> {
    if token == "<<" {
        return Err(Error::at("merge keys are unsupported", line, col));
    }
    if token.starts_with('\'') || token.starts_with('"') {
        return quoted_scalar(token, line, col);
    }
    if token.is_empty() {
        return Err(Error::at("mapping keys must be strings", line, col));
    }
    if token.contains('#') {
        return Err(Error::at(
            "`#` is not permitted within unquoted keys",
            line,
            col,
        ));
    }
    if token.contains(':') {
        return Err(Error::at(
            "`:` is not permitted within unquoted keys",
            line,
            col,
        ));
    }
    if !valid_key(token) {
        return Err(Error::at("unsupported unquoted key syntax", line, col));
    }
    match plain_scalar(token, Mode::Standard, false, line, col)? {
        Value::String(_) if token != "~" => Ok(token.into()),
        _ => Err(Error::at("mapping keys must be strings", line, col)),
    }
}

pub(crate) fn valid_key(s: &str) -> bool {
    !s.is_empty()
        && s.chars()
            .all(|c| c.is_alphanumeric() || "_-./$()~".contains(c))
}

fn quoted_scalar(token: &str, line: usize, col: usize) -> Result<String, Error> {
    let err = |message: &str| Error::at(message, line, col);
    let chars: Vec<char> = token.chars().collect();
    let quote = chars[0];
    if chars.len() < 2 || chars[chars.len() - 1] != quote {
        return Err(err("quoted scalar is not terminated"));
    }
    let inner = &chars[1..chars.len() - 1];
    let mut out = String::new();
    let mut i = 0;
    while i < inner.len() {
        let c = inner[i];
        i += 1;
        if quote == '\'' {
            if c == '\'' {
                if inner.get(i) != Some(&'\'') {
                    return Err(err("apostrophes within single quotes must be doubled"));
                }
                i += 1;
            }
            out.push(c);
            continue;
        }
        match c {
            '"' => return Err(err("unescaped quote within double quotes")),
            '\\' => {
                let escape = *inner
                    .get(i)
                    .ok_or_else(|| err("quoted scalar is not terminated"))?;
                i += 1;
                let decoded = match escape {
                    '0' => '\0',
                    'a' => '\u{7}',
                    'b' => '\u{8}',
                    't' | '\t' => '\t',
                    'n' => '\n',
                    'v' => '\u{b}',
                    'f' => '\u{c}',
                    'r' => '\r',
                    'e' => '\u{1b}',
                    ' ' => ' ',
                    '"' => '"',
                    '/' => '/',
                    '\\' => '\\',
                    'N' => '\u{85}',
                    '_' => '\u{a0}',
                    'L' => '\u{2028}',
                    'P' => '\u{2029}',
                    'x' | 'u' | 'U' => {
                        let width = match escape {
                            'x' => 2,
                            'u' => 4,
                            _ => 8,
                        };
                        let digits: String = inner.iter().skip(i).take(width).collect();
                        if digits.len() != width || !digits.chars().all(|d| d.is_ascii_hexdigit()) {
                            return Err(err("invalid Unicode escape"));
                        }
                        i += width;
                        u32::from_str_radix(&digits, 16)
                            .ok()
                            .and_then(char::from_u32)
                            .ok_or_else(|| err("invalid Unicode code point"))?
                    }
                    _ => return Err(err("unknown escape sequence")),
                };
                out.push(decoded);
            }
            c => out.push(c),
        }
    }
    Ok(out)
}

const SPECIAL: [&str; 6] = ["true", "false", "null", ".inf", "-.inf", ".nan"];

/// Resolves an unquoted scalar following the Myml scalar resolution order.
pub(crate) fn plain_scalar(
    token: &str,
    mode: Mode,
    in_flow: bool,
    line: usize,
    col: usize,
) -> Result<Value, Error> {
    let err = |message: &str| Err(Error::at(message, line, col));
    let range = || Error::at("numeric range exceeded", line, col);
    match token {
        "" => return err("expected a value"),
        "null" => return Ok(Value::Null),
        "true" => return Ok(Value::Bool(true)),
        "false" => return Ok(Value::Bool(false)),
        ".inf" => return Ok(Value::F64(f64::INFINITY)),
        "-.inf" => return Ok(Value::F64(f64::NEG_INFINITY)),
        ".nan" => return Ok(Value::F64(f64::NAN)),
        _ => {}
    }
    if SPECIAL.contains(&token.to_lowercase().as_str()) {
        return err("special scalars must use lowercase spellings");
    }
    if token.contains('_') && is_numeric_with_underscores(token) {
        return err("numeric separators are unsupported");
    }
    if token == "-0" {
        return err("`-0` is not a supported numeric form");
    }
    if opt_neg(token).strip_prefix('.').is_some_and(digits) {
        return err("leading-dot decimals are unsupported");
    }
    if whole_frac(opt_neg(token)).is_some_and(|(w, _)| w.len() > 1 && w.starts_with('0')) {
        return err("plain fractional decimals may use exactly one `0.` prefix");
    }
    if let Some(hex) = token.strip_prefix("0x").filter(|h| is_hex_digits(h)) {
        return u64::from_str_radix(hex, 16)
            .map(Value::U64)
            .map_err(|_| range());
    }
    if is_int(token) {
        return if token.starts_with('-') {
            token.parse().map(Value::I64).map_err(|_| range())
        } else {
            token.parse().map(Value::U64).map_err(|_| range())
        };
    }
    if is_decimal(token) || is_normalized_exponent(token) {
        let n: f64 = token.parse().map_err(|_| range())?;
        return if n.is_finite() {
            Ok(Value::F64(n))
        } else {
            Err(range())
        };
    }
    if is_exponent(token) {
        return err("scientific notation must use a normalized coefficient with 1 <= m < 10");
    }
    if is_core_number(token) {
        // YAML 1.2 reads these as numbers, so they cannot be strings either.
        return if token.starts_with('+') {
            err("numbers may not use a `+` prefix")
        } else if token.starts_with("0o") {
            err("octal notation is unsupported")
        } else if digits(opt_neg(token)) {
            err("integers may not have leading zeros")
        } else {
            err("unsupported numeric form")
        };
    }
    if mode == Mode::Strict {
        return err("quoted string scalars are required");
    }
    let mut cs = token.chars();
    let first = cs.next().unwrap();
    if "!\"'`*%&>|,[]{}#@".contains(first)
        || "-?".contains(first) && matches!(cs.next(), None | Some(' '))
    {
        return err("invalid unquoted string scalar");
    }
    if token.ends_with(':') || token.contains(": ") {
        return err("`:` is not permitted at the end of or before a space in unquoted strings");
    }
    if in_flow && token.contains([',', '[', ']', '{', '}']) {
        return err(
            "unquoted strings in flow containers may not contain `,`, `[`, `]`, `{`, or `}`",
        );
    }
    Ok(Value::String(token.into()))
}

fn opt_neg(s: &str) -> &str {
    s.strip_prefix('-').unwrap_or(s)
}
fn digits(s: &str) -> bool {
    !s.is_empty() && s.bytes().all(|b| b.is_ascii_digit())
}
fn is_hex_digits(s: &str) -> bool {
    !s.is_empty() && s.bytes().all(|b| b.is_ascii_hexdigit())
}
fn whole_frac(s: &str) -> Option<(&str, &str)> {
    s.split_once('.').filter(|(w, f)| digits(w) && digits(f))
}
fn is_int(s: &str) -> bool {
    let body = opt_neg(s);
    s == "0" || digits(body) && !body.starts_with('0')
}
fn is_decimal(s: &str) -> bool {
    whole_frac(opt_neg(s)).is_some_and(|(w, _)| w == "0" || !w.starts_with('0'))
}
/// Splits `-?<coefficient>e-?<digits>` into its coefficient.
fn exponent_coefficient(s: &str) -> Option<&str> {
    let (coeff, exp) = opt_neg(s).split_once('e')?;
    digits(opt_neg(exp)).then_some(coeff)
}
fn is_exponent(s: &str) -> bool {
    exponent_coefficient(s).is_some_and(|c| {
        digits(c) || whole_frac(c).is_some() || c.strip_prefix('.').is_some_and(digits)
    })
}
fn is_normalized_exponent(s: &str) -> bool {
    exponent_coefficient(s).is_some_and(|c| {
        let (whole, frac) = c.split_once('.').unwrap_or((c, "0"));
        whole.len() == 1 && whole != "0" && digits(whole) && digits(frac)
    })
}
/// Whether the YAML 1.2 core schema resolves plain scalar `s` to an integer or float.
fn is_core_number(s: &str) -> bool {
    let unsigned = s.strip_prefix(['-', '+']).unwrap_or(s);
    if digits(unsigned) || matches!(unsigned, ".inf" | ".Inf" | ".INF") {
        return true;
    }
    if let Some(octal) = s.strip_prefix("0o") {
        return !octal.is_empty() && octal.bytes().all(|b| (b'0'..=b'7').contains(&b));
    }
    let (mantissa, exponent) = match unsigned.split_once(['e', 'E']) {
        Some((m, e)) => (m, Some(e)),
        None => (unsigned, None),
    };
    let mantissa_ok = match mantissa.split_once('.') {
        Some(("", frac)) => digits(frac),
        Some((whole, frac)) => digits(whole) && frac.bytes().all(|b| b.is_ascii_digit()),
        None => digits(mantissa),
    };
    mantissa_ok && exponent.is_none_or(|e| digits(e.strip_prefix(['-', '+']).unwrap_or(e)))
}
fn is_numeric_with_underscores(s: &str) -> bool {
    let body = opt_neg(s);
    let separated = |x: &str| !x.is_empty() && x.chars().all(|c| c.is_ascii_digit() || c == '_');
    if let Some(hex) = body.strip_prefix("0x") {
        return !hex.is_empty() && hex.chars().all(|c| c.is_ascii_hexdigit() || c == '_');
    }
    let (mantissa, exp) = match body.split_once('e') {
        Some((m, e)) => (m, Some(e)),
        None => (body, None),
    };
    let (whole, frac) = match mantissa.split_once('.') {
        Some((w, f)) => (w, Some(f)),
        None => (mantissa, None),
    };
    whole.starts_with(|c: char| c.is_ascii_digit())
        && separated(whole)
        && frac.is_none_or(separated)
        && exp.is_none_or(|e| separated(opt_neg(e)))
}
