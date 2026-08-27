## Context

The `character` panel (v3 today) is built by `character_presenter()` → `build_character_read_model()`
(`world/rules/status_query.py`) → `_serialize()`/`validate_character()`
(`web/webclient/presentation/character.py`), and is only ever rendered for the connection's own puppet
(`PresentationContext.actor`) — there is no cross-player broadcast path for this panel, so `intimate`
inherits that existing self-view-only scoping unchanged; nothing new needs to be built to keep this
data private.

`world/rules/sexual_state.py`'s `SexualState` already holds every value this section needs:
`arousal` (a derived read-only view over the `pleasure` counter, via `PLEASURE_CONFIG.ordinal_for`),
`wetness`/`shame`/`exposure`/`climax_phase` (each an `OrderedLevelTrait` over a fixed vocabulary in
`world/lore/sexual_vocab.py`), and `climax_today` (a counter). But `character_presenter()` must never
construct a `SexualState` handler directly — doing so can *materialize* default trait Attributes on an
entity that has never had them written, which
`openspec/specs/webclient-status-presentation/spec.md`'s "Status presentation has no mutation side
effects" requirement forbids for the sibling `status` panel, and the same no-create discipline applies
here. `status_query.py` already solves exactly this problem for the `status` panel's threshold-gated
condition entries: `_sexual_level(entity, field)` reads the raw persisted trait dict (or the
import-time baseline) without ever touching `entity.sexual`, returning `None` only when no record
exists at all. This proposal reuses that function rather than inventing a second reading path.

## Goals / Non-Goals

**Goals:**
- Expose `arousal`/`wetness`/`shame`/`exposure`/`climax_phase` (level words, never raw numbers) and
  `climax_today` (a count) in the `character` panel, backed entirely by existing canonical state.
- Preserve the no-create, no-mutation presenter discipline already established for `status`/`character`.
- Render the design draft's collapsed-by-default `親密狀態` section with its vocabulary-closed hint
  copy, absent entirely (not placeholder-rendered) when no backing record exists.

**Non-Goals:**
- Per-body-part `敏感部位` (sensitivity) — the 設計稿's summary line
  ("敏感部位（4 級）：口唇 高 · 頸項 高 · 乳房 極高 · ...（其餘普通）") only lists parts that deviate
  from the `普通` baseline, which requires iterating every materialized `sensitivity__<part>` trait and
  designing a summarization rule not needed for the six scalar fields this proposal adds. Follow-up,
  not attempted here.
- `virgin`/`experience_types`/lifetime act counters (masturbation/toy/duo/group/etc.) — not shown in
  the 設計稿's `#dr-status` block at all; out of scope.
- Any change to `world/rules/sexual_state.py`, the pleasure→arousal band config, or any mutation path —
  read-only exposure of already-computed state.
- Any change to how/when the sexual-threshold condition entry appears in the `status` panel's
  `conditions` array — unrelated, unchanged.

## Decisions

**Reuse `_sexual_level()` for the five ordered fields, but the new caller — not `_sexual_level()`
itself — enforces fail-closed on every value it returns.** Re-reading `_sexual_level()`
(`world/rules/status_query.py:268-308`) turned up a fourth, unhandled branch its docstring doesn't
name: when the materialized `sexual_traits` entry for a field is a `Mapping` but its `value` is
neither a matching vocabulary string nor an in-range int — e.g. a corrupted ordinal, `None`, or a
`bool` (Python's `isinstance(True, int)` is `True`, so a stray `bool` silently passes the `isinstance`
check as ordinal `1`/`0`) — the function falls through to `return value` (line 302) and hands back that
**raw, unvalidated value verbatim**, never raising. Separately, when `raw` (the field's materialized
entry) is present but is not a `Mapping` at all, the function silently ignores it and falls back to the
baseline instead of failing closed. The sole existing caller, `_sexual_condition_context()`, tolerates
both because it only accepts an exact `_LevelRef` and silently drops anything else from the
combat-modifier context (`elif isinstance(value, _LevelRef): ...`) — a shape this proposal's
always-rendered UI reader cannot inherit by assumption.

`_read_intimate()` therefore does its own exhaustive validation on every `_sexual_level()` result
instead of trusting the callee's contract: for each of the five fields, the returned value MUST be
either `None` (record entirely absent — the whole `intimate` resolves to `None`), a `_LevelRef` whose
`.level` is a member of that field's vocabulary tuple, or — matching the "unmaterialized baseline"
path — a `str` that is a member of that vocabulary tuple; any other returned shape (including the
Python-`bool`-as-ordinal case and the "value present but wrong type" case above) raises
`StatusQueryError` inside `_read_intimate()` itself, which `character_presenter()`'s existing
`except StatusQueryError: raise PanelUnavailableError` already catches — so a corrupted record fails
the whole `character` panel closed rather than crashing the server with an unhandled exception or
silently showing garbage. `_sexual_level()`'s own body is left unmodified (its existing caller's
tolerant behaviour is unrelated to this change and stays exactly as shipped); the stricter contract is
enforced entirely at the new call site.

