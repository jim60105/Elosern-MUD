## Context

Delivers the generic **on-hit counter-damage / source-targeted reaction** seam the earth wave needs for 荊棘反甲 (`docs/lore/skill-trees/earth.md` thorned_carapace: 「受到物理攻擊時反彈 1.0 係數的傷害」) and that fire's future 灼熱反甲 will reuse as pure data (constitution §4.2 fire row: 「灼熱反灼…都是本動詞的合法表達，不借用反彈動詞」 — the borrow happens at the event layer, not the verb layer). Per the user-ratified naming requirement the seam is element-agnostic mechanic vocabulary; the `thorned_carapace` row (MP 40, self-target, buff key) belongs to `earth-spell-catalog`. Pre-audited engine facts (verified at e7234ad):

- **Zero counter/reflect primitives exist.** The reaction engine (`world/rules/state_reactions.py`) dispatches outcome events `hp_loss`, `mp_zero`, `negative_buff_added` via `dispatch_outcome_reaction(entity, event, source_tier=…, source_skill=…)`, validates a closed `when` key set and a closed `then` vocabulary {`apply_buff`, `remove_buff`, `pleasure_gain`}, and every action writes only to the dispatched (victim-side) entity. There is no on-physical-hit event and no source entity in the dispatch context.
- **The damage commit leg already knows everything the event needs.** `_handle_damage` (`world/rules/combat.py`) parses the school (`physical`/`magic`), computes `actual_loss` post-clamp inside the staged `apply()`, and already dispatches exactly one `hp_loss` from that same leg; `source_tier` is captured there and the resolved `source_skill` rides the event context. The attacker entity is the handler's `actor` argument — the source attribution the event must carry exists at the exact dispatch site.
- **`PendingEffect` commits are the transaction.** The counter can settle as ordinary staged HP movement (or a direct write inside the same commit pass, matching `hp_loss` reaction precedent — reactions already write pleasure/buffs at dispatch time inside the initiating transaction; the `damage-state-feedback` cascade requirement already pins that feedback stays inside the initiating transaction with full snapshot/restore).
- **`damage-state-feedback` is the reaction capability's spec home** (its Purpose: 「reusable passive reactions to actual damage and new negative buffs」; its cascade requirement already forbids recursive damage-event loops — the recursion guard this change pins is that requirement's own law extended to the new event).
- **The event vocabulary is NOT closed today**: `validate_state_reaction_rules` validates `when` KEYS only — a `when.event` VALUE is never enumerated and an unknown value loads silently as a never-firing rule (`evaluate_condition` string-compares). Closing the enum is part of this change's scope (D5).

User-ratified givens: **no second rules engine, no element-key branches in generic code** — the seam is declarative vocabulary growth on `state_reactions.yaml`/`state_reactions.py`. **NON-GOAL: 遊戲資料契約** — behavior contracts on synthetic skills/state transitions only; this change ships zero live reaction rows (inert-but-valid vocabulary, the `caster_share` precedent) — `earth-spell-catalog` authors the `thorned_carapace` rule + buff row. **Clean cut, zero users**: no migrations, no aliases.

## Goals / Non-Goals

