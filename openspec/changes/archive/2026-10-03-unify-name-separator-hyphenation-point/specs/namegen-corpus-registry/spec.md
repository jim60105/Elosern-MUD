## MODIFIED Requirements

### Requirement: Display names compose from Chinese renderings with the middle-dot separator
`world/lore/names.py` SHALL define `NAME_SEPARATOR = "‧"` (U+2027 HYPHENATION POINT) as the only
composition constant in the registry layer, and `compose_display_name(given: NamePart, surname:
NamePart) -> str` returning `f"{given.zh}{NAME_SEPARATOR}{surname.zh}"`. The original-language
`text` field SHALL never appear in the composed output.

#### Scenario: Composition format is given, separator, surname
- **WHEN** `compose_display_name` is called with a given part (`zh` 「加斯帕」) and a surname part
  (`zh` 「斯諾」)
- **THEN** it returns 「加斯帕‧斯諾」 with the U+2027 separator between the two Chinese renderings

#### Scenario: Raw corpus text never reaches composed output
- **WHEN** composed display names are built for every given/surname pairing within one pack
- **THEN** no result contains any part's `text` value as a substring where a Chinese rendering is
  expected, i.e. every composed name is built solely from `zh` fields and the separator
