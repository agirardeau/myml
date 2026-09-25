//! Serde support for the Myml subset of YAML.
//! Dynamic integers are limited to `i64` and `u64`; other numbers use `f64`.
use serde::de::DeserializeOwned;
use serde::{Deserialize, Deserializer, Serialize, Serializer};
use std::collections::BTreeMap;
use std::fmt;
use std::io::{Read, Write};
use yaml_rust2::parser::{Event, Parser};
use yaml_rust2::scanner::{Marker, TScalarStyle};

#[derive(Clone, Copy, Debug, Default, Eq, PartialEq)]
pub enum Mode {
    #[default]
    Standard,
    Strict,
}

#[derive(Clone, Debug, PartialEq)]
pub enum Value {
    Null,
    Bool(bool),
    I64(i64),
    U64(u64),
    F64(f64),
    String(String),
    Sequence(Vec<Value>),
    Mapping(BTreeMap<String, Value>),
}

#[derive(Debug)]
pub struct Error {
    message: String,
    line: Option<usize>,
    column: Option<usize>,
}
impl Error {
    fn new(message: impl Into<String>) -> Self {
        Self {
            message: message.into(),
            line: None,
            column: None,
        }
    }
    fn at(message: impl Into<String>, mark: Marker) -> Self {
        Self {
            message: message.into(),
            line: Some(mark.line()),
            column: Some(mark.col()),
        }
    }
    pub fn line(&self) -> Option<usize> {
        self.line
    }
    pub fn column(&self) -> Option<usize> {
        self.column
    }
}
impl fmt::Display for Error {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match (self.line, self.column) {
            (Some(l), Some(c)) => write!(f, "{} at line {l}, column {c}", self.message),
            _ => f.write_str(&self.message),
        }
    }
}
impl std::error::Error for Error {}

impl Serialize for Value {
    fn serialize<S: Serializer>(&self, s: S) -> Result<S::Ok, S::Error> {
        match self {
            Self::Null => s.serialize_unit(),
            Self::Bool(v) => s.serialize_bool(*v),
            Self::I64(v) => s.serialize_i64(*v),
            Self::U64(v) => s.serialize_u64(*v),
            Self::F64(v) => s.serialize_f64(*v),
            Self::String(v) => s.serialize_str(v),
            Self::Sequence(v) => v.serialize(s),
            Self::Mapping(v) => v.serialize(s),
        }
    }
}
impl<'de> Deserialize<'de> for Value {
    fn deserialize<D: Deserializer<'de>>(d: D) -> Result<Self, D::Error> {
        struct Visitor;
        impl<'de> serde::de::Visitor<'de> for Visitor {
            type Value = Value;
            fn expecting(&self, f: &mut fmt::Formatter) -> fmt::Result {
                f.write_str("a Myml value")
            }
            fn visit_unit<E: serde::de::Error>(self) -> Result<Value, E> {
                Ok(Value::Null)
            }
            fn visit_none<E: serde::de::Error>(self) -> Result<Value, E> {
                Ok(Value::Null)
            }
            fn visit_bool<E: serde::de::Error>(self, v: bool) -> Result<Value, E> {
                Ok(Value::Bool(v))
            }
            fn visit_i64<E: serde::de::Error>(self, v: i64) -> Result<Value, E> {
                Ok(Value::I64(v))
            }
            fn visit_u64<E: serde::de::Error>(self, v: u64) -> Result<Value, E> {
                Ok(Value::U64(v))
            }
            fn visit_f64<E: serde::de::Error>(self, v: f64) -> Result<Value, E> {
                Ok(Value::F64(v))
            }
            fn visit_str<E: serde::de::Error>(self, v: &str) -> Result<Value, E> {
                Ok(Value::String(v.into()))
            }
            fn visit_string<E: serde::de::Error>(self, v: String) -> Result<Value, E> {
                Ok(Value::String(v))
            }
            fn visit_seq<A: serde::de::SeqAccess<'de>>(self, mut a: A) -> Result<Value, A::Error> {
                let mut v = Vec::new();
                while let Some(x) = a.next_element()? {
                    v.push(x)
                }
                Ok(Value::Sequence(v))
            }
            fn visit_map<A: serde::de::MapAccess<'de>>(self, mut a: A) -> Result<Value, A::Error> {
                let mut v = BTreeMap::new();
                while let Some((k, x)) = a.next_entry()? {
                    v.insert(k, x);
                }
                Ok(Value::Mapping(v))
            }
        }
        d.deserialize_any(Visitor)
    }
}

