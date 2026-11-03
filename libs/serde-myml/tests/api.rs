use serde::{Deserialize, Serialize};
use serde_myml::{from_str, from_str_with_mode, to_string, to_string_with_mode, Map, Mode, Value};
#[derive(Debug, PartialEq, Serialize, Deserialize)]
struct Example {
    name: String,
    count: u32,
    items: Vec<String>,
}
#[test]
fn typed_roundtrip() {
    let x = Example {
        name: "hello".into(),
        count: 3,
        items: vec!["one".into(), "two".into()],
    };
    let s = to_string(&x).unwrap();
    assert_eq!(from_str::<Example>(&s).unwrap(), x);
}
#[test]
fn strict() {
    assert!(from_str_with_mode::<Value>("name: hello\n", Mode::Strict).is_err());
    let s = to_string_with_mode(&"hello", Mode::Strict).unwrap();
    assert_eq!(s, "\"hello\"\n");
}
#[test]
fn ranges() {
    assert!(from_str::<Value>("18446744073709551616").is_err());
    assert!(from_str::<u8>("256").is_err());
}
#[test]
fn quoted_scalars_must_stay_on_one_line() {
    for input in ["value: \"first\n  second\"\n", "value: 'first\n  second'\n"] {
        for mode in [Mode::Standard, Mode::Strict] {
            assert!(from_str_with_mode::<Value>(input, mode).is_err());
        }
    }
    assert!(from_str::<Value>("value: \"first\\nsecond\"\n").is_ok());
    assert!(from_str::<Value>("value: 'it''s fine'\n").is_ok());
}
#[test]
fn flow_containers_nest_on_one_line() {
    let value =
        from_str::<Value>("scopes:\n  plan: {dispatches: [], tags: [[a], {b: 1}]}\n").unwrap();
    assert_eq!(
        to_string(&value).unwrap(),
        "scopes:\n  plan:\n    dispatches: []\n    tags:\n      -\n        - a\n      - b: 1\n"
    );
    for input in [
        "value: [a,\n  b]\n",
        "value: [a, {b: 1,\n  c: 2}]\n",
        "value: {a: [1,\n  2]}\n",
    ] {
        assert!(from_str::<Value>(input).is_err(), "{input:?}");
    }
}
#[derive(Debug, PartialEq, Serialize, Deserialize)]
enum Shape {
    Empty,
    Circle(f64),
    Point(i32, i32),
    Rect { w: u32, h: u32 },
}
#[test]
fn enums_and_options_roundtrip() {
    let shapes = vec![
        Shape::Empty,
        Shape::Circle(1.5),
        Shape::Point(-1, 2),
        Shape::Rect { w: 3, h: 4 },
    ];
    let s = to_string(&shapes).unwrap();
    assert_eq!(
        s,
        "- Empty\n- Circle: 1.5\n- Point:\n    - -1\n    - 2\n- Rect:\n    w: 3\n    h: 4\n"
    );
    assert_eq!(from_str::<Vec<Shape>>(&s).unwrap(), shapes);
    let options: Vec<Option<u8>> = vec![Some(1), None];
    assert_eq!(
        from_str::<Vec<Option<u8>>>(&to_string(&options).unwrap()).unwrap(),
        options
    );
}
#[test]
fn block_scalars_clip_and_fold() {
    let v = from_str::<Value>(
        "lit: |\n  a\n\n  b\n\n\nfold: >\n  one\n  two\n\n  three\n    kept\n  four\n",
    )
    .unwrap();
    let Value::Mapping(m) = v else { panic!() };
    assert_eq!(m["lit"], Value::String("a\n\nb\n".into()));
    assert_eq!(
        m["fold"],
        Value::String("one two\nthree\n  kept\nfour\n".into())
    );
}
#[derive(Serialize)]
struct Unsorted {
    zebra: u8,
    apple: u8,
}
#[test]
fn mappings_keep_original_key_order() {
    assert_eq!(
        to_string(&Unsorted { zebra: 1, apple: 2 }).unwrap(),
        "zebra: 1\napple: 2\n"
    );
    for input in ["b: 1\na:\n  d: 2\n  c: 3\n", "{b: 1, a: {d: 2, c: 3}}\n"] {
        let v = from_str::<Value>(input).unwrap();
        assert_eq!(to_string(&v).unwrap(), "b: 1\na:\n  d: 2\n  c: 3\n");
    }
    let v = from_str::<Value>("- b: 1\n  a: 2\n").unwrap();
    assert_eq!(to_string(&v).unwrap(), "- b: 1\n  a: 2\n");
}
#[test]
fn keys_resolving_to_non_strings_are_rejected_and_quoted() {
    for input in ["1: a\n", "true: a\n", "null: a\n", "{1: a}\n"] {
        assert!(from_str::<Value>(input).is_err(), "{input:?}");
    }
    let v = from_str::<Value>("\"1\": a\n\"true\": b\n\"<<\": c\n").unwrap();
    let s = to_string(&v).unwrap();
    assert_eq!(s, "\"1\": a\n\"true\": b\n\"<<\": c\n");
    assert_eq!(from_str::<Value>(&s).unwrap(), v);
}
#[test]
fn quoted_strings_roundtrip() {
    for text in [
        "a\"b\\c",
        "line\nbreak\ttab",
        "\u{1}\u{85}\u{2028}",
        "\u{80}\u{fffe}\u{c}",
        "\u{200b}\u{202e}\u{2066}\u{feff}",
        "True",
        " pad",
        "a: b",
        "+",
        "-x",
        "-",
        "- x",
        "~",
        ".5",
        "0123",
        "1E5",
        "0o17",
        "-0x1F",
        "2026-04-09",
        "13:22",
        "café 😀",
        "nb\u{a0}sp",
        "\u{8}\u{c}",
    ] {
        let s = to_string(&text).unwrap();
        assert_eq!(from_str::<String>(&s).unwrap(), text, "{s:?}");
    }
}
#[test]
fn unsupported_syntax_is_rejected() {
    for input in [
        "---\na: 1\n",
        "a: 1\n...\n",
        "a: &x 1\n",
        "a: !tag 1\n",
        "a: ~\n",
        "<<: {}\n",
        "a: 1\na: 2\n",
        "a:\n\tb: 1\n",
        "a: +1\n",
        "a: 0o17\n",
        "a: 1_000\n",
        "a: 1.5e400\n",
        "a: |\n",
    ] {
        assert!(from_str::<Value>(input).is_err(), "{input:?}");
    }
}
#[test]
fn errors_report_positions() {
    let e = from_str::<Value>("a: 1\nb: [1, 2\n").unwrap_err();
    assert_eq!((e.line(), e.column()), (Some(2), Some(4)));
}
#[test]
fn large_mappings_keep_order_through_insert_and_remove() {
    let mut m = Map::new();
    for i in (0..20).rev() {
        assert_eq!(m.insert(format!("k{i}"), Value::U64(i)), None);
    }
    assert_eq!(
        m.insert("k5".into(), Value::Null),
        Some(Value::U64(5)),
        "replacing keeps position"
    );
    for i in [19, 0, 7] {
        assert_eq!(m.remove(&format!("k{i}")), Some(Value::U64(i)));
    }
    let expected: Vec<String> = (1..19)
        .rev()
        .filter(|&i| i != 7)
        .map(|i| format!("k{i}"))
        .collect();
    assert_eq!(m.keys().cloned().collect::<Vec<_>>(), expected);
    assert_eq!(m["k12"], Value::U64(12));
    assert_eq!(m["k5"], Value::Null);
    while m.len() > 3 {
        let key = m.keys().next().unwrap().clone();
        m.remove(&key);
    }
    assert_eq!(m.keys().collect::<Vec<_>>(), ["k3", "k2", "k1"]);
    assert_eq!(m.get("k2"), Some(&Value::U64(2)));
}
#[test]
fn multiline_strings_use_literal_blocks_when_representable() {
    let v = from_str::<Value>("- |\n  a\n   b\n- c: |\n    d\n").unwrap();
    assert_eq!(to_string(&v).unwrap(), "- |\n  a\n   b\n- c: |\n    d\n");
    assert_eq!(to_string(&"top\n").unwrap(), "|\n  top\n");
    assert_eq!(to_string(&"\na\n  \n").unwrap(), "|\n\n  a\n    \n");
    for text in [
        "no newline\nend",
        "two\n\n",
        " lead\n",
        "tab\there\n",
        "  \nspaces before\n",
    ] {
        let s = to_string(&text).unwrap();
        assert!(s.starts_with('"'), "{s:?}");
        assert_eq!(from_str::<String>(&s).unwrap(), text);
    }
}
#[test]
fn floats_keep_their_type_and_value() {
    assert_eq!(from_str::<Value>("1e6").unwrap(), Value::F64(1e6));
    let cases = [
        (1e6, "1e6"),
        (-1e6, "-1e6"),
        (150.0, "150.0"),
        (1000.0, "1000.0"),
        (10000.0, "1e4"),
        (1.0, "1.0"),
        (0.0, "0.0"),
        (-0.0, "-0.0"),
        (0.5, "0.5"),
        (0.0001, "0.0001"),
        (0.00001, "1e-5"),
        (1.25e-7, "1.25e-7"),
        (12345678.9, "12345678.9"),
        (0.1 + 0.2, "0.30000000000000004"),
        (1e300, "1e300"),
        (f64::MAX, "1.7976931348623157e308"),
        (f64::MIN_POSITIVE, "2.2250738585072014e-308"),
    ];
    for (v, text) in cases {
        assert_eq!(to_string(&v).unwrap(), format!("{text}\n"));
        let back = from_str::<Value>(text).unwrap();
        assert!(
            matches!(back, Value::F64(x) if x.to_bits() == v.to_bits()),
            "{text}"
        );
    }
    assert_eq!(to_string(&1_000_000u32).unwrap(), "1000000\n");
}
