# Design

## Context

The authoritative scope is `docs/superpowers/specs/2026-10-30-wilderness-camping-design.md`, overriding the blueprint's approximate beat/example timing. Blueprint §§6/7.4 keep the server in exploration and allow camping rules alongside sight/reveal. Read root and webclient AGENTS.md, engine architecture §§2/3, and `docs/development/spec-test-traceability.md` before apply.

Observed owners are `time_skip.py::_validate_sleep_request`, `_accepted_sleep_seconds`, `enter_party_sleep`, `continue_owner_sleep`; `sleep_receipt.py` stores closed modes and deadlines; `sleep_control.py::begin_all_party_sleep` adds selection/control validation; `server/dream_service.py::answer_sleep_dream` owns guarded answers. Entry already snapshots fatigue/receipt surfaces and restores caches on failure. The service currently schedules continuation after decline, so calling it unchanged inside a larger entry transaction would start recovery too early. `exploration_actions.py::_validate_sleep_wait_payload` accepts only recovery/duration, and `validate_sleep_party_payload` currently accepts `{}`. CmdSleep already parses explicit party scope. AppClient owns one choices-card chain and `use-sleep-handoff.js` owns the existing handoff.

The sibling leg proposal supplies `openTravelCamp()` and log proposal supplies `TravelEvent`, `TravelLogFact`, commit-qualified grouping and closed `camp_result` params `{summary}`. These are prerequisites for integration, not code to implement here. See proposal dependency/conflict matrix.

## Goals / Non-Goals

Deliver one whole-party camping decision using existing sleep identities and continuation, with a server-only prediction and a presentation-only beat. Keep deterministic rules in `world/rules/`; services orchestrate guarded rules operations and never write physiology directly.

Do not change party selection, safety, forced targets, dream generation/departure rules, map disclosure, travel planning, movement queues, dialogue/combat layout or authored world content. Do not implement any sibling UI. Do not add ambush/watch/respawn rules, art production, an event database, alternate clock or compatibility schema.

## Decisions

### 1. Dawn is a retained sleep deadline

Add `MODE_UNTIL_DAWN = "until-dawn"` to `world/rules/sleep_receipt.py::MODES`; update its exact receipt validation and `__all__`. Extend `time_skip.py::_validate_sleep_request` to accept dawn without seconds and `_accepted_sleep_seconds(member, mode, duration_seconds)` to return `min(seconds_until_daypart(clock.calendar, "dawn"), MAX_SKIP_SECONDS)`. Existing `seconds_until_daypart` is strictly positive even exactly at the anchor. Persist `mode="until-dawn"`, `target_tick=limit_tick=entry_tick+accepted_seconds`. Do not turn this into recovery mode or allow early reserve saturation to wake it. Existing sleepers keep their old identities/targets. Continue through the same boundary executor; preserve due events and actual prefix accounting. A capped dawn target reports its actual earlier deadline without claiming dawn was reached.

Internal `recovery` remains the existing value; the new camp wire uses `until-recovered`, translated once at the service boundary. No rename of existing wire modes.

### 2. Share planning, admission and answers

Add `world/rules/camping.py` with these contracts:

```python
def preview_camp(actor) -> dict: ...
def plan_camp(actor, *, mode: str) -> dict: ...
def commit_camp_entry(actor, *, mode: str, dream: bool,
                      operation_id: str, session=None) -> dict: ...
```

`plan_camp` returns `{owner, members:tuple, mode, entry_tick:int, target_tick:int, targets:tuple[{member,mode,target_tick,accepted_seconds,existing:bool}], dream_offerable:bool}` or raises the existing typed refusal. Entities stay internal; wire output never contains entities. `commit_camp_entry` returns `{owner,outcome,plan,camp_id,owner_sleep_id:str|None,generation:int,dream_entered:bool}`. Its target contract is shared with the preview serializer. Do not add another planner interface.

