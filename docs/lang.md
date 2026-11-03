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

## Encoding and Line Breaks

A Myml document is UTF-8 text. It may begin with a byte order mark (U+FEFF),
which is not content.

The following characters are errors when unescaped anywhere in a document,
including in quoted scalars and comments. Double-quoted strings may contain
them as escapes such as `\N`, `\L`, `\P`, or `\uFEFF`.

* Characters that YAML 1.2 does not allow unescaped, such as most control
  characters
* Characters that are invisible or confusing in editors and rendered text,
  although YAML 1.2 allows them:
  * NEL (U+0085), line separator (U+2028), and paragraph separator (U+2029),
    which can render as line breaks
  * Byte order marks (U+FEFF) after the start of the document
  * Zero-width space (U+200B)
  * Bidirectional embedding, override, and isolate controls (U+202A to U+202E
    and U+2066 to U+2069)

Line breaks are CRLF, CR, or LF, and a document may mix them. Each line break
within a scalar value is read as LF.

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

Integer and hexadecimal integer forms are integers. Fixed-point decimal,
exponential, infinity, and NaN forms are floats, as in the YAML 1.2 core schema,
so `1e6` is a float.

In hexadecimal notation, `x` is lowercase. Hex digits may use uppercase or
lowercase letters.

In exponential notation, `e` is lowercase.

An unquoted scalar that the YAML 1.2 core schema resolves to a number but that
matches no supported form, such as `0123`, `+1`, `0o17`, `1.`, or `1E5`, is an
error rather than a string.

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

* `a-zA-Z0-9_./()$+=;<\^ `
* ``!"'`*%&>|@``, except as the first character
* `,[]{}`, except as first character or in flow containers
* `-?`, except as the first character if followed by a space character or as
  the only character
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

* A flow container, including any flow containers nested within it, appears on
  a single line
* A flow container contains scalar values and nested flow containers
* Empty flow containers `[]` and `{}` are allowed
* Comments may follow a flow container

## Unsupported YAML 1.2 Features

YAML 1.2 constructs outside this specification result in errors. These include:

* Non-string keys
* Multiline strings other than block scalar strings introduced by `|` or `>`
* Document markers `---` and `...`, including multiple documents
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

* UTF-8 encoding without a byte order mark
* LF line breaks
* Block-style containers only
* Compact block mappings within sequences, with the first mapping entry on the
  same line as the `-` sequence marker
* Two spaces of indentation per nesting level
* `{}` and `[]` for empty mappings and sequences
* Mapping entries in the order the serialized value provides them
* Unquoted keys whenever possible
* Unquoted string scalars whenever possible, in standard mode

A string is a `|` block scalar string when it ends with exactly one line break,
contains no tabs or characters that must be escaped, its first line with a
non-space character does not begin with a space, and all lines before that
line are empty. Its content lines are indented two spaces beyond the key or `-`
that introduces it, and its empty lines contain no spaces. This applies in both modes.

Other strings that are not unquoted are double-quoted. Double-quoted strings
escape `"`, `\`, backspace, tab, line feed, form feed, and carriage return as
`\"`, `\\`, `\b`, `\t`, `\n`, `\f`, and `\r`. Other characters that may not
appear unescaped, and the no-break space (U+00A0), are written as `\u` with four
lowercase hexadecimal digits. All other characters are written unescaped.

Integers are written in decimal. Floats are written as `.inf`, `-.inf`, `.nan`,
or with the fewest significant digits that read back as the same value. They use
fixed-point decimal notation unless that would need more than three zeros
between the significant digits and the decimal point, in which case they use
exponential notation. A fixed-point float with no fractional digits ends in
`.0`, so a float never reads back as an integer. For example, the float
1000000 is `1e6`, the integer 1000000 is `1000000`, and the floats 1000, 0.0001,
and 0.00001 are `1000.0`, `0.0001`, and `1e-5`.

## Modes

### Standard Mode

Standard mode accepts the full Myml language defined in this specification.

### Strict Mode

Strict mode rejects all unquoted string scalars.
