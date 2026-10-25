# Dialogue Panel Protocol and Publication Budgets

This document records the version-3 `dialogue` presentation panel wire format,
canonical UTF-8 JSON publication budgets, and the conditional envelope allowance
governing dialogue delivery over the Elosern Out-of-Band (OOB) protocol.

## Publication Budgets

Dialogue delivery enforces finite canonical UTF-8 JSON publication budgets across
both backend selection and frontend transport:

| Scope | Budget | Enforcement Point | Description |
| --- | ---: | --- | --- |
| Scene | 8,192 bytes | `world.lore.scenes::Scene`, `world.rules.dialogue::select_authored_topic` | Maximum canonical UTF-8 wire size of an individual scene (lines, speakers, and revisions). |
| Delivery Bundle | 16,384 bytes | `world.lore.dialogue.codec::validate_dialogue`, `select_authored_topic` | Selected delivery scene plus all reachable `pure_chain` public successor scenes. |
| Dialogue Panel | 24,576 bytes | `protocol.py::check_envelope`, `validate_dialogue`, UMD `core.js::checkEnvelope`, UMD `misc.js::validateDialoguePanel` | Maximum canonical UTF-8 wire size of the complete version-3 dialogue panel. |
| Generic Envelope | 65,536 bytes | `protocol.py::check_envelope`, UMD `core.js::checkEnvelope` | Global size ceiling for generic OOB messages and dialogue-removed envelopes. |
| Dialogue Envelope | 98,304 bytes | `protocol.py::check_envelope`, UMD `core.js::checkEnvelope`, UMD `store.js` | Conditional ceiling for snapshots and updates carrying an available version-3 dialogue panel. |

## Conditional Dialogue Envelope Allowance

Ordinary envelopes retain the 65,536-byte limit. A snapshot or update carrying an
available version-3 dialogue panel (`schema_version: 3`, `available: true`, `kind: "dialogue"`)
may use up to 98,304 canonical UTF-8 bytes only when:

1. The complete envelope canonical JSON is at most 98,304 bytes.
2. The dialogue panel payload is at most 24,576 bytes.
3. The same envelope with the `dialogue` panel removed passes the generic 65,536-byte limit.

This allowance reserves publication capacity for multilingual attributed dialogue scenes
and pure chain successors without relaxing size bounds on sibling panels. If any bound is
exceeded, the frame is rejected without truncation.

## Pre-Effect Operational Rejection

Selection of authored topics (`select_authored_topic`) enforces scene, bundle, and panel
budgets before entering any database transaction and before applying state mutations (such as
talk affinity advancement or session updates). Oversized content raises
`DialogueBudgetExceededError`, resulting in a safe operational refusal with zero partial side
effects; relations data and session snapshots are preserved untouched.

## Reconnect and Transport Generation Adoption

Presentation coordinator (`coordinator.py`) enforces `check_envelope` on candidate snapshots
and updates before advancing session revision counters. The UMD client store (`store.js`)
applies the same conditional allowance in `checkEnvelope`:
- A reconnect full snapshot establishing a new presentation epoch adopts the bounded frame up
  to 98,304 bytes cleanly.
- Stale snapshots from retired epochs remain rejected.
- Non-dialogue frames or frames where the dialogue-removed envelope exceeds 65,536 bytes are
  rejected.
