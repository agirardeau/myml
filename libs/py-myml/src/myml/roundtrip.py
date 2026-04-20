from __future__ import annotations

from collections.abc import Iterator, MutableMapping, MutableSequence
from dataclasses import dataclass
from typing import Any

from .nodes import DocumentNode, MappingEntry, MappingNode, Node, ScalarNode, SequenceItem, SequenceNode


@dataclass(slots=True)
class ScalarFormat:
    value: Any
    style: str = "plain"


@dataclass(slots=True)
class MappingFormat:
    value: dict[str, Any] | None = None
    style: str = "block"


@dataclass(slots=True)
class SequenceFormat:
    value: list[Any] | None = None
    style: str = "block"


@dataclass(slots=True)
class EntryFormat:
    value: Any
    before: str | list[str] | None = None
    eol_comment: str | None = None


def to_plain_data(node: Node) -> Any:
    if isinstance(node, ScalarNode):
        return node.value
    if isinstance(node, MappingNode):
        return {entry.key: to_plain_data(entry.value) for entry in node.entries}
    if isinstance(node, SequenceNode):
        return [to_plain_data(item.value) for item in node.items]
    raise TypeError(f"Unsupported node type: {type(node)!r}")


def _normalize_comment_lines(before: str | list[str] | None) -> list[str]:
    if before is None:
        return []
    if isinstance(before, str):
        parts = before.splitlines() or [before]
    else:
        parts = list(before)
    normalized: list[str] = []
    for part in parts:
        stripped = part.strip()
        if not stripped:
            normalized.append("")
        elif stripped.startswith("#"):
            normalized.append(stripped)
        else:
            normalized.append(f"# {stripped}")
    return normalized


def _normalize_inline_comment(comment: str | None) -> str | None:
    if comment is None:
        return None
    stripped = comment.strip()
    if not stripped:
        return None
    return stripped if stripped.startswith("#") else f"# {stripped}"


def scalar(value: Any, *, style: str = "plain") -> ScalarFormat:
    return ScalarFormat(value, style=style)


def mapping(value: dict[str, Any] | None = None, *, style: str = "block") -> MappingFormat:
    return MappingFormat(value=value, style=style)


def sequence(value: list[Any] | None = None, *, style: str = "block") -> SequenceFormat:
    return SequenceFormat(value=value, style=style)


def entry(value: Any, *, before: str | list[str] | None = None, eol_comment: str | None = None) -> EntryFormat:
    return EntryFormat(value=value, before=before, eol_comment=eol_comment)


def coerce_node(value: Any) -> Node:
    from .emitter import infer_scalar_kind

    if isinstance(value, RoundTripMapping):
        return value._node
    if isinstance(value, RoundTripSequence):
        return value._node
    if isinstance(value, ScalarFormat):
        kind = infer_scalar_kind(value.value)
        return ScalarNode(value.value, kind=kind, style=value.style, raw=None)
    if isinstance(value, MappingFormat):
        node = MappingNode([], style=value.style)
        for key, item in (value.value or {}).items():
            node.entries.append(_entry_from_value(str(key), item))
        return node
    if isinstance(value, SequenceFormat):
        node = SequenceNode([], style=value.style)
        for item in (value.value or []):
            node.items.append(_item_from_value(item))
        return node
    if isinstance(value, dict):
        node = MappingNode([], style="flow" if not value else "block")
        for key, item in value.items():
            node.entries.append(_entry_from_value(str(key), item))
        return node
    if isinstance(value, list):
        node = SequenceNode([], style="flow" if not value else "block")
        for item in value:
            node.items.append(_item_from_value(item))
        return node
    kind = infer_scalar_kind(value)
    style = "plain" if kind != "string" or "\n" not in str(value) else "literal"
    raw = None
    return ScalarNode(value, kind=kind, style=style, raw=raw)


def wrap_node(node: Node, document: DocumentNode):
    if isinstance(node, MappingNode):
        return RoundTripMapping(node, document)
    if isinstance(node, SequenceNode):
        return RoundTripSequence(node, document)
    if isinstance(node, ScalarNode):
        return node.value
    raise TypeError(f"Unsupported node type: {type(node)!r}")


def as_format_aware(value: Any, *, mode: str = "default"):
    if isinstance(value, (RoundTripMapping, RoundTripSequence)):
        return value
    node = coerce_node(value)
    if not isinstance(node, (MappingNode, SequenceNode)):
        raise TypeError("as_format_aware() only accepts mappings and sequences.")
    document = DocumentNode(node, "", mode)
    return wrap_node(node, document)


def _entry_from_value(key: str, value: Any) -> MappingEntry:
    if isinstance(value, EntryFormat):
        node = coerce_node(value.value)
        return MappingEntry(
            key,
            node,
            before=_normalize_comment_lines(value.before),
            inline_comment=_normalize_inline_comment(value.eol_comment),
        )
    return MappingEntry(key, coerce_node(value))


def _item_from_value(value: Any) -> SequenceItem:
    if isinstance(value, EntryFormat):
        node = coerce_node(value.value)
        return SequenceItem(
            node,
            before=_normalize_comment_lines(value.before),
            inline_comment=_normalize_inline_comment(value.eol_comment),
        )
    return SequenceItem(coerce_node(value))


