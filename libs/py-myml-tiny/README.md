# py-myml-tiny

`py-myml-tiny` is a tiny, dependency-free reader for Myml.

It exposes `load` and `loads` for parsing Myml into plain Python values. It
does not expose `dump`, `dumps`, roundtrip metadata, formatting-aware editing,
or any emitter API.

```python
from myml_tiny import loads

data = loads("name: Ada\nactive: true\n")
```
