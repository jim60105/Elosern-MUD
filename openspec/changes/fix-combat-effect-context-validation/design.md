## Context

`_skill_wide_failure` (`world/rules/action_preview.py:72-104`) checks ownership, cost, blocking buffs, effect-prefix registration, and time metadata only; `ActionResolver.preflight` (`world/rules/action.py:986-1011`) repeats the same prefix-only check. The handlers `_handle_set_disguise` (`action.py:273-293`) and `_handle_confer_skill_partial` (`action.py:243-270`) call `_require_context` (`action.py:233-240`) only during effect resolution — after `roll_initiative`. The combat session context (`combat_session.py:397-415`) supplies only `battlefield` (+`nonlethal` for exams). The out-of-combat `CmdCast` supplies disguise context (`commands/action.py:93-113`).

## Goals / Non-Goals

**Goals:**
- Context availability decided before initiative, in preview and preflight.
- Menu honesty for skills the session cannot serve.

**Non-Goals:**
- Adding new player-facing inputs for dominion_art's three required keys (no combat caller provides them; the skill stays context-less in combat until a caller exists).
- Changing what the handlers do once context exists.

## Decisions

**D1 — Declared context requirements on handler registration.** Each handler registration gains `requires_event_context: frozenset[str]`; `_require_context` at resolution time uses the same declaration, keeping one source of truth.

**D2 — Preflight/preview consult the declaration.** `_skill_wide_failure` and `preflight` check `requires_event_context <= event_context.keys()`; a miss rejects with the existing `EFFECT_RESOLUTION_FAILED`-family reason (a new stable `MISSING_EFFECT_CONTEXT` code for clarity), before any round cost.

**D3 — Menu availability derives from the same check.** The combat menu preview path marks the skill unavailable when the context check fails, so UI and preflight agree.

**D4 — Registration API requires an explicit declaration on every handler.** `register_effect_handler` SHALL require a `requires_event_context` argument (an explicit `frozenset`, possibly empty) so no handler can silently skip the contract; a registry-completeness test asserts every registered handler declares the field.

## Risks / Trade-offs

- **Handler declaration drift**: `_require_context` and the registration share the declaration (D1), eliminating drift.
- **Out-of-combat path**: CmdCast's context construction already satisfies the declarations; unchanged behavior is verified by test.
- **Landing order**: applies to `submit_player_action`/preflight seams; lands after `fix-combat-settlement-recovery` where it touches the round path.
