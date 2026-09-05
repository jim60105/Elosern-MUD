# Tasks: service-anchor-presentation-silence

## 1. The silence predicate

- [ ] 1.1 `world/rules/service_gate.py`: add `schedule_silenced(npc) -> bool` — true iff the npc
  carries any service component with `service_binding == "place"` AND `npc.db.party_member` is
  non-null AND `npc.location` is not the component's resolved anchor room; docstring names the
  possession change as the future second trigger (single OR-site).
- [ ] 1.2 `world/rules/npc_schedules.py::settle_npc_schedules`: at the per-NPC loop head, before
  due-entry iteration, `if schedule_silenced(npc): continue` with one `log_debug` event
  (`context`: npc id + service), reusing the module's facade imports.

## 2. Disabled navigation entry

- [ ] 2.1 `web/webclient/presentation/affordances.py`: where guild/shop navigation entries are
  emitted for a local host, call `service_available(actor, host, component)`; `allowed` →
  unchanged entry; `off_anchor` / `malformed_binding` → `enabled: False` +
  `disabled_reason.message` from the gate's registry constant; `remote` unreachable at that site
  (host is by construction local) — assert-guard it.
- [ ] 2.2 Confirm both presenters (exploration panel + context_actions) pick the change up
  through the shared emitter without edits; the Vue side consumes the committed view unchanged.

## 3. Tests

- [ ] 3.1 Predicate matrix (pure, in `world/rules/tests/test_service_gate.py`): place-bound +
  party-member + off-room → True; any leg false (person-bound, unbound, at-anchor, no component)
  → False.
- [ ] 3.2 Settlement tests (`EvenniaTestCase`, existing schedule test module): traveling
  place-bound clerk settles nothing across a full authored shift; return-to-anchor resumes;
  guard/resident byte-identical control assertions.
- [ ] 3.3 Affordance tests (`web/webclient/presentation/tests/`): off-anchor traveling merchant →
  disabled shop entry with the fixed message (both presenter consumers); anchor room with no
  host → no shop entry (darkness pin); at-anchor host unchanged enabled; malformed binding →
  disabled.
- [ ] 3.4 `covers_requirement` annotations for both delta requirements; shard manifest untouched
  unless a new module appears (3.1 extends an existing one — verify).

## 4. Verification

- [ ] 4.1 `MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb
  world web.webclient` focused labels; `tools.spec_traceability check`.
- [ ] 4.2 `uv run --locked python -m tools.observability_lint check`; `compileall -q world web`.
- [ ] 4.3 `pnpm test` untouched-path sanity is NOT required (no Vue component change) — note it
  in the handoff; the committed-view contract is the Python-side test.
