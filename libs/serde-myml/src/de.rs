//! Deserializing Rust values from a `Value`.
use crate::{Error, Value};
use serde::de::value::{MapDeserializer, SeqDeserializer};
use serde::de::{self, DeserializeSeed, IntoDeserializer, Visitor};

impl<'de> IntoDeserializer<'de, Error> for Value {
    type Deserializer = Value;
    fn into_deserializer(self) -> Value {
        self
    }
}

impl<'de> de::Deserializer<'de> for Value {
    type Error = Error;

    fn deserialize_any<V: Visitor<'de>>(self, visitor: V) -> Result<V::Value, Error> {
        match self {
            Value::Null => visitor.visit_unit(),
            Value::Bool(v) => visitor.visit_bool(v),
            Value::I64(v) => visitor.visit_i64(v),
            Value::U64(v) => visitor.visit_u64(v),
            Value::F64(v) => visitor.visit_f64(v),
            Value::String(v) => visitor.visit_string(v),
            Value::Sequence(v) => {
                let mut seq = SeqDeserializer::new(v.into_iter());
                let result = visitor.visit_seq(&mut seq)?;
                seq.end()?;
                Ok(result)
            }
            Value::Mapping(v) => {
                let mut map = MapDeserializer::new(v.into_iter());
                let result = visitor.visit_map(&mut map)?;
                map.end()?;
                Ok(result)
            }
        }
    }

    fn deserialize_option<V: Visitor<'de>>(self, visitor: V) -> Result<V::Value, Error> {
        match self {
            Value::Null => visitor.visit_none(),
            v => visitor.visit_some(v),
        }
    }

    fn deserialize_newtype_struct<V: Visitor<'de>>(
        self,
        _name: &'static str,
        visitor: V,
    ) -> Result<V::Value, Error> {
        visitor.visit_newtype_struct(self)
    }

    /// Enums are externally tagged: a unit variant is a string, and other variants are a
    /// single-entry mapping from the variant name to its content.
    fn deserialize_enum<V: Visitor<'de>>(
        self,
        _name: &'static str,
        _variants: &'static [&'static str],
        visitor: V,
    ) -> Result<V::Value, Error> {
        match self {
            Value::String(variant) => visitor.visit_enum(Enum {
                variant,
                content: Value::Null,
            }),
            Value::Mapping(m) if m.len() == 1 => {
                let (variant, content) = m.into_iter().next().unwrap();
                visitor.visit_enum(Enum { variant, content })
            }
            _ => Err(de::Error::custom(
                "expected an enum variant as a string or a single-entry mapping",
            )),
        }
    }

    serde::forward_to_deserialize_any! {
        bool i8 i16 i32 i64 i128 u8 u16 u32 u64 u128 f32 f64 char str string
        bytes byte_buf unit unit_struct seq tuple tuple_struct map struct
        identifier ignored_any
    }
}

struct Enum {
    variant: String,
    content: Value,
}

impl<'de> de::EnumAccess<'de> for Enum {
    type Error = Error;
    type Variant = Value;
    fn variant_seed<V: DeserializeSeed<'de>>(self, seed: V) -> Result<(V::Value, Value), Error> {
        let variant = seed.deserialize(Value::String(self.variant))?;
        Ok((variant, self.content))
    }
}

impl<'de> de::VariantAccess<'de> for Value {
    type Error = Error;
    fn unit_variant(self) -> Result<(), Error> {
        match self {
            Value::Null => Ok(()),
            _ => Err(de::Error::custom("expected a unit variant")),
        }
    }
    fn newtype_variant_seed<T: DeserializeSeed<'de>>(self, seed: T) -> Result<T::Value, Error> {
        seed.deserialize(self)
    }
    fn tuple_variant<V: Visitor<'de>>(self, _len: usize, visitor: V) -> Result<V::Value, Error> {
        de::Deserializer::deserialize_seq(self, visitor)
    }
    fn struct_variant<V: Visitor<'de>>(
        self,
        _fields: &'static [&'static str],
        visitor: V,
    ) -> Result<V::Value, Error> {
        de::Deserializer::deserialize_map(self, visitor)
    }
}