class RoundTripEntry:
    def __init__(self, owner: RoundTripMapping | RoundTripSequence, slot: MappingEntry | SequenceItem) -> None:
        self._owner = owner
        self._slot = slot

    @property
    def value(self) -> Any:
        return wrap_node(self._slot.value, self._owner._document)

    @value.setter
    def value(self, value: Any) -> None:
        node = coerce_node(value)
        node.attach(self._owner._node, self._owner._document)
        self._slot.value = node
        self._owner._node.mark_dirty()

    @property
    def before(self) -> list[str]:
        return list(self._slot.before)

    @before.setter
    def before(self, value: str | list[str] | None) -> None:
        self._slot.before = _normalize_comment_lines(value)
        self._owner._node.mark_dirty()

    @property
    def eol_comment(self) -> str | None:
        return self._slot.inline_comment

    @eol_comment.setter
    def eol_comment(self, value: str | None) -> None:
        self._slot.inline_comment = _normalize_inline_comment(value)
        self._owner._node.mark_dirty()


class RoundTripMapping(MutableMapping[str, Any]):
    def __init__(self, node: MappingNode, document: DocumentNode) -> None:
        self._node = node
        self._document = document

    def __getitem__(self, key: str) -> Any:
        entry = self._node.entry_for_key(key)
        if entry is None:
            raise KeyError(key)
        return wrap_node(entry.value, self._document)

    def __setitem__(self, key: str, value: Any) -> None:
        entry = self._node.entry_for_key(key)
        if entry is None:
            new_entry = _entry_from_value(str(key), value)
            new_entry.value.attach(self._node, self._document)
            self._node.entries.append(new_entry)
        else:
            replacement = _entry_from_value(str(key), value)
            replacement.value.attach(self._node, self._document)
            entry.value = replacement.value
            if isinstance(value, EntryFormat):
                entry.before = replacement.before
                entry.inline_comment = replacement.inline_comment
        self._node.mark_dirty()

    def __delitem__(self, key: str) -> None:
        for index, entry in enumerate(self._node.entries):
            if entry.key == key:
                del self._node.entries[index]
                self._node.mark_dirty()
                return
        raise KeyError(key)

    def __iter__(self) -> Iterator[str]:
        return (entry.key for entry in self._node.entries)

    def __len__(self) -> int:
        return len(self._node.entries)

    def entry(self, key: str) -> RoundTripEntry:
        slot = self._node.entry_for_key(key)
        if slot is None:
            raise KeyError(key)
        return RoundTripEntry(self, slot)

    def insert(self, key: str, value: Any, *, before: str | None = None, after: str | None = None) -> None:
        if before is not None and after is not None:
            raise ValueError("insert() accepts only one of before= or after=.")
        if self._node.entry_for_key(key) is not None:
            raise KeyError(key)
        if before is not None:
            anchor = self._index_for_key(before)
            index = anchor
        elif after is not None:
            anchor = self._index_for_key(after)
            index = anchor + 1
        else:
            index = len(self._node.entries)
        new_entry = _entry_from_value(str(key), value)
        new_entry.value.attach(self._node, self._document)
        self._node.entries.insert(index, new_entry)
        self._node.mark_dirty()

    def move_before(self, key: str, anchor_key: str) -> None:
        if key == anchor_key:
            return
        entry = self._pop_entry(key)
        index = self._index_for_key(anchor_key)
        self._node.entries.insert(index, entry)
        self._node.mark_dirty()

    def move_after(self, key: str, anchor_key: str) -> None:
        if key == anchor_key:
            return
        entry = self._pop_entry(key)
        index = self._index_for_key(anchor_key)
        self._node.entries.insert(index + 1, entry)
        self._node.mark_dirty()

    def reorder(self, keys: list[str]) -> None:
        current = [entry.key for entry in self._node.entries]
        if len(keys) != len(current) or set(keys) != set(current):
            raise ValueError("reorder() requires a complete ordering of existing keys.")
        order = {key: index for index, key in enumerate(keys)}
        self._node.entries.sort(key=lambda item: order[item.key])
        self._node.mark_dirty()

    def _index_for_key(self, key: str) -> int:
        for index, entry in enumerate(self._node.entries):
            if entry.key == key:
                return index
        raise KeyError(key)

    def _pop_entry(self, key: str) -> MappingEntry:
        index = self._index_for_key(key)
        return self._node.entries.pop(index)


class RoundTripSequence(MutableSequence[Any]):
    def __init__(self, node: SequenceNode, document: DocumentNode) -> None:
        self._node = node
        self._document = document

    def __getitem__(self, index: int) -> Any:
        return wrap_node(self._node.items[index].value, self._document)

    def __setitem__(self, index: int, value: Any) -> None:
        replacement = _item_from_value(value)
        replacement.value.attach(self._node, self._document)
        item = self._node.items[index]
        item.value = replacement.value
        if isinstance(value, EntryFormat):
            item.before = replacement.before
            item.inline_comment = replacement.inline_comment
        self._node.mark_dirty()

    def __delitem__(self, index: int) -> None:
        del self._node.items[index]
        self._node.mark_dirty()

    def __len__(self) -> int:
        return len(self._node.items)

    def insert(self, index: int, value: Any) -> None:
        item = _item_from_value(value)
        item.value.attach(self._node, self._document)
        self._node.items.insert(index, item)
        self._node.mark_dirty()

    def entry(self, index: int) -> RoundTripEntry:
        return RoundTripEntry(self, self._node.items[index])
