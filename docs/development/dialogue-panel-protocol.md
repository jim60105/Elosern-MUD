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

Canonical mutation writers call the companion
`world/rules/dialogue_availability.py::queue_dialogue_refresh(owners, *, cause)` with the
owner objects they captured **before** any destructive membership or control write. It
deduplicates the lawful owner identities, registers one commit callback per write, and
re-resolves each owner row, acting body, host binding and published generated phase
inside that callback. Pre-commit eligibility is never used, several callbacks from one
outer operation may each re-evaluate the final committed state, and an outer rollback
discards them all. `affected_dialogue_owners(entity, *, prior_owner=None)` is the
discovery half: a persistent player owns itself; any other body contributes its lawful
party-bound owner and its currently lawful possession owner; a caller detaching a body
passes the pre-detach owner as `prior_owner`. It never returns an account-wide sibling
character and never creates a conversation, session or selection. Refresh is
source-neutral: it re-reads the current static snapshot or published generated
binding/phase, so no static membership filter or immutable-package edit is involved,
and the already-delivered scene keeps its selected wording.

An already delivered scene keeps its chosen variant/scene revision across a refresh: the
session stores the committed delivery, and only the projected choices are recomputed.
Context invalidation, phase change, movement, combat and host cleanup keep their existing
owners.

### Canonical physical source matrix

These are the exact commit hooks `authored-dialogue-refresh-physical` owns. Every row
captures its owner(s) before the write, registers only after the successful write, and
therefore publishes nothing when the owning transaction rolls back.

| Condition source | Exact commit hook | Captured owner(s) | Committed acceptance |
|---|---|---|---|
| Carried item, including use/trade/transfer | `world/rules/equipment.py::apply_inventory_plan`, after the inventory + ACQUIRE writes inside the caller transaction | `affected_dialogue_owners(plan.entity)`; each transfer plan captures its own owner | Telnet, another web connection and a no-session call all refresh; an outer rollback publishes nothing |
| Worn exposure bias | `world/rules/equipment.py::toggle_equipment`, after the final equipment/gauge write | `affected_dialogue_owners(entity)` | Wearing/unequipping changes the threshold choice while the delivered variant stays unchanged |
| Base exposure transition | `world/rules/sexual_transitions.py::apply_event`, after the converged cascade | owner captured before the operation | Threshold crossing refreshes once the final committed state is visible; a later fault cancels the callbacks |
| Structured social identity | `world/rules/social_identity.py::set_social_identities`, after the validated write | `affected_dialogue_owners(entity)`; construction with no lawful owner is a no-op | Tag add/remove refreshes a live possessed actor; persona prose is not a source and has no effect |
| Skill ownership and proficiency | `world/rules/progression/_gates.py::award_practice_xp` after the stored XP assignment; `world/rules/progression/_lineage.py::apply_lineage_auto_seed` after the ownership/proficiency assignment; `world/rules/cross_lineage_unlock.py::grant_owned_skill` immediately after the ownership write, only on a new grant | affected learner owner | Passive/active ownership and proficiency thresholds refresh from any origin (study, another session, a scheduled tick) |
| Race | existing construction/import establishes race before any dialogue; opening and selection always re-read the acting body's race | no speculative new race writer | A new body's race is honored; control refresh owns changing actor identity |

The cross-lineage hook is exactly `grant_owned_skill`, not `clause_satisfied` and not a
second call in `evaluate_cross_lineage_unlocks`; no new skill mutation API is
introduced. A raw GM console Attribute repair stays outside ordinary gameplay
publication and its next canonical sync re-evaluates state.

The lifecycle slice (`authored-dialogue-refresh-lifecycle`) extends the same two helpers
for quest, world-time, companion-presence and control sources; completion-to-refresh
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
