//! Serializing Rust values into a `Value`.
use crate::{Error, Value};
use serde::ser::{self, Serialize};
use std::collections::BTreeMap;

pub(crate) struct ValueSerializer;

fn range_error() -> Error {
    Error::new("numeric range exceeded")
}

impl ser::Serializer for ValueSerializer {
    type Ok = Value;
    type Error = Error;
    type SerializeSeq = Seq;
    type SerializeTuple = Seq;
    type SerializeTupleStruct = Seq;
    type SerializeTupleVariant = TupleVariant;
    type SerializeMap = Map;
    type SerializeStruct = Map;
    type SerializeStructVariant = StructVariant;

    fn serialize_bool(self, v: bool) -> Result<Value, Error> {
        Ok(Value::Bool(v))
    }
    fn serialize_i8(self, v: i8) -> Result<Value, Error> {
        Ok(Value::I64(v.into()))
    }
    fn serialize_i16(self, v: i16) -> Result<Value, Error> {
        Ok(Value::I64(v.into()))
    }
    fn serialize_i32(self, v: i32) -> Result<Value, Error> {
        Ok(Value::I64(v.into()))
    }
    fn serialize_i64(self, v: i64) -> Result<Value, Error> {
        Ok(Value::I64(v))
    }
    fn serialize_i128(self, v: i128) -> Result<Value, Error> {
        if let Ok(v) = u64::try_from(v) {
            return Ok(Value::U64(v));
        }
        i64::try_from(v).map(Value::I64).map_err(|_| range_error())
    }
    fn serialize_u8(self, v: u8) -> Result<Value, Error> {
        Ok(Value::U64(v.into()))
    }
    fn serialize_u16(self, v: u16) -> Result<Value, Error> {
        Ok(Value::U64(v.into()))
    }
    fn serialize_u32(self, v: u32) -> Result<Value, Error> {
        Ok(Value::U64(v.into()))
    }
    fn serialize_u64(self, v: u64) -> Result<Value, Error> {
        Ok(Value::U64(v))
    }
    fn serialize_u128(self, v: u128) -> Result<Value, Error> {
        u64::try_from(v).map(Value::U64).map_err(|_| range_error())
    }
    fn serialize_f32(self, v: f32) -> Result<Value, Error> {
        Ok(Value::F64(v.into()))
    }
    fn serialize_f64(self, v: f64) -> Result<Value, Error> {
        Ok(Value::F64(v))
    }
    fn serialize_char(self, v: char) -> Result<Value, Error> {
        Ok(Value::String(v.into()))
    }
    fn serialize_str(self, v: &str) -> Result<Value, Error> {
        Ok(Value::String(v.into()))
    }
    fn serialize_bytes(self, v: &[u8]) -> Result<Value, Error> {
        Ok(Value::Sequence(
            v.iter().map(|&b| Value::U64(b.into())).collect(),
        ))
    }
    fn serialize_none(self) -> Result<Value, Error> {
        Ok(Value::Null)
    }
    fn serialize_some<T: ?Sized + Serialize>(self, value: &T) -> Result<Value, Error> {
        value.serialize(self)
    }
    fn serialize_unit(self) -> Result<Value, Error> {
        Ok(Value::Null)
    }
    fn serialize_unit_struct(self, _name: &'static str) -> Result<Value, Error> {
        Ok(Value::Null)
    }
    fn serialize_unit_variant(
        self,
        _name: &'static str,
        _index: u32,
        variant: &'static str,
    ) -> Result<Value, Error> {
        Ok(Value::String(variant.into()))
    }
    fn serialize_newtype_struct<T: ?Sized + Serialize>(
        self,
        _name: &'static str,
        value: &T,
    ) -> Result<Value, Error> {
        value.serialize(self)
    }
    fn serialize_newtype_variant<T: ?Sized + Serialize>(
        self,
        _name: &'static str,
        _index: u32,
        variant: &'static str,
        value: &T,
    ) -> Result<Value, Error> {
        Ok(tagged(variant, value.serialize(self)?))
    }
    fn serialize_seq(self, len: Option<usize>) -> Result<Seq, Error> {
        Ok(Seq(Vec::with_capacity(len.unwrap_or(0))))
    }
    fn serialize_tuple(self, len: usize) -> Result<Seq, Error> {
        self.serialize_seq(Some(len))
    }
    fn serialize_tuple_struct(self, _name: &'static str, len: usize) -> Result<Seq, Error> {
        self.serialize_seq(Some(len))
    }
    fn serialize_tuple_variant(
        self,
        _name: &'static str,
        _index: u32,
        variant: &'static str,
        len: usize,
    ) -> Result<TupleVariant, Error> {
        Ok(TupleVariant(variant, Seq(Vec::with_capacity(len))))
    }
    fn serialize_map(self, _len: Option<usize>) -> Result<Map, Error> {
        Ok(Map::default())
    }
    fn serialize_struct(self, _name: &'static str, _len: usize) -> Result<Map, Error> {
        Ok(Map::default())
    }
    fn serialize_struct_variant(
        self,
        _name: &'static str,
        _index: u32,
        variant: &'static str,
        _len: usize,
    ) -> Result<StructVariant, Error> {
        Ok(StructVariant(variant, Map::default()))
    }
}

