# Test Corpus

`/corpus` contains test data for verifying implementations of Myml parsers and emitters.

* Corpus (input) files use the template `{CORPUS_NAME}.yaml`
  * `CORPUS_NAME` describes notable features of the input and may contain
    `[a-z0-9-]`
* Corpus files containing valid Myml have a corresponding
  `{CORPUS_NAME}_success.json` file
  * Contains data parsers are expected to produce for the input
  * Key order matches input
* Corpus files containing invalid Myml have a corresponding
  `{CORPUS_NAME}_error.json` file
  * Contains error code and metadata parsers are expected to produce