`plan_camp` is a detached no-create projection of the same selection/eligibility, bounded per-member sleep target and physiological prediction used by admission. Extract the common read-only target/selection helpers in `time_skip.py` and reuse them; never run `WorldClock.advance` speculatively and roll back to obtain preview. Use existing read-only clock/optional fatigue reads, canonical reserve policy and detached interval prediction. No preview call creates a clock, fatigue record, receipt, room or reveal state. Browser reserve percentages are serialized by the server. Preview guarantees predictions for the unchanged uninterrupted state, not future interaction immunity.

`commit_camp_entry` locks owner/present rows in the existing stable order, rechecks safety, co-location, possession, eligibility and selected targets, and performs party entry plus answer under one outer `transaction.atomic()`. Reuse existing snapshot/restore helpers for every touched fatigue, receipt and view-decision surface; also discard any newly opened dream/session/cache on rollback. A guard failure returned as an error object must become a rollback exception inside the outer transaction. No failure response may commit partial entries. Publish only via existing commit hooks.

Refactor the existing guarded answer into an entry-safe operation with a continuation switch, preserving current public behavior:

```python
def answer_sleep_dream(actor, *, decision, sleep_id, revision, generation,
                       session=None, defer_continuation=False): ...
```

Default false retains separate text/browser answers. True validates and records the answer without starting recovery, deferring any public stage publication until transaction commit. The camp/sleep-entry orchestrator invokes it using the newly accepted authoritative owner receipt and generation, never client-supplied identity. This is an internal switch, not a second transport or compatibility shim. Persistent answer writes stay in existing rules owners.

Ordinary sleep-entry requests accept optional `dream` with exact boolean validation. True requires an authenticated owner selected for a new voluntary sleeping receipt, no possessed companion, and successful receipt/control revalidation; forced owner sleep, already-met recovery with no sleeping receipt, excluded owner or unauthenticated request reject atomically. False/absent ordinary requests do not call the answer operation. Camp false records decline on a current voluntary owner receipt, or an existing forced owner receipt if present, before continuation; forced sleep can be declined but never entered into a dream. If recovery is already met and there is no owner sleeping receipt, do not fabricate one solely to decline: there is no question to suppress. Existing forced companion sleepers do not prevent an eligible voluntary owner from opting in.

`begin_all_party_sleep` remains the selection/control authority. It already releases a valid possessed companion inside its compensated transaction. Preserve that release for nondream camp, then invoke decline as the authenticated owner after release in the same outer transaction. Include its control/session/location snapshots in rollback. A true request made while a companion is possessed rejects before that release; later release must never retroactively authorize opt-in. Invalid possession bindings refuse without release.

### 3. Exact protocol and completion

Extend the existing exploration action registry/validators/adapters in `web/webclient/actions/exploration_actions.py` and their dispatch registration, bounded result validation and JS mirror. Preview is read-only and returns through the ordinary request-correlated result path, not a persistent panel or schema-wide status bump. Add `server/camp_service.py` orchestration with:

```python
def camp(actor, *, mode: str, dream: bool, operation_id: str,
         seconds: int | None = None, session=None) -> dict: ...
```

Browser allows only the two modes and no seconds. The internal optional seconds supports text `camp <duration>` while preserving text/browser rule parity. The existing action envelope remains unchanged. `operation_id` comes from the transport request identity or text invocation, not an extra browser payload field.

`explore.camp_preview` payload is exactly `{}`. Result `data` is exactly:

```text
{available:boolean, refusal:null|{code,message},
 dream_offerable:boolean, default_mode:"until-dawn"|"until-recovered",
 current_tick:integer, current_time:string,
 modes:[{mode, wake_tick:integer, wake_time:string,
         members:[{member_id:string,name:string,current_reserve:integer,
                   predicted_reserve:integer,reserve_max:integer,
                   current_percent:integer,predicted_percent:integer,
                   wake_tick:integer,wake_time:string}]}]}
```

Available preview has both modes in dawn/recovered order. Unavailable preview has `modes:[]`, false dream_offerable and nonnull refusal. `default_mode` derives from the canonical current daypart: dusk/night dawn, otherwise recovery. `wake_tick` at mode level denotes the existing owner continuation target; member fields preserve distinct existing targets and predict reserves at the mode-level continuation endpoint. A member already awake/full in recovery remains in the scope with unchanged values. Preserve underlying accepted targets instead of promising that every member wakes simultaneously.

