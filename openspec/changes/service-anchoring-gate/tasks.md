# Tasks: service-anchoring-gate

## 1. The resolver

- [ ] 1.1 `world/rules/service_gate.py`: frozen `ServiceVerdict(allowed: bool, reason: str |
  None)`; `REASON_REMOTE` / `REASON_OFF_ANCHOR` / `REASON_MALFORMED_BINDING` constants with the
  fixed zh-TW messages (registry-owned); `service_available(actor, host, component)` in the rule
  order of the delta (co-location → binding → anchor resolution via lazy room lookup); malformed
  or missing stored binding fails closed with a per-host `ndb` debounced `log_warn` through
  `world.observability`.
- [ ] 1.2 Module docstring: read-only contract (writes nothing), per-component semantics, and
  the "new professions wire in here" note.

## 2. Persistence through assembly

- [ ] 2.1 `world/rules/profession_assembly.py`: after attaching each component, persist
  `service_binding` from the row's `default_binding`, and for `place` rows persist
  `anchor_room_id` — extend the helper's signature with an `anchor_room` parameter (the sync
  passes its resolved room; the import loader passes the record's authored anchor room resolved
  by tag inside the record's transaction). Invalid combinations are validation-time rejects, but
  the helper re-asserts and raises `ProfessionAssemblyError` on any `place`-without-room.
- [ ] 2.2 `world/imports/schema.py`: optional `anchor_room` (room tag string) on character
  records; reject `person`-bound + anchor and `place`-bound + missing-anchor for any component the
  record assembles (validator layer, batch-rejection).
- [ ] 2.3 `world/rules/guild_config.py`: roster rows for `place` professions must resolve to
  `anchor_room` (they already carry `anchor_room` — assert binding consistency against the
  profession row's `default_binding`).
- [ ] 2.4 `world/rules/guild_economy.py::_sync_service_host`: reuse path re-converges
  `service_binding` / `anchor_room_id` from the roster each sync (idempotent config
  convergence — docstring line naming why this is not a runtime identity write).

## 3. Gate rewiring

- [ ] 3.1 `world/rules/economy.py::_require_local_merchant`: after the existing unambiguous-host
  resolution, consult `service_available`; `remote` maps to today's `REMOTE_MERCHANT`, the other
  two reasons map to a new `TradeReason` value carrying the gate's registry message (extend the
  trade-reason table + fixed-message dict).
- [ ] 3.2 Guild registration access path (`world/rules/guild.py` registration command/API):
  consult the resolver for the resolved staff component with the same reason mapping.
- [ ] 3.3 Exam authority check (`start_guild_exam`): consult the resolver for the examiner's
  `GuildExaminer` component; `remote` keeps today's refusal lineage, `off_anchor` refuses with the
  gate's fixed message, `malformed_binding` fails closed — all before eligibility, zero writes.
  (Registration/exam suites pin behavior; the guild-rank-exams MODIFIED delta owns the wording.)

## 4. Tests

- [ ] 4.1 Pure resolver matrix (`world/rules/tests/test_service_gate.py`, new module → register
  in `.github/evennia-shards.json`): every (co-location × binding × anchor-state) combination →
  exact verdict; debounce behavior; fail-closed rows.
- [ ] 4.2 Assembly persistence tests: roster-synced hosts carry binding+anchor; import record
  with `person`-bound test profession serves anywhere; invalid authored combinations rejected at
  config/schema; binding/anchor fields survive a save/reload round-trip (reload evidence, not a
  framework assumption).
- [ ] 4.3 Gate tests: shop list/buy/sell against an off-anchor merchant (fixed message, zero
  state); registration against an off-anchor clerk; exam start refused; existing remote-lineage
  scenarios pass unmodified; `person`-bound host trades anywhere (test profession).
- [ ] 4.4 Sync convergence: a component missing the attributes gains them on the next sync
  without rename/retitle touching identity fields.
- [ ] 4.5 `covers_requirement` annotations for all five delta requirements.

## 5. Verification

- [ ] 5.1 `MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb
  world commands` focused; `tools.spec_traceability check`.
- [ ] 5.2 All pre-existing economy/guild/exam suites green unmodified (no-shipped-config-drift
  proof); `tools.observability_lint check`; `compileall -q world commands`.
