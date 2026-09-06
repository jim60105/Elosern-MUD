# Tasks: webclient-quest-log-panel

## 1. Presenter

- [ ] 1.1 New `web/webclient/presentation/quest_log.py` building the version-1 available form from
  the shared strict reader in quest-log order, capped at `MAX_QUEST_ROWS` imported from the services
  panel bounds so the two cannot drift.
- [ ] 1.2 Row fields: identity and progress from the record; `stage_total` from the definition;
  `objective_quantity` from the current stage objective; prose from `describe_objective`,
  `describe_deadline`, `describe_quest_detail`; `tracked` from the record.
- [ ] 1.3 `issuer`: parse the record's stored issuer key for `kind` and `key`; derive `label` from
  the guild branch registry for a `guild:` key and from the resolved commissioner for an `npc:` key,
  truncated to the shared display-name bound. A label that cannot be resolved falls back to the key's
  remainder rather than inventing a name.
- [ ] 1.4 `settlement` and `reward_line` from `resolve_issuance`; an unresolvable issuance yields
  `reward_line` null and the row still renders every other field. `reward_line` uses
  `describe_reward`.
- [ ] 1.5 `track`: the `guild.quest_track` descriptor, always enabled — the action is
  host-independent by contract.
- [ ] 1.6 Host independence: assert by construction that no service host, registration, schedule, or
  room is consulted.

## 2. Validator

- [ ] 2.1 Exact-shape validator: the panel key set, the row key set, per-field code-point bounds, the
  bounded `state` and `settlement` vocabularies, non-negative integers, the twelve-row cap, and
  unique `quest_id` values.
- [ ] 2.2 Close with the shared `MAX_CANONICAL_JSON_BYTES` envelope guard, failing closed.
- [ ] 2.3 Reject lone surrogates in every string field, following the party and objectives panel
  precedent.

## 3. Degradation

- [ ] 3.1 Any `QuestDataError` from the strict reader raises `PanelUnavailableError` so the registry
  emits the common unavailable form; no partial row list, no skipped entry, no rewrite of the stored
  log.

## 4. Registration and push

- [ ] 4.1 Register the panel in `web/webclient/presentation/registry.py` with the common unavailable
  reason.
- [ ] 4.2 Mark dirty and push on the existing quest-log mutation seams — acceptance, abandonment,
  tracking, stage advance, completion, deadline settlement — for exploration AND combat puppets.

## 5. Client mirror

- [ ] 5.1 Add the `quest_log` validator to `web/static/webclient/js/elosern/protocol.js` mirroring
  the exact Python bounds.
- [ ] 5.2 Add the panel entry to the `webclient-vue-application` protocol mirror table so a stale
  client rejects rather than renders it.
- [ ] 5.3 Extend the dual-direction parity test to cover the new panel.

## 6. Tests

- [ ] 6.1 Shape tests: two-row serialization; empty log is available with `rows: []`; exact key sets;
  every bound.
- [ ] 6.2 Read-only test: building twice leaves quest log, tracking, wallet, and inventory unchanged
  and both serializations identical.
- [ ] 6.3 Host-independence tests: a wilderness room with no NPC still yields every row; an
  `npc`-issued record appears with kind `npc` and settlement `auto`.
- [ ] 6.4 Prose-parity tests: the objective and deadline lines are byte-identical to the `objectives`
  panel for the same tracked record; the objective summary, deadline, and detail are byte-identical
  to the `services` guild quest row for the same record with a clerk present.
- [ ] 6.5 Unresolvable-issuance tests: `reward_line` is null, the row still renders, and no copper,
  item, or merit figure appears.
- [ ] 6.6 Degradation tests: one malformed entry hides the whole panel; `db.quest_log` is unchanged
  afterwards.
- [ ] 6.7 Push tests: completing a quest mid-combat pushes the panel; `guild.quest_track` pushes it.
- [ ] 6.8 Client-mirror rejection tests: extra row field, thirteenth row, unknown `state`, unknown
  `settlement`.
- [ ] 6.9 Annotate with `covers_requirement` against the new requirement IDs; update
  `.github/evennia-shards.json` in the same change.
- [ ] 6.10 Run the observability lint plus the focused presentation, protocol-parity, and quest test
  modules in the same batch.