Codes reuse stable gate values, not prose: `in_combat`, `hostile_present` from skip safety and `party_unavailable` from the existing all-party admission wrapper. Keep that wrapper's member/possession reason as its zh-TW message instead of inventing more-specific codes. Deeper receipt failures preserve their existing `SleepRefused.code` constants. `dream_not_offerable` is used for a true request which the preview advertises as unofferable; `malformed_payload` for wire validation. Share the read-only all-party gate projection with commit so preview and refusal code/message match. Precedence follows the same shared preflight order; never independently duplicate it.

`explore.camp` payload is exactly `{mode:"until-dawn"|"until-recovered",dream:boolean}`. Result `data` is exactly:

```text
{camp_id:string, phase:"dream"|"complete"|"interrupted",
 elapsed_seconds:integer, result_tick:integer, result_time:string,
 wake_tick:null|integer, wake_time:null|string,
 members:[{member_id,name,reserve_before:integer,reserve_after:integer,
           reserve_max:integer,before_percent:integer,after_percent:integer,
           sleeping:boolean,wake_tick:null|integer}],
 events:[<existing serialized ScheduledEvent>],
 interrupted:boolean, interruption_reason:null|string}
```

Integer fields are nonnegative safe integers; reserve values are bounded by their positive reserve_max and percentages by 0..100. Member IDs are existing opaque identifiers, max64 ASCII; names max256 codepoints, display times max32; camp IDs max80 ASCII, reasons/codes max64 ASCII; selected members use the existing party-scope bound. Validate complete objects with exact keys on Python/JS boundaries; reuse existing scheduled-event serializer/bounds. The source action-result envelope byte ceiling remains enforced. Never invent a client clock or infer a result from prose.

Nondream camp records decline under the entry transaction, commits entry, then calls existing owner continuation using the same receipt/authorization. Existing owner-targeted continuation may finish while a slower companion still sleeps; report that truthful state and preserve lawful handoff/recovery. Do not introduce a new all-members continuation policy. Actual interaction/safety interruption commits the safe prefix and returns `interrupted`; a refusal before accepted entry writes nothing. A post-entry unexpected continuation failure must preserve the accepted resumable sleep and report its authoritative interrupted/pending recovery surface, never mislabel it an atomic refusal or undo committed time.

Dream entry returns `phase:"dream"`, zero elapsed, unchanged reserves, null actual wake and no final camp event. Extend `sleep_receipt.py::read_party_operation/write_party_operation` with optional `camp` metadata. Ordinary operations omit it. Its exact shape is `{camp_id,owner_sleep_id,mode,dream,entry_tick,before:[{member_id,name,reserve,reserve_max,percent}],result:null|<camp result data>,event_id:null|string}` with the wire bounds above and at most64 members. Include it in existing sleep surface compensation. No new model or migration. Add `camping.py::finalize_camp(actor, result) -> dict|None`, called by `time_skip.py::continue_owner_sleep` immediately before its committed return for completed/interrupted results; absent metadata is inert. This covers direct continuation, `server/dream_service.py::_continue_owner_after_commit`, dream departure and reconnect through the same owner. Bind owner_sleep_id to reject unrelated results. Store actual final result and event identity in the same result transaction before publishing. Replayed results return stored data without another event. An interrupted result is one camp result; resuming the same camp updates accepted sleep progress but does not emit another camp_result. Recovery intervals retain their own existing idempotence.

Use sibling `travel_events.py` source group accumulator and `on_publication_commit` to publish `kind="camp_result", params={summary:<server text>}`. Preserve its exact entry shape, IDs, bounds and duplicate semantics; no alternate event format or fabricated per-client event. The full result is action data, not extra camp_result params. If a delayed dream result has no live request, refresh the ordinary authoritative presentation and travel log through that existing completion publication path.

### 4. Text parity and docs

Extend CmdSleep `_request`/`func` for `until-dawn`, token aliases 睡到天亮 / 天亮, and a single terminal `dream` after an explicit mode; `sleep dream` stays invalid. Plain `sleep all <mode>` still enters without an answer; the dream suffix uses the shared atomic orchestrator. Extend `explore.wait` sleep grammar with `sleep_mode:"until-dawn"` and optional exact boolean dream; `explore.sleep_party` accepts optional `sleep_mode`, optional duration seconds, optional dream with the same validation, retaining valid empty/default requests. Do not change unrelated waits.

