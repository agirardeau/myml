use serde_myml::{from_str_with_mode, to_string_with_mode, Mode, Value};
use std::collections::BTreeMap;
use std::fs;
#[test]
fn baseline_parse_profiles() {
    let mut failures = Vec::new();
    for dir in case_dirs() {
        let meta = read_json(&dir.join("meta.json"));
        let input = fs::read_to_string(dir.join("input.yaml")).unwrap();
        let Some(Json::Obj(profiles)) = meta.get("parse_profiles") else {
            panic!("{}: parse_profiles must be an object", dir.display())
        };
        for (name, profile) in profiles {
            if profile.get("requires").is_some() {
                continue;
            }
            let modes = match profile.get("modes") {
                Some(Json::Arr(v)) => v
                    .iter()
                    .filter_map(|x| match x {
                        Json::Str(s) => Some(s.as_str()),
                        _ => None,
                    })
                    .collect(),
                _ => vec!["standard", "strict"],
            };
            for m in modes {
                let mode = if m == "strict" {
                    Mode::Strict
                } else {
                    Mode::Standard
                };
                let result = from_str_with_mode::<Value>(&input, mode);
                if profile.get("expect_error").is_some() {
                    if result.is_ok() {
                        failures.push(format!("{} {name} {m}: expected error", dir.display()))
                    }
                } else if let Err(e) = &result {
                    failures.push(format!("{} {name} {m}: {e}", dir.display()))
                } else if let Some(Json::Str(expected)) = profile.get("expect_node_graph") {
                    let expected = read_json(&dir.join(expected));
                    let actual = graph(result.unwrap());
                    if actual != expected {
                        failures.push(format!(
                            "{} {name} {m}: expected {expected:?}, got {actual:?}",
                            dir.display()
                        ))
                    }
                }
            }
        }
    }
    assert!(failures.is_empty(), "{}", failures.join("\n"));
}
#[test]
fn baseline_emit_profiles() {
    let mut failures = Vec::new();
    for dir in case_dirs() {
        let meta = read_json(&dir.join("meta.json"));
        let Some(Json::Obj(profiles)) = meta.get("emit_profiles") else {
            continue;
        };
        let input = fs::read_to_string(dir.join("input.yaml")).unwrap();
        for (name, profile) in profiles {
            if profile.get("requires").is_some() || profile.get("options").is_some() {
                continue;
            }
            let mode = match profile.get("mode") {
                Some(Json::Str(m)) if m == "strict" => Mode::Strict,
                Some(Json::Str(m)) if m == "standard" => Mode::Standard,
                other => panic!("{} {name}: unknown emit mode {other:?}", dir.display()),
            };
            let emitted = from_str_with_mode::<Value>(&input, Mode::Standard)
                .and_then(|v| to_string_with_mode(&v, mode));
            match (profile.get("expect_output"), emitted) {
                (Some(Json::Str(expected)), Ok(actual)) => {
                    let expected = fs::read_to_string(dir.join(expected)).unwrap();
                    if actual != expected {
                        failures.push(format!(
                            "{} {name}: expected {expected:?}, got {actual:?}",
                            dir.display()
                        ))
                    }
                }
                (Some(Json::Str(_)), Err(e)) => {
                    failures.push(format!("{} {name}: {e}", dir.display()))
                }
                (None, Ok(_)) => failures.push(format!("{} {name}: expected error", dir.display())),
                (None, Err(_)) => {}
                (Some(other), _) => {
                    panic!("{} {name}: invalid expect_output {other:?}", dir.display())
                }
            }
        }
    }
    assert!(failures.is_empty(), "{}", failures.join("\n"));
}

fn case_dirs() -> Vec<std::path::PathBuf> {
    let root = concat!(env!("CARGO_MANIFEST_DIR"), "/../../corpus/cases");
    let mut dirs: Vec<_> = fs::read_dir(root)
        .unwrap()
        .map(|entry| entry.unwrap().path())
        .filter(|dir| dir.is_dir() && !dir.file_name().unwrap().to_string_lossy().starts_with('.'))
        .collect();
    dirs.sort();
    dirs
}

#[test]
fn emitted_values_parse() {
    let data = [
        "{b: 2, a: 1}",
        "[a, b]",
        "name: hello\nitems:\n  - one\n  - two\n",
    ];
    for s in data {
        let v = from_str_with_mode::<Value>(s, Mode::Standard).unwrap();
        for mode in [Mode::Standard, Mode::Strict] {
            let emitted = to_string_with_mode(&v, mode).unwrap();
            let parsed = from_str_with_mode::<Value>(&emitted, mode).unwrap();
            assert_eq!(v, parsed, "{emitted}")
        }
    }
}

