//! Emitting canonical block-style Myml from a `Value`.
use crate::parse::{is_allowed_raw, parse_key, plain_scalar};
use crate::{Mode, Value};
use std::fmt::Write;

pub(crate) fn emit(v: &Value, indent: usize, mode: Mode, out: &mut String) {
    match v {
        Value::Mapping(m) => {
            if m.is_empty() {
                out.push_str("{}\n");
                return;
            }
            for (k, v) in m {
                out.push_str(&" ".repeat(indent));
                if parse_key(k, 0, 0).is_ok_and(|parsed| parsed == *k) {
                    out.push_str(k);
                } else {
                    out.push_str(&quote(k));
                }
                out.push(':');
                emit_nested(v, indent, mode, out);
            }
        }
        Value::Sequence(seq) => {
            if seq.is_empty() {
                out.push_str("[]\n");
                return;
            }
            for v in seq {
                out.push_str(&" ".repeat(indent));
                out.push('-');
                match v {
                    Value::Mapping(m) if !m.is_empty() => {
                        // Compact form: the first entry shares the line with the marker.
                        let mut part = String::new();
                        emit(v, indent + 2, mode, &mut part);
                        out.push(' ');
                        out.push_str(&part[indent + 2..]);
                    }
                    _ => emit_nested(v, indent, mode, out),
                }
            }
        }
        _ => emit_scalar(v, indent + 2, mode, out),
    }
}

/// Emits a scalar, writing a block scalar's content lines at `content_indent`.
fn emit_scalar(v: &Value, content_indent: usize, mode: Mode, out: &mut String) {
    if let Value::String(s) = v {
        if let Some(lines) = literal_block_lines(s) {
            out.push_str("|\n");
            for line in lines {
                if !line.is_empty() {
                    out.push_str(&" ".repeat(content_indent));
                    out.push_str(line);
                }
                out.push('\n');
            }
            return;
        }
    }
    out.push_str(&render_scalar(v, mode));
    out.push('\n')
}

/// The content lines of `s` as a `|` block scalar, or `None` when that style cannot represent it.
/// Block scalars use clip chomping and take their indentation from the first non-blank line, so
/// the value must end with exactly one line break, its first non-blank line may not start with
/// whitespace, and the blank lines before that one must be empty.
fn literal_block_lines(s: &str) -> Option<Vec<&str>> {
    let body = s.strip_suffix('\n')?;
    if body.ends_with('\n')
        || s.chars()
            .any(|c| c != '\n' && (c == '\t' || !is_allowed_raw(c)))
    {
        return None;
    }
    let lines: Vec<&str> = body.split('\n').collect();
    let first = lines.iter().position(|line| !line.trim().is_empty())?;
    (!lines[first].starts_with(' ') && lines[..first].iter().all(|line| line.is_empty()))
        .then_some(lines)
}

/// Emits a mapping value or sequence item after its `key:` or `-` marker.
fn emit_nested(v: &Value, indent: usize, mode: Mode, out: &mut String) {
    match v {
        Value::Mapping(x) if !x.is_empty() => {
            out.push('\n');
            emit(v, indent + 2, mode, out)
        }
        Value::Sequence(x) if !x.is_empty() => {
            out.push('\n');
            emit(v, indent + 2, mode, out)
        }
        _ => {
            out.push(' ');
            emit(v, indent, mode, out)
        }
    }
}

fn render_scalar(v: &Value, mode: Mode) -> String {
    match v {
        Value::Null => "null".into(),
        Value::Bool(v) => v.to_string(),
        Value::I64(v) => v.to_string(),
        Value::U64(v) => v.to_string(),
        Value::F64(v) => {
            if v.is_nan() {
                ".nan".into()
            } else if *v == f64::INFINITY {
                ".inf".into()
            } else if *v == f64::NEG_INFINITY {
                "-.inf".into()
            } else {
                render_float(*v)
            }
        }
        Value::String(v) => {
            if mode == Mode::Standard && valid_plain(v) && resolves_to_itself(v) {
                v.clone()
            } else {
                quote(v)
            }
        }
        Value::Sequence(_) | Value::Mapping(_) => unreachable!(),
    }
}