pub fn from_str<T: DeserializeOwned>(input: &str) -> Result<T, Error> {
    from_str_with_mode(input, Mode::Standard)
}
pub fn from_str_with_mode<T: DeserializeOwned>(input: &str, mode: Mode) -> Result<T, Error> {
    let value = parse(input, mode)?;
    T::deserialize(to_serde_value(value)).map_err(|e| Error::new(e.to_string()))
}
pub fn from_reader<R: Read, T: DeserializeOwned>(reader: R) -> Result<T, Error> {
    from_reader_with_mode(reader, Mode::Standard)
}
pub fn from_reader_with_mode<R: Read, T: DeserializeOwned>(
    mut reader: R,
    mode: Mode,
) -> Result<T, Error> {
    let mut s = String::new();
    reader
        .read_to_string(&mut s)
        .map_err(|e| Error::new(e.to_string()))?;
    from_str_with_mode(&s, mode)
}
pub fn to_string<T: Serialize>(value: &T) -> Result<String, Error> {
    to_string_with_mode(value, Mode::Standard)
}
pub fn to_string_with_mode<T: Serialize>(value: &T, mode: Mode) -> Result<String, Error> {
    let v = serde_value::to_value(value).map_err(|e| Error::new(e.to_string()))?;
    let v = from_serde_value(v)?;
    let mut out = String::new();
    emit(&v, 0, mode, &mut out);
    Ok(out)
}
pub fn to_writer<W: Write, T: Serialize>(writer: W, value: &T) -> Result<(), Error> {
    to_writer_with_mode(writer, value, Mode::Standard)
}
pub fn to_writer_with_mode<W: Write, T: Serialize>(
    mut writer: W,
    value: &T,
    mode: Mode,
) -> Result<(), Error> {
    writer
        .write_all(to_string_with_mode(value, mode)?.as_bytes())
        .map_err(|e| Error::new(e.to_string()))
}

fn to_serde_value(v: Value) -> serde_value::Value {
    use serde_value::Value as S;
    match v {
        Value::Null => S::Unit,
        Value::Bool(x) => S::Bool(x),
        Value::I64(x) => S::I64(x),
        Value::U64(x) => S::U64(x),
        Value::F64(x) => S::F64(x),
        Value::String(x) => S::String(x),
        Value::Sequence(x) => S::Seq(x.into_iter().map(to_serde_value).collect()),
        Value::Mapping(x) => S::Map(
            x.into_iter()
                .map(|(k, v)| (S::String(k), to_serde_value(v)))
                .collect(),
        ),
    }
}
fn from_serde_value(v: serde_value::Value) -> Result<Value, Error> {
    use serde_value::Value as S;
    Ok(match v {
        S::Unit => Value::Null,
        S::Option(None) => Value::Null,
        S::Option(Some(v)) | S::Newtype(v) => return from_serde_value(*v),
        S::Bool(v) => Value::Bool(v),
        S::I8(v) => Value::I64(v.into()),
        S::I16(v) => Value::I64(v.into()),
        S::I32(v) => Value::I64(v.into()),
        S::I64(v) => Value::I64(v),
        S::U8(v) => Value::U64(v.into()),
        S::U16(v) => Value::U64(v.into()),
        S::U32(v) => Value::U64(v.into()),
        S::U64(v) => Value::U64(v),
        S::F32(v) => Value::F64(v.into()),
        S::F64(v) => Value::F64(v),
        S::Char(v) => Value::String(v.to_string()),
        S::String(v) => Value::String(v),
        S::Bytes(v) => Value::Sequence(v.into_iter().map(|x| Value::U64(x.into())).collect()),
        S::Seq(v) => Value::Sequence(
            v.into_iter()
                .map(from_serde_value)
                .collect::<Result<_, _>>()?,
        ),
        S::Map(v) => {
            let mut m = BTreeMap::new();
            for (k, v) in v {
                let k = match k {
                    S::String(k) => k,
                    S::Char(k) => k.to_string(),
                    _ => return Err(Error::new("mapping keys must be strings")),
                };
                m.insert(k, from_serde_value(v)?);
            }
            Value::Mapping(m)
        }
    })
}

