## ADDED Requirements

### Requirement: A persona edit during an asynchronous exchange discards the stale response
Every asynchronous NPC dialogue exchange SHALL capture the NPC's identity and current `persona_version` when it builds the prompt, and at settlement, before any response-side effect, SHALL compare the NPC's current `persona_version` with the captured value. Any inequality SHALL produce a distinct stale-persona terminal outcome, separate from the degraded/offline outcome and from the separated-context outcome. A stale-persona exchange SHALL NOT present its speech, append the NPC response to chat memory, apply any intent, record or replace the dialogue-session line, or run the degraded party-invite threshold; it SHALL settle with one safe localized explanation, clear the thinking state, and SHALL NOT retry. The player's own line recorded before the edit MAY remain in memory. An unchanged or no-op save SHALL NOT invalidate an exchange. The gate SHALL apply to every consumer of the exchange seam — the browser free-form talk action, the browser party-invite action, the text `invite` command, and any other caller of the shared exchange — through the shared result and memory path, not only a browser control. Already committed speech and effects SHALL NOT be undone.

#### Scenario: A one-leaf edit discards a pending free-form reply
- **WHEN** a browser free-form talk is in flight and the NPC's `habit` is saved through the persona writer before the reply settles
- **THEN** the reply's speech is not shown, no NPC line is appended to memory, no intent applies, the dialogue session line is unchanged, and the action settles with the stale-persona explanation

#### Scenario: Change-and-revert still discards
- **WHEN** a leaf is changed and then changed back by two saves while an exchange is in flight
- **THEN** the exchange settles as stale-persona even though the card text equals the captured card

#### Scenario: A stale invite runs no threshold fallback
- **WHEN** a party invitation exchange degrades offline after the NPC's card was edited mid-flight
- **THEN** no party join, refusal line, or threshold decision occurs, and both the browser action and the text `invite` command report the stale-persona explanation

#### Scenario: A no-op save leaves the exchange valid
- **WHEN** an unchanged card is saved while an exchange is in flight
- **THEN** the exchange settles normally, presents its speech, and applies its verified intent

#### Scenario: Stale-persona settlement clears thinking state without retry
- **WHEN** an exchange settles as stale-persona after its thinking timer started
- **THEN** the timer is cancelled, no second request is made, and the pending state ends
