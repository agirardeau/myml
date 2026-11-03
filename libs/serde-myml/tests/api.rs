use serde::{Deserialize, Serialize};
use serde_myml::{from_str, from_str_with_mode, to_string, to_string_with_mode, Mode, Value};
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