**Goals:** One new outcome event `physical_hit` with source attribution; two source-targeted then-actions (`counter_damage`, `apply_buff_to_source`) so an on-hit apply-buff-to-source variant (fire's ignite) needs only data later; exactly-once, same-transaction, non-recursive settlement; behavior-test-only proof; everything generic.

**Non-Goals:** No `thorned_carapace` registry/buff/reaction rows (catalog owns all data); no `hp_loss`-keyed counter variant (the lore trigger is 「受到物理攻擊」 — magic hits, DoT ticks and MP crossings must not rebound; the event is precisely scoped); no hit roll / accuracy / to-hit participation for the counter (a thorn does not miss — pinned decision, D3); no combat-modifier bundle field for counters (it is an event action, not a passive numeric adjustment); no `terrain-marker` surfaces (sibling change owns `buffs.py`/`target_facts.py`/`effects.py`/`combat_session.py` — file-disjoint); no data-contract tests.

## Decisions

### D1 — Carrier: a new `physical_hit` outcome event on the existing reaction engine

The reaction table is the shipped home for 「when X happens to me, do Y」 declaratively; growing its event enum and then vocabulary is the one-surface extension the constitution allows. Alternatives rejected:

| Candidate | Rejection |
|---|---|
| `hp_loss` + `buff_active: <carapace>` reaction | fires for DoT ticks, MP-side nothing, magic damage — wrong trigger set; disambiguating school inside the reaction engine means a second matching language inside the one engine (forbidden) |
| `combat_modifiers.yaml` numeric field (e.g. `counter_damage: 1.0`) | the modifier table is a pure passive stat-bundle query (`evaluate_combat_modifiers` never writes entity state — requirement-pinned); a counter is an event-driven HP write against another entity — a modifier row cannot express source targeting, exactly-once-per-strike, or non-recursion |
| new handler effect prefix on the defender's skill (`counter_stance:`) | reactions must fire when the defender is *hit*, not when it *acted*; effect handlers run in the actor's action pipeline only — would need a lookup of every defender skill at every damage commit = a second dispatch engine |
| `state_reactions.py` new engine | literally the forbidden duplicate |

### D2 — Event dispatch site and payload

In `_handle_damage`'s staged `apply()`, immediately where `actual_loss > 0` already gates `hp_loss`: if the parsed school is `physical` and the strike landed positive actual loss, additionally `dispatch_outcome_reaction(target, "physical_hit", source=actor, source_tier=source_tier, source_skill=source_skill)` — one dispatch per landing strike (the double-strike policy loop dispatches per strike, each with the same source). The dispatch context gains exactly one new key (`source` — the attacker object) consumed ONLY by the two new then-actions; the existing `hp_loss` dispatch call is untouched (order: `hp_loss` first, then `physical_hit`, so today's rules observe unchanged ordering). `validate_state_reaction_rules` recognizes `physical_hit` in the event enum; `event_source_skill` filtering keeps working on it for free. Misses (`hit` False), zero-actual-loss writes, magic school, rate ticks (`_apply_rate_modifier` unchanged) dispatch nothing new. The `physical_hit` dispatch additionally threads the initiating round's nonlethal facts already in the handler's event context (session flag, protected key set, battlefield handle) into the dispatch context so a protected source's counter floors at 1 and marks the knockout through the existing battlefield shape — no second terminal-settlement path.

### D3 — `counter_damage: <coefficient>` settlement semantics