Add `camp` as an alias on CmdSleep, routing `self.cmdstring == "camp"` through `camp_service.camp` with explicit party selection, common default, mode/duration parsing and optional terminal dream. This alias has the required one-decision continuation/decline semantics; a literal rewrite to current `sleep all` would leave an unwanted question. No separate command class/cmdset registration is needed. Ensure the alias is admitted in the existing sleeping command whitelist and available in the forced-sleep handoff context under existing action gates. Both `docs/game/commands.md` and `docs/game/command-reference.md` describe all forms, tokens, defaults, decline-versus-no-answer behavior and sleeping-view availability. Preserve text dream enter/decline and offline escape.

### 5. Card and beat state machine

Add `components/travel/CampCard.vue`, `CampfireCard.vue`, `composables/use-camp.js`, `stores/elosern/camp.js` and focused `tests/travel/camp.test.js`, `campfire.test.js`. Reuse the existing `ChoiceCard.vue` frame/classes, focus-trap helper, motion preferences, committed travel medallion/artwork model and input guards; never import prototype code. `useCamp` exposes `{openCamp,closeCamp,selectMode,toggleDream,confirmCamp,finishBeat,continueTravel}`. Store exports `openTravelCamp()` by replacing only the leg-owned existing destination. Camp state is `closed -> previewPending -> choosing|refused -> submitting -> dream|beat -> closed`. Dream false resets on every open, including reopen after refusal; hide the checkbox if unofferable. Preview/refusal pending cannot confirm. Match request ID, generation/epoch and current view before accepting results. Disconnect/mode retirement discards local card state and never auto-resubmits.

Stop existing walking through its public stop action before preview; wait for any already-admitted move to commit before querying. Neither opening nor canceling issues sleep. New keys are handled only while the card owns focus; block underlying compass/queue/handoff keys. Card takes focus and traps Tab; keys1/2 select supplied modes, D toggles offered checkbox, Enter dispatches exactly once, Esc cancels. Return focus to the leg opener, or forced handoff row when that was the opener; if gone use existing lawful fallback. Refusal keeps the leg opener enabled and shows only server reason/cancel. Card displays current location/time, mode wake/note and selected per-member name/current-to-predicted reserve from server facts.

Mount cards in AppClient's existing `choices` chain with one modal owner, before the old sleep question. When a walking collapse opens handoff, `use-sleep-handoff.js` prepends the 全員紮營 row and invokes `openTravelCamp()` without removing/reordering existing rows relative to one another. Card cancel restores that handoff. This shortcut is limited to the walking forced-sleep context; do not alter unrelated sleep/handoff semantics.

Beat uses event-card width, a nighttime `forest_path` through existing artwork lifecycle with CSS fire/glow/embers until dedicated illustration exists, and anonymous silhouettes in the scene rather than standing actor portraits. Travel-style medallions form the arc, far side higher, with crescent for supplied sleepers. Animate bars from committed before to after for1.6s, then show server result/interruption and due-event lines. An early key/click only finishes animation; consume that input so it cannot also dismiss or move. A later Continue/Enter closes to the authoritative travel/actionable surface, without executing movement. Motion off sets final bars and result on the first frame. Dream result transfers to existing dream stage, no beat. Visual composition and prose are human-reviewed against the detailed design and `docs/design/wilderness-travel/{CampCard,CampfireCard}.vue`; no requirement pins copy/markup or illustration quality.

### 6. Observability and executable evidence

All new paths use named `world.observability` imports. Existing command/action boundaries emit cmd_in/cmd_done and action_commit with context identifiers; clock advancement retains clock_advance. Add one `camp_entry` info event after accepted entry and `camp_result` info event after final committed result, with `{char,room,tick,camp_id,mode,dream}` and result elapsed/interrupted reason when available. These operational events are distinct from the single structured travel event. Preview is read-only and requires no mutation event. Exceptions re-raise or emit facade diagnostics with `exc=`; never log credentials or unrestricted dream text. Patch caller bindings in event tests.

