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

The successor bundle budget measures the selected delivery plus reachable `pure_chain`
successors for a **formal** delivery only. A refusal reveals no successor, so an
undelivered successor's protected size never blocks a permitted refusal; the refusal
scene and the complete resulting panel are still measured against their own budgets.

## Server-Qualified Topic Availability

`world/rules/dialogue_availability.py::project_topics(context)` is the single
availability/disclosure authority. The version-3 panel's `choices`, the exploration
`explore.talk_scripted` vocabulary, the deterministic selection boundary and the text
`talk` surface all read it, so no surface can disagree about a topic or disclose a
protected body first.

- **hidden** topics are absent from every projection, and an explicit topic ID behaves
  exactly like an unknown one.
- **locked** topics (declared `unavailable: "locked"` with an authored `refusal`) carry
  only the stable ID, keyword, label, lock state, canonical `requirement_hint` and the
  server-built `{npc_id, topic_id, context_id}` action descriptor. Selecting one delivers
  the authored refusal with zero effects and never the fallback/variant body.
- **open** topics expose the same descriptor fields only; the authorized scene is chosen
  inside `select_authored_topic` after it rechecks current canonical state.

No row, choice, affordance descriptor, hint or text answer carries scene text, a variant,
a fallback, a successor bundle or a private phase body. The projection is pure: it writes
no session, reading record, affinity value or world state.

Guarded topics fail closed. A `requires` that does not hold is hidden or visibly locked
per the declaration; an unmet `predecessors` gate stays unavailable until reading
persistence lands (so a `pure_chain` successor is not listed yet); a projection with no
lawful actor withholds every guarded topic instead of asserting an availability; and a
locked row whose canonical hint cannot render is withheld rather than shipped.

Availability is never accepted from the client. The composed
`explore.talk_scripted` payload is exactly `{npc_id, topic_id, context_id}` plus the
server-injected `selection_id`; any extra field (including an `availability` flag) is a
malformed payload.

## Availability Refresh

`world/rules/dialogue_availability.py::refresh_dialogue_availability(owner, *, cause)`
is the explicit refresh API. It re-resolves the owner's current acting body (the owner,
or the companion it lawfully possesses) **inside** a `transaction.on_commit` callback,
emits the `dialogue_availability_refreshed` boundary event with
`char`/`actor`/`npc`/`context`/`cause`, and fans the freshly rendered `dialogue` panel
out to that body's live watchers through the existing epoch-guarded pusher. Nothing is
persisted; a failed push is isolated to one `dialogue_availability_refresh_failed` event
and recovers on the next canonical sync. A rolled-back owning write schedules nothing.

An already delivered scene keeps its chosen variant/scene revision across a refresh: the
session stores the committed delivery, and only the projected choices are recomputed.
Context invalidation, phase change, movement, combat and host cleanup keep their existing
owners.

Production mutation hooks are owned by `authored-dialogue-refresh-physical` and
`authored-dialogue-refresh-lifecycle`; completion-to-refresh
(`cause="reading_completed"`) belongs to `authored-dialogue-reading-server`. Command and
presentation observers are not a substitute: a committed writer with no live session
(Telnet, a scripted clock tick, another actor's change, or an offline character) never
walks a command, panel render or action path, so only the owning writer can schedule the
refresh. The one non-mutation cause this slice adds is `cause="open"` from the successful
open/selection path.

The text `talk` command introduces no new listing syntax: its topic enumeration (which
keyword resolves to which topic) reads the same projected rows, so a hidden keyword
answers with the ordinary no-understanding line instead of its formal prose and a locked
keyword plays the authored refusal. A player-facing text listing remains a UI decision
outside this slice; no scenario or existing surface defines one.

## Reconnect and Transport Generation Adoption

Presentation coordinator (`coordinator.py`) enforces `check_envelope` on candidate snapshots
and updates before advancing session revision counters. The UMD client store (`store.js`)
applies the same conditional allowance in `checkEnvelope`:
- A reconnect full snapshot establishing a new presentation epoch adopts the bounded frame up
  to 98,304 bytes cleanly.
- Stale snapshots from retired epochs remain rejected.
- Non-dialogue frames or frames where the dialogue-removed envelope exceeds 65,536 bytes are
  rejected.
