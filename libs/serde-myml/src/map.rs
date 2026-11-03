//! An insertion-ordered string-keyed map for `Value` mappings.
use crate::Value;
use std::collections::HashMap;
use std::fmt;
use std::ops::Index;

/// Mappings with at most this many entries find keys by scanning, which is faster than hashing at
/// this size and avoids allocating an index for the many small mappings typical of documents.
const INDEX_THRESHOLD: usize = 8;

/// A mapping that keeps entries in insertion order. Equality ignores entry order.
#[derive(Clone, Default)]
pub struct Map {
    entries: Vec<(String, Value)>,
    /// Entry positions by key, kept only while the mapping exceeds `INDEX_THRESHOLD` entries.
    index: Option<HashMap<String, usize>>,
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
    fn position(&self, key: &str) -> Option<usize> {
        match &self.index {
            Some(index) => index.get(key).copied(),
            None => self.entries.iter().position(|(k, _)| k == key),
        }
    }
    pub fn get(&self, key: &str) -> Option<&Value> {
        self.position(key).map(|i| &self.entries[i].1)
    }
    pub fn get_mut(&mut self, key: &str) -> Option<&mut Value> {
        self.position(key).map(|i| &mut self.entries[i].1)
    }
    pub fn contains_key(&self, key: &str) -> bool {
        self.get(key).is_some()
    }
    /// Inserts an entry. An existing key keeps its position and its previous value is returned.
    pub fn insert(&mut self, key: String, value: Value) -> Option<Value> {
        if let Some(i) = self.position(&key) {
            return Some(std::mem::replace(&mut self.entries[i].1, value));
        }
        let i = self.entries.len();
        if let Some(index) = &mut self.index {
            index.insert(key.clone(), i);
        }
        self.entries.push((key, value));
        if self.index.is_none() && self.entries.len() > INDEX_THRESHOLD {
            self.rebuild_index();
        }
        None
    }
    /// Removes an entry, preserving the order of the remaining entries.
    pub fn remove(&mut self, key: &str) -> Option<Value> {
        let i = self.position(key)?;
        let (_, value) = self.entries.remove(i);
        if self.entries.len() <= INDEX_THRESHOLD {
            self.index = None;
        } else {
            self.rebuild_index();
        }
        Some(value)
    }
    fn rebuild_index(&mut self) {
        let index = self.entries.iter().enumerate();
        self.index = Some(index.map(|(i, (k, _))| (k.clone(), i)).collect());
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

impl fmt::Debug for Map {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.debug_map().entries(self.iter()).finish()
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
