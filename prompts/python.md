# Python Myml Library

In addition to default parsing and emitting, support roundtrip mode that
preserves leading comments on array and map entries.

Enable via Myml Value Types (MVTs):

* `Mapping`, `Sequence`, and others as necessary
* Contain information to preserve input format or modify output format
* Extra data may include:
  * Comments
  * Key order information
  * Whitespace and indentation
  * Numeric scalar format
  * String scalar format (block/quoted/unquoted)

* Use standard `load|loads|dump|dumps` method names
* Control `roundtrip` mode with a boolean kwarg (default false)
* In roundtrip mode:
  * `load|loads` returns MVTs
  * `dump|dumps` formats output per information in received MVTs
  * Key order is preserved
* In non-roundtrip mode:
  * `load|loads` returns regular python containers
  * `dump|dumps` outputs in default format, treats MVTs as regular pythong
    containers
  * Key order is not preserved

When testing against corpus files, validate that roundtrip mode replicates the
input exactly.

Support `strict` and `yaml_1p1_safety` modes through boolean kwargs (default
false).
