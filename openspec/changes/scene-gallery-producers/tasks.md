# Tasks

Test prefix: `uv run --locked --env-file=/tmp/mud-test.env evennia test --settings test_settings.py --keepdb`.

## 1. Producers

- [ ] 1.1 Apply design decisions 1–3 in `world/art/service.py`. Verify `rg -n "queue_ensure\(" world/art/service.py` shows no scene call.
- [ ] 1.2 Apply design decision 4 in `world/art/presenter.py` and update the scene presenter tests (no classic fallback; gallery-only generation state and retention). Verify the scene presenter test module passes under the prefix.
- [ ] 1.3 Update and add tests for the ADDED startup requirement scenarios (fresh database → one gallery request per synthetic archetype; carded scene → none) and the modified room-entry scenarios, retargeting decorators from the removed requirement. Verify the startup-sync and room-entry test modules pass under the prefix.

## 2. Gates

- [ ] 2.1 Run `uv run --locked python -m tools.spec_traceability check` and `uv run --locked python -m tools.contract_gate --change scene-gallery-producers`; both pass.
- [ ] 2.2 Run `openspec validate scene-gallery-producers --strict`; it passes.