1. **Magnitude**: `max(combat.yaml damage floor, round(holder_skills.effective_value("atk_phys") × coefficient) − _adjusted_defense(source))` — the holder's effective physical attack (buff bounds included, same reader as ordinary damage) times the declared finite positive coefficient, minus the source's ordinary effective defense, floored at the shipped `combat.yaml` damage floor exactly like a landed physical strike (the counter prices like one, the coefficient replacing the roll multiplier — a high-defense source absorbs the counter down to the floor, never to zero). No hit roll, no agility, no accuracy, no crit (a thorn doesn't miss and can't crit; pinned because lore says only 「反彈 1.0 係數的傷害」).
2. **Exactly-once + non-recursion**: one `physical_hit` dispatch → at most one `counter_damage` action → one HP write. The counter write dispatches the source's `hp_loss` (it is real damage; the source's own damage-feedback passives legitimately fire) but dispatches **no `physical_hit`** — the counter leg writes through a dedicated settlement that never re-enters the on-hit dispatch, so two mutual thorn-holders settle one exchange per initiating strike (test-pinned). The dispatch context carries a settled-counter guard flag as a second belt.
3. **Same transaction**: the counter HP write executes inside the same commit pass as the initiating `apply()` (reactions already run at commit-dispatch time; the initiating action's snapshot/restore surfaces already cover `traits`/`buffs`, so a late commit failure rolls the counter back with everything else — the `damage-state-feedback` cascade requirement's own law).
4. **Death/immunity/floor**: dead-or-unresolvable source → silent zero write (same posture as the leech's dead-origin skip); a counter crossing the source to ≤0 honors the per-target nonlethal policy already threaded in the event context (protected → floor at 1 + the existing knockout mark path via the same battlefield shape, at most one terminal settlement per round); the counter NEVER revives a dead source.
5. **Genericness**: the coefficient is data in `state_reactions.yaml`; no element/skill key is read. `thorned_carapace` authors `counter_damage: 1.0` later; no shipped row today.

### D4 — `apply_buff_to_source: <definition-key>` — the scorching_armor seam, opened now

The same `physical_hit` event carries an `apply_buff_to_source` action: `apply_buff(source, key, source_key=holder attribution per the shipped public-entry attribution contract, source_tier=the event's tier)`. This is deliberately shipped in THIS change (not deferred) because the user-ratified contract demands the trigger vocabulary be designed so fire's on-hit ignite needs only data later — the two actions share the event, the source context key, the load-validation frame and the non-recursion guard, so the wave proves both action shapes and the catalog proves neither is earth-shaped code. Debuff immunity rides the shipped `apply_buff` backstop (no-write); refresh stacking rides unchanged; the applied debuff's own `negative_buff_added` dispatch fires once on the source exactly like any cast-applied debuff (and cannot recurse: `negative_buff_added` rules cannot dispatch `physical_hit`).

### D5 — Rule load validation

`then` keys grow to exactly {`apply_buff`, `remove_buff`, `pleasure_gain`, `counter_damage`, `apply_buff_to_source`}; still exactly one action per rule (no `then` composition — composition needs multiple rules, which the table already supports and prices once each). `counter_damage`: finite positive number (bool rejected, same frame as `DamagePolicy.attack_multiplier`); `apply_buff_to_source`: non-empty string, must name a `BUFF_DEFINITIONS` key (same frame as `apply_buff`). `when.event` values become a CLOSED enum {`hp_loss`, `mp_zero`, `negative_buff_added`, `physical_hit`} — an unknown value raises at load naming the rule id (NEW validation: today unknown values load silently and never fire; the three shipped values keep working unchanged).

### D6 — Interface ownership (earth wave matrix lives in `terrain-marker/design.md` D4)

| Interface | Owner | Consumers |
|---|---|---|
| `physical_hit` event (dispatch + validation + source context key) | this change | `earth-spell-catalog` (`thorned_carapace` rule data); future fire `scorching_armor` (`apply_buff_to_source` data) |
| `counter_damage` / `apply_buff_to_source` then-actions | this change | same |
| marker fact + lifecycle + `buff:<key>` predicate | `terrain-marker` | catalog data |
| earth registry/buff/modifier rows, display census, echo retirement, shards final | `earth-spell-catalog` | — |

## Risks / Trade-offs

- **Counter bypasses to-hit by design** — a high-agility attacker can be thorned while its own swing missed the *reactor*? No: the event only fires when the attacker's strike actually landed positive loss; a miss never dispatches. The counter itself adding a roll would make two independent rolls per exchange and let 「反甲」 whiff — pinned decision, matches 「反彈」 imagery.
- **`physical_hit` inside an area physical attack** dispatches per landing victim, each counter hitting the shared attacker — intended thorn-field semantics; bounded by the victim count and the same round's settlement.
- **Feedback loops through `hp_loss` passives stay reachable** (pain_to_pleasure-style reactions on the counter's loss) — that is the shipped cascade law (stays in-transaction, restorable); only the on-hit recursion is closed.
- **A counter kill through nonlethal-protected settlement** reuses the existing knockout mark path exactly — no second terminal-settlement path is opened (test-pinned).

## Migration Plan

Nothing migrates. Enum growth + validation + two executors + dispatch leg → synthetic behavior suites → shard registration, one reviewable slice. Zero live reaction rows ship here; `earth-spell-catalog` authors the `thorned_carapace` rule and buff row. Main-spec sync, ledger and freeze-list edits stay in the separately authorized workflow.

## Open Questions

None blocking. Recorded decision: the lore 「反彈 1.0 係數的傷害」 has no hit/miss language — resolved as no-roll (D3.1); if the lore owner later wants to-hit participation it is a new coefficient-shaped clause, not a redesign.
