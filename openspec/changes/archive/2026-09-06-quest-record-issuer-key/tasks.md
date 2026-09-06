# Tasks: quest-record-issuer-key

## 1. Record field

- [x] 1.1 Add `issuer_key: str` to the frozen `QuestRecord` dataclass in `world/quests/runtime.py`
  and to `_RECORD_FIELDS`. It is required — do NOT add it to the optional-with-default set that
  holds `tracked`.
- [x] 1.2 `to_storage` writes the field; `from_storage` requires it, validates it through the shared
  `parse_issuer_key`, and raises `QuestDataError` on a missing, non-string, empty, or malformed
  value without rewriting or coercing the stored entry.
- [x] 1.3 Extend `validate_record_runtime` with the shared grammar check: a malformed issuer key is
  a `QuestDataError` like other corruption, while a well-formed key whose issuance was unregistered
  after acceptance stays readable (design D2 — no registry lookup, no reader crash).

## 2. Acceptance path

- [x] 2.1 `accept_quest(actor, definition_key, issuer_key)`: validate the definition, the duplicate
  active record, and `resolve_issuance(definition_key, issuer_key)` is not `None`, all before any
  write; carry the key into the created record.
- [x] 2.2 `accept_guild_offer` derives the key with the shared `guild_issuer_key(branch_key)`
  constructor from the resolved `GuildStaff` host's `branch_key` and passes it through. No string
  concatenation at the call site.
- [x] 2.3 The `offer_quest` applier in `world/rules/npc_intents.py` passes the same guild-derived
  key. Widening the gate to non-guild speakers is explicitly NOT part of this change.
- [x] 2.4 Extend the `quest_transition` boundary event context (the acceptance event among all
  transitions) with the `issuer` key per the observability catalog.

## 3. Call-site and fixture updates

- [x] 3.1 Update the direct `QuestRecord(...)` construction sites:
  `world/quests/tests/test_describe.py`, `world/quests/tests/test_quests_observability.py`,
  `world/rules/tests/test_service_view.py` (two sites), `world/rules/tests/test_titles.py`,
  `web/webclient/presentation/tests/test_objectives_panel.py`.
- [x] 3.2 Update the shared quest fixtures (`world/quests/tests/_fixtures.py`) so the new `accept()`
  helper registers the shared `npc:test_commission` commission and every helper-built record and
  helper acceptance supplies a resolvable issuer key; `QuestRegistryIsolation` and
  `RegistryIsolationMixin` snapshot/restore `QUEST_ISSUANCE_REGISTRY`.
- [x] 3.3 Sweep for remaining `accept_quest(` call sites across `commands/`, `world/`, `web/`, and
  `server/` and update each: issuer-agnostic tests ride the fixture helper; guild-flavored flows
  pass `guild_issuer_key(...)` for the offer their fixtures register.

## 4. Tests

- [x] 4.1 Round-trip test: a record with each issuer-key form serializes, JSON-encodes, and
  reconstructs with the field intact.
- [x] 4.2 Strict-reader tests: missing key rejects; non-string rejects; empty rejects; malformed
  grammar rejects; none of these rewrite the stored entry.
- [x] 4.3 Acceptance tests: acceptance under an unregistered issuance raises and leaves the log
  unchanged; acceptance under a registered issuance stores the key; the same definition held twice
  under different issuers keeps distinct keys.
- [x] 4.4 Guild board test: an accepted board offer's record carries `guild:<branch_key>` for the
  resolved host's branch, and two branches offering one definition produce distinguishable records.
- [x] 4.5 Annotate tests with `covers_requirement` against the modified `quest-lifecycle` and
  `guild-quest-board` requirement IDs.
- [x] 4.6 Run the observability lint plus the focused quest, guild, service-view, objectives, and
  title test modules in the same batch.

## 5. Documentation

- [x] 5.1 Note in the change that existing development quest logs are unreadable after this lands
  and must be recreated; no migration is written (the project has no released users).