fn parse(input: &str, mode: Mode) -> Result<Value, Error> {
    prevalidate(input)?;
    let prepared = prepare(input);
    let mut parser = Parser::new_from_str(&prepared);
    let mut events = Vec::new();
    loop {
        let (e, m) = parser
            .next_token()
            .map_err(|e| Error::at(e.info(), *e.marker()))?;
        let end = e == Event::StreamEnd;
        events.push((e, m));
        if end {
            break;
        }
    }
    let mut pos = 0;
    while matches!(
        events.get(pos),
        Some((Event::StreamStart | Event::DocumentStart, _))
    ) {
        pos += 1;
    }
    let value = if matches!(
        events.get(pos),
        Some((Event::DocumentEnd | Event::StreamEnd, _))
    ) {
        Value::Null
    } else {
        parse_node(&events, &mut pos, mode, false, &prepared)?
    };
    while matches!(
        events.get(pos),
        Some((Event::DocumentEnd | Event::StreamEnd, _))
    ) {
        pos += 1;
    }
    if pos != events.len() {
        return Err(Error::new("multiple documents are unsupported"));
    }
    Ok(value)
}
fn parse_node(
    events: &[(Event, Marker)],
    pos: &mut usize,
    mode: Mode,
    in_flow: bool,
    input: &str,
) -> Result<Value, Error> {
    let (event, mark) = events
        .get(*pos)
        .ok_or_else(|| Error::new("unexpected end of document"))?
        .clone();
    *pos += 1;
    match event {
        Event::Scalar(s, style, anchor, tag) => {
            if anchor != 0 || tag.is_some() {
                return Err(Error::at("anchors and tags are unsupported", mark));
            }
            scalar(&s, style, mark, mode, in_flow)
        }
        Event::Alias(_) => Err(Error::at("aliases are unsupported", mark)),
        Event::SequenceStart(anchor, tag) => {
            let flow = input.as_bytes().get(mark.index()) == Some(&b'[');
            if in_flow {
                return Err(Error::at("nested flow containers are unsupported", mark));
            }
            if anchor != 0 || tag.is_some() {
                return Err(Error::at("anchors and tags are unsupported", mark));
            }
            let mut v = Vec::new();
            while !matches!(events.get(*pos), Some((Event::SequenceEnd, _))) {
                if *pos >= events.len() {
                    return Err(Error::at("unterminated sequence", mark));
                }
                v.push(parse_node(events, pos, mode, in_flow || flow, input)?);
            }
            *pos += 1;
            Ok(Value::Sequence(v))
        }
        Event::MappingStart(anchor, tag) => {
            let flow = input.as_bytes().get(mark.index()) == Some(&b'{');
            if in_flow {
                return Err(Error::at("nested flow containers are unsupported", mark));
            }
            if anchor != 0 || tag.is_some() {
                return Err(Error::at("anchors and tags are unsupported", mark));
            }
            let mut v = BTreeMap::new();
            while !matches!(events.get(*pos), Some((Event::MappingEnd, _))) {
                let keymark = events.get(*pos).map(|x| x.1).unwrap_or(mark);
                let key = match parse_node(events, pos, Mode::Standard, in_flow || flow, input)? {
                    Value::String(k) => k,
                    _ => return Err(Error::at("mapping keys must be strings", keymark)),
                };
                if key == "<<" {
                    return Err(Error::at("merge keys are unsupported", keymark));
                }
                let val = parse_node(events, pos, mode, in_flow || flow, input)?;
                if v.insert(key.clone(), val).is_some() {
                    return Err(Error::at(format!("duplicate mapping key {key:?}"), keymark));
                }
            }
            *pos += 1;
            Ok(Value::Mapping(v))
        }
        _ => Err(Error::at("unexpected YAML syntax", mark)),
    }
}
fn scalar(
    s: &str,
    style: TScalarStyle,
    mark: Marker,
    mode: Mode,
    _flow: bool,
) -> Result<Value, Error> {
    if style != TScalarStyle::Plain {
        if matches!(style, TScalarStyle::Literal | TScalarStyle::Folded) && s.is_empty() {
            return Err(Error::at("empty block scalar is unsupported", mark));
        }
        return Ok(Value::String(s.into()));
    }
    if s.is_empty() {
        return Err(Error::at("mapping entries require a value", mark));
    }
    if s.contains('\n') {
        return Err(Error::at("multiline plain scalars are unsupported", mark));
    }
    if s == "null" {
        return Ok(Value::Null);
    }
    if s == "true" {
        return Ok(Value::Bool(true));
    }
    if s == "false" {
        return Ok(Value::Bool(false));
    }
    if s == ".inf" {
        return Ok(Value::F64(f64::INFINITY));
    }
    if s == "-.inf" {
        return Ok(Value::F64(f64::NEG_INFINITY));
    }
    if s == ".nan" {
        return Ok(Value::F64(f64::NAN));
    }
    if let Some(hex) = s.strip_prefix("0x") {
        if !hex.is_empty() && hex.chars().all(|c| c.is_ascii_hexdigit()) {
            return u64::from_str_radix(hex, 16)
                .map(Value::U64)
                .map_err(|_| Error::at("numeric range exceeded", mark));
        }
    }
    let body = s.strip_prefix('-').unwrap_or(s);
    let neg = body.len() != s.len();
    if !body.is_empty() && body.bytes().all(|b| b.is_ascii_digit()) {
        if neg && body == "0" {
            return Err(Error::at("invalid numeric form", mark));
        }
        if body.len() > 1 && body.starts_with('0') {
            if mode == Mode::Strict {
                return Err(Error::at("quoted string scalars are required", mark));
            }
            return Ok(Value::String(s.into()));
        }
        if neg {
            return s
                .parse::<i64>()
                .map(Value::I64)
                .map_err(|_| Error::at("numeric range exceeded", mark));
        }
        return s
            .parse::<u64>()
            .map(Value::U64)
            .map_err(|_| Error::at("numeric range exceeded", mark));
    }
    if body.contains('.') || body.contains('e') {
        let mut split = body.split('e');
        let coeff = split.next().unwrap();
        let exponent = split.next();
        if split.next().is_none() {
            let decimal = if let Some((whole, frac)) = coeff.split_once('.') {
                !whole.is_empty()
                    && frac.len() > 0
                    && whole.bytes().all(|b| b.is_ascii_digit())
                    && frac.bytes().all(|b| b.is_ascii_digit())
                    && (whole == "0" || !whole.starts_with('0'))
            } else {
                !coeff.is_empty()
                    && coeff.bytes().all(|b| b.is_ascii_digit())
                    && !coeff.starts_with('0')
            };
            let exp_ok = exponent
                .map(|e| {
                    let d = e.strip_prefix('-').unwrap_or(e);
                    !d.is_empty() && d.bytes().all(|b| b.is_ascii_digit())
                })
                .unwrap_or(true);
            let normalized = exponent.is_none()
                || coeff.starts_with(|c: char| ('1'..='9').contains(&c))
                    && coeff.chars().nth(1).map(|c| c == '.').unwrap_or(true);
            if body.starts_with("00.") {
                return Err(Error::at("invalid numeric form", mark));
            }
            if decimal && exp_ok && !normalized {
                return Err(Error::at("non-normalized numeric form", mark));
            }
            if decimal && exp_ok && normalized {
                let n = s
                    .parse::<f64>()
                    .map_err(|_| Error::at("invalid numeric form", mark))?;
                if !n.is_finite() {
                    return Err(Error::at("numeric range exceeded", mark));
                }
                return Ok(Value::F64(n));
            }
        }
    }
    if matches!(
        s,
        "~" | "True" | "FALSE" | "False" | "Null" | ".Inf" | "-.Inf" | ".NaN"
    ) || s.starts_with('+') && s.chars().nth(1).is_some_and(|c| c.is_ascii_digit())
        || s.starts_with("0o")
        || s.starts_with("0b")
        || s.starts_with("0X")
        || s.starts_with("-0x")
        || s.starts_with('.') && s.chars().nth(1).is_some_and(|c| c.is_ascii_digit())
        || s.contains('_')
            && s.chars().any(|c| c.is_ascii_digit())
            && s.chars().all(|c| c.is_ascii_digit() || c == '_')
    {
        return Err(Error::at("invalid or unsupported scalar form", mark));
    }
    if mode == Mode::Strict {
        return Err(Error::at("quoted string scalars are required", mark));
    }
    if !valid_plain(s, false) {
        return Err(Error::at("invalid unquoted string scalar", mark));
    }
    Ok(Value::String(s.into()))
}
fn valid_key(s: &str) -> bool {
    !s.is_empty()
        && s.chars()
            .all(|c| c.is_alphanumeric() || "_-./$()~".contains(c))
}
fn valid_plain(s: &str, flow: bool) -> bool {
    if s.is_empty() || s == "~" || s == "|" || s == ">" || s.ends_with(':') {
        return false;
    }
    let chars: Vec<char> = s.chars().collect();
    for (i, c) in chars.iter().enumerate() {
        let prev = i.checked_sub(1).and_then(|j| chars.get(j)).copied();
        let next = chars.get(i + 1).copied();
        if i == 0 && "!\"'`*%&>|,[]{}#@".contains(*c) {
            return false;
        }
        if i == 0 && (*c == '-' || *c == '?') && next == Some(' ') {
            return false;
        }
        if *c == ':' && next == Some(' ')
            || *c == '#' && (i == 0 || prev == Some(' '))
            || flow && ",[]{}".contains(*c)
            || *c == '\t'
            || *c == '\n'
            || *c == '\r'
        {
            return false;
        }
        if !(c.is_alphanumeric()
            || c.is_whitespace()
            || "_./()$+=;<\\!\"'`*%&>|,[]{}-?:#~".contains(*c))
        {
            return false;
        }
    }
    true
}
fn quote(s: &str) -> String {
    serde_json::to_string(s).unwrap()
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
            if mode == Mode::Standard && valid_plain(v, false) && plain_is_string(v) {
                v.clone()
            } else {
                quote(v)
            }
        }
        _ => unreachable!(),
    }
}
fn emit(v: &Value, indent: usize, mode: Mode, out: &mut String) {
    match v {
        Value::Mapping(m) => {
            if m.is_empty() {
                out.push_str("{}\n");
                return;
            }
            for (k, v) in m {
                out.push_str(&" ".repeat(indent));
                out.push_str(if valid_key(k) { k } else { "" });
                if !valid_key(k) {
                    out.push_str(&quote(k))
                }
                out.push(':');
                match v {
                    Value::Mapping(x) if !x.is_empty() => {
                        out.push('\n');
                        emit(v, indent + 2, mode, out)
                    }
                    Value::Sequence(x) if !x.is_empty() => {
                        out.push('\n');
                        emit(v, indent + 2, mode, out)
                    }
                    Value::Mapping(_) | Value::Sequence(_) => {
                        out.push(' ');
                        emit(v, 0, mode, out)
                    }
                    _ => {
                        out.push(' ');
                        out.push_str(&render_scalar(v, mode));
                        out.push('\n')
                    }
                }
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
                        let mut part = String::new();
                        emit(v, indent + 2, mode, &mut part);
                        let prefix = " ".repeat(indent + 2);
                        if let Some(first) = part.strip_prefix(&prefix) {
                            out.push(' ');
                            out.push_str(first)
                        } else {
                            out.push('\n');
                            out.push_str(&part)
                        }
                    }
                    Value::Sequence(x) if !x.is_empty() => {
                        out.push('\n');
                        emit(v, indent + 2, mode, out)
                    }
                    Value::Mapping(_) | Value::Sequence(_) => {
                        out.push(' ');
                        emit(v, 0, mode, out)
                    }
                    _ => {
                        out.push(' ');
                        out.push_str(&render_scalar(v, mode));
                        out.push('\n')
                    }
                }
            }
        }
        _ => {
            out.push_str(&render_scalar(v, mode));
            out.push('\n')
        }
    }
}

