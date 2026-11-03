//! An insertion-ordered string-keyed map for `Value` mappings.
use crate::Value;
use std::ops::Index;

/// A mapping that keeps entries in insertion order. Equality ignores entry order.
#[derive(Clone, Debug, Default)]
pub struct Map {
    entries: Vec<(String, Value)>,
}

impl Map {
    pub fn new() -> Self {
        Self::default()
    }
    pub fn len(&self) -> usize {
        self.entries.len()
    }
    pub fn is_empty(&self) -> bool {
        self.entries.is_empty()
    }
    pub fn get(&self, key: &str) -> Option<&Value> {
        self.entries.iter().find(|(k, _)| k == key).map(|(_, v)| v)
    }
    pub fn get_mut(&mut self, key: &str) -> Option<&mut Value> {
        self.entries
            .iter_mut()
            .find(|(k, _)| k == key)
            .map(|(_, v)| v)
    }
    pub fn contains_key(&self, key: &str) -> bool {
        self.get(key).is_some()
    }
    /// Inserts an entry. An existing key keeps its position and its previous value is returned.
    pub fn insert(&mut self, key: String, value: Value) -> Option<Value> {
        match self.get_mut(&key) {
            Some(slot) => Some(std::mem::replace(slot, value)),
            None => {
                self.entries.push((key, value));
                None
            }
        }
    }
    /// Removes an entry, preserving the order of the remaining entries.
    pub fn remove(&mut self, key: &str) -> Option<Value> {
        let i = self.entries.iter().position(|(k, _)| k == key)?;
        Some(self.entries.remove(i).1)
    }
    pub fn iter(&self) -> impl Iterator<Item = (&String, &Value)> {
        self.entries.iter().map(|(k, v)| (k, v))
    }
    pub fn keys(&self) -> impl Iterator<Item = &String> {
        self.entries.iter().map(|(k, _)| k)
    }
    pub fn values(&self) -> impl Iterator<Item = &Value> {
        self.entries.iter().map(|(_, v)| v)
    }
}

impl PartialEq for Map {
    fn eq(&self, other: &Self) -> bool {
        self.len() == other.len() && self.iter().all(|(k, v)| other.get(k) == Some(v))
    }
}

impl Index<&str> for Map {
    type Output = Value;
    fn index(&self, key: &str) -> &Value {
        self.get(key).expect("key not found in mapping")
    }
}

impl FromIterator<(String, Value)> for Map {
    fn from_iter<I: IntoIterator<Item = (String, Value)>>(iter: I) -> Self {
        let mut map = Self::new();
        map.extend(iter);
        map
    }
}

impl Extend<(String, Value)> for Map {
    fn extend<I: IntoIterator<Item = (String, Value)>>(&mut self, iter: I) {
        for (k, v) in iter {
            self.insert(k, v);
        }
    }
}

impl IntoIterator for Map {
    type Item = (String, Value);
    type IntoIter = std::vec::IntoIter<(String, Value)>;
    fn into_iter(self) -> Self::IntoIter {
        self.entries.into_iter()
    }
}

impl<'a> IntoIterator for &'a Map {
    type Item = (&'a String, &'a Value);
    type IntoIter = std::iter::Map<
        std::slice::Iter<'a, (String, Value)>,
        fn(&'a (String, Value)) -> (&'a String, &'a Value),
    >;
    fn into_iter(self) -> Self::IntoIter {
        self.entries.iter().map(|(k, v)| (k, v))
    }
}
