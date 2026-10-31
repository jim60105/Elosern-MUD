# Design

## Context

The tracked `PlayerPreset` rows live in `world/lore/player_presets/data_pack_cards.py` and `data_story_cards.py`. They already support `active_skills`, `passive_skills`, and `skill_proficiency: tuple[tuple[str, float], ...]`. `_preset_lineage_state` and starting-companion construction share prerequisite closure and seed. Existing rows have no explicit proficiency entries.

The approved investigation established that all five original story presets' resolved innate values already match their originals. Allocation tuples are increments over racial floors and modifiers; they are not the final values. This proposal preserves those tuples verbatim. Elysa, Nazka and Sylwen are developer-authored templates whose prose needs race/role consistency.

## Goals / Non-Goals

Author complete initial learned breadth for every currently implemented eligible ordinary tree on every elf preset, and preserve original deeper abilities. This is a data-only change after both prerequisite changes. MUST NOT change resolver/seed code, race/subrace ranges, allocation budgets, innate bases, gauges, effect multipliers, skill definitions, freeform rules, importer semantics, companions' relationships, equipment or disguise numbers. Other weapon lineages are unimplemented and separately scheduled; no spec shall reject them.

Do not edit explicit sexual content or reproduce it in planning/review documents. Existing unrelated fields remain untouched. Review uses non-sexual combat, learning, movement and identity facts.

## Decisions

### D1. Concrete baseline content for every eligible tree

For each of `sylwen_stillwater`, `yuka_darknight`, `yuna_darknight` and `elosia_shadowmoon`, add missing roots from the following authored matrix to `active_skills` and give each listed baseline root Lv.1 (currently 50.0 raw XP), except where a deeper specialty or mastery closure requires more. These are content choices, not general runtime defaults or normative spec values.

| Ordinary learning domain | All current roots to own and initially develop |
| --- | --- |
| fire | `fire_arrow` |
| water | `tide_pull`, `water_bolt` |
| wind | `gale_step`, `wind_blade` |
| earth | `stone_shard`, `hardened_skin` |
| lightning | `static_ward`, `spark_shock` |
| ice | `frost_breath`, `ice_shard` |
| light | `heal`, `light_arrow` |
| dark | `weaken`, `shadow_bolt` |
| common sword lineage | `basic_swordplay` |
| common shadow martial lineage | `shadow_slash` |
| common divine mystery roots | `dominion_art`, `mentors_covenant`, `status_disguise` |

Both ordinary roots are included even when a later apex connects their components; wind speed and attack, earth defense and attack, light healing and attack all begin developed. The shadow martial root is public and needs no dual-wield stance; do not grant a stance or advanced shadow technique to baseline-only learners. `basic_attack` is an innate general action, with no new baseline grant needed.

Common elemental and martial roots have unrestricted eligibility. Divine roots require `can_use_divine_arts`; current elf races satisfy it. No human/beastfolk receives divine roots. Species-only or otherwise identity-ineligible skills are excluded. Monster-like public spell names remain ordinary where the registry says so. Church office rites, personal event-granted systems, independent enhancement passives and unimplemented weapon catalogs are outside this ordinary-root matrix; their existing ownership is preserved. This does not grant every passive or mastery.

### D2. Mastery/explicit-XP precedence, no weakened specialty

Preserve fire/dark masteries on Yuka and Yuna, wind/light masteries on Elosia, and no elemental mastery on Sylwen or Violet. The prerequisite change makes those declarations close over their entire ordinary elemental catalogs. Do not copy terminal lists into presets or explicitly seed any baseline XP inside a mastered elemental closure. The shared seed supplies all required ancestor levels and terminal Lv.10; an explicit Lv.1 there would take precedence and invalidate mastery.

Author literal XP entries for nonmastered baseline roots only. For existing deeper learned specialties, use the following data choices and let closure supply ancestors at the required minimum. If an explicitly authored root also belongs to a deeper closure, use the greater of the chosen baseline level and the greatest required incoming-consumer threshold for that owned closure; write this final literal into the row. Never leave a lower explicit value that blocks an owned descendant.

