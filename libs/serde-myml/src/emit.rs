//! Emitting canonical block-style Myml from a `Value`.
use crate::parse::{is_allowed_raw, plain_scalar, valid_key};
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
                if valid_key(k) && resolves_to_itself(k) {
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
        _ => {
            out.push_str(&render_scalar(v, mode));
            out.push('\n')
        }
    }
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
            emit(v, 0, mode, out)
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
                let s = v.to_string();
                if s.contains('.') || s.contains('e') {
                    s
                } else {
                    format!("{s}.0")
                }
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

/// Whether `s` written unquoted parses back as the string `s`. Strings that look numeric or begin
/// with `-` or `.` are quoted even when Myml would accept them unquoted.
fn resolves_to_itself(s: &str) -> bool {
    !s.starts_with(|c: char| c.is_ascii_digit() || "+-.".contains(c))
        && matches!(plain_scalar(s, Mode::Standard, false, 0, 0), Ok(Value::String(x)) if x == s)
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
        if !(c.is_alphanumeric() || c == ' ' || "_./()$+=;<\\^!\"'`*%&>|@,[]{}-?:#~".contains(c)) {
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
            c if !is_allowed_raw(c) => write!(out, "\\u{:04x}", c as u32).unwrap(),
            c => out.push(c),
        }
    }
    out.push('"');
    out
}
