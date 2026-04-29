# Minimal Yaml - The Yaml Subset That Doesn't Suck

The language definition lives in
[`docs/lang.md`](/home/andrew/truehome/repos/myml/wt1/docs/lang.md) and the
active OpenSpec artifacts live under
[`openspec/`](/home/andrew/truehome/repos/myml/wt1/openspec).

The reference Python implementation lives in
[`libs/py-myml`](/home/andrew/truehome/repos/myml/wt1/libs/py-myml) and is
verified against the checked-in corpus in
[`corpus/`](/home/andrew/truehome/repos/myml/wt1/corpus).

## CI

GitHub Actions runs the baseline Python validation workflow on every pull
request and push. The workflow installs the package from
[`libs/py-myml`](/home/andrew/truehome/repos/myml/wt1/libs/py-myml) and runs
the checked-in unit test suite with:

```bash
python -m pip install -e libs/py-myml
python -m unittest discover libs/py-myml/tests
```

If your local shell does not provide a `python` shim, use `python3` for the
same commands.

The CI matrix covers Python 3.11 and 3.12 so the project checks both the
declared support floor and a newer CPython release.