| Preset | Retained/additional learned depth |
| --- | --- |
| Sylwen | Add `basic_swordplay` Lv.3, `flowing_strikes` Lv.1; develop `hardened_skin` Lv.3 and `heal` Lv.3; other nonmastered baseline roots Lv.1 |
| Yuka | Retain `dual_blade_waltz` and seed its chosen Lv.8 (400.0 XP); `shadow_slash` reaches Lv.3 and closure adds `phantom_dance` Lv.5. Preserve the existing dual-wield stance. No `shadow_dance_finale` grant |
| Yuna | Preserve existing specialist skills/passives unchanged; nonmastered ordinary/divine/martial roots Lv.1 |
| Elosia | Preserve `dominion_art`, `status_disguise` and their utility; those and the added `mentors_covenant` start Lv.1; wind/light mastery closure supplies deeper elemental depth |
| Violet | Retain `fire_ball`, `wind_blade`, accuracy/MP passives and `flight`; `fire_arrow`, `fire_ball` and `wind_blade` each Lv.3 (150.0 XP), respecting their current derived caps. Do not add mastery |
| Lidzia | Add `flowing_strikes` Lv.1 (50.0 XP); `basic_swordplay` Lv.3 (150.0 XP). Retain retainer training, guardian instinct and basic body enhancement |

For all nonmastered elf baseline roots not superseded above, write Lv.1 as 50.0 XP. No passive proficiency entries. Maintain existing tuple order, append absent skills in matrix order, and keep each key unique. Do not generate kits dynamically from the live registry; these remain reviewed literal templates. The matrix is the full current baseline, with no future-tree promise.

### D3. Innate and role data corrections

All elves retain `elf_longevity` as narrative-only. Append it where absent. Sylwen receives `body_enhancement` x100. Yuka retains only `body_enhancement_extreme` x1000 and MUST NOT also receive x100 or basic x1.2. Yuna and Elosia retain x100. Retain all movement/flight/disguise and boon abilities. Yuka's agility boon remains +5%; Elosia's WIND scoped practice boon remains x5. No effect code or multiplier edits.

| Preset | Prose/content action, with innate values unchanged |
| --- | --- |
| Elysa | Retain basic sword and basic body enhancement. Replace allocation/optimization role phrasing with an established novice adventurer's learned breadth |
| Nazka | Retain foxkin, wind affinity, `gale_step`, `flash_step`, longbow/throwing-axe courier identity. Replace misleading melee-priority prose with ranged scouting/courier practice. Do not add body enhancement or claim beastfolk are born with x1.2 |
| Sylwen | Retain existing values/equipment and defensive identity; sword, defensive earth and light healing are learned depth; full elf baseline supplies breadth |
| Violet | Retain original 5/6/6 physical bases and innate magic 56; describe wind-focused learned control without granting mastery or weakening high-magic narrative |
| Lidzia | Retain original 8/9/7 physical bases and innate magic 28, consistent with an elite trained human. Administrative/writing skill remains narrative, with no new mechanic |
| Yuka | Retain original 88/92/90 physical bases, innate magic 477 and original disguise values. Remove false comments claiming budget changed her original magic 250 |
| Yuna | Retain original 70/70/92 physical bases, innate magic 515 and original disguise values. Remove false comments claiming original physical 65/65 and magic 350 |
| Elosia | Retain original 70/70/95 physical bases, innate magic 512 and original disguise values. Replace learning-raised-magic prose with innate 512 plus learned skill depth; remove stale 873 comments |

Keep elf HP/MP/SP 10000 and approved ranges untouched. Elf all-round innate strength remains exceptional. Specialization describes learned depth. No human-balance redesign, budget changes or baking body enhancement into bases.

### D4. Tracked authority and retired-reference treatment