fn tagged(variant: &str, content: Value) -> Value {
    Value::Mapping(BTreeMap::from([(variant.to_string(), content)]))
}

pub(crate) struct Seq(Vec<Value>);

impl ser::SerializeSeq for Seq {
    type Ok = Value;
    type Error = Error;
    fn serialize_element<T: ?Sized + Serialize>(&mut self, value: &T) -> Result<(), Error> {
        self.0.push(value.serialize(ValueSerializer)?);
        Ok(())
    }
    fn end(self) -> Result<Value, Error> {
        Ok(Value::Sequence(self.0))
    }
}
impl ser::SerializeTuple for Seq {
    type Ok = Value;
    type Error = Error;
    fn serialize_element<T: ?Sized + Serialize>(&mut self, value: &T) -> Result<(), Error> {
        ser::SerializeSeq::serialize_element(self, value)
    }
    fn end(self) -> Result<Value, Error> {
        ser::SerializeSeq::end(self)
    }
}
impl ser::SerializeTupleStruct for Seq {
    type Ok = Value;
    type Error = Error;
    fn serialize_field<T: ?Sized + Serialize>(&mut self, value: &T) -> Result<(), Error> {
        ser::SerializeSeq::serialize_element(self, value)
    }
    fn end(self) -> Result<Value, Error> {
        ser::SerializeSeq::end(self)
    }
}

pub(crate) struct TupleVariant(&'static str, Seq);

impl ser::SerializeTupleVariant for TupleVariant {
    type Ok = Value;
    type Error = Error;
    fn serialize_field<T: ?Sized + Serialize>(&mut self, value: &T) -> Result<(), Error> {
        ser::SerializeSeq::serialize_element(&mut self.1, value)
    }
    fn end(self) -> Result<Value, Error> {
        Ok(tagged(self.0, ser::SerializeSeq::end(self.1)?))
    }
}

#[derive(Default)]
pub(crate) struct Map {
    entries: BTreeMap<String, Value>,
    key: Option<String>,
}

impl ser::SerializeMap for Map {
    type Ok = Value;
    type Error = Error;
    fn serialize_key<T: ?Sized + Serialize>(&mut self, key: &T) -> Result<(), Error> {
        match key.serialize(ValueSerializer)? {
            Value::String(k) => {
                self.key = Some(k);
                Ok(())
            }
            _ => Err(Error::new("mapping keys must be strings")),
        }
    }
    fn serialize_value<T: ?Sized + Serialize>(&mut self, value: &T) -> Result<(), Error> {
        let key = self
            .key
            .take()
            .ok_or_else(|| Error::new("mapping value serialized before its key"))?;
        self.entries.insert(key, value.serialize(ValueSerializer)?);
        Ok(())
    }
    fn end(self) -> Result<Value, Error> {
        Ok(Value::Mapping(self.entries))
    }
}
impl ser::SerializeStruct for Map {
    type Ok = Value;
    type Error = Error;
    fn serialize_field<T: ?Sized + Serialize>(
        &mut self,
        key: &'static str,
        value: &T,
    ) -> Result<(), Error> {
        self.entries
            .insert(key.into(), value.serialize(ValueSerializer)?);
        Ok(())
    }
    fn end(self) -> Result<Value, Error> {
        ser::SerializeMap::end(self)
    }
}

pub(crate) struct StructVariant(&'static str, Map);

impl ser::SerializeStructVariant for StructVariant {
    type Ok = Value;
    type Error = Error;
    fn serialize_field<T: ?Sized + Serialize>(
        &mut self,
        key: &'static str,
        value: &T,
    ) -> Result<(), Error> {
        ser::SerializeStruct::serialize_field(&mut self.1, key, value)
    }
    fn end(self) -> Result<Value, Error> {
        Ok(tagged(self.0, ser::SerializeMap::end(self.1)?))
    }
}
