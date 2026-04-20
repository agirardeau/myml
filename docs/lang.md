# Myml Language Definition

## Scope and Relationship to YAML 1.2

Myml is a subset of YAML 1.2.

A valid Myml document is also a valid YAML 1.2 document and produces the same
representation graph when parsed by a compliant YAML 1.2 parser.

Myml is a simplified human-oriented format. YAML 1.2 constructs not explicitly
supported by this specification are outside the language and result in errors.

## Data Model

A Myml document represents a YAML 1.2 representation graph consisting of:

* mapping nodes
* sequence nodes
* scalar nodes

Mapping keys are strings.

## Grammar Categories

A Myml document may contain:

* block-style mappings
* block-style sequences
* flow-style mappings
* flow-style sequences
* comments
* empty lines
* scalar values

Outside quoted scalars and block scalar strings, `#` begins a comment.

### Scalar Categories

Scalar values are one of:

* string
* number
* boolean
* null

### String Forms

String forms are:

* double-quoted string
* single-quoted string
* unquoted string
* block scalar string introduced by `|` or `>`

Quoted scalars and block scalar strings are strings.

Non-block scalar strings do not span multiple lines.

Double-quoted and single-quoted strings follow YAML 1.2 string syntax and
escaping rules.

Block scalar strings are restricted as follows:

* only `|` and `>` style indicators are supported
* chomping indicators `+` and `-` are not supported
* indentation indicators are not supported
* otherwise, YAML 1.2 block scalar semantics are preserved

### Number Forms

Number forms are:

* integer
* hexadecimal integer
* fixed-point decimal
* exponential notation
* infinity and NaN literals

The following numeric forms are supported:

* integer, for example `42`
* hexadecimal integer in standard form, for example `0xFF01`
* fixed-point decimal, for example `3.14` or `0.5`
* exponential notation with a normalized coefficient, for example
  `1e6` or `1.5e2`
* `.inf`, `-.inf`, and `.nan`

The following numeric restrictions apply:

* `0` is valid
* `-0` is not valid
* `.5` is not valid
* `+` prefixes are not valid
* a leading `-` is allowed only for non-hex numbers, non-`.nan` values, and
  nonzero values
* leading `0` characters are not allowed except:
  * the value `0`
  * plain fractional decimals beginning with exactly one `0.`
  * hexadecimal values beginning with `0x`
* scientific notation coefficients must satisfy `1 <= m < 10`
* underscore digit separators are not allowed
* octal notation is not supported

In hexadecimal notation, `x` is lowercase. Hex digits may use uppercase or
lowercase letters.

In exponential notation, `e` is lowercase.

### Boolean and Null Forms

Boolean literals are:

* `true`
* `false`

The null literal is:

* `null`

### Unquoted Keys and Unquoted Strings

Unquoted keys may contain:

* `a-zA-Z0-9_`
* `-`, except as the first character
* Unicode letters

Unquoted string scalars may contain:

* `a-zA-Z0-9_`
* `.,/()`
* `-!&*?{}[], |>%@'"`
* Unicode letters
* emojis

The following additional restrictions apply:

* the first character of an unquoted string scalar may not be one of
  `-!&*?{}[], |>%@'"`
* `#` is not permitted within unquoted keys
* `#` is not permitted within unquoted string scalars
* `:` is not permitted within unquoted keys
* `:` is not permitted within unquoted string scalars
* unquoted string scalars in flow-style containers may not contain `,`

## Scalar Resolution

Unquoted scalars are resolved in the following order:

1. null
2. boolean
3. number
4. string

Quoted scalars and block scalar strings always resolve as strings.

## Container Rules

### General

Mappings and sequences may use block style or flow style.

Mappings contain only string keys.

Duplicate keys within the same mapping are errors. Duplicate detection occurs
after each key is parsed to its final string value.

### Block Style

Nested combinations of block-style mappings and block-style sequences are
allowed.

Indentation uses spaces only.

Tabs are not permitted in indentation.

Within a block mapping, all entries at the same nesting level begin at the same
indentation column.

Within a block sequence, all sequence markers at the same nesting level begin at
the same indentation column.

A nested block collection begins at an indentation column greater than that of
its parent entry.

### Flow Style

Flow-style mappings and flow-style sequences are restricted as follows:

* a flow container appears on a single line
* a flow container contains scalar values only
* empty flow containers `[]` and `{}` are allowed
* comments may follow a flow container

## Unsupported YAML 1.2 Features

YAML 1.2 constructs outside this specification result in errors. These include:

* non-string keys
* multiline strings other than block scalar strings introduced by `|` or `>`
* anchors
* tags
* merge keys
* tabs in indentation
* indentation that does not satisfy the container rules in this specification
* numeric scalars outside the supported forms described above
* `true`, `false`, `null`, `.inf`, `-.inf`, and `.nan` written with any
  non-lowercase letters
* null scalar `~`
* mapping entries with no value
* chomping indicators `+` and `-` on block scalar strings
* indentation indicators on block scalar strings

## Error Behavior

Invalid input produces useful error messages.

Useful error messages are produced for, at minimum:

* malformed mappings
* malformed sequences
* duplicate keys within the same mapping
* unquoted keys containing `:`
* unquoted keys containing `#`
* unquoted string scalars containing `:`
* unquoted string scalars containing `#`
* use of any unsupported YAML 1.2 feature

## Serialization Defaults

The default serialized form uses:

* UTF-8 encoding
* block-style containers only
* unquoted keys whenever possible
* unquoted string scalars whenever possible

## Optional Modes

### Strict Mode

In strict mode, unquoted string scalars are not permitted.

### YAML 1.1 Safety Mode

In YAML 1.1 Safety Mode, unquoted strings that could be interpreted as special
values by YAML 1.1 are not permitted.

These include:

* boolean scalars `yes`, `no`, `on`, `off`, `y`, and `n`, in any capitalization
* date and time forms such as ISO 8601 values and `HH:MM:SS.ss`
* octal numbers in `0123` form
* sexagesimal numbers such as `13:22`
