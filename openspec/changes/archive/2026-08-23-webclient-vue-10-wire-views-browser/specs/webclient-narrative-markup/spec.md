## MODIFIED Requirements

### Requirement: The converted-stream assumption is bounded and enforced
The pipeline's safety argument rests on the transport stream having been converted and escaped by the portal, but the tokenizer cannot distinguish a converted string from an arbitrary one. That assumption SHALL therefore be bounded rather than asserted globally. The project SHALL NOT send narrative text with Evennia's `raw` or `client_raw` output options, which bypass conversion and escaping, and a repository test SHALL fail if any project code path sets either option. Client-synthesized notices that the shell inserts into the narrative without conversion SHALL be fixed literal strings containing no markup characters, so they tokenize to a single text token. Any content whose source is not the converted transport stream SHALL be inserted as text.

#### Scenario: No project code path bypasses conversion
- **WHEN** the repository test inspects project code for narrative output options
- **THEN** no call site sets `raw` or `client_raw`, and the test fails if one is introduced

#### Scenario: Client-synthesized notices are inert
- **WHEN** the transport reports a closed connection or a reconnection attempt and the shell inserts its notice into the narrative
- **THEN** the notice renders as plain readable text and produces no element
