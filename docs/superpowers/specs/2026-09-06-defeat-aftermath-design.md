# Defeat Aftermath Design

Date: 2026-09-06
Status: approved by the project owner in a brainstorming session (sections 1-3, final decisions below)
Change split: `defeat-aftermath-core` (PG skeleton, independently shippable) →
`defeat-aftermath-adult-scenes` (adult layer, depends on core)

## 1. Problem and current state

Today player defeat is one line of prose and nothing else. `_terminal_outcome()`
(`world/rules/combat_session.py:1292`) returns `"defeat"`, the session settles
time, the flag clears, and the player keeps HP 0 as a passive statue. The
surrounding guards (heal cannot revive, `submit_player_action` rejects a
0-HP actor, settlement never regenerates a dead actor) plus unguarded
escape routes (movement has no HP gate; `rest` regen has no life check;
`skip_safety` only blocks active combat and a co-located living monster) mean
the real loop is: lose → stand at 0 HP → walk out → `rest` back to full →
refight the same coordinate, whose wilderness monster respawns as a fresh
full-HP object on the next activation. Defeat carries zero mechanical,
narrative, or economic cost.

## 2. Goals and hard constraints

- **Always continuable, zero record loss.** No permadeath. Quest progress,
  protected-objective state, guild rank, guild merit, affinity values,
  inventory, wallet, and the character itself are untouched by defeat.
  Enforced as regression assertions, not intentions.
- **Adult content is the core** of the defeat fantasy (owner decision).
- **Any defeating entity may initiate** an adult scene; the existing d100
  resist contest (`_step4b_sexual_resist_gate`, `world/rules/action.py:407`)
  is the hard rail — the victim resists, and full resistance collapses the
  sequence into the PG variant.
- **No monetary or item loss.** Monsters do not use a coin economy, so
  looting gold is world-view-inconsistent and removed (owner decision).
  Items are also never removed.
- **No affinity writes.** Being violated by a monster has no causal channel
  to how a companion feels about the player, so the affinity system is not
  touched at all (owner decision).
- **World tone** ("light adventure, avoid oppressive darkness",
  `tmp/story_settings/world_info.md` rule block): the negative weight lands
  on time, degraded body state, and embarrassed-flavor prose, not suffering.
- **Offline determinism.** The whole aftermath executes fully with every LLM
  profile dead; Narrator prose is an overlay on a deterministic EventLog.
- **Single-writer boundary.** All state changes are applied by the
  deterministic core (`world/rules/`); `world/ai/` only renders.
- **Guild exams are exempt.** The simulated-battle full-restoration path is
  unchanged.

## 3. Mechanics (deterministic core)

All steps run inside the existing `settle_session()` `transaction.atomic()`
for hostile-mode defeat. There is no interactive downed state: "waiting to
recover" is fiction over an atomic settlement.

### 3.1 Timeline

1. **HP floors at 1** and the player is marked knocked out — the nonlethal
   floor precedent (companions, guild exams) extended to the player. This
   keeps the "settlement never revives a defeated player" invariant
   untouched and makes the fiction ("crippled, conscious") match the state.
2. **Victory arousal table**: every living member of the winning foe team
   gains archetype-keyed arousal steps (YAML table: goblin +2, beast +1,
   slime +3 ...). Arousal accumulated during combat (e.g. the player's own
   sexual-magic casts, or sexual acts the monster used via the combat
   catalog) is already stored and counts toward the threshold. This opens
   the per-archetype monster sexual-baseline seam that the design doc
   §6.4 (amended 2026-08-09) explicitly deferred; this change owns it.
3. **Violation sequence**: for each living violator whose post-victory
   arousal ≥ its archetype threshold (YAML), repeat up to the archetype's
   per-victory attempt cap:
   - Select a target from the non-fled allied roster (player + knocked-out
     companions; the player is always in the pool). Selection uses the
     seeded d100 pipeline (replayable, deterministic).
   - One resist roll per attempt (existing resist-gate formula, victim
     resisting). Success → that attempt's deltas shrink, sequence may
     shorten; **full resistance across attempts → the sequence truncates
     into the PG variant**.
   - Each attempt applies its YAML-declared state deltas through existing
     EventLog kinds (`sexual_transition`, `pleasure_gain`, `sexual_counter`,
     counter records) and **advances the world clock** by its declared
     duration.
   - Counter crediting is symmetric for every participant (§3.4).
4. **Violators depart** (mechanically necessary: `skip_safety` forbids
   time-skip with a living monster in the room, which would strand the
   player):
   - Wilderness population monsters: despawn and drop from
     `itemcoordinates`. The next coordinate activation respawns per the
     untouched population model.
   - Quest-tracked / scene monsters are **never removed** (a vanished
     extermination target would soft-lock its quest = disguised record
     loss). They stay, narratively ignoring the player; the player may
     leave (movement has no HP gate) and rest elsewhere.
