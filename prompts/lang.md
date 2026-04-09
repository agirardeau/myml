# Language Definition

Myml is a subset of Yaml 1.2. Any valid Myml is valid Yaml 1.2, and has the same
evaluation.

Myml supports:

* Block-style mappings and sequences
  * Nested combinations of mappings and sequences
  * Mapping keys must be strings
* Flow-style mappings and sequences with restrictions
  * Must be single-line
  * May contain scalar values only
* Comments beginning with `#`
  * Allowed anywhere except quoted/block string scalars
* Empty lines
* Scalar values
  * Strings
    * Double-quoted and single-quoted
      * Escape sequences match yaml standard
    * Unquoted strings with restrictions below
    * Block scalar strings with `|` and `>` only
    * Non-block scalar strings may not span multiple lines
  * Numbers
    * Formats:
      * Integer
      * Hex in standard format e.g. `0xFF01`
        * `x` must be lowercase
        * Digits may be either lower or uppercase
      * Fixed-point decimal (e.g. `3.14`)
      * Exponential/scientific notation
        * `e` must be lowercase
      * `.inf`, `-.inf`, and `.nan`
    * May have leading `-` when not hex format or `.nan`
    * May not have leading `+`
    * May not have leading `0` characters
    * May not have comma thousands separators
    * Octal numbers are not supported
  * Bolean literals `true` and `false`
  * `null` literal

Unquoted string/key restrictions:

* Unquoted keys may contain:
  * `a-zA-Z0-9_`
  * `-`, except as first character
  * Unicode letters
* Unquoted string scalars may contain:
  * `a-zA-Z0-9_`
  * `.,/()`
  * `-!&*?{}[],#, |>%@'"`, except as first character
  * Unicode letters
  * Emojis
* Unquoted string scalars in flow-style containers may not contain `,`

Any constructs from Yaml 1.2 not supported by Myml result in an error with a
message indicating the disallowed feature. These include:

* Non-string keys
* Multiline strings
* Anchors
* Tags
* Merge keys
* Tabs in indentation
* Inconsistent indentation
* Numeric scalars other than as described above
* `true`, `false`, `null`, `.inf`, `-.inf`, `.nan` with non-lowercase letters
* Null scalar `~`
* Mapping entries with no value (interpretted as null in yaml)
* Chomping indicators `+` and `-` on block scalar strings

Other errors must also result in useful error messages, including:

* Malformed mappings or sequences
* Duplicate keys within the same mapping
* Unquoted strings/keys with `:` or `#`

Default output format:

* UTF-8
* Block style containers only
* Unquoted keys and string scalars whenever possible

## Strict Mode

In strict mode, unquoted string scalars are disallowed.

### Yaml 1.1 Safety Mode

In Yaml 1.1 Safety Mode, unquoted strings that could be Yaml 1.1 special
values are disallowed:

* Boolean scalars `yes`, `no`, `on`, `off`, `y`, and `n` (any capitalization)
* Dates/times in formats like ISO 8601 and `HH:MM:SS.ss`
* Octal numbers in `0123` format
* Sexagesimal numbers such as `13:22`
