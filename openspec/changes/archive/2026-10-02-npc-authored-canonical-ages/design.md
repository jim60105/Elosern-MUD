## Context

See proposal.md for P2-1. Static source: `guild_economy._create_and_initialize_host` (137–171) initializes a profile card without age data; `guild_exams._spawn_opponent` (244–303) calls `ensure_npc_canonical_age` before resolving the authored card. The helper (`typeclasses/npcs.py:23–36`) independently sets missing fields to 18. `NpcProfile` (`world/lore/npc_profiles/shape.py:60–82`) currently has no mechanical age fields. Existing `npc-canonical-age` and `guild-rank-exams` specs explicitly pin 18 and must be amended, not bypassed.

## Goals / Non-Goals

**Goals:** New/reused host identity initialization uses explicit authored values when fields are absent; new exam opponents agree with their profiles. Ages remain mechanical, read-only editor context, not parsed from mutable prose.

**Non-Goals:** No age extraction from edited cards, NPC age editor, extra stats, automatic ongoing aging, companion/template changes, bundle/generated-quest integration, legacy DB repair or cutover.

## Decisions

### Put the age pair on the existing authored profile

Extend frozen `NpcProfile` with required `age` and `apparent_age` integer fields (bool rejected), both inclusive 0..10000. Update every profile constructor and synthetic fixture; no compatibility defaults on the authored type. Reuse the existing pure canonical age validation authority, or its exact bounded integer contract without rules-layer imports into lore. Reject invalid profile ages with the profile key before producer writes. This is smaller and less drift-prone than duplicating ages on both place and rank declarations, and unlike prose parsing remains stable after editing.

### Complete static inventory and approved values

All 32 shipped profile-backed sources are affected by the 18 fallback. The table defines initial values, not a mandate for exact-string prose tests. Host references come from place/service identity; examiner references from the rank registry. Verify the actual source registries match this inventory at implementation time rather than trusting the historical count.

| Slice/source profile | age | apparent_age | Existing authored constraint / narrow correction |
|---|---:|---:|---|
| altoria_lower / altoria_eatery_owner | 52 | 52 | Early fifties; restaurant operating over twenty years |
| altoria_lower / altoria_tavern_keeper | 36 | 36 | Thirties; ten years running inherited tavern |
| altoria_lower / altoria_innkeeper | 59 | 59 | Nearly sixty; nearly twenty years running inn alone |
| altoria_lower / altoria_bathhouse_keeper | 44 | 44 | Forties; twenty years at bathhouse |
| altoria_lower / altoria_guard_captain | 45 | 45 | Joined at seventeen; ten years at gate before promotion |
| altoria_trade / altoria_merchant | 44 | 44 | Forties; caravan work before owning shop |
| altoria_trade / altoria_blacksmith | 43 | 43 | Around forty-five; entered at fourteen, nearly thirty years at forge |
| altoria_trade / altoria_tailor | 33 | 33 | Early thirties; entered at sixteen, took over ten years ago |
| altoria_trade / altoria_jeweller | 28 | 28 | Twenty-seven/eight; apprentice at fifteen |
| altoria_trade / altoria_alchemist | 40 | 40 | Around forty; several years as assistant before shop |
| altoria_trade / altoria_merchant_master | 56 | 56 | Fifties; twelve years as chair after caravan career |
| altoria_guild / altoria_guild_master | 50 | 50 | Around fifty; began at seventeen, fifteen years as master after field and clerical careers |
| altoria_upper / altoria_high_priestess | 40 | 40 | Twelve + twenty years serving + eight as priestess |
| altoria_upper / altoria_sanctum_deacon | 35 | 35 | Around thirty-five; entered at twenty |
| altoria_upper / altoria_noble_watch_captain | 40 | 40 | Joined at sixteen; assigned at thirty, ten years leading. Correct appearance from early forties to around forty |
| altoria_upper / altoria_drill_instructor | 48 | 48 | Eighteen + twenty years on border + ten at drill ground. Correct appearance from fifties to late forties |
| altoria_upper / altoria_academy_dean | 65 | 65 | Sixties; clarify forty years of research includes the latest fifteen as dean, not sequential 40+15 after entering as a teenager |
| ciaran_homes_a / ciaran_elenis | 980 | 42 | Actual age near one thousand; appears early forties |
| ciaran_homes_a / ciaran_gwenaera | 420 | 23 | Centuries of jewelry-making; appears early twenties |
| ciaran_homes_a / ciaran_hailiel | 480 | 30 | Watched smiths for two hundred years before taking up forge; appears thirty |
| ciaran_homes_a / ciaran_lareneth | 390 | 26 | Centuries cooking; appears twenty-five/six |
| ciaran_homes_b / ciaran_nireth | 460 | 33 | Centuries tending herbs; appears early thirties |
| ciaran_homes_b / ciaran_teliel | 620 | 28 | Several hundred years watching plus several hundred practicing; appears twenty-seven/eight |
| ciaran_homes_b / ciaran_valwyn | 370 | 20 | Centuries collecting; appears around twenty |
| ciaran_homes_b / ciaran_vethiel | 450 | 36 | Centuries weaving; appears thirties |
| altoria_guild / guild_examiner_f | 33 | 33 | Early thirties; several E-rank years and six as examiner |
| altoria_guild / guild_examiner_e | 26 | 26 | Twenty-five/six; promoted two years ago |
| altoria_guild / guild_examiner_d | 40 | 40 | Around forty; over ten years as a shield bearer |
| altoria_guild / guild_examiner_c | 36 | 36 | Thirties; registered at nineteen |
| altoria_guild / guild_examiner_b | 45 | 45 | Around forty-five; ship and hunting career |
| altoria_guild / guild_examiner_a | 40 | 40 | Around forty; over ten years advancing after knight apprenticeship |
| altoria_guild / guild_examiner_s | 68 | 52 | Deliberately uncertain apparent age; seasoned traveler, no exact narrative claim |

Non-numeric elf and S-rank values are explicit authoring choices consistent with current prose, not facts extracted from it. Preserve their ambiguity in the prose; do not invent birthdays or rewrite official companions/伊洛.

### Apply before fallback, preserve reuse

Allow the existing set-if-absent age helper to receive an explicit validated pair while retaining 18 only for genuinely unauthored callers. Each missing field uses its corresponding authored value independently; never overwrite a present value even when it differs from today's profile. Host creation supplies the pair inside its existing transaction before publication; host reuse supplies it at the existing age-ensure point without reinitializing/repairing the persona. Exam creation resolves/validates the profile pair before defaulting and initializes ages/card in the existing all-or-nothing start. Maintain service ids, keys, traits, schedule, and title semantics. Source edits and restarts never recompute ages from a post-edit card.

## Risks / Trade-offs

- [Lore chronology contains unrelated contradictions] → Correct only the three identified local inconsistencies above, review all rows against their appearance/history, and keep service/dialogue semantics unchanged.
- [Generic fallback runs first] → Update the existing age-ensure callsites in creation and reuse; prove actual fresh host/exam ages, not mere field forwarding.
- [Constructor change affects fixtures] → Update all constructors without aliases/default compatibility and keep synthetic tests free of shipped prose assertions.
- [Shipped data drift] → A registry-derived data contract checks bounded explicit pairs and source coverage; editorial review handles prose consistency rather than regex age extraction.

## Migration Plan

No migration or runtime cutover. Implement on a fresh development DB using `docs/development/database-reset.md` per design §13b. Existing present age attributes remain protected on normal reuse; this is not an upgrade repair path. Roll back code/content together and reset disposable development data if needed.
