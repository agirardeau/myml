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
