## ADDED Requirements

### Requirement: The speech_style field renders with its localized label
`PersonaStore` flattening SHALL render a requested `speech_style` field with the localized label `說話風格：` under the same per-field and whole-block caps as every other field, and SHALL leave the default field set, the generic shape handling, the public view, and the truncation behavior for every other consumer unchanged.

#### Scenario: A speech style flattens with its label
- **WHEN** a record carries a non-empty `speech_style` and `flatten` is called with a field set including `speech_style`
- **THEN** the block contains a `說話風格：` section carrying that text in the requested field order

#### Scenario: Default flattening is unchanged
- **WHEN** `flatten()` is called with its default field set on a record that carries `speech_style`
- **THEN** the block contains no `說話風格：` section and is identical to the pre-change output
