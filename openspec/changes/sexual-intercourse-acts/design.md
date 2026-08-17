# Design: Sexual Intercourse Acts (交合 / 深度交合)

## Context

`sexual-catalog-partner` (archived 2026-08-16) shipped fourteen of the line's sixteen acts and
deferred 交合/深度交合 with an explicit follow-up contract (design.md D-2): "a way for an act's cast
to compute `actor.sex`/`target.sex` and select the emitted event accordingly, landing in
`sexual-act-effects` or a dedicated successor capability." The same document's D-3 named the second
gap this change closes: `_handle_sexual_event` iterates raw `targets` instead of
`participants(actor, targets)`, so a two-party act's declared event reaches the partner only.

The shipped rulebook already contains everything the branch needs: `virginity_once`,
`experience_vaginal_added`, `experience_lesbian_added`, `experience_gay_added` (plus the B3-added
`penetrative_sex_with_male` row). `LivingEntity.sex` (`AttributeProperty(default="other")`,
`world/lore/sex.py`) has waited since S1 for its first consumer.

## Goals / Non-Goals

**Goals:**
- Ship 交合 (`partner_vaginal_sex`) and 深度交合 (`partner_deep_vaginal_sex`) as ordinary
  `_act_family()` rows with a per-row sex-conditional event table.
- Make acts' declared `sexual_event:` entries fire on every participant (actor + targets), closing
  partner D-3's asymmetry for 乳交 and 異種交合 in the same change.
- Implement the full D-12 table: opposite-sex → `first_vaginal_penetration` (breaks `virgin` for
  both), both-female → `penetrative_sex_with_female`, both-male → `penetrative_sex_with_male`,
  either `other`/unknown (including monsters) → no event.
- Preserve the legacy `divine_sexual_arts` skill's target-scoped `stimulus_applied` (D-9: divine
  arts must never self-apply pleasure).

**Non-Goals:**
- No `sexual.yaml` rulebook changes (all needed rules shipped).
- No changes to `SexualState` or the `sex` field itself.
- No new lines or non-intercourse acts; the 忍耐 tier and 搾取 deferrals belong to their own
  proposals.

## Decisions

### D-1: The pair-event table is per-act data on `SexualActDef`, selected by a pure function

`SexualActDef` gains `pair_events: tuple[tuple[tuple[str, str], str], ...] = ()`. Each entry is a
(sorted, two-member, `SEX_VALUES`) sex pair plus an event name. At cast time the selector
`pair_event_name(actor, targets, act)` in `world/rules/sexual_act_effects.py` builds the sorted sex
tuple of `participants(actor, targets)` (exactly two for the structurally-mandated `SINGLE`
targeting) and returns the first matching entry's event, or `None`. The D-12 branch is therefore
data, not code, and lives in the catalog row — matching the source document's "the branch lives
here, in which event each act emits."

**Rejected — a dedicated `intercourse_event(actor, target)` function.** The branch is the same for
both acts today, but a per-act table keeps the mechanism general (a future line with a different
conditional table reuses it unchanged) and stays within the codebase's explicit-tables discipline.

**Rejected — the archive D-2 alternative of three separately-keyed acts.** The player would have to
declare their own and their partner's sex through act choice; the schema already tracks it.

### D-2: `_act_family()` rows accept an optional 14th element; zero churn for existing rows

The row format is a fixed-position tuple. Adding a 14th positional element would force edits to all
63 shipped rows. Instead the unpacking accepts 13 or 14 fields with an explicit fail-closed guard
(a 14th field is `pair_events`, default `()`); any other length raises `ValueError`. Only the two
new acts carry the 14th field.

### D-3: Acts' `sexual_event:` entries apply to every participant; a dedicated legacy set keeps the divine skill target-scoped

