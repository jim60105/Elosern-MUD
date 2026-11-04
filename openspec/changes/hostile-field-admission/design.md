# Design

## Context

`field_enemy_roster` already collects every living local Monster in numeric-ID order. `engage_group` is the staged opponent API and gates voluntary sleeping actors. `settle_forced_sleep_opening` is called by engagement and exams and currently declares zero-round defeat. Natural fatigue/wake is deferred until terminal settlement. The required incapacitated-hostile-rounds predecessor amends those timing/wake contracts before this contact slice starts.

## Goals / Non-Goals

Deliver immediate contact admission and real enemy turns for incapacitated allies. Forecasting a long skip belongs to the next change; admission at every accepted boundary already works here. Preserve voluntary sleep/movement gates and designated exams.

## Decisions

### Rules-only contact authority

Create `world/rules/field_contact.py` with frozen `FieldContact(commander_id: int, location: LocationRef, tick: int, trigger_ids: tuple[int,...], source_id: str)`, pure `evaluate_field_contact(commander: Any, *, tick: int) -> FieldContact | None` and writer `admit_field_contact(commander: Any, contact: FieldContact) -> dict[str,Any] | None`. Conditions use the explicit activity declarations for passive, contact, defended area and declared dayparts. A trigger selects admission, never roster membership. Revalidate actual location/time/condition under the existing serialized combat writer; an active session deduplicates admission.

Factor validated session creation out of engage_group into an internal helper with explicit authority `voluntary` or `hostile_contact`. Only the rules owner may request hostile authority; client payloads cannot. Skip only the initiating voluntary sleep-action gate; retain party ownership/eligibility and collect field_enemy_roster independently of triggering IDs. Add no opening action, damage or initiative slot. Awake actors get normal editable draft choices. Exams retain their declared roster and FAIL policy.

Invoke after player physical arrival, monster arrival and committed birth in an occupied idle cell, at relevant daypart/territory boundaries, and before authoritative time-consuming exploration mutations. Cover movement, field cast/item/use, wait/rest/sleep, study/camp and conversation-time owners; inventory shared entry points with CodeGraph so text/browser cannot bypass. Present contact admits before exploration effects/costs. Presentation/look/preview never admits combat. Traverse scope from movement-edge-history prevents early pooled-room relocation from admitting contact in passage. Walking continuation stops before another edge.

At each lifecycle tick completed lawful arrivals and site/regional births precede contact; contact precedes idle departures. Equal facts sort owner/group/individual order. New protection prevents departure/reinforcement. Historical protection survives session close/catch-up; an escaped individual's protection ends at its real departure occurrence. No grace, cooldown or last-opponent flag.

### Accepted sleep transitions

Before interruptible-field-contact lands, include every next journey/decision/birth/condition boundary in the registered upcoming query. Existing interruptible callers therefore stop conservatively at the next maintenance tick and cannot pass a hostile contact. The next change replaces these conservative returns with the first relevant contact forecast, removing distant-maintenance interruptions. Never admit a past contact after settling physiology through a later requested endpoint.

Add `interrupt_sleep_for_contact(body: Any, *, tick: int, operation_id: str) -> None` in existing sleep owner `time_skip.py`. Validate read_sleep_receipt, retain actual recovered reserve, change voluntary posture through write_fatigue_state, persist STATE_INTERRUPTED with progress through tick, and revoke owner/camp continuation through the current writers. Forced posture and receipt remain unchanged. Field_contact and presentation never write fatigue/receipts directly. No refill or defeated-body revival.

Remove the hostile zero-defeat branch of settle_forced_sleep_opening and migrate callers/tests. Retain a narrowly named examination-only helper for existing exam FAIL. Voluntary engage and movement still reject sleeping initiation. Hostile admission does not grant the sleeping body action authority.

### Existing real continuation API