fn plain_is_string(s: &str) -> bool {
    !matches!(
        s,
        "null" | "true" | "false" | ".inf" | "-.inf" | ".nan" | "~"
    ) && !s.starts_with('+')
        && !s.chars().next().is_some_and(|c| c.is_ascii_digit())
        && !s.starts_with('-')
        && !s.starts_with('.')
}

fn prevalidate(input: &str) -> Result<(), Error> {
    let mut prior_plain = false;
    for (i, line) in input.lines().enumerate() {
        let trimmed = line.trim_start();
        let col = line.len() - trimmed.len() + 1;
        if trimmed.is_empty() || trimmed.starts_with('#') {
            continue;
        }
        if line.starts_with(' ')
            && prior_plain
            && !trimmed.starts_with('-')
            && !trimmed.contains(':')
        {
            return Err(Error::new(format!(
                "multiline plain scalar at line {}, column {}",
                i + 1,
                col
            )));
        }
        if let Some((_, rhs)) = trimmed.split_once(": ") {
            let rhs = rhs.trim_end();
            if (rhs == "|" || rhs == ">")
                && input
                    .lines()
                    .nth(i + 1)
                    .is_none_or(|next| next.trim().is_empty())
            {
                return Err(Error::new(format!(
                    "empty block scalar at line {}, column {}",
                    i + 1,
                    col + trimmed.find(rhs).unwrap_or(0)
                )));
            }
            if rhs.starts_with('[') && rhs.contains('{')
                || rhs.starts_with('{') && rhs.contains('[')
            {
                return Err(Error::new(format!(
                    "nested flow container at line {}, column {}",
                    i + 1,
                    col
                )));
            }
            prior_plain = !rhs.is_empty()
                && !rhs.starts_with('[')
                && !rhs.starts_with('{')
                && !rhs.starts_with('"')
                && !rhs.starts_with('\'')
                && rhs != "|"
                && rhs != ">";
        } else {
            prior_plain = false
        }
    }
    Ok(())
}
fn prepare(input: &str) -> String {
    let mut out = String::new();
    for line in input.lines() {
        if let Some((prefix, rhs)) = line.split_once(": ") {
            let value = rhs.trim_end();
            if valid_plain(value, false)
                && (plain_is_string(value) || value == "-" || value.starts_with('?'))
                && !value.contains(" #")
                && (value.chars().any(|c| "[]{}".contains(c))
                    || value.starts_with('?')
                    || value == "-")
            {
                out.push_str(prefix);
                out.push_str(": ");
                out.push_str(&quote(value));
                out.push('\n');
                continue;
            }
        }
        out.push_str(line);
        out.push('\n')
    }
    out
}
