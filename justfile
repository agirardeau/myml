set positional-arguments

test-py-myml:
    uv run --no-project python -m unittest discover libs/py-myml/tests

test-py-myml-tiny:
    uv run --no-project python -m unittest discover libs/py-myml-tiny/tests

test-serde-myml:
    cargo test --manifest-path libs/serde-myml/Cargo.toml --locked --all-targets

release-python pkg bump:
    scripts/release-python-lib "$1" "$2"

release-rust bump:
    scripts/release-serde-myml "$1"
