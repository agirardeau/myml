# serde-myml

Serde parsing and emission for [Myml](../../docs/lang.md).

```rust
use serde::{Deserialize, Serialize};
use serde_myml::{from_str, to_string, Mode, to_string_with_mode};

#[derive(Debug, Serialize, Deserialize)]
struct Config { name: String, enabled: bool }

let config: Config = from_str("name: demo\nenabled: true\n")?;
let standard = to_string(&config)?;
let strict = to_string_with_mode(&config, Mode::Strict)?;
# Ok::<(), serde_myml::Error>(())
```

The public API also includes `from_reader`, `to_writer`, and mode variants of each function. `Value` is a dynamic Serde value with lexicographically ordered mapping keys.

Dynamic integers use `i64` or `u64`, and non-integer numbers use `f64`. Integer literals outside those ranges produce a range error. Infinity and NaN use `.inf`, `-.inf`, and `.nan`.

The crate emits canonical block-style Myml. It does not preserve source formatting or provide a format-aware editing API.
