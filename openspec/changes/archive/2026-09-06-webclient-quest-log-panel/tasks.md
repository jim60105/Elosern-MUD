# Tasks: webclient-quest-log-panel

## 1. Presenter

- [x] 1.1 New `web/webclient/presentation/quest_log.py` building the version-1 available form from
  the shared strict reader in quest-log order, capped at `MAX_QUEST_ROWS` imported from the services
  panel bounds so the two cannot drift.
- [x] 1.2 Row fields: identity and progress from the record; `stage_total` from the definition;
  `objective_quantity` from the current stage objective; prose from `describe_objective`,
  `describe_deadline`, `describe_quest_detail`; `tracked` from the record.
- [x] 1.3 `issuer`: parse the record's stored issuer key for `kind` and `key`; derive `label` from
  the guild branch registry for a `guild:` key and from the resolved commissioner for an `npc:` key,
  truncated to the shared display-name bound. A label that cannot be resolved falls back to the key's
  remainder rather than inventing a name. The validator re-parses the key with the canonical grammar
  and rejects a `kind` that contradicts the namespace.
- [x] 1.4 `settlement` and `reward_line` from `resolve_issuance`; an unresolvable issuance yields
  `reward_line` null and `settlement` null (null together or present together, enforced by both
  validators), and the row still renders every other field.
  `reward_line` uses `describe_reward`.
- [x] 1.5 `track`: the `guild.quest_track` descriptor, always enabled — the action is
  host-independent by contract.
- [x] 1.6 Host independence: assert by construction that no service host, registration, schedule, or
  room is consulted.

## 2. Validator

- [x] 2.1 Exact-shape validator: the panel key set, the row key set, per-field code-point bounds, the
  bounded `state` vocabulary and the nullable bounded `settlement` vocabulary, the settlement/
  reward_line null-pair coherence, the issuer-key grammar with kind/namespace coherence,
  non-negative integers, the twelve-row cap, and unique `quest_id` values.
- [x] 2.2 Close with the shared `MAX_CANONICAL_JSON_BYTES` envelope guard, failing closed.
- [x] 2.3 Reject lone surrogates in every string field, following the party and objectives panel
  precedent.

## 3. Degradation

- [x] 3.1 Any `QuestDataError` from the strict reader raises `PanelUnavailableError` so the registry
  emits the common unavailable form; no partial row list, no skipped entry, no rewrite of the stored
  log.

## 4. Registration and push

- [x] 4.1 Register the panel in `web/webclient/presentation/registry.py` with the common unavailable
  reason.
- [x] 4.2 Mark dirty and push on the existing quest-log mutation seams — acceptance, abandonment,
  tracking, stage advance, completion, deadline settlement, and the trade surfaces whose ACQUIRE
  settlement can advance or complete a quest — for exploration AND combat puppets.

## 5. Client mirror

- [x] 5.1 Add the `quest_log` validator to `web/static/webclient/js/elosern/protocol.js` mirroring
  the exact Python bounds.
- [x] 5.2 Add the panel entry to the `webclient-vue-application` protocol mirror table so a stale
  client rejects rather than renders it.
- [x] 5.3 Extend the dual-direction parity test to cover the new panel.

## 6. Tests

- [x] 6.1 Shape tests: two-row serialization; empty log is available with `rows: []`; exact key sets;
  every bound.
- [x] 6.2 Read-only test: building twice leaves quest log, tracking, wallet, and inventory unchanged
  and both serializations identical.
- [x] 6.3 Host-independence tests: a wilderness room with no NPC still yields every row; an
  `npc`-issued record appears with kind `npc` and settlement `auto`.
- [x] 6.4 Prose-parity tests: the objective and deadline lines are byte-identical to the `objectives`
  panel for the same tracked record; the objective summary, deadline, and detail are byte-identical
  to the `services` guild quest row for the same record with a clerk present.
- [x] 6.5 Unresolvable-issuance tests: `reward_line` is null, `settlement` is null, the row still
  renders, and no copper, item, or merit figure appears.
- [x] 6.6 Degradation tests: one malformed entry hides the whole panel; `db.quest_log` is unchanged
  afterwards.
- [x] 6.7 Push tests: completing a quest mid-combat pushes the panel; `guild.quest_track` pushes it.
- [x] 6.8 Client-mirror rejection tests: extra row field, thirteenth row, unknown `state`, unknown
  `settlement`.
- [x] 6.9 Update `.github/evennia-shards.json` in the same change. `covers_requirement`
  annotations against the new requirement IDs land at the change's archive/sync commit
  (objectives-panel P1 precedent): the traceability check rejects IDs the current-contract
  index does not know yet, and the annotation must never precede the synced spec.
- [x] 6.10 Run the observability lint plus the focused presentation, protocol-parity, and quest test
  modules in the same batch.
