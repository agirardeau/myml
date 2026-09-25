# Deferred: Arbitrary-Precision Numbers

A future `arbitrary_precision` Cargo feature flag may allow parsing, representing, and emitting Myml numbers larger than the baseline `i64` and `u64` integer ranges without loss of precision. The baseline crate returns a numeric range error for such integers. This feature is deferred and is not required by `spec.md`.
