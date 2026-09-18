## Context

`parse_effect` splits `damage:<element>:<school>` on two colons and hands the two segments to
`DamageEffect(element=..., school=...)` without validating either against a registry
(`world/skills/effects.py:1077-1084`). The element segment is therefore already unvalidated slop in
practice — synthetic fixtures ship `damage:t_dummy:physical`, `damage:t_glowmire:magic`,
`damage:physical:physical` and even `damage:nope:magic` — and the field has exactly one
reader in the whole codebase — `world/rules/progression.py:509`, which compares it to the skill's own
element inside `_is_elemental_magic`. That reader is unreachable for an elementless effect: the
function returns at line 505 when the skill declares no element, and D3's check forbids the one shape
that could reach the comparison with a `None` on the other side. Every other consumer that looks
elemental reads a different field:

- `world/rules/combat.py` reads only the school (via the attack-key selection) and the
  `DamagePolicy`; the parsed element never enters the damage formula, the event log line, or the
  projection. It does, however, independently re-parse and validate the raw `effect_id` string in
  its own `_parse_damage_effect` helper (a second, duplicate parser of the same grammar, separate
  from `world.skills.effects.parse_effect`) purely to gate `element not in ELEMENT_REGISTRY` before
  discarding the element and keeping only the school — this gate had to learn the reserved `none`
  token too (found during implementation; corrected in `_parse_damage_effect` alongside D1).
- `world/rules/combat_view.py:365` exports `skill.element.key` — the `SkillDef` field — which
  `SkillDetailPane.vue:50` renders as a visible badge.
- `world/rules/progression.py:494` (`_is_elemental_magic`) gates the affinity practice factor on a
  skill whose parsed effects include a **magic-school** damage of the skill's **own** element — the
  one place the parsed element is read, and only after the skill's own element is known non-`None`;
  its docstring names `basic_attack` as the reason the element field alone cannot decide, which is
  why D4 moves that example when the row converts.
- `world/skills/cost_tiers.py` requires both an element and an `mp` cost for tier labelling and
  freeform eligibility, so an SP-costed physical art is outside both by construction.

So the element field's real axis is "which magic affinity does this skill run on", and the field
being pressed into service as a classification carrier for weapon arts is the defect. Classification
already has its own field: `SkillCategory.MARTIAL_ARTS`.

## Goals / Non-Goals

**Goals:**

- Give the damage grammar a way to say "this skill has no element", so a physical weapon art is not
  forced to borrow a placeholder that the UI then renders as a badge.
- Fail closed on the one declaration that would make presentation and effect disagree.
- Keep the change small enough to review in one sitting and to land independently of any catalog.

**Non-Goals:**

- Adding a ninth `ELEMENT_REGISTRY` entry for 武藝. Measured and rejected (D2).
- Validating the element segment against `ELEMENT_REGISTRY`. 217 test sites author `damage:` strings,
  several deliberately with non-registry tokens; tightening that is a separate, larger cleanup.
- Re-authoring `light_sword_style`, whose `light` is lore-true (D4).
- Any settlement, audience, policy, buff, modifier or lineage behavior.

## Decisions

**D1 — The reserved token is `none`, not a shortened two-segment form.** `damage:physical` would
parse as element `physical` with an empty school under the existing split, so a two-segment form
cannot be added without special-casing the ambiguity. `damage:none:<school>` keeps the grammar's
shape (prefix, element segment, school segment), reads as prose, and cannot collide with a registry
key (`none` is not and will not be an element). `DamageEffect.element` widens to `str | None` and the
reserved token is the only input producing `None`.

