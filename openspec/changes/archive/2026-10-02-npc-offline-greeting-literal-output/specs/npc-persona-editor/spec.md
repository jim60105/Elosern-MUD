## MODIFIED Requirements

### Requirement: Card data reaches only the requesting session
Only the success result of `npc.persona.read` or `npc.persona.update` SHALL carry the private editor card and offline/default greeting fields, and only to the requesting session. Exploration, dialogue, and every other presentation panel SHALL NOT carry card text, hidden identity, or the editor's greeting keys. No editor action message, narrative output, operational event, or analytics record SHALL include card or greeting-field text; error results SHALL carry no `data`. The intentional public speech selected by the no-keyword/degraded greeting resolver is the narrow exception: speech output and the dialogue-session/panel line SHALL carry the selected greeting only, rendered as literal text when sourced from the editable instance field, never the full editor payload or other card text. The result data SHALL use only fixed lowercase keys, SHALL use `persona_version` rather than any reserved state key, and SHALL fit the protocol's result-data field, string, and byte limits for every valid payload, including maximal cards and maximal 300-code-point greetings of CJK text, astral characters, and JSON-escaped characters.

#### Scenario: Snapshots never carry the card
- **WHEN** a full snapshot is published for an actor standing with an NPC whose hidden identity is set
- **THEN** no panel contains any card leaf text

#### Scenario: Logs never carry the card
- **WHEN** a read and an update succeed and a third request is rejected for a field violation
- **THEN** no captured operational event context or editor action message contains any card leaf or greeting-field text

#### Scenario: Maximal valid cards fit the protocol
- **WHEN** valid cards at the total budget, together with a 300-code-point offline greeting and a default greeting, built from CJK text, astral characters, and JSON-escape-heavy characters are returned as success data
- **THEN** both the server result validator and the browser protocol mirror accept the envelope

#### Scenario: Intentional public greeting does not disclose the editor snapshot
- **WHEN** an NPC with private hidden identity and an edited greeting opens or degrades a conversation
- **THEN** its selected greeting is intentionally presented publicly as speech/session text without any card leaf, editor greeting key, default preview, or private author payload