| Delta requirement | Discoverable Python test evidence to implement |
| --- | --- |
| sleep computes its own duration from gauge regen, capped at a configured maximum | `world.rules.tests.test_time_skip.CampingDawnTests.test_strict_dawn_cap_and_interrupt` plus retained existing tests |
| Sleep transports expose declared duration and recovery modes | `commands.tests.test_skip.CampingCommandTests.test_dawn_alias_camp_and_dream_parity` and action validators |
| Optional collaboration follows one accepted sleep result | `world.rules.tests.test_sleep_control.CampingConsentTests.test_entry_consent_and_rollback` |
| Dream collaboration consumes the committed elapsed result | `world.narrative.tests.test_dream_surface.CampingDreamTests.test_answered_receipt_and_departure` |
| Explicit dream answers have browser and text parity | `CampingCommandTests.test_dawn_alias_camp_and_dream_parity` and `CampingDreamTests` |
| Camp preview is read-only and authoritative | `world.rules.tests.test_camping.CampPreviewTests.test_preview_parity_and_no_writes` |
| Camp commits consent and continues accepted party sleep | `world.rules.tests.test_camping.CampActionTests.test_atomic_admission_and_continuation` |
| Camp results describe committed recovery once | `CampActionTests.test_result_interruption_dream_and_replay` |
| Camp card selects only server-supplied choices | `web.tests.browser.test_wilderness_camping.CampingTests.test_card_inputs_refusal_and_handoff` |
| Campfire beat is presentation-only and skippable | `CampingTests.test_dusk_camp_to_dawn_and_beat_controls` |

Use synthetic party/clock/policy fixtures and independently known expected intervals/reserves. Cover before/exactly/after dawn, midnight/cap, due events, hostile/combat/member/possession refusals, ordinary false/absent versus camp decline, forced/excluded-owner true rejection, entry/answer fault injection and stale revalidation rollback including caches. Check preview does not initialize missing surfaces. Include existing mixed sleepers/remote members and slower companion results. UI tests cover all keys, default, reopening, focus/refusal, early finish, motion off, dream replacement and forced handoff; use Vitest fake timers and discoverable Python browser assertions for traceability.

Obtain canonical IDs with `uv run --locked python -m tools.spec_traceability list`, including an equivalent merged spec tree for new IDs under the documented workflow. Never guess IDs. Preserve modified titles, so IDs remain stable. Before sync, associate new tests only to substantively established nearest existing requirements (party sleep, guarded dream answer, action dispatch or contextual HUD) and record the temporary mapping in implementation notes; remount new generated wilderness-camping IDs at sync. No skipped/placeholder tests or copy-pinning assertions. Every new server test module goes into exactly one `.github/evennia-shards.json` shard; every browser method into exactly one `.github/browser-shards.json` shard.

## Risks / Trade-offs

An outer transaction alone does not restore Evennia caches or prevent service-side continuation; explicit snapshots and deferred answer continuation are required. Preview cannot predict future interactive events, so result parity is conditional on unchanged uninterrupted state. Existing owner continuation can leave a companion asleep; report that truth instead of expanding scope into a new sleep policy. New dream-delayed result metadata belongs to current operation persistence and needs rollback/idempotence tests. Shared dispatcher/protocol/AppClient/manifests must be serialized using proposal matrix. Rules can begin independently of reveal; full browser integration waits for leg/log seams.

## Migration Plan

Pre-release clean cutover with no migration, compatibility layer or parallel transport. Rollback is source reversal with dependent browser integration. All listed implementation paths are permitted only for the described seam and its focused tests/docs/registry mirrors; unrelated refactors and all sibling artifacts are forbidden. This proposal itself edits only its change directory.

## One-day boundary

Reuse existing admission/continuation/answer machinery and existing UI frames. Suggested engineer-day allocation is2h dawn/shared planning and atomic consent,1.5h adapters/result publication,1.5h card/beat/handoff,2h focused deterministic/Vitest/browser evidence and1h docs/traceability/integration. There is no new model, generic recovery executor, art pipeline or travel layout in this slice.