/// Fixed-point zeros beyond which a finite float is written in exponential notation instead.
const MAX_PADDING_ZEROS: usize = 3;

/// Renders a finite float with the fewest significant digits that read back as the same value.
/// It uses fixed-point notation unless that would need more than `MAX_PADDING_ZEROS` zeros
/// between the significant digits and the decimal point, in which case it uses normalized
/// exponential notation. Either way the text reads back as a float, never as an integer.
fn render_float(v: f64) -> String {
    let sci = format!("{:e}", v.abs());
    let (mantissa, exp) = sci.split_once('e').unwrap();
    let exp: i32 = exp.parse().unwrap();
    let digits = mantissa.replace('.', "");
    let sign = if v.is_sign_negative() { "-" } else { "" };
    if v == 0.0 {
        return format!("{sign}0.0");
    }
    let k = digits.len() as i32;
    let padding = if exp < 0 {
        -exp - 1
    } else {
        (exp - k + 1).max(0)
    };
    if padding as usize > MAX_PADDING_ZEROS {
        return format!("{sign}{mantissa}e{exp}");
    }
    if exp < 0 {
        format!("{sign}0.{}{digits}", "0".repeat(padding as usize))
    } else if exp + 1 >= k {
        format!("{sign}{digits}{}.0", "0".repeat(padding as usize))
    } else {
        let (whole, frac) = digits.split_at(exp as usize + 1);
        format!("{sign}{whole}.{frac}")
    }
}

/// Whether `s` written unquoted parses back as the string `s`.
fn resolves_to_itself(s: &str) -> bool {
    s != "~"
        && matches!(plain_scalar(s, Mode::Standard, false, 0, 0), Ok(Value::String(x)) if x == s)
}

/// Whether `c` is an emoji or a character that joins or styles emoji sequences.
fn is_emoji(c: char) -> bool {
    matches!(c,
        '\u{1f000}'..='\u{1faff}' | '\u{2600}'..='\u{27bf}' | '\u{2b00}'..='\u{2bff}'
        | '\u{200d}' | '\u{fe0f}' | '\u{20e3}' | '\u{e0020}'..='\u{e007f}')
}

/// Conservative character rules for emitting an unquoted string in block context.
fn valid_plain(s: &str) -> bool {
    if s.is_empty() || s.trim() != s || s == "~" || s.ends_with(':') {
        return false;
    }
    let chars: Vec<char> = s.chars().collect();
    for (i, &c) in chars.iter().enumerate() {
        let prev = i.checked_sub(1).map(|j| chars[j]);
        let next = chars.get(i + 1).copied();
        if i == 0
            && ("!\"'`*%&>|,[]{}#@".contains(c)
                || "-?".contains(c) && matches!(next, None | Some(' ')))
        {
            return false;
        }
        if c == ':' && next == Some(' ') || c == '#' && prev == Some(' ') {
            return false;
        }
        if !(c.is_alphanumeric()
            || is_emoji(c)
            || c == ' '
            || "_./()$+=;<\\^!\"'`*%&>|@,[]{}-?:#~".contains(c))
        {
            return false;
        }
    }
    true
}

fn quote(s: &str) -> String {
    let mut out = String::with_capacity(s.len() + 2);
    out.push('"');
    for c in s.chars() {
        match c {
            '"' => out.push_str("\\\""),
            '\\' => out.push_str("\\\\"),
            '\n' => out.push_str("\\n"),
            '\t' => out.push_str("\\t"),
            '\r' => out.push_str("\\r"),
            '\u{8}' => out.push_str("\\b"),
            '\u{c}' => out.push_str("\\f"),
            // A no-break space is indistinguishable from a space in most editors.
            c if !is_allowed_raw(c) || c == '\u{a0}' => write!(out, "\\u{:04x}", c as u32).unwrap(),
            c => out.push(c),
        }
    }
    out.push('"');
    out
}