**D2 — A ninth element for 武藝 was measured and rejected.** `ELEMENT_REGISTRY` is a world-lore
registry with player-facing consumers well outside the skill system: `world/rules/creation_wizard.py`
builds the character-creation affinity picker from every entry, `world/rules/lore_knowledge.py:86`
publishes the registry as the codex's `element` category, `world/imports/validate.py:381` and
`world/rules/character_creation.py:91` accept any registry key as a character affinity,
`world/ai/character_creation.py:423` lists the keys into the LLM prompt, `world/lore/titles.py:380`
draws on them as title vocabulary, and `world/rules/combat_view.py:432` groups the skill panel by
them. A 武 entry would therefore be selectable as a character's elemental affinity and appear in the
codex as a world element, and it would collide with the shipped requirement
`skill-registry::All eight elements have a mastery skill`. Every one of those consumers would need a
new exclusion rule — more new behavior than the defect is worth, and all of it to express "no
element", which the grammar can simply say.

**D3 — The consistency check is one-directional.** Rejecting an elementless effect on an
element-bearing skill costs nothing: no shipped or synthetic definition has that shape, because the
token does not exist before this change. Rejecting the reverse (an element-bearing effect on a skill
declaring no element) would retroactively invalidate an unknown number of the 217 fixture sites and
possibly shipped rows, converting this change into a fixture migration. The reverse shape is
pre-existing slop, is not what this change is for, and stays legal.

**D4 — `basic_attack` converts here; `light_sword_style` does not.** The two shipped placeholder
tokens are not the same case. `basic_attack` is 基本攻擊, the universal innate sword swing every entity
owns, and its `fire` is pure placeholder — it is the reason `_is_elemental_magic` exists and the
reason this defect was noticed at all. Converting it is a single row (`element=None`,
`damage:none:physical`) and is the honest close of the loop: creating a token to say "no element" and
leaving the game's most-used elementless attack declaring 火 would be debt with no reason to exist.
Its key, label, zero cost, kind, target, category, faction constraint, damage school and
innate-ownership membership all stay, so `universal-action-ownership`
(「a zero-cost active SINGLE/ENEMY physical-damage skill」), `monster-action-policy`'s fallback,
`freeform-casting`'s ineligibility example (which cites the missing `mp` cost, not the element) and
the webclient combat-menu contract are all untouched. The only observable difference is that the
combat dock stops rendering an element badge for it.

`light_sword_style` keeps `light`. 光劍架式 is a light-magic weapon art in the lore, not a steel
swing, so its element is true rather than borrowed; it also inherits `basic_attack`'s former role as
the spec's worked example of a physical skill that does carry an element
(`skill-lineage::Successful ACTIVE resolution accruses lineage practice XP`, whose prose moves in this
change). `skill-registry::light_sword_style deals damage via the standard damage convention` therefore
stays green with no delta.

Two text consumers follow the conversion: the `_is_elemental_magic` docstring in
`world/rules/progression.py`, which walks through `basic_attack` as its case study, and the
skill-lineage requirement's parenthetical. Both move to `light_sword_style`; the rule each explains is
unchanged.

**D5 — Evidence is behavioral and synthetic.** The reserved token is proved by resolving real casts
through the shipped pipeline (an elementless strike against an element-bearing twin under fixed
rolls, and a practice accrual comparison between an affinity-bearing and a neutral actor), not by
asserting that `parse_effect` returns a particular dataclass field. No shipped content is named.

## Risks / Trade-offs

- **`DamageEffect.element` becomes nullable.** Any future consumer must handle `None`. Today there is
  no consumer at all, and the widened annotation is the signal that one must decide what an
  elementless effect means before reading it.
- **`none` as a magic string.** It is a reserved word in a grammar that otherwise looks up a
  registry. The alternative — a registry entry meaning "not an element" — is D2's rejected shape and
  strictly worse, because it makes the non-element selectable everywhere an element is.
- **The one-directional check leaves the reverse contradiction unguarded.** Accepted with eyes open
  (D3); the martial catalog authors both sides consistently, and a future cleanup that validates the
  element segment against the registry is the natural place to close it.
- **Converting `basic_attack` touches the most-resolved skill in the game.** Mitigated by the shape
  of the change: one field and one effect string, with the school — the only segment settlement reads
  — unchanged. The risk that repays it is real: every future weapon art would otherwise copy the
  placeholder, which is exactly how the current five-row wart accumulated.
