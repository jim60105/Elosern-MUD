# Design: Party management help content and assembled acceptance

## Context

See proposal.md. `HelpOverlay.vue` renders authored help sections; the deletion changes removed components one by one; the 2026-10-15 batch used a final runtime-acceptance change with real browser and text evidence.

## Goals / Non-Goals

**Goals:** help content for every rule text removed from the windows; zero residue; recorded assembled evidence across rules, protocol and client.

**Non-Goals:** new behaviour; fixing defects inside this change (they go back to the owning change).

## Decisions

- **Help content** is static Traditional Chinese authored text grouped under 隊伍; it states rules, never live state.
- **Residue sweep** is a scripted search (`rg` over `web/webclient-app`, stories, specs, tests) recorded in the task evidence; the manifest is compared with the registered stories by the coverage gate.
- **Journey** uses `agent-browser` against a local server with synthetic companions 艾拉 and 卡恩 (fixture setup through the GM console verbs only), headless, screenshots saved to the scratch area, never committed.
- **Text paths** run through the Telnet/command test harness and a short live session transcript.

## Risks / Trade-offs

- [Journey flakiness] → Each step asserts committed panel state before the next.

## Migration Plan

Pre-release; revert the implementation commit.

## Verification and documentation ownership

Vitest for the help section; Storybook build and showcase coverage; one managed browser method for the help party section registered in `.github/browser-shards.json`; the agent-browser journey and text transcript recorded in the task notes; `tests.test_evennia_test_optimization_contract`, `tests.test_webclient_frozen_contract`, `tests/test_command_docs.py`, `uv run --locked python -m tools.contract_gate`. Full managed browser execution and traceability evidence remain CI-owned.
