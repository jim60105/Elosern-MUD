## ADDED Requirements

### Requirement: Altoria upper-terrace hosts carry individual authored profiles and rewritten dialogue
Each upper-terrace host owned by the `altoria_upper` inventory slice SHALL name, through its place record, an authored NPC profile whose key equals the host's service identity, whose card satisfies the compact card contract, and which authors a misunderstanding reply in that host's voice and no profile greeting. Each corresponding dialogue table SHALL keep its keyword identifiers and its greeting, and every greeting and keyword response SHALL be newly authored against the host's card: no provisional greeting or response SHALL survive verbatim. Within the slice, no two profiles SHALL share a personality or speech-style text, and no two greetings SHALL be identical after replacing the hosts' names and titles with one placeholder. Rewritten dialogue SHALL keep every service semantic its settlement and dialogue specifications require and SHALL NOT state fixed prices, stock counts, or availability that live service data owns.

#### Scenario: Every owned host references its own valid profile
- **WHEN** the slice's place rows are resolved against the profile registry
- **THEN** each names a profile keyed by its service identity, the profile's card validates, and it authors a misunderstanding reply and no profile greeting

#### Scenario: Topics survive the rewrite
- **WHEN** each owned dialogue table is inspected
- **THEN** its keyword identifiers equal the pre-change identifiers in the same order and it still authors a greeting

#### Scenario: No provisional line survives
- **WHEN** every owned greeting and response is compared with the digests of the provisional lines
- **THEN** none matches

#### Scenario: Voices are not name substitutions
- **WHEN** the owned greetings are compared after replacing host names and titles with one placeholder, and the owned profiles' personality and speech-style texts are compared
- **THEN** no two are identical

#### Scenario: Service semantics are preserved
- **WHEN** the existing settlement, merchant, and scripted-dialogue behavior tests run against the rewritten tables
- **THEN** they pass without weakening any behavior assertion
