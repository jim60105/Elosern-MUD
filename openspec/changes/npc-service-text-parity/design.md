# Design

## Context

commands/guild.py::_GuildCommandBase currently resolves one room staff; commands/church.py::CmdChurchJoin similarly resolves one ChurchHost. The existing look/interaction conventions and docs/game/{commands,command-reference}.md are protected by tests/test_command_docs.py. P provides immutable contextual descriptors and T provides exact target validation.

## Goals / Non-Goals

Deliver `X` as one closed runnable engineer-day slice. Completed prerequisites are the exact depends-on lines in proposal.md.

No new gameplay services, balance, recruitment changes, save migration, legacy input conversion, capability bundles or player class system. The NPC-menu prototype proves layout/navigation only and never authorizes backend behavior. The approved source and archived history remain unchanged.

## Decisions

Extend existing `看 <NPC>` inspection with a services section from the same projection and inline reasons. Add `services <npc>` (alias `服務`) for discovery using the existing visible NPC resolver; it prints semantic key, label, reason and exact route guidance. The command does no service mutation. Preserve no-services vs unreadable text. For targeted execution, extend existing provider commands with `@<npc>` suffix (shop list/buy/sell, guild register/list/accept/turnin, combat exam); absence retains their established unambiguous room behavior, while an explicit suffix resolves only that visible host and uses T's core target validator. Exact syntax uses a terminal ` @#<positive dbid>` token to avoid collision with item/quest/member arguments. Church join cuts over to required `church join <npc>` because the command route pre-fills its explicit target. All parser changes and aliases are documented in both docs/game/commands.md and command-reference.md and tests/test_command_docs.py in this slice. NPC intent paths retain their existing trusted speaker and domain revalidation, never trust client enabled flags.

An obsolete route must re-project/resolve selected identity, current capability, binding, schedule, actor/control and topic/source/phase immediately before execution. No target substitution even if another provider is now available. General look/talk/invite/leave/possession/editor/delivery stay outside service projection. Existing invitations never become more permissive for newly configured services.


## Risks / Trade-offs

X follows P; U follows X so church command routing is real when advertised. Shares command docs/manifest and church/guild/commerce parser fixtures with R/T. No semantic dependency on unrelated authored prose or publication receiver internals.

The root-level batch contract in `../npc-examination-reception/batch.md` defines sequential cutover, active proposal amendment ownership, source conflicts and approved-scope traceability. New test files named below are proposed additions, not claims that they already exist. Existing focused labels were researched from current source.

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