Consume the preceding change’s `continue_incapacitated_hostile_rounds(commander)` API and its strict settled_rounds accounting. This change does not reimplement automatic rounds, fatigue wake policy or terminal remainder billing. The contact writer calls the API only after the accepted clock advance has returned, as specified below. Contact admission itself never wakes a forced sleeper.

### Publication and observability

Clock sources admit the session and return its interactive event; they never recursively run enemy-only clock advances. The owning rules action invokes continue_incapacitated_hostile_rounds after the accepted WorldClock.advance has returned and persisted its endpoint, within the same outer durable/publication operation. A source invoked during a paid combat prefix cannot admit another session for that already engaged party.

One outer publication group/transaction joins location arrivals, interrupted receipts, admission and automatic rounds to final actionable/terminal state. No actionable exploration frame between arrival and combat. Snapshot initiation/dialogue/skip-safety, full clock-source registry, room/coordinate, roster, physiology and receipt surfaces before earliest mutation. Restore on any later failure and re-raise with field_contact_failed. Add catalog commit event field_contact_admitted with source_id, commander, triggering/full enemy IDs, session, location and tick. Existing round/clock events identify paid rounds; reads emit none.

## Risks / Trade-offs

The zero-round defeat and live-wake prohibitions conflict with the approved target; deltas explicitly replace hostile incapacitation behavior. Requested retreat with no acting ally and examinations retain their own outcomes. A paid-prefix cursor avoids an engine-wide conversion of ordinary rounds to live fatigue.

## Verification

Register new `world.rules.tests.test_field_contact` in evennia-shards; extend the predecessor-owned hostile continuation tests without registering a second owner. Real A+A+B player/monster/birth contact admits all IDs once with no extra attack; passive/defended-area/daypart/read controls remain. Forced reserve71928 reaches72000 after one real six-second enemy round and becomes actionable. Test awake companion, all temporarily blocked party, defeat/cap, unpaid prefix, terminal replay and post-reserve/session fault restoration. Voluntary receipt interrupts without refill, forced receipt persists. Exams retain FAIL and voluntary sleep gates. Text/browser and both command docs expose identical authority and mode.

## Implementation evidence contract

Canonical IDs copied from traceability list output for the equivalent merged tree:

- `hostile-field-contact::authored-hostile-contact-admits-immediate-ordinary-combat`, tasks1.1/3.1, test_field_contact.
- `hostile-field-contact::hostile-sleep-interruption-preserves-accepted-body-state`, task2.1, sleep-receipt and contact tests.
Create `/tmp/mud-field-tests.env` containing `MUD_TEST_SETTINGS=1` outside tracked source. Run one focused method/class at a time using the guarded command shown below; never concatenate the inventory or exceed 100 discovered tests. Register every new Python test module exactly once in `.github/evennia-shards.json`; new managed browser modules/methods belong exactly once in `.github/browser-shards.json`. Full managed-browser and complete traceability evidence remain CI-owned.

`uv run --locked --env-file=/tmp/mud-field-tests.env evennia test --settings test_settings.py --keepdb <named-label>`

Use canonical identifiers generated by `uv run --locked python -m tools.spec_traceability list`, never by concatenating names. For added/removed requirements, generate the equivalent merged specification tree outside Git and run the same tool with `--repo-root`; use its output before updating annotations. Preserve substantive assertion roles; delete retired claims without forwarding decorators, copy/data pin tests or waivers. Record requirement/scenario-to-test assertions and exercised evidence in `docs/development/monster-field-behaviour.md`. Human ecology/wording/visual judgment is reviewed there rather than asserted by shipped strings or counts.

At implementation handoff run focused tests, `uv run --locked python -m tools.observability_lint check` alongside changed-logging tests, the existing command-doc contract whenever command docs change, `openspec validate <change> --strict` and `uv run --locked python -m tools.contract_gate`. These are future worker checks, not feature verification during proposal creation. Failure restores every owning durable/live surface and emits no committed success. No compatibility readers, migrations, hidden initialization of an existing save or reset-on-load.
