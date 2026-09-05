# Design: possession-validator-lockstep

## Context

Three validator surfaces between the affordance vocabulary and the browser were never widened
when `explore.possess` / `explore.possess_release` joined the vocabulary. Each fails differently
(presenter exception → whole-panel degrade; bare-dict `KeyError` → panel unavailable; client
mirror enum → accepted-bytes rejected), which is why unit tests over the vocabulary/banner passed.
The fix is registration + total-function hardening; no new architecture, no relocations.

## D-LS1: The exploration panel's action enumeration is derived, not duplicated

`web/webclient/presentation/exploration.py` keeps a private `ACTION_IDS` tuple (:83-89) — the
drift source. Replace it with a reference to the shared vocabulary's `ACTION_CODE_ALLOWLIST`
(`affordances.py` already owns it as a frozen tuple). Deriving from the single source means the
next vocabulary addition cannot re-poison the panel; the extra codes (`explore.move/look/wait`)
in the panel's accepted set are inert because the presenter only ever emits target-scoped codes
in `interact`. A test asserts the equality (`exploration.ACTION_IDS is
affordances.ACTION_CODE_ALLOWLIST` or set-equal if the import shape differs).

## D-LS2: Possession payload validators register in place — no relocation

`options.py` already imports seven payload validators (`validate_move_payload` …
`validate_wait_payload`) plus `ExplorationActionError` from
`web.webclient.actions.exploration_actions` (options.py:20-29) — that edge exists and runs in
production today. The two possession validators (`validate_possess_payload`,
`validate_possess_release_payload`, exploration_actions.py:233-249) join that same import list and
register in `_ACTION_PAYLOAD_VALIDATORS`. Moving the functions INTO `options.py` and re-exporting
them back from `exploration_actions.py` would create a genuine `options ⇄ exploration_actions`
cycle (options is half-initialized when the re-export runs) — explicitly rejected. Both stay in
their current module; registry and tests keep their import paths untouched.

## D-LS3: The validator table lookup becomes a structured rejection, plus a totality pin

`options.py:88`'s bare `validators[action_id]` becomes `dict.get` + a
`ProtocolValidationError`-shaped structured rejection naming the code (the panel/presenter layer
already degrades correctly for a genuinely invalid affordance — what must never happen is a
Python `KeyError` escaping into a presenter except-clause or a suggestion validator). Structured
rejection alone is NOT the fix: a test asserts the table's registered keys are a superset of
`ACTION_CODE_ALLOWLIST`, so totality over the vocabulary is pinned and the rejection only ever
fires for out-of-vocabulary garbage.

## D-LS4: UMD mirror re-locks to the server tables; Vue is audited, not assumed

`web/static/webclient/js/elosern/protocol.js` gains:
- `CONTEXT_ACTIONS_ACTION_CODES` (:544) += `explore.possess`, `explore.possess_release`;
- `EXPLORATION_ACTION_IDS` (:3090) += the same two;
- `validateContextActionsAffordanceParams` (:1093) switch branches mirroring the Python
  validators EXACTLY: BOTH codes accept exactly `{"npc_id": <positive integer ≤ MAX_SAFE_INTEGER>}`
  (the shape exploration_actions.py:233-249 accepts and affordances.py emits at :434-450 and
  :733-736), rejecting missing/extra keys, non-integers, and out-of-range values.

Parity is pinned by an extended Node test carrying the server table as an inline fixture — honest
label: a **JS contract pin**, not automatic cross-language parity (the dependency-free Node gate
cannot read the Python tuple; the fixture gains a "update whenever `ACTION_CODE_ALLOWLIST`
changes" review marker, and the Python-side superset test from D-LS3 remains the vocabulary-side
guard). Vectors drive REAL emitted entries — the fixture feeds a possess/release affordance
through `validateContextActionsPanel`/`validateContextActionsAffordanceParams`, not just the
exported enumeration arrays — covering the canonical `npc_id` shape and its malformed variants.
The Vue app is audited
for equivalent enumeration tables (none found in the static pass — `grep -rln
CONTEXT_ACTIONS_ACTION_CODES web/webclient-app` empty); if the audit finds any, the same tables
widen and the Vitest/Storybook gates run; otherwise the Vue tree and the committed dist stay
untouched (`pnpm run build` only if app sources actually changed).

## D-LS5: The regression test renders panels, not vocabulary

The gap was a composition failure, so the regression test is exactly the untested combination: an
EvenniaTest room containing a bound companion renders the full `exploration` and `context_actions`
panels through the production presenters/validators and asserts (a) both available, (b) the
companion descriptor carries an enabled/disabled `explore.possess` affordance, (c) no presenter
exception was logged. Lands in the existing exploration-presentation test module if one fits
(no shard-manifest edit); a new module file MUST update `.github/evennia-shards.json` in the same
change. Same shape for `context_actions` via the PartyDrawer source path (`combat_panel.py`
validator call included — a bound companion beside the actor is the poison fixture).

## Risks / Trade-offs

- [Deriving `ACTION_IDS` widens what the panel validator ACCEPTS] — acceptance ≠ emission: the
  presenter still only emits target-scoped codes; the widened accepted set is exactly the
  vocabulary's own allowlist, so nothing the panel could previously emit changes form.
- [Structured rejection at :88 could mask a future forgotten registration] — prevented by the
  D-LS3 totality superset test, which is the real guard.
- [UMD/Vue drift recurs on the next vocabulary change] — the fixture-parity Node test converts
  future drift into a red gate instead of a silent client rejection.
