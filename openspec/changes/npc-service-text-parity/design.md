# Design

## Context

commands/guild.py::_GuildCommandBase currently resolves one room staff; commands/church.py::CmdChurchJoin similarly resolves one ChurchHost. The existing look/interaction conventions and docs/game/{commands,command-reference}.md are protected by tests/test_command_docs.py. P provides immutable contextual descriptors and T provides exact target validation.

## Goals / Non-Goals

Deliver `X` as one closed runnable engineer-day slice. Completed prerequisites are the exact depends-on lines in proposal.md.

No new gameplay services, balance, recruitment changes, save migration, legacy input conversion, capability bundles or player class system. The NPC-menu prototype proves layout/navigation only and never authorizes backend behavior. The approved source and archived history remain unchanged.

## Decisions

Extend 看 <NPC> and new services <npc> (alias 服務) with the same labels/keys/reasons and none/unreadable distinction, without mutation. Add terminal ` @#<positive dbid>` to CmdShopStock (`shop stock`, aliases `shop 庫存`, `商店庫存`), CmdBuy (`buy`, aliases `購買`, `買`, `shop buy`) and CmdSell in commands/economy.py, and CmdGuildExam (`guild exam`, aliases `guild 考核`, `公會考核`) in commands/combat.py. Apply the same suffix to CmdGuildRegister/List/Accept/TurnIn/Abandon in commands/guild.py; ordinary abandonment retains its selected-staff gate, while private escort abandonment and tracking stay host-free. Strip the terminal target before existing quantity, member `=` or rank parsing. Preserve every current alias; add no shop list or combat exam alias. Explicit targets use require_service_target with no fallback; omission keeps current room-ambiguity behavior. P already completed church join <npc>. Update both command references and the curated manifest together. NPC intents keep their trusted speaker and existing deterministic revalidation.

An obsolete route must re-project/resolve selected identity, current capability, binding, schedule, actor/control and topic/source/phase immediately before execution. No target substitution even if another provider is now available. General look/talk/invite/leave/possession/editor/delivery stay outside service projection. Existing invitations never become more permissive for newly configured services.


## Risks / Trade-offs

X follows P; U follows X so church command routing is real when advertised. Shares command docs/manifest and church/guild/commerce parser fixtures with R/T. No semantic dependency on unrelated authored prose or publication receiver internals.

The batch contract in section 11 of `docs/superpowers/specs/2026-10-25-npc-capabilities-and-services-design.md` defines sequential cutover, active proposal amendment ownership, source conflicts and approved-scope traceability. New test files named below are proposed additions, not claims that they already exist. Existing focused labels were researched from current source.

## Worker execution contract

This is planning only. At apply time complete this slice within one engineer-day, using the exact interfaces below. Each checkbox includes its focused regression evidence and documentation. Do not add compatibility exports, legacy input readers, migrations, replacement professions, gameplay services, or a new persistent service registry. Deterministic owners retain every mutation; AI and UI propose/select only. Preserve player titles, ranks, age bounds, literal bases, scene roles/tiers, recruitment and possession eligibility, schedules and commerce arithmetic.

All paths are relative to the repository root. Reuse current test helpers and behavioral traceability decorators. Update `.github/evennia-shards.json` and `.github/browser-shards.json` only for changed test ownership; serialize manifest edits. Run focused checks once after the slice is complete, followed by `uv run --locked python -m tools.contract_gate` and strict validation of its delta. Use the project's test environment only during apply. Full browser/traceability suites remain CI-owned. No implementation checks were exercised during planning.

## Focused verification at implementation handoff

```text
uv run --locked --env-file=.env.test evennia test --settings test_settings.py --keepdb commands.tests.test_npc_services commands.tests.test_guild_economy_commands commands.tests.test_church_commands
uv run --locked python -m unittest tests.test_command_docs
uv run --locked python -m tools.contract_gate
openspec validate npc-service-text-parity --strict
```

If this slice changes logging paths, also run `uv run --locked python -m tools.observability_lint check` with its focused event tests in the same final batch. Do not run the full browser or full traceability-evidence suite locally.