During implementation create `docs/lore/character-template-alignment.md` as the tracked non-sexual roster review document. Record the approved matrix, original final innate values, source decisions and mastery choices there. Link it from `docs/development/adding-player-presets.md` §1. Correct that guide's allocation explanation in §2 item 2 to racial floor plus allocation, with physical subrace modifiers; its current claim that magic allocation alone is the final value is stale. Keep this a source-data explanation, without a new docs framework.

Explicitly amend `docs/superpowers/specs/2026-07-29-ai-mud-engine-design.md` §1 source-authority note: ignored `tmp/story_settings/` remains non-authoritative and is never loaded at runtime; approved non-sexual facts are re-authored in tracked registry/lore documents before becoming seed authority. This reconciles the reference provenance with tracked runtime ownership, without making a personal ignored file a deployment dependency.

`light_sword_style` was retired in commit `40c254d233f85b8d880e0a5dc90ca2866a0d7e72`. The approved search found no live production/main-spec residue; the lone current source reference is ignored `tmp/story_settings/character/LidziaRosenthal.md:40`, with historical log/archive mentions. In the tracked review document record its correction as common sword training plus `flowing_strikes`. Do not restore the key, add an alias, rewrite archives/logs, commit ignored personal files, or promise an ignored-file edit as shipped acceptance. The owner may separately update that personal reference; no runtime task depends on it.

### D5. The presentation actives bound follows the widened roster

The character panel's flattened `actives` bound (`MAX_ACTIVE_ROWS`, mirrored by the JS wire validator
and parity-guarded) is a fail-closed guard that must sit above every legitimately assembled active
row set. The completed elf baseline lifts the largest shipped card from 86 to 102 active rows (2
declared, 25 fire/dark mastery-closure actives, the 16 authored roots, `basic_attack`, and 58
unlocked act-catalogue acts), so the bound moves 96 -> 128 and the delta spec carries that one
number. Dropping authored baseline roots to fit the old bound would let the guard shape content:
the bound follows the roster, never the reverse. `passives` stays 32, the payload shape and the
canonical JSON envelope are unchanged, and the worst-case actives payload still fits.

## Acceptance and automated evidence

Use existing `world.lore.tests.test_player_presets` generic integrity checks for kinds, references, eligibility, duplicate/finite XP and budget constraints. Extend an existing representative activation/companion test only when a generic consumer boundary needs coverage: construct from an actual chosen preset, compare stored literal bases with the resolver's selected source, observe closure and usable existing mastery, reload, and check an untouched recipient. No tests approving exact roster identities, initial XP tables, prose, labels or counts.

Existing synthetic tests from `complete-elemental-mastery` prove closure and explicit-precedence mechanics. This data-only change introduces no new behavior requirement. Human review of the authored matrix checks that every current eligible ordinary root has positive initial development, mastered closures remain lawful, deeper abilities are preserved and disallowed keys are absent. Generic data relationship checks may derive eligible roots and assert positive initial development for current elf templates; derive from registry identity/category and normalized kits, without copying this matrix or numeric levels into tests.

## Risks / Trade-offs

- Literal kits are verbose. Keep per-card declarations with current project conventions; do not add a dynamic global baseline injector that changes future content automatically.
- Explicit XP overrides shared seeding. D2's mastered-closure omission and greater-required-depth rule avoid suppressing a specialty.
- Original reference prose contains content outside this task. Review only approved non-sexual facts and leave unrelated content unchanged.

## Human review document

The implementation's `docs/lore/character-template-alignment.md` is the review authority for authored builds, innate/source fidelity and role wording. This planning `design.md` supplies its full decisions. These qualities receive human review; tests establish parsing, eligibility, construction and generic graph relationships.

## Migration Plan

Source-data clean cutover on fresh activation/build only. No existing-character reset, live save rewrite or migration. Revert the data commit as a unit if review fails. Keep both prerequisite logic changes intact when reverting this optional authored roster alignment.
