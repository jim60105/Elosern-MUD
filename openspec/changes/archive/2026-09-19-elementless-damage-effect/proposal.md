## Why

The martial-arts lineage tree (`docs/lore/skill-trees/martial-arts.md`) authors an eight-node 劍術 route of plain steel swordplay that carries no element at all, but the shipped damage grammar is `damage:<element>:<school>` and offers no way to say "no element". Every shipped physical weapon art therefore borrows an inert placeholder token — `basic_attack` declares `element="fire"` for an ordinary sword swing, `light_sword_style` declares `light` — and `SkillDetailPane` renders `skill.element` as a visible badge, so the combat dock labels a plain strike 「fire」. Landing eight more sword nodes on that placeholder would multiply a lore-visible defect instead of fixing its owning surface.

## What Changes

- `parse_effect` recognizes the reserved element segment `none`: `damage:none:<school>` parses to `DamageEffect(element=None, school=<school>)`, and `DamageEffect.element` widens to `str | None`. Every existing `damage:<element>:<school>` form parses byte-identically.
- `SkillDef.__post_init__` fails closed on one contradictory declaration: a skill declaring an element SHALL NOT also declare an elementless damage effect. The check is deliberately one-directional — an element-bearing damage effect on a skill that declares no element predates this change across shipped and synthetic definitions (217 test sites author `damage:` strings) and stays legal; widening the rule would turn a ten-line primitive into a fixture migration.
- No settlement behavior changes. `school` still selects the attacking stat (`atk_phys` / `magic_power`), and the parsed damage element has exactly one consumer — `world/rules/progression.py:509` compares it to the skill's own element inside `_is_elemental_magic` — which is unreachable for an elementless effect, because that function returns at line 505 for a skill with no element and the one-directional check below forbids an element-bearing skill from carrying one (verified: `world/rules/combat.py` reads only the school and the policy; `world/rules/combat_view.py:365` reads `SkillDef.element`, not the effect token; `world/rules/progression.py:494` gates affinity on a magic-school damage of the skill's own element, so an elementless physical art takes the neutral 1.0 exactly as a placeholder-token art does today).
- The eight-element `ELEMENT_REGISTRY` stays closed and untouched. Classification of a weapon art is already carried by `SkillCategory.MARTIAL_ARTS`; this change stops the element field from being pressed into that role.
- `basic_attack` converts to the new form in this change: `element=None` with `damage:none:physical`. It is the defect's origin — the plainest sword swing in the game declaring 火 — and leaving it behind a token created specifically to fix it would be debt with no reason to exist. `light_sword_style` keeps `light`: 光劍架式 is a light-magic weapon art in the lore, so its element is true, and it becomes the spec's standing example of a physical skill that does carry an element.

## Capabilities

### New Capabilities
None.

### Modified Capabilities
- `skill-lineage`: MODIFIED 「Successful ACTIVE resolution accruses lineage practice XP」 — the prose example of a physical skill carrying an element moves off the converted `basic_attack` to `light_sword_style`, and an added scenario pins the neutral factor for a skill declaring no element. The formula itself does not change.
- `damage-effect-handlers`: MODIFIED 「damage:<element>:<school> is the defined convention for this prefix」 — the element segment additionally admits the reserved token `none`, which denotes the absence of an element rather than a registry lookup; the school segment's stat selection is unchanged.
- `skill-effect-model`: MODIFIED 「parse_effect classifies every declared prefix into a typed dataclass」 — the damage branch yields `element=None` for the reserved token; ADDED 「An elementless damage effect and a declared skill element are mutually exclusive」 — the registry rejects that one contradiction at load, leaving the pre-existing reverse shape legal.

## Impact

`world/skills/effects.py` (the `DamageEffect` field type + the damage parse branch); `world/skills/registry.py` (one added `SkillDef.__post_init__` consistency check, plus the one-row `basic_attack` conversion); `world/rules/progression.py` (the `_is_elemental_magic` docstring cites `basic_attack` as its worked example and must move to `light_sword_style`); `world/rules/combat.py` (one-line fix: `_parse_damage_effect`'s independent `ELEMENT_REGISTRY` gate must also accept the reserved `none` token — found during implementation, not anticipated at proposal time; the element it validates is still discarded immediately after, so no settlement math changes); a new synthetic behavior test module. `world/rules/action.py` and every rulebook YAML are untouched — no audience, policy or modifier path reads the parsed element. `basic_attack`'s key, label, cost, kind, target, category, faction constraint, effects school and innate-ownership membership are all unchanged, so `universal-action-ownership`, `monster-action-policy`, `freeform-casting` and the combat-menu contracts are untouched; the one visible difference is that the combat dock stops rendering an element badge for it. No preset or census row names its element (verified: the shipped registry tests assert only its faction constraint, and the combat-view and webclient element fixtures are synthetic). `.github/evennia-shards.json` needs no edit — the `quests-skills-art-ai-lore` shard's package label `world.skills` already resolves every module under `world/skills/tests/`.

This turn creates planning artifacts only. Do not apply, archive, sync main specs, create feature branches or merge until requested.

## Batch

- depends-on: (none) — this change lands FIRST of the two-change martial wave and may merge on its own.
- Downstream: `martial-arts-catalog` consumes `damage:none:physical` for its eight 劍術 nodes and MUST land after this merges.
- Code conflicts with the in-flight divine wave: `world/skills/registry.py` (this change adds a validator in `SkillDef.__post_init__`; `divine-mystery-catalog` swaps the divine block — different regions of the same file, order-independent but textually adjacent), `.github/evennia-shards.json` (append-only manifest edit; serializes naturally).