`climax_today` is a `CounterTrait`, not an `OrderedLevelTrait`, so it needs its own small reader
following the same shape and the same file's own established counter/gauge-reading precedent: like
`_require_static_trait`, which reads `raw.get("current", raw.get("base"))` rather than `.base` alone,
the new reader reads the materialized `sexual_traits` dict's `climax_today` entry the same way —
preferring a computed `current` value over `base` when present — rather than reading `.base` directly.
`SexualState.climax_today` (`world/rules/sexual_state.py:536-537`) itself returns
`self._traits.climax_today.value` (the modifier-adjusted figure), not `.base`; today no code path ever
sets a `mod`/`mult` on this counter so the two are numerically identical, but matching the canonical
accessor's semantics — and this file's own existing convention for every other counter/gauge field —
avoids a silent future divergence if a modifier-bearing effect (this domain already has an analogous
"extension" mechanic on `climax_extension_count`) is ever added. Absent a materialized record, the
baseline's `climax_today` (default `0`) applies when a baseline exists, else the field (and therefore
all of `intimate`) is `None` — mirroring `_sexual_level()`'s three-way absent/resolved/malformed shape,
with the same caller-side fail-closed rule as above: a present-but-malformed record raises
`StatusQueryError`, never silently defaulting to `0`.

**`intimate` is `null`, not a `reason`-carrying unavailable sub-object.** Every other optional
character sub-value in this payload that can be legitimately absent uses a bare nullable field, not a
nested availability discriminator (`guild.rank: null`, `persona.background: null`) — the panel-level
`available`/`reason` pair already exists for the whole-panel unavailable case (outside exploration
mode). `intimate: null` follows that established convention rather than inventing a second
availability shape nested one level down.

**Schema version bump (3 → 4), not a same-version additive field.** `validate_character()` uses
`_require_exact_fields()` — an exact field-set check — so adding `intimate` without a version bump
would make the new field simultaneously required (old clients that don't send/expect it break) with no
signal of the shape change. `CHARACTER_SCHEMA_VERSION` already exists precisely to gate this; bumping
it is the established mechanism, at zero cost since there are 0 released users (per repository
convention, no migration path is needed).

**Native `<details>`/`<summary>` for the collapsed section, matching the 設計稿's own markup.** The
設計稿's `#dr-status` intimate block is a plain `<details id="intimate">` (`index.html:1088`) — no
custom JS toggle, no animation. `CharacterStatusDrawer.vue` has no existing disclosure-widget
component to reuse or extend, and introducing one here for a single collapsed section is unwarranted
complexity; the native element is keyboard-accessible and requires no script.

**Ordering: last section, after 偽裝.** Matches the 設計稿's `#dr-status` sequence
(生命量→屬性→計數・公會→條件/修正→偽裝→親密狀態) established by
`fix-webclient-character-status-drawer-order`, this change's dependency. Concretely it renders after
偽裝 and before the pre-existing 錢包/背景 rows that proposal keeps at the end (see that change's
design.md) — i.e. this proposal inserts one more section between 偽裝 and 錢包, it does not reorder
anything that proposal already placed.

## Risks / Trade-offs

- **`_sexual_level()` reused outside its narrow original call site could silently pass through
  malformed data instead of failing closed.** → Confirmed by review: the function has a fourth,
  undocumented return branch (see Decisions above) that its sole existing caller tolerates but a
  general-purpose UI reader must not. Fixed by making `_read_intimate()` itself the fail-closed
  boundary — it validates every value `_sexual_level()` returns against the exact vocabulary
  membership it expects and raises `StatusQueryError` on anything else, rather than trusting the
  callee. `_sexual_level()`'s own body and its existing caller are unmodified.
- **This proposal's spec delta for `webclient-contextual-hud` is a full-text copy of
  `fix-webclient-character-status-drawer-order`'s order/filtering/label wording, taken at the time this
  proposal was drafted — and that sibling change is still being revised.** → OpenSpec requirement
  deltas are whole-requirement replacements, not patches, so if the sibling's wording changes again
  before it archives, this proposal's already-drafted copy would silently regress the merged spec on
  archive. Declaring "the sibling must archive first" (as this design already does) is necessary but
  not sufficient — it doesn't catch a *wording* drift that happens before that archive. Mitigated by
  tasks.md's new pre-archive reconciliation task (§4.3): diff this delta's copied text against the
  sibling's actual final archived text and reconcile any divergence before this change's own archive
  step, rather than assuming the drafted copy is still accurate.
- **A malformed persisted sexual-state record now fails the whole `character` panel closed, not just
  the intimate section.** → Matches every other section's existing behaviour in this presenter (a
  malformed disguise or equipment row already fails the panel, not just that section) — consistent,
  not a new failure mode class.
- **Schema version bump requires touching every test that pins `CHARACTER_SCHEMA_VERSION`'s value.** →
  Enumerated explicitly in proposal.md's Impact section (`test_registry.py`'s hardcoded `3`), so it is
  not discovered mid-implementation.

## Migration Plan

Additive server field + new client section; no persisted client/server state to migrate. Lands as a
single PR. No feature flag: `intimate` is `null` for any actor without materialized/baseline sexual
data, so the client change is inert until the server change ships in the same PR (both are in the same
change/PR here, so there is no partial-rollout window to design for).

## Open Questions

- None blocking. 敏感部位 summarization (Non-Goals) is the natural next OpenSpec change once this
  lands.
