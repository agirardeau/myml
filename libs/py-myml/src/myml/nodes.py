from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


class Node:
    def __init__(self) -> None:
        self.parent: Node | None = None
        self.document: DocumentNode | None = None
        self.dirty = False

    def attach(self, parent: Node | None, document: DocumentNode | None) -> "Node":
        self.parent = parent
        self.document = document
        return self

    def mark_dirty(self) -> None:
        if self.dirty:
            return
        self.dirty = True
        if self.parent is not None:
            self.parent.mark_dirty()


@dataclass
class ScalarNode(Node):
    value: Any
    kind: str
    style: str = "plain"
    raw: str | None = None

    def __post_init__(self) -> None:
        Node.__init__(self)


@dataclass
class MappingEntry:
    key: str
    value: Node
    before: list[str] = field(default_factory=list)
    inline_comment: str | None = None
    key_style: str = "plain"


@dataclass
class SequenceItem:
    value: Node
    before: list[str] = field(default_factory=list)
    inline_comment: str | None = None


@dataclass
class MappingNode(Node):
    entries: list[MappingEntry]
    style: str = "block"
    compact: bool = False
    trailing_lines: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        Node.__init__(self)

    def entry_for_key(self, key: str) -> MappingEntry | None:
        for entry in self.entries:
            if entry.key == key:
                return entry
        return None


@dataclass
class SequenceNode(Node):
    items: list[SequenceItem]
    style: str = "block"
    trailing_lines: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        Node.__init__(self)


@dataclass
class DocumentNode:
    root: Node
    original_text: str
    mode: str
    leading_lines: list[str] = field(default_factory=list)
    trailing_lines: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self._attach(self.root, None)

    def _attach(self, node: Node, parent: Node | None) -> None:
        node.attach(parent, self)
        if isinstance(node, MappingNode):
            for entry in node.entries:
                self._attach(entry.value, node)
        elif isinstance(node, SequenceNode):
            for item in node.items:
                self._attach(item.value, node)

    @property
    def dirty(self) -> bool:
        return self.root.dirty
