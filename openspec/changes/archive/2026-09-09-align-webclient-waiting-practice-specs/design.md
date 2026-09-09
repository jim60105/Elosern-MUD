# Design: Align waiting and practice specifications with the shipped WebClient

## Context

The branch already ships the behavior; this change only rewrites specification text so the
main specs describe what exists and what the tests already prove. The design questions are
therefore about *specification* decisions, not implementation.

## Decisions

### D1 — Reconcile the exhaustive allowlist fully, not partially

`webclient-action-dispatch` states the registry list as an exhaustive "exactly" enumeration, so a
delta cannot add only `explore.practice` without leaving the enumeration false: the shipped registry
carries 40 action IDs while the master spec lists 34, silently missing
`account.character.create`, `account.character.switch`, `creation.roll_name`, `guild.quest_track`
(pre-existing `master` drift) and `explore.deliver` (also pre-existing), plus `explore.practice`
(this branch). The amended body and scenario list all 40 IDs, equal to the enumeration pinned by
`test_dispatcher.py::test_production_registry_exposes_only_specified_adapters`, which is the
executable authority. Rationale: a half-fixed exhaustive list is still false; the group-by-family
sentence structure is preserved so the delta stays reviewable.

### D2 — `explore.practice` is specified under `webclient-exploration-menu`

The action is an exploration action riding the unchanged dispatcher, beside `explore.wait`.
`webclient-action-dispatch` owns the registry/ABI contract only. The new requirement pins the
exact `{skill, seconds}` payload, the stable preflight codes `PRACTICE_SKILL_UNKNOWN` /
`PRACTICE_SKILL_CAPPED` with zero clock advance and no surviving booking, the commit-time
revalidation (hence `skill` joins the tampered-field enumeration), and the whole-hour settlement
reuse of the existing clock stage. It deliberately re-states no rule that
`time-skip-commands` / `settlement-stage-order` already own — it names the graphical entry into
them.

### D3 — The hours conversion is a unit conversion, not "client-side clock arithmetic"

The exploration-menu clause "no client-side clock arithmetic" targets clock *derivation* (the
client must never predict the resulting world time). Converting a user-entered duration unit
(hours → whole seconds, `Math.round(hours * 3600)`) at the presentation boundary is the same kind
of unit entry the seconds form always was. The amended sentence says this explicitly so the
clause remains coherent, and the new waiting-surface requirement pins the bounds
(≥ 1 s, ≤ 12 h = 43,200 s, fractional hours allowed) and the single
`explore.wait {seconds}` dispatch.

### D4 — The three-operation selector is a client menu composition; the server payload contract is unchanged

The graphical surface renders dawn / sleep / custom-hours only. The `explore.wait` payload still
accepts all four dayparts — suggestion cards and the text commands still use them — so the delta
edits the *wait menu sentence* and adds the *surface* requirement, and does not touch
"explore.wait obeys the shared skip safety and clock API".

### D5 — Practice lives in the skill drawer, and the footer carve-out is written down

The implementation hides the cast-syntax footer and swaps the drawer title to 修煉 only while the
practice sub-screen replaces the book body. The footer clause "always" is amended to
"whenever the drawer presents the skill book itself", which keeps the existing scenario passing
verbatim and makes the body true. A new `contextual-hud` requirement specifies the practice
sub-screen surface itself (payload-gated affordance, single dispatch, server-authored feedback,
no client-computed eligibility or reward).

### D6 — Traceability follows the established sync-then-annotate pattern

Every new/renamed requirement needs a `@covers_requirement` annotation once its ID enters the
index at sync (the pattern documented in `tests/test_vue_breakdown_evidence.py`). The four
existing practice action tests (`test_exploration_actions.py`, declared-growth, unknown/capped/
unsafe, ambiguous payload, rollback) are the substantive evidence for the action requirement; the
waiting-surface and practice-screen requirements are evidenced by the vitest suites through the
Python evidence-runner pattern (`tests/test_node_suite_evidence.py` precedent). Annotating before
sync would create a dangling annotation, so tasks sequence it after the delta lands in
`openspec/specs/`.

## Risks / trade-offs

- Restating 40 IDs in body + scenario duplicates the dispatcher test's list; that is the
  requirement's existing style and the test is the enforcement — accepted.
- Copying the two long `exploration-menu` requirement blocks verbatim into MODIFIED deltas risks
  transcription drift; mitigated by diffing the delta blocks against the main spec text after
  writing (`tasks.md` step 1).
