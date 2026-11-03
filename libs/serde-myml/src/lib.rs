//! Serde support for the Myml subset of YAML.
//! Dynamic integers are limited to `i64` and `u64`; other numbers use `f64`.
use serde::de::DeserializeOwned;
use serde::{Deserialize, Deserializer, Serialize, Serializer};
use std::collections::BTreeMap;
use std::fmt;
use std::io::{Read, Write};

mod de;
mod emit;
mod parse;
mod ser;

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
    fn at(message: impl Into<String>, line: usize, column: usize) -> Self {
        Self {
            message: message.into(),
            line: Some(line),
            column: Some(column),
        }
    }
    /// The 1-based line of the error, when known.
    pub fn line(&self) -> Option<usize> {
        self.line
    }
    /// The 1-based column of the error, when known.
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
impl serde::de::Error for Error {
    fn custom<T: fmt::Display>(message: T) -> Self {
        Self::new(message.to_string())
    }
}
impl serde::ser::Error for Error {
    fn custom<T: fmt::Display>(message: T) -> Self {
        Self::new(message.to_string())
    }
}

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
            fn visit_some<D: Deserializer<'de>>(self, d: D) -> Result<Value, D::Error> {
                Value::deserialize(d)
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
    T::deserialize(parse::parse(input, mode)?)
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
    let v = value.serialize(ser::ValueSerializer)?;
    let mut out = String::new();
    emit::emit(&v, 0, mode, &mut out);
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
