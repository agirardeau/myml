Make sorted keys the default mapping ordering for libraries in the "Serialization Defaults" section of lang.md

- Corpus needs to be updated
- Python libraries need to be updated to follow this

After doing this, verify whether there are other reasons that serde-myml doesn't use the corpus emit fixtures, and assuming there are none, switch it to using those.