`_handle_sexual_event` changes its recipient iteration: `event_name in
_LEGACY_TARGET_SCOPED_EVENTS` (a new, dedicated `frozenset({"stimulus_applied"})` in `_builder.py`)
keeps the historic target-scoped behavior — it names exactly the legacy `divine_sexual_arts` skill's
declared event, so D-9's divine-arts exemption from self-pleasure holds. Every other event name
iterates `participants(actor, targets)`, mirroring the pleasure and counter handlers. This is the
exact fix partner D-3 named ("a future proposal that extends `_handle_sexual_event` to call
`participants(actor, targets)`"). The set is deliberately distinct from
`_FORBIDDEN_SEXUAL_EVENTS`, which remains solely the act-catalog emission prohibition: a future
addition to the forbidden set can never silently change a legacy skill's recipient semantics.

**Rejected — a new `act_event:` prefix.** A second prefix would churn every catalog act's effect
strings and add a parallel handler for identical semantics. The legacy-set discriminator needs no
effect-string changes and is structurally pinned (acts can never declare those names).

### D-4: The pair event applies to every participant, delivering the symmetric `virgin` break

The `act_pair_event:<act_key>` handler stages one `PendingEffect` per participant of the surviving
cast (resisted targets were already excluded by `_step4b`). Both parties receive
`first_vaginal_penetration` → `virginity_once` fires for both through the ordinary one-way setter,
and `experience_vaginal_added` credits both. This matches the catalog design's explicit statement:
"`virgin` breaks symmetrically... breaks it for both parties at once, which is correct and needs no
extra logic."

### D-5: The `other`/unknown branch emits nothing

The source table's "either party `other`/unknown — `penetrative_sex_with_female`'s shape, no virgin
rule" is implemented as **no event**. Rationale: the only "shape" that branch could take is an
experience add, and no rulebook experience type fits an other/unknown pairing; the operative
requirement is that `virgin` never breaks, which the no-event resolution guarantees — and the
monster case "falls out for free" exactly as the catalog design promised (`Monster` reads `sex` as
the default `"other"`).

### D-6: 交合/深度交合 magnitudes are an escalation pair, not a strict dominance trap

Tier 3 currently holds 後庭交合 (26, ratio 0.6) and 相互自慰 (18, ratio 1.0). The two new acts share
the same part (私處), gate (`duo:30, climax:10`), and resistibility, so a pure magnitude difference
would let 深度交合 strictly dominate 交合. They are instead tuned as an **escalation** pair: 交合
`base=28, ratio=0.6` (target gain 28, actor gain 16.8) and 深度交合 `base=34, ratio=0.9` (target gain
34, actor gain 30.6). The target-side gap is +6 while the actor-side gap is +13.8 — choosing the
deeper act trades a modest partner benefit for a disproportionate self-gauge cost, the same
self-limiting shape every act in the system relies on (D-4 of the overview design). Both numbers
are tunable registry constants; the delta spec pins the ratio relationship, not the absolute
values.

## Risks / Trade-offs

- **[Risk] `_handle_sexual_event` recipient change alters every existing act's event scope.** 乳交
  and 異種交合 now credit both parties; SELF acts are unchanged. This is the designed fix (partner
  D-3), pinned by new tests and the amended `sexual-act-effects` requirement.
- **[Risk] The legacy-set discriminator adds a second event-name policy next to
  `_FORBIDDEN_SEXUAL_EVENTS`.** → Documented in the handler docstring and the delta spec; a
  structural test asserts `_LEGACY_TARGET_SCOPED_EVENTS` and the acts' declared event names are
  disjoint, so the two populations cannot drift.
- **[Risk] A future non-act skill declaring a non-forbidden `sexual_event:` would inherit
  participant semantics.** Accepted: that semantics is the catalog's default contract; the legacy
  exception exists only for the shipped divine skill.
- **[Trade-off] `pair_events` is validated only at `_act_family()` time, not at module load of
  `partner.py` alone.** The structural registry tests (event existence, SINGLE-only, sex
  vocabulary) cover the assembled registry, matching the shipped test strategy.
- **[Risk] Implementation must serialize with `sexual-public-act-events`**, which also edits
  `world/rules/action.py` event handling. This change owns the participant-semantics edit; the
  follow-up must build on it, not beside it.

## Migration Plan

No migration: the project has no released users. The two acts register through the ordinary
`_register_rows` path at server startup; existing saves are unaffected (new `SexualActDef` field
defaults to `()`).

## Open Questions

None.
