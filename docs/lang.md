# Myml Language Definition

## Scope and Relationship to YAML 1.2

Myml is a subset of YAML 1.2.

A valid Myml document is also a valid YAML 1.2 document and produces the same
representation graph when parsed by a compliant YAML 1.2 parser.

Myml is a simplified human-oriented format. YAML 1.2 constructs not explicitly
supported by this specification are outside the language and result in errors.

## Data Model

A Myml document represents a YAML 1.2 representation graph consisting of:

* Mapping nodes
* Sequence nodes
* Scalar nodes

Mapping keys are strings.

## Grammar Categories

A Myml document may contain:

* Block-style mappings
* Block-style sequences
* Flow-style mappings
* Flow-style sequences
* Comments
* Empty lines
* Scalar values

A `#` begins a comment when it appears outside string-scalar content; the
unquoted string rules below define when `#` is scalar content.

### Scalar Categories

Scalar values are one of:

* String
* Number
* Boolean
* Null

### String Forms

String forms are:

* Double-quoted string
* Single-quoted string
* Unquoted string
* Block scalar string introduced by `|` or `>`

Quoted scalars and block scalar strings are strings.

Non-block scalar strings do not span multiple lines.

Double-quoted and single-quoted strings follow YAML 1.2 string syntax and
escaping rules.

Block scalar strings are restricted as follows:

* Only `|` and `>` style indicators are supported
* Chomping indicators `+` and `-` are not supported
* Indentation indicators are not supported
* Otherwise, YAML 1.2 block scalar semantics are preserved

### Number Forms

Number forms are:

* Integer
* Hexadecimal integer
* Fixed-point decimal
* Exponential notation
* Infinity and NaN literals

The following numeric forms are supported:

* Integer, for example `42`
* Hexadecimal integer in standard form, for example `0xFF01`
* Fixed-point decimal, for example `3.14` or `0.5`
* Exponential notation with a normalized coefficient, for example
  `1e6` or `1.5e2`
* `.inf`, `-.inf`, and `.nan`

The following numeric restrictions apply:

* `0` is valid
* `-0` is not valid
* `.5` is not valid
* `+` prefixes are not valid
* A leading `-` is allowed only for non-hex numbers, non-`.nan` values, and
  nonzero values
* Leading `0` characters are not allowed except:
  * The value `0`
  * Plain fractional decimals beginning with exactly one `0.`
  * Hexadecimal values beginning with `0x`
* Scientific notation coefficients must satisfy `1 <= m < 10`
* Underscore digit separators are not allowed
* Octal notation is not supported

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

* `a-zA-Z0-9_-./$()~`
* Unicode letters

Unquoted string scalars may contain:

* `a-zA-Z0-9_./()$+=;<\ `
* ``!"'`*%&>|``, except as the first character
* `,[]{}`, except as first character or in flow containers
* `-?`, except as the first character if followed by a space character
* `:`, except as the last character or followed by a space character
* `#`, except as the first character or preceded by a space character
* `~`, except as the only character
* Unicode letters
* Emojis

## Scalar Resolution

Unquoted scalars are resolved in the following order:

1. Null
2. Boolean
3. Number
4. String

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

* A flow container appears on a single line
* A flow container contains scalar values only
* Empty flow containers `[]` and `{}` are allowed
* Comments may follow a flow container

## Unsupported YAML 1.2 Features

YAML 1.2 constructs outside this specification result in errors. These include:

* Non-string keys
* Multiline strings other than block scalar strings introduced by `|` or `>`
* Anchors
* Tags
* Merge keys
* Tabs in indentation
* Indentation that does not satisfy the container rules in this specification
* Numeric scalars outside the supported forms described above
* `true`, `false`, `null`, `.inf`, `-.inf`, and `.nan` written with any
  non-lowercase letters
* Null scalar `~`
* Mapping entries with no value
* Chomping indicators `+` and `-` on block scalar strings
* Indentation indicators on block scalar strings

## Error Behavior

Invalid input produces useful error messages.

Useful error messages are produced for, at minimum:

* Malformed mappings
* Malformed sequences
* Duplicate keys within the same mapping
* Unquoted keys containing disallowed characters
* Unquoted string scalars containing disallowed characters or restricted
  characters in disallowed forms (e.g. `:` followed by space)
* Use of any unsupported YAML 1.2 feature

## Serialization Defaults

The standard serialized form uses:

* UTF-8 encoding
* Block-style containers only
* Compact block mappings within sequences, with the first mapping entry on the
  same line as the `-` sequence marker
* Unquoted keys whenever possible
* Unquoted string scalars whenever possible

## Modes

### Standard Mode

Standard mode accepts the full Myml language defined in this specification.

### Strict Mode

Strict mode rejects all unquoted string scalars.
