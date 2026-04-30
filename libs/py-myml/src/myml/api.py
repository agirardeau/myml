from __future__ import annotations

from typing import TextIO

from .emitter import dump_to_text
from .parser import parse_text


def loads(text: str, *, mode: str = "standard", roundtrip: bool = False):
    return parse_text(text, mode=mode, roundtrip=roundtrip)


def load(stream: TextIO, *, mode: str = "standard", roundtrip: bool = False):
    return loads(stream.read(), mode=mode, roundtrip=roundtrip)


def dumps(value, *, mode: str = "standard", roundtrip: bool = False) -> str:
    _ = roundtrip
    return dump_to_text(value, mode=mode)


def dump(value, stream: TextIO, *, mode: str = "standard", roundtrip: bool = False) -> None:
    stream.write(dumps(value, mode=mode, roundtrip=roundtrip))
