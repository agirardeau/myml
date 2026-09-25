use serde_myml::{from_str_with_mode, to_string_with_mode, Mode, Value};
use std::fs;
#[test]
fn baseline_parse_profiles() {
    let root = concat!(env!("CARGO_MANIFEST_DIR"), "/../../corpus/cases");
    let mut failures = Vec::new();
    for entry in fs::read_dir(root).unwrap() {
        let dir = entry.unwrap().path();
        if !dir.is_dir() {
            continue;
        }
        let meta: serde_json::Value =
            serde_json::from_slice(&fs::read(dir.join("meta.json")).unwrap()).unwrap();
        let input = fs::read_to_string(dir.join("input.yaml")).unwrap();
        for (name, profile) in meta["parse_profiles"].as_object().unwrap() {
            if profile.get("requires").is_some() {
                continue;
            }
            let modes = profile["modes"]
                .as_array()
                .map(|v| v.iter().filter_map(|x| x.as_str()).collect::<Vec<_>>())
                .unwrap_or(vec!["standard", "strict"]);
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
                } else if let Some(expected) = profile.get("expect_node_graph") {
                    let expected: serde_json::Value = serde_json::from_slice(
                        &fs::read(dir.join(expected.as_str().unwrap())).unwrap(),
                    )
                    .unwrap();
                    let actual = graph(result.unwrap());
                    if actual != expected {
                        failures.push(format!(
                            "{} {name} {m}: expected {expected}, got {actual}",
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

fn graph(v: Value) -> serde_json::Value {
    use serde_json::Value as J;
    match v {
        Value::Null => J::Null,
        Value::Bool(x) => J::Bool(x),
        Value::I64(x) => J::Number(x.into()),
        Value::U64(x) => J::Number(x.into()),
        Value::F64(x) if x.is_nan() => J::String(".nan".into()),
        Value::F64(x) if x == f64::INFINITY => J::String(".inf".into()),
        Value::F64(x) if x == f64::NEG_INFINITY => J::String("-.inf".into()),
        Value::F64(x) if x.fract() == 0.0 && x >= 0.0 && x <= u64::MAX as f64 => {
            J::Number((x as u64).into())
        }
        Value::F64(x) => serde_json::to_value(x).unwrap(),
        Value::String(x) => J::String(x),
        Value::Sequence(x) => J::Array(x.into_iter().map(graph).collect()),
        Value::Mapping(x) => J::Object(x.into_iter().map(|(k, v)| (k, graph(v))).collect()),
    }
}