5. **Recovery advance**: the clock advances until HP reaches
   `ceil(max_hp × 0.05)`, computed from regen rate reduced by the weak debuff.
6. **Wake-up**: on the spot, HP at 5%, weak buff mounted, sexual state
   rewritten, world time spent.

### 3.2 Loss menu (exhaustive)

Only three loss channels exist, all on existing machinery:

1. **World-clock time** (violation durations + recovery to the 5% threshold).
2. **Weak debuff** (buffs surface, self-expiring; core effect is a reduced
   regen rate, which is what kills the zero-cost loop).
3. **Sexual-state residue** on everyone violated — `combat_modifiers.yaml`
   already degrades agility/accuracy at high arousal, so a violated party
   walks into the next fight with a mechanically worse body. The punishment
   compounds through the existing modifier pipeline with zero new systems.

### 3.3 Content switch

`settings` flag `DEFEAT_ADULT_SCENES` (default on — this project's genre).
Off = skip step 3 entirely (one guard); HP floor, recovery, weak debuff,
and PG wake-up still run.

### 3.4 Counter crediting (catalog-wide symmetric convention)

Owner decision: the "actor-only" crediting convention is retired **across
the whole sexual-act catalog**, not just in the defeat writer. Every
consensual or non-consensual sexual act credits every participant's body —
"the body that underwent the act has the record", direction-free. The
defeat-aftermath writer therefore shares one convention with the skill
path; there is no divergence.

- Mechanism: the `participant_counters` field and its handler already ship
  (the `sexual-act-effects` spec increments `participant_counters` on every
  other participant). Existing acts merely declare `participant_counters=()`;
  the change is act-definition data plus spec/test rewrites, not new
  machinery. Default rule: every non-solo act credits the target the same
  counter set it credits the actor.
- Semantics re-documented per counter (keys unchanged):
  `hostile_act_count` = hostile sexual acts participated in (either side);
  `interspecies_act_count` = acts with a different-species partner (either
  side); `duo_act_count` / `group_act_count` fix an existing oddity where a
  two-person act left the partner with no record. Solo seeds
  (`masturbation_count`) have no target and are unchanged.
- Monster counters are usually transient (population monsters `delete()` on
  departure; the owner accepted this — records persist for surviving scene
  monsters and during any still-live session).
- Downstream effects are real and accepted: both sides' counts feed the
  unlock gates (`hostile_act_count`, `interspecies_act_count >= 20`,
  compound `climax_count` gates) and the title system's
  `COUNTER_THRESHOLD` / `SEXUAL_EXPERIENCE` predicates
  (`world/lore/titles.py`). "Deliberately lose to goblins to unlock
  interspecies acts" remains an accepted farm route; its price is the §3.2
  loss menu.
- No migration: no released users; existing characters' historical records
  are not back-derived.
- Spec surface to re-delta in the same change: `sexual-catalog-combat`
  ("credits … on the actor only" scenarios), `sexual-catalog-interspecies`,
  `sexual-catalog-shame` (`shame_provocative_gaze`: the gaze target did get
  watched — crediting them `watched_count` is the semantically correct
  fix), `sexual-act-seeds` (combat seed only; solo seeds untouched), and
  every pinned regression test rewritten to the symmetric expectation.

## 4. Scene registry and narrative layer

### 4.1 Structure

- `world/rules/defeat_aftermath.py` — new deterministic-core module (same
  side of the wall as `combat_session`, not `world/ai/`).
- `rulebook/defeat_aftermath.yaml` — archetype → scene family registry.
  Families are **structures** (threshold, attempt caps, per-attempt deltas,
  durations, credited counters, PG variant), not prose. Every future
  initiator kind (humanoid NPCs, guild examiners as foes later, church,
  beastfolk) adds rows to the same table; v1 ships monster rows only
  (`engage()` currently admits only `Monster` foes).
- Missing archetype row or unparseable table ⇒ treated as "threshold not
  met" ⇒ PG variant + `log_warn` facade event. Never raises, never blocks
  settlement.

### 4.2 EventLog is the scene

Attempts emit existing log kinds only — no schema change, so the webclient's
current render path consumes defeat scenes for free. The Narrator overlay
renders the EventLog into prose; offline it degrades to per-kind zh-tw
template lines (same shape as `world/rules/action.py`'s built-in
descriptions). Prose never gates state.

### 4.3 Companion handling (two layers only)

1. **Own-state effects (always)**: a selected companion takes the same
   mechanical treatment as the player — own `SexualState` deltas, own
   counter credits, own aftermath digest. Bystanders (conscious, not
   selected) get a lighter digest.
2. **Digest table keyed on the companion's own sexual-state records** (zero
   new numerics, zero race checks — persona is flavor-only per design doc
   D7). YAML rulebook conditions read only existing ordered-level fields:
   - high `sensitivity` + `climax` ≥ 1 ⇒ "residue" positive-ish buff;
   - low `sensitivity` + high `shame` ⇒ "humiliated" negative buff;
   - mid band + full resistance ⇒ no digest buff (pure dishevelment).
   Digest buffs use only the existing buff effect surface (rates / bounds /
   decay).
