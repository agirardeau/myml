set positional-arguments

test-py-myml:
    uv run --no-project python -m unittest discover libs/py-myml/tests

test-py-myml-tiny:
    uv run --no-project python -m unittest discover libs/py-myml-tiny/tests

test-serde-myml:
    cargo test --manifest-path libs/serde-myml/Cargo.toml --locked --all-targets

release package level:
    case "$1" in \
        all) scripts/release-python-lib py-myml "$2" && \
             scripts/release-python-lib py-myml-tiny "$2" && \
             scripts/release-serde-myml "$2" ;; \
        py-myml|py-myml-tiny) scripts/release-python-lib "$1" "$2" ;; \
        serde-myml) scripts/release-serde-myml "$2" ;; \
        *) echo "Unknown release package: $1" >&2; exit 2 ;; \
    esac
