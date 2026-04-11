from __future__ import annotations

from collections.abc import Iterator, MutableMapping, MutableSequence
from typing import Any

from .nodes import DocumentNode, MappingEntry, MappingNode, Node, ScalarNode, SequenceItem, SequenceNode


def to_plain_data(node: Node) -> Any:
    if isinstance(node, ScalarNode):
        return node.value
    if isinstance(node, MappingNode):
        return {entry.key: to_plain_data(entry.value) for entry in node.entries}
    if isinstance(node, SequenceNode):
        return [to_plain_data(item.value) for item in node.items]
    raise TypeError(f"Unsupported node type: {type(node)!r}")


def coerce_node(value: Any) -> Node:
    from .emitter import infer_scalar_kind

    if isinstance(value, RoundTripMapping):
        return value._node
    if isinstance(value, RoundTripSequence):
        return value._node
    if isinstance(value, dict):
        node = MappingNode([], style="flow" if not value else "block")
        for key, item in value.items():
            child = coerce_node(item)
            node.entries.append(MappingEntry(str(key), child))
        return node
    if isinstance(value, list):
        node = SequenceNode([], style="flow" if not value else "block")
        for item in value:
            node.items.append(SequenceItem(coerce_node(item)))
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
        new_node = coerce_node(value)
        new_node.attach(self._node, self._document)
        if entry is None:
            self._node.entries.append(MappingEntry(str(key), new_node))
        else:
            entry.value = new_node
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


class RoundTripSequence(MutableSequence[Any]):
    def __init__(self, node: SequenceNode, document: DocumentNode) -> None:
        self._node = node
        self._document = document

    def __getitem__(self, index: int) -> Any:
        return wrap_node(self._node.items[index].value, self._document)

    def __setitem__(self, index: int, value: Any) -> None:
        new_node = coerce_node(value)
        new_node.attach(self._node, self._document)
        self._node.items[index].value = new_node
        self._node.mark_dirty()

    def __delitem__(self, index: int) -> None:
        del self._node.items[index]
        self._node.mark_dirty()

    def __len__(self) -> int:
        return len(self._node.items)

    def insert(self, index: int, value: Any) -> None:
        new_node = coerce_node(value)
        new_node.attach(self._node, self._document)
        self._node.items.insert(index, SequenceItem(new_node))
        self._node.mark_dirty()
