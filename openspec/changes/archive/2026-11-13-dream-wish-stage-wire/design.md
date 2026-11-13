# Design: the dream panel wire carries the wish stages

## Context

After `dream-wish-stages`:

- `DreamSession` records `stage` (`"conversing"` | `"finalized"`) through one
  additive migration; there is no data migration, because this batch ships
  with a reset database.
- `dream_session.progress()` / `choices()` and `begin_turn` /
  `settle_exchange` / `resume_saved_session` follow the stage;
  `finalize_session(session_id, owner_id, *, tick=0)` exists.
- `server/dream_service.py::act` gates `say`, `choose_thread`, `finalize`,
  `draft`, `confirm` and `awaken` by stage and stores a submitted finalized
  form as the working proposal through `surface.store_proposal`.
- `dream_surface.wish_state(actor)` returns `{"proposal", "changes",
  "thread_id", "thread_locked"}`; `dream_surface.dream_state(actor)` still
  publishes the schema-3 shape and derives `direction_parts` and
  `requirements` from the working proposal.
- `world/narrative/dream_proposal.py` bounds one proposal at
  `MAX_PROPOSAL_BYTES` and one change report at `MAX_CHANGES_BYTES`.
- The panel is schema 3 (`web/webclient/presentation/dream.py`,
  `protocol/constants.js`, `protocol/panels/dream.js`), validated with exact
  field lists; `validateDreamPanel` checks the literal schema number on
  `protocol/panels/dream.js` line 15.
- The production action roster lists `dream.choose_thread`, `dream.say`,
  `dream.draft`, `dream.confirm` and `dream.awaken`.

## Goals / Non-Goals

**Goals:** the stage fields in the read model, schema 4 on both sides with
its bounds and invariants, the `dream.finalize` web action, and the envelope
proof that the aggregate budgets fit.

**Non-Goals:** `DreamPanel.vue` behaviour (only its test and story fixtures
gain the new keys so they stay valid payloads); removing the schema-3 keys
(`dream-wish-change-report`); text commands (`dream-wish-text-commands`); any
server rule or stage decision (`dream-wish-stages`); the farewell;
`world/narrative/authoring.py`; `world/ai/`.

## Decisions

1. **Read model (`dream_state`).** Add keys: `stage` (`session.stage`),
   `proposal` (copy of the working proposal), `changes`, `thread_id`,
   `can_choose_thread` (open, conversing, not `thread_locked`, no pending
   response), `can_finalize` (open, conversing, no pending response),
   `can_edit` (open and finalized), `drafted` (`bool(session.draft_id)`).
   Change `can_confirm` to open and finalized. `can_input` follows
   `progress()`. Keep the schema-3 keys: `direction_parts` from
   `proposal["summary"]`, `requirements` from `proposal["requirements"]`,
   `requirement_version` and `draft_preferences` from the saved draft as
   today.

2. **Wire schema 4.** `DREAM_SCHEMA_VERSION = 4` in
   `web/webclient/presentation/dream.py` and `dream: 4` in
   `protocol/constants.js`. In `protocol/panels/dream.js` change the literal
   schema check on line 15 (`payload.schema_version !== 4`) and add the eight
   keys to the exact field list, then validate:
   - `stage` is `"conversing"` or `"finalized"`;
   - `proposal` has exactly `summary`, `themes`, `atmosphere`, `participants`,
     `emphasis`, `exclusions`, `requirements`; `summary` is a string of at
     most 2000 code points; each list has at most 32 non-blank strings of at
     most 200 code points; `requirements` passes the existing row check with
     at most 8 rows;
   - `changes` is `null` or has exactly `summary` (`null`, `"formed"` or
     `"changed"`), `lists` (exactly the five list keys, each exactly `added`
     and `removed`, arrays of strings within the list bounds) and
     `requirements` (exactly `added` and `removed`, arrays of rows within the
     row bounds);
   - `thread_id` is `null` or a string of 1..128 characters;
   - `can_choose_thread`, `can_finalize`, `can_edit`, `drafted` are booleans;
   - invariants (throw on violation): `can_input` requires `stage ===
     "conversing"`; `can_finalize` and `can_choose_thread` require `open`,
     `stage === "conversing"` and `!pending`; `can_edit` and `can_confirm`
     require `open` and `stage === "finalized"`; `open && remaining === 0`
     requires `stage === "finalized"`. The last one holds because
     `settle_exchange` sets the stage in the same save that records the
     sixth exchange.

3. **Envelope proof.** The proposal and report budgets of
   `dream-proposal-editing` are only useful if the largest legal panel still
   fits. Add one test to
   `web/webclient/presentation/tests/test_dream_artwork.py` (already in an
   Evennia shard) that builds a state with a proposal just under
   `MAX_PROPOSAL_BYTES` and a report just under `MAX_CHANGES_BYTES` (the
   helper adds synthetic list items until the next one would cross the
   bound), 32 thread choices with 160-code-point labels, and the prose keys
   at their 2048-code-point bound — once open (scene and dialogue) and once
   closed (ending) — and asserts `json_byte_size` of the presenter's payload
   against `MAX_CANONICAL_JSON_BYTES`. Lowering either budget is the fix when
   it fails; raising one requires the test to keep passing.

4. **Web action.** `dream_actions.validate("finalize", payload)` requires
   exactly `session_id` and `revision`. Register `dream.finalize`. Echo
   `"dream.finalize": function () { return "dream finalize"; }` with its test
   case and manifest id; add it to the registry enumeration test. Both roster
   scenarios of `specs/webclient-action-dispatch/spec.md` must hold: they now
   list `dream.finalize` and count six dream collaboration adapters.

5. **Fixtures and tests.**
   - `web/static/webclient/js/tests/protocol_dream.test.js`: schema 4 accept
     case and one reject case per rule of decision 2.
   - Fixtures only: add the eight keys (conversing, empty proposal,
     `changes: null`, `thread_id: null`, flags consistent with decision 2)
     to the `state()` fixture of `web/webclient-app/tests/dream.test.js`, to
     `fixture()` of `stories/World/DreamPanel.stories.js`, and change the
     literal schema `3` to `4` in both files. Do not change any component or
     assertion about component behaviour.
   - `web/webclient/presentation/tests/test_dream_artwork.py`: the version
     assertion follows the constant, plus decision 3's envelope test.
   - `world/narrative/tests/test_dream_surface.py`: assert the new keys and
     the stage flags in the existing state tests.

## Risks / Trade-offs

- [Schema bumped twice in the batch] → each bump is one constant on each side
  plus fixtures; keeping the old panel untouched until its replacement costs
  less than porting it twice.
- [The old browser panel cannot render a schema-4 state] → accepted and
  documented: stages are applied in one batch and the panel is replaced two
  stages later; no release happens in between.
- [The envelope test is a fixture rather than a proof] → it recomputes the
  canonical bytes of the real presenter output, so a budget change that does
  not fit fails it.
