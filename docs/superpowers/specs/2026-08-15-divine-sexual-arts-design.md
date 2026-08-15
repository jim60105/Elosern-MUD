# 神之秘法：性愛系統 — Design

**Date:** 2026-08-15
**Status:** Approved (pending final user review)
**Scope:** `world/skills/sexual_acts/divine.py`, `world/rules/sexual_state.py`,
`world/rules/rulebook/sexual.yaml`.

Part of the [Sexual Act System document set](2026-08-15-sexual-act-system-overview-design.md).
Covers proposals `C7a` (three acts reusing existing mechanisms) and `C7b` (four acts requiring new
sanctioned mutators).

---

## 1. Position in the Design

神之秘法 is defined in world lore as the highest technique for altering the world through divinity.
The skill-system redesign shipped it as free-cost, race-gated ACTIVE skills, deliberately without a
new numeric resource (its D7). This line inherits that position and takes it seriously:

> **Every balancing mechanism the other five lines depend on has exactly one 神之秘法 built to break
> it.**

That framing is the design. It is not an escalation of magnitude; it is a set of targeted exemptions.

### 1.1 What gates them

Not counters. `requires_divine_arts=True` routes through the shipped `_step1_divine_arts_gate`,
which rejects any actor whose `RaceProfile.can_use_divine_arts` is false and also rejects an actor
with no resolvable race, so the gate never silently opens. That is an already very narrow door, and
it is the containment for this entire line.

Two consequences follow, and both matter:

- **Counter thresholds do not apply.** These acts are visible and castable from the moment a
  qualifying character exists.
- **The 性魔法主宰 blanket unlock does not reach them.** That unlock covers the counter-gated
  catalogue only. Mastery and divine arts are two unrelated acquisition paths, and conflating them
  would let a mastery holder cast world-altering mysteries.

### 1.2 The exemption that makes them break

Overview D-4 requires every act to apply pleasure to its own actor. That single rule is what stops
sex acts being a free action-denial engine: sustained offensive use degrades the actor through the
shipped `high_arousal_agility_accuracy_penalty` and eventually locks their own actions.

**神之秘法 acts are exempt.** The exemption is keyed on the existing `requires_divine_arts` data
field, never on a hardcoded key list, so the structural invariant test remains meaningful for every
other act.

Divinity does not injure itself. Every other act in the game punishes overuse; these do not, and
that asymmetry is the whole point.

---

## 2. `C7a` — Three Acts Reusing Existing Mechanisms

These require no new `SexualState` surface at all.

### 絕頂律令 — breaks the multiplier economy

`AREA`. Sets every enemy's `pleasure` to 100 outright, ignoring sensitivity, shame, and participant
multipliers. Everyone caught climaxes at the next upkeep: a whole-team action lockout plus a
whole-team SP drain, from one free action.

Implemented by emitting the shipped `extreme_stimulus_applied` event, whose rule
`arousal_extreme_stimulus_to_max` becomes `{field: pleasure, set: 100}` after the gauge change. The
multipliers are bypassed because the rule *sets* rather than adds — no new mechanism is needed to
ignore them.

### 時姦 — breaks the per-round cost of suppression

`SINGLE`. Forces several consecutive climax extensions from one action, so the caster does not spend
a turn per extension.

Ordinary extension is a 1-for-1 action trade, which is exactly what keeps chain-suppression fair
([Pleasure Model](2026-08-15-sexual-pleasure-model-design.md) §3.5). 時姦 pays once and collects
several rounds. It sets `pending_climax_extension` to a count greater than one — the field is an
integer for precisely this reason — and upkeep decrements it, emitting `climax_extended` each round
until it is exhausted.

Thematically this is the sexual application of the same divinity behind `divine_time_dilation`.

### 神域搾取 — breaks the resource economy

`SINGLE`. Converts the target's accumulated pleasure directly into the caster's MP, SP, **and** HP,
uncapped by the ratio that bounds the catalogue's 搾取.

Writes through `entity.traits`, the surface the effect handlers already declare, so gauge floors and
ceilings apply unchanged and rollback covers it.

---

## 3. `C7b` — Four Acts Requiring New Sanctioned Mutators

Each of these needs one new, explicitly named mutator on `SexualState`. None weakens an existing
guard; each adds a separate, auditable door that no ordinary rule path can reach.

### 感度創世 — breaks the sensitivity build-up curve

`SINGLE`. Sets **every** body part of the target to `敏感異常` (×2.5) permanently.

New mutator: `SexualState.saturate_sensitivity()`. It writes through the existing
`_SensitivityProxy`, seeding every `BODY_PARTS` member (or `GENERIC_BODY_PART` for a `Monster`).

This hands over, in one action and on someone else's body, what the catalogue is designed to take
tens of hours of part-specific training to reach.

### 恥辱剝奪 — breaks the shame inhibition arc

`SINGLE` or `SELF`. Permanently pins the target's `shame` at `成癮`, locking in the ×1.6
amplification and removing the inhibition trough the 羞恥線 is built around.

New mutator: `SexualState.clamp_shame_to(level)`. The mechanism is **already in the codebase** —
`SexualState.__init__` clamps monster `shame` with `shame.min = shame.max = 0`. This pins it at the
ceiling instead of the floor, using the same `OrderedLevelTrait` bound setters. The mutator exists so
that the clamp has one sanctioned owner rather than an effect handler reaching into trait internals.

