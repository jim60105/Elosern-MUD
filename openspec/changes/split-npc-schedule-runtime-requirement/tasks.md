# Tasks

## 1. Split the capability contract without behavior changes

- [x] 1.1 Remove the oversized clock-source requirement and apply the eight replacement requirements in the delta, keeping every current semantic clause and scenario, including the full exam-hold contract.
- [x] 1.2 Replace old canonical ID `npc-schedule-runtime::the-npc-schedules-clock-source-settles-due-schedule-entries` in substantive `covers_requirement` annotations with the appropriate replacement IDs, following the source-to-test mapping in `design.md`; verify assertions, ensure every replacement requirement has substantive coverage, and leave no stale IDs.

## 2. Run required gates

- [x] 2.1 Run `openspec validate --all --strict` and resolve every failure.
- [x] 2.2 Run `uv run --locked python -m tools.spec_traceability check` and resolve stale, unknown, or uncovered requirement associations.
- [x] 2.3 Run `uv run --locked python -m tools.contract_gate` and resolve every failure.