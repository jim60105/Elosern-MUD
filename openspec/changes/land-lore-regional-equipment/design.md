## Context

See `proposal.md` — Why. The equipment seam is already fully built, which is what makes this slice data rather than behavior.

`world/rules/equipment_effects.py` does a strict two-sided close at startup: every `EquipmentModifierKey` member must have exactly one entry in `equipment_effects.yaml`, every entry must have a member, and the member's value must equal the item key that declares it. It then checks each authored value against the budget column its field maps to for the item's registered rarity — `atk_phys`/`defense`/`magic_power` and flat `agility` against `flat`, `mp_cost`/`sp_cost` and percent `agility` against `percent`, `pleasure_gain`/`heal_gain` against `soft_percent`, `exposure_bias` against `bias`, `gauge_caps` against `gauge`. A wrong number is a startup failure, not a balance bug.

`exposure_bias` is a top-level field of a rulebook entry, not a member of `adjustments`; the codex's seventh-layer table now says so explicitly, and `elven_forest_veil` is the only piece in this slice that carries one.

## Goals / Non-Goals

**Goals:**
- Give the Beastfolk Kingdom and the elves a culturally coherent equipment line at the tiers the codex assigns them.
- Make "registered but unstocked" an explicitly valid state rather than an unstated deviation.

**Non-Goals:**
- **New game-data contract tests.** No test added here transcribes or parses the codex's published adjustments, enumerates the new keys, or asserts that a named item carries a particular number. The budget ceiling is enforced by the rulebook loader at startup and the binding by its two-sided close; a test restating those values would echo registry content for no added guarantee.
- Stocking any of it. The 聖所器具商店 and 精靈村商店 are their own change; this slice deliberately ships unstocked.
- Retuning the 45 shipped equipment entries, including the three where the codex and the rulebook state different numbers (`sister_vestments`, `saintess_vestments`, `silver_feather_earring`). The codex declares the rulebook authoritative for tuned values, so those are an intentional divergence, not drift.
- Any new adjustment field, budget column, or slot.

## Decisions

**Twelve items in one slice, not split by slot.** The whole group shares one mechanical shape and one enum, and splitting weapons from armor would mean touching `EquipmentModifierKey`, the rulebook, and the same two roster assertions twice for no isolation benefit. Twelve entries is roughly five hours of careful authoring with the budget check run after each group.

**The loader is the budget gate; no test re-states the numbers.** Two earlier drafts of this design added a check comparing the codex's published adjustments against the rulebook — first by parsing the adjustment cells, then by hand-transcribing them into a fixture. Both are game-data contract tests, and neither buys anything the loader does not already give: `world/rules/equipment_effects.py` refuses to start the server on a value above its rarity's ceiling, on an unbound key, and on an orphaned entry. A test that re-asserted `atk_phys: 6` for a named item would echo the registry and would have to be maintained against every future retune. What the change does add is a behavior test on a synthetic item proving the *gate itself* is live — an over-budget synthetic entry must fail the load — which is a mechanics assertion and needs no shipped key. Authoring the twelve entries in small groups and running the load after each keeps a failure attributable to three entries rather than twelve.

**Unstocked is a stated decision, recorded in the spec.** `equipment-effects` already carries a roster requirement that ends "...and a listing in the existing general store's offered keys", which reads as a general rule. It is not one — it was the right call for ten Empire/Kingdom/Church pieces and is the wrong call for beastfolk tribal gear. Rather than silently deviating, this change adds a parallel requirement making tradeability an explicit per-roster statement. Alternative considered: stocking them in Altoria anyway. Rejected — it would contradict the provenance column of the codex we just reconciled, and the store is already implausibly universal.

**獸人雙爪刃 is `攻擊 +6、防禦 -2`, not `攻擊 +7`.** The codex originally published `+7` at `uncommon`, whose flat ceiling is 6; the rulebook loader would have rejected it at startup. The codex was corrected to `+6` with a `-2` defence penalty, which keeps the design intent — highest raw damage in the tribal line, no guard at all — inside budget. This is recorded here because the number differs from earlier drafts of the document.

**龍之巢穴戰利品劍 uses the `magic_weapon` band despite being forged, not enchanted.** It carries `魔力 +3`, which puts it past the `mundane_weapon` ceiling in spirit as well as in tier: an `epic` dungeon trophy priced under 2000 copper would sit below the `apprentice_focus_staff`. Since it is stocked nowhere, the band is never range-checked; it is declared for coherence with the other `epic` weapon rather than to authorise a price.

**Rarity spread follows the codex, not power.** Five beastfolk weapons all sit at `uncommon` with different trade-offs rather than climbing a ladder, because the codex frames them as one tribal armoury with different roles. `精靈長弓` at `rare` and `精靈森林輕紗` at `legendary` reflect elven craft standing, not a stat jump — the veil's `防禦 +4` is deliberately modest for a legendary, which the budget model permits because rarity caps what a piece *may* carry, not what it must.

## Risks / Trade-offs

- **Twelve unstocked items look like dead data until a storefront lands.** → They are reachable today through quest rewards, starting kits, presets, and the scenario director, all of which resolve against `ITEM_REGISTRY` directly. The new requirement pins this with scenarios written against a synthetic item, so the state is specified and tested without naming any of the twelve.
- **Dropping the codex-versus-rulebook check means a transcription slip can ship.** → Only within the budget ceiling: a slip that raises a value past its rarity's cap fails startup, and a slip that lowers it is a balance detail the codex already declares the rulebook authoritative for. The residual risk is a number that is legal but not what the designer wrote, which is a review responsibility.
- **A mistyped budget value fails the whole server at startup, not just the item.** → That is the existing fail-closed design and is desirable; the mitigation is to author the twelve entries in four small groups and run the rulebook load after each, so a failure names one of three entries rather than one of twelve.
- **`EquipmentModifierKey` is alphabetically ordered and twelve insertions touch the middle of it.** → Mechanical but conflict-prone if another slice edits the enum concurrently; this is the main reason the codex slices run sequentially rather than in parallel.
- **The new `equipment-effects` requirement weakens an existing guarantee.** → It does not remove the ten-item roster requirement, which keeps its own tradeability statement. It only denies that tradeability was ever a *general* rule, which the shipped registry already demonstrates — `elven_traditional_robe`, `crescent_earring`, and the relic weapons are registered and stocked nowhere today.

## Migration Plan

Not applicable. Pre-release, no stored inventory can reference a key this change adds, and it removes none.