### 絕對從屬 — breaks the consent system

`SINGLE`. Permanently marks the target as auto-complying toward this caster; every future resist
contest between them short-circuits.

New state: a `submission_marks` set of caster keys, stored in the existing `sexual_state` attribute
category beside `virgin` and `experience_types`, with `SexualState.mark_submission(caster_key)` as
its sole mutator. The resist contest consults it at the same point it consults the affinity
`auto_comply` flag, so there is one short-circuit path, not two.

Where affinity's `auto_comply` is *earned* compliance at `至愛`, this is compliance by fiat, with no
affinity requirement and no way back.

### 無垢回歸 — breaks irreversibility itself

`SINGLE`. Restores `virgin` to `True`. **`experience_types` is not cleared.**

New mutator: `SexualState.restore_purity()`.

This is the one act in the set that touches a live shipped requirement, and it is handled carefully
rather than quietly:

- The `sexual-state-handler` requirement constrains **the public setter** — "once the `SexualState`
  **public setter** sets it `False`, no later mutation **through that public setter** SHALL be able
  to set it back to `True`". A separately named mutator does not weaken that: the setter remains
  one-way and every ordinary rule path still cannot reverse the flag. **No shipped requirement text
  needs to change.**
- The same requirement's `experience_types` clause is absolute — "the handler SHALL expose **no**
  replacement or removal method". Clearing experience would require rewriting a live requirement and
  its tests, so this act deliberately leaves it intact.
- `2026-07-29-ai-mud-engine-design.md` §6.4 describes `virgin` as "one-way, irreversible". This
  document **explicitly amends** that description: irreversible by every path except one race-gated
  divine mystery. Recorded as overview D-10, per the project rule that the design document wins
  unless a change amends it explicitly.

Leaving experience intact is also the better fantasy: the body is restored, the memory is not.

---

## 4. Existing Skills in This Line

Three skills already exist and are recategorised into `sexual_act` by the
[skill category system](2026-08-15-skill-category-system-design.md) D-5, with no change to how they
are acquired:

| Skill | New group | Note |
|---|---|---|
| `divine_sexual_arts` (神之秘法：性愛系統) | 神之秘法 | Its shipped `sexual_event:stimulus_applied` effect is superseded by this line's acts; it is retained as the line's entry-level mystery |
| `divine_sexual_mastery` (性魔法主宰) | 精通 | Carries `SexualMasteryEffect`; grants the catalogue blanket unlock |
| `reincarnation_boon_yuna` (轉生祝福·悠奈) | 精通 | Carries `SexualMasteryEffect`; same blanket unlock |

---

## 5. Error Handling & Validation

| Condition | Behaviour |
|---|---|
| A non-divine race casts one | `_step1_divine_arts_gate` rejects with `DIVINE_ARTS_FORBIDDEN`. Unchanged shipped behaviour. |
| An actor with no resolvable race | Rejected. The shipped gate fails closed. |
| A divine act declaring `actor_pleasure_ratio > 0` | Permitted — the exemption removes the *requirement*, not the *option*. |
| A **non**-divine act declaring `actor_pleasure_ratio == 0` | Structural test failure. The exemption is scoped strictly to `requires_divine_arts`. |
| `restore_purity()` called on an already-virgin entity | No-op, no error. |
| `clamp_shame_to()` on a `Monster` | Rejected. Monster `shame` bounds are already pinned at the floor by construction; re-pinning at the ceiling would contradict the shipped monster baseline requirement. |
| A mid-pipeline failure after a permanent mutation was staged | Full rollback through the declared `sexual` surface. Every mutation here is staged as a `PendingEffect` like any other; "permanent" means no decay path, not un-rollbackable. |

---

## 6. Testing Strategy

- **Gate:** each of the seven rejects for a non-divine race and for an actor with no race; each is
  castable by a divine-capable race regardless of every counter being zero.
- **Blanket-unlock isolation:** an entity owning 性魔法主宰 has the full counter-gated catalogue in
  `owned_keys()` but **none** of these seven, absent a divine-capable race. This is the §1.1 claim
  and the most important test in the document.
- **Exemption scope:** a structural test proving the D-4 invariant is waived exactly for
  `requires_divine_arts` acts and for no others.
- **絕頂律令:** every enemy in an AREA reaches `pleasure` 100 regardless of their shame and
  sensitivity levels; a low-sensitivity, high-shame target reaches 100 identically to a saturated
  one.
- **時姦:** one cast produces the declared number of `climax_extended` emissions across successive
  upkeeps, each charging the half SP cost, with the caster spending exactly one action.
- **神域搾取:** caster MP/SP/HP rise and are capped at their maxima; target pleasure falls.
- **感度創世:** every `BODY_PARTS` member reads `敏感異常` afterward; a `Monster` target has
  `軀體` saturated and no other key created.
- **恥辱剝奪:** `shame` cannot subsequently move in either direction, including under `decay_tick`;
  the pleasure multiplier is ×1.6 thereafter.
- **絕對從屬:** every subsequent resist contest between that pair short-circuits; contests involving
  a different caster are unaffected.
- **無垢回歸:** `virgin` is `True` afterward; `experience_types` is unchanged; the ordinary public
  setter still cannot reverse the flag afterward — the shipped requirement's own scenario must stay
  green, which is the proof that the guard was not weakened.
- **Rollback:** a forced mid-pipeline failure after each permanent mutation restores the prior state.