3. **Wake-up lines** (pure narrative): digest + persona flavor text feed the
   Narrator; offline fallback selects a template by digest. Tone anchor:
   dry banter, not accusation.

No layer writes affinity, gold, items, quests, or rank.

## 5. Edge cases and error handling

| Case | Resolution |
|---|---|
| Whole foe team dies in the same round the player falls | Player-defeat outcome wins (existing precedence); living-violator pool empty ⇒ PG variant |
| No companions present | Pool = {player}; sequence runs normally |
| Fled companions | Excluded from the pool (not present) |
| NPC defeating entity | Registry mechanism applies; v1 tables contain monster rows only |
| Quest-tracked monster | Never despawned; stays in room, narratively ignoring; no soft-lock (movement is HP-free) |
| Crash mid-settlement | Sequence + recovery advance + `settled_tick` marker are one transaction; the recovery path re-runs the full aftermath deterministically (seeded dice replay). `test_solo_defeat_settlement_never_revives_the_player` and `test_restored_dead_player_session_never_revives_the_player` are rewritten for the HP-1 outcome, kept as regression |
| Server restart refreshes a fresh monster next to the weak player | Accepted risk: no outdoor monster-initiated-attack model exists; the player can move/flee |
| `DEFEAT_ADULT_SCENES=False` | Sequence skipped; core losses unchanged |
| Table missing / malformed | PG variant + `log_warn` (`archetype`, `tick` in context) |
| Narrator failure | EventLog is complete; template-line fallback |

## 6. Invariants preserved (explicit)

- Settlement never revives a *dead* actor — the player is never dead (HP
  floor 1).
- Guild-exam simulated-battle semantics fully unchanged (exempt mode).
- `world/ai/` never mutates state; Narrator renders EventLog only.
- Population model ("coordinate is a function") unchanged; despawn happens
  only through the defeat writer, respawn is the ordinary activation pass.
- Currency stays integer copper; defeat touches no wallet field.
- All logging through the `world.observability` facade with snake_case
  event ids and business context keys.

## 7. Testing

Deterministic (fixed-seed) suites, no live LLM:

- EventLog sequence golden: kind order/values per archetype fixture; clock
  delta per attempt; final HP == `ceil(max×0.05)`; weak buff mounted.
- Zero-record-loss battery (same test): affinity, wallet, inventory, quest
  progress, guild rank/merit all byte-identical after defeat.
- Full resistance ⇒ PG variant: truncated sequence, shrunk deltas.
- Digest table three bands (high sens+climax / low sens+high shame / mid +
  full resist).
- Emergent chain: player's sexual-magic cast raises monster arousal ⇒
  longer sequence.
- Companion pool determinism (fixed seed replays same selection order);
  fled companion excluded.
- Symmetric counter crediting: every participant's declared counters +1 per
  act (victim `interspecies_act_count`, aggressor monster credits); the
  skill-path catalog tests rewritten to the symmetric expectation (owned by
  `sexual-counter-symmetric-crediting`).
- Population monster despawn + next-activation respawn; quest-tracked
  monster retained.
- Offline guardrail: every LLM profile failing ⇒ full
  accept-quest → fight → defeat → wake loop completes.
- Exam exemption: existing exam tests green unmodified.
- Shard manifest (`.github/evennia-shards.json`) updated in the same
  change; `covers_requirement` annotations + `tools.spec_traceability
  check` green.

## 8. Change split

| Change | Contents | Independently shippable |
|---|---|---|
| `defeat-aftermath-core` | HP floor 1 + knockout, 5% recovery advance (regen-rate math), weak debuff, violator departure (population despawn / quest-tracked retain), PG wake-up, `DEFEAT_ADULT_SCENES` switch, zero-loss assertion battery, recovery-path rewrites | Yes — a usable PG defeat system |
| `sexual-counter-symmetric-crediting` | Catalog-wide crediting flip: act-definition `participant_counters` declarations, counter semantics re-documentation, main-spec deltas + regression-test rewrites across combat/interspecies/shame lines (solo seeds untouched) | Yes — orthogonal to defeat; prerequisite for the adult layer's shared convention |
| `defeat-aftermath-adult-scenes` | Victory-arousal table + per-archetype monster sexual baselines (owns the §6.4 deferred seam), violation sequence (registry, resist rolls, per-attempt clock advance, companion pool), digest table, companion buffs, Narrator overlay + offline templates | No — depends on core; sequenced after the crediting change so both writers share the one convention |

Rationale: core changes the high-risk `settle_session` semantics (rewritten
existing tests); the adult layer is purely additive on the seam core opens.
The crediting flip rewrites shipped main specs and their pinned tests, so it
gets its own change with its own delta specs and archive pass.
Each change validates and archives on its own.