/// Converts a parsed value to the corpus node-graph JSON form, where special floats are strings
/// and floats are JSON numbers with a fraction or exponent, so they never compare equal to integers.
fn graph(v: Value) -> Json {
    match v {
        Value::Null => Json::Null,
        Value::Bool(x) => Json::Bool(x),
        Value::I64(x) => Json::Int(x.into()),
        Value::U64(x) => Json::Int(x.into()),
        Value::F64(x) if x.is_nan() => Json::Str(".nan".into()),
        Value::F64(x) if x == f64::INFINITY => Json::Str(".inf".into()),
        Value::F64(x) if x == f64::NEG_INFINITY => Json::Str("-.inf".into()),
        Value::F64(x) => Json::Float(x),
        Value::String(x) => Json::Str(x),
        Value::Sequence(x) => Json::Arr(x.into_iter().map(graph).collect()),
        Value::Mapping(x) => Json::Obj(x.into_iter().map(|(k, v)| (k, graph(v))).collect()),
    }
}

/// A minimal JSON reader for the corpus control files, which keeps the corpus test free of
/// dependencies beyond the crate itself.
#[derive(Debug, PartialEq)]
enum Json {
    Null,
    Bool(bool),
    Int(i128),
    Float(f64),
    Str(String),
    Arr(Vec<Json>),
    Obj(BTreeMap<String, Json>),
}

impl Json {
    fn get(&self, key: &str) -> Option<&Json> {
        match self {
            Json::Obj(m) => m.get(key),
            _ => None,
        }
    }
}

fn read_json(path: &std::path::Path) -> Json {
    let text = fs::read_to_string(path).unwrap();
    let mut reader = JsonReader { text: &text, i: 0 };
    let value = reader.value();
    reader.ws();
    assert_eq!(reader.i, text.len(), "{}: trailing content", path.display());
    value
}

struct JsonReader<'a> {
    text: &'a str,
    i: usize,
}

impl JsonReader<'_> {
    fn peek(&self) -> u8 {
        self.text.as_bytes()[self.i]
    }
    fn ws(&mut self) {
        while self.i < self.text.len() && self.peek().is_ascii_whitespace() {
            self.i += 1;
        }
    }
    fn eat(&mut self, b: u8) {
        self.ws();
        assert_eq!(self.peek() as char, b as char, "at byte {}", self.i);
        self.i += 1;
    }
    fn value(&mut self) -> Json {
        self.ws();
        match self.peek() {
            b'{' => {
                let mut m = BTreeMap::new();
                self.items(b'}', |r| {
                    r.ws();
                    let k = r.string();
                    r.eat(b':');
                    m.insert(k, r.value());
                });
                Json::Obj(m)
            }
            b'[' => {
                let mut v = Vec::new();
                self.items(b']', |r| v.push(r.value()));
                Json::Arr(v)
            }
            b'"' => Json::Str(self.string()),
            _ => {
                let rest = &self.text[self.i..];
                let len = rest
                    .find(|c: char| !(c.is_ascii_alphanumeric() || "+-.".contains(c)))
                    .unwrap_or(rest.len());
                let word = &rest[..len];
                self.i += len;
                match word {
                    "null" => Json::Null,
                    "true" => Json::Bool(true),
                    "false" => Json::Bool(false),
                    _ if word.contains(['.', 'e', 'E']) => Json::Float(word.parse().unwrap()),
                    _ => Json::Int(word.parse().unwrap()),
                }
            }
        }
    }
    /// Reads a bracketed, comma-separated list whose opening bracket is next.
    fn items(&mut self, close: u8, mut item: impl FnMut(&mut Self)) {
        self.i += 1;
        self.ws();
        if self.peek() == close {
            self.i += 1;
            return;
        }
        loop {
            item(self);
            self.ws();
            let c = self.peek();
            self.i += 1;
            if c == close {
                return;
            }
            assert_eq!(c, b',', "at byte {}", self.i - 1);
        }
    }
    fn string(&mut self) -> String {
        self.eat(b'"');
        let mut out = String::new();
        loop {
            let c = self.text[self.i..].chars().next().unwrap();
            self.i += c.len_utf8();
            match c {
                '"' => return out,
                '\\' => {
                    let e = self.peek();
                    self.i += 1;
                    out.push(match e {
                        b'"' => '"',
                        b'\\' => '\\',
                        b'/' => '/',
                        b'b' => '\u{8}',
                        b'f' => '\u{c}',
                        b'n' => '\n',
                        b'r' => '\r',
                        b't' => '\t',
                        b'u' => {
                            let mut cp = self.hex4();
                            if (0xd800..0xdc00).contains(&cp) {
                                self.eat(b'\\');
                                self.eat(b'u');
                                cp = 0x10000 + ((cp - 0xd800) << 10) + (self.hex4() - 0xdc00);
                            }
                            char::from_u32(cp).unwrap()
                        }
                        _ => panic!("invalid JSON escape at byte {}", self.i),
                    });
                }
                c => out.push(c),
            }
        }
    }
    fn hex4(&mut self) -> u32 {
        let v = u32::from_str_radix(&self.text[self.i..self.i + 4], 16).unwrap();
        self.i += 4;
        v
    }
}
