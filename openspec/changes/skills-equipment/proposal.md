## Why

This is roadmap item #5 (design doc §11), depending on change 3 (`entity-traits`) for `LivingEntity`'s
declared `skills`/`equipment` seam attributes and the base-value trait boundary. Design doc §3.2
forward-declares `world/skills/` (registry, handler, equipment) as its own package, and change 4
(`import-contract`) has already forward-declared the exact module path and symbol name this change
must satisfy: `world.skills.registry.SKILL_REGISTRY`. Change 4's own skill-key validation is
deliberately degraded to a WARNING until that module exists, with a self-arming test
(`test_skill_registry_self_arming.py`) that sits `skipped` until this change lands and then starts
asserting REJECT-on-unknown-key automatically. Until this change exists, every character import's
`skills`/`passives` array is effectively unchecked — a typo'd skill key silently passes.

Design doc §5.2 also sketches `SkillHandler` and `EquipmentHandler` as declared-but-unbuilt
`LivingEntity` handlers, and §5.1/§5.3/change 3's D-7 establish a hard boundary this change must
honor operationally, not just document: skill multipliers (×10/×100/×1000, per the source cards'
`88*1000` notation) are a resolution-time-only layer and must never be written back into
`entity.traits`.

## What Changes

- Add `world/skills/registry.py`: `SkillKind` (`ACTIVE`/`PASSIVE`) and `TargetSpec`
  (`NONE`/`SELF`/`SINGLE`/`AREA`) as plain `StrEnum`s — forward-declared here (this change needs them
  as `SkillDef` field types now) for change 8 (`action-resolver`) to import rather than redefine,
  mirroring the forward-declaration pattern change 2 → change 4 already established for `Subrace`
  and change 4 → this change already established for `SKILL_REGISTRY` itself. Add the frozen
  `SkillDef` dataclass with exactly the seven fields design doc §5.2 gives (`key`, `kind`,
  `target_spec`, `cost`, `usable_out_of_combat`, `element`, `effects`) — no field added or dropped.
  Add `SKILL_REGISTRY: dict[str, SkillDef]` at the exact forward-declared path
  (`world.skills.registry.SKILL_REGISTRY`), seeded with a representative set (~24 entries, not an
  exhaustive catalogue) spanning every skill category inventoried from the five sample character
  cards: stat multipliers (身體強化 ×100, 身體超強化 ×1000, 基礎身體強化), elemental mastery (火/暗/
  風/光之主宰, tied to change 2's `RankTitle` 主宰 rank), direct spells (火球術, 風刃術, 飛行術),
  weapon arts (雙刀流, 輕劍術, 影斬, 瞬影步), 狀態偽裝, 統御術, and the passive set (防禦本能,
  刀術強化, 極限耐久, 魔法陣理解, 魔力精密控制, 侍從武術訓練, 護主本能, and per-character 轉生特典
  entries for Elosia/Yuka/Yuna).
- Add `world/skills/handler.py`: `SkillHandler`, a facade object constructed from an entity
  (`SkillHandler(entity)`, exposed via a new `entity.skill_handler` property on `LivingEntity`) that
  reads the raw `{"active": [...], "passive": [...]}` dict change 4's loader already writes to
  `entity.skills` (change 3's seam attribute) without requiring any change to how that attribute is
  populated. Provides `effective_value(trait_key)` — the sole place stat-multiplier skills
  (身體強化/身體超強化/基礎身體強化) are applied: it reads `entity.traits.<key>.value` (the base) and
  returns a derived, transient multiplied value, **never** writing back into `entity.traits`. A
  regression test (mirroring change 3's D-9 disguise-boundary tripwire) asserts no function in this
  module multiplies and stores a trait value, and every value `effective_value()` can produce for a
  freshly-constructed entity's base falls in the exact same base-value band change 3 already checks —
  the multiplied *return* value is expected to exceed it; the *stored* trait must not.
- Add the 統御術 (dominion art) data model: a frozen `ConferredSkillGrant` dataclass (`source_key`,
  `skill_key`, `trait_keys`, `scale`) stored in a new, additive attribute (`entity.db.skill_grants`,
  requiring no edit to change 3's typeclass, mirroring change 4's D-13 treatment of
  `entity.db.inventory`). `SkillHandler.effective_value()` folds in any conferred grants at the
  documented scale (Violet's card: a partial ×10 grant from Elosia's ×100 身體強化). The *casting* of
  統御術 — i.e., an entity actually creating a grant on another entity through gameplay — is
  declared as a seam for change 8's `ActionResolver` (effect-resolution step); this change builds the
  data shape and the read-side computation, not the cast-time write path. The analogous partial
  magic-growth-rate grant (Elosia → Violet) is explicitly deferred to whichever change owns
  progression/learning-rate mechanics — noted as an unresolved seam, not built here.
- Wire 狀態偽裝 as a registered `SkillDef` whose effect resolution (a small, directly-callable
  function, not routed through any rulebook engine) can only ever set `entity.db.disguised_stats`
  (change 3's D-8 storage) — it contains no code path that reads or writes `entity.traits`, so it
  structurally cannot violate decision D2 regardless of when change 8 wires it up.
- Add `world/skills/equipment.py`: an `EquipmentSlot` `StrEnum` (`WEAPON_MAIN`, `WEAPON_OFF`,
  `ARMOR`, `ACCESSORY`) borrowing evadventure's wield-location slot *structure* (design doc §4:
  reference only, not its d20 formulas), sized to the sample cards' own equipment shapes (a single
  weapon or a dual-wielded pair, one body armor slot, a small list of accessories). `EquipmentHandler`
  is a facade over the same raw dict change 4's loader already writes to `entity.equipment`,
  providing `.equip()`/`.unequip()`/`.slot_contents()`. Plain module-level functions
  (`add_item`/`remove_item`/`list_items`) operate directly on `entity.db.inventory`, the raw
  attribute change 4's D-13 already established with no seam declaration required.
- Replace the `skills`/`equipment` placeholder `AttributeProperty` declarations in
  `typeclasses/entities.py` with the real handler-access properties (`skill_handler`,
  `equipment_handler`) per change 3's own D-10, which explicitly anticipates this change replacing
  the placeholder "the same way `traits` is mounted" — the underlying `entity.skills`/
  `entity.equipment` attributes themselves are left exactly as change 3/4 defined them, so change 4's
  loader continues to work unmodified.
- Add a verification task confirming change 4's `test_skill_registry_self_arming.py` now runs
  (not skipped) and passes once `world.skills.registry.SKILL_REGISTRY` exists — the acceptance
  criterion for the cross-change contract this change fulfills.

## Capabilities

### New Capabilities
- `skill-registry`: `SkillDef`, `SkillKind`, `TargetSpec`, and `SKILL_REGISTRY` at the exact
  forward-declared path, seeded with a representative cross-category skill set.
- `skill-handler`: `SkillHandler`, the resolution-time-only multiplier boundary, the 統御術 partial
  conferral data model and read-side computation, the 狀態偽裝/D2 compliance guarantee, and the
  declared `ActionResolver` seam (no combat-state branching anywhere in this module).
- `equipment-inventory`: `EquipmentSlot`, `EquipmentHandler`, and the inventory helper functions,
  compatible with change 4's `entity.equipment`/`entity.db.inventory` write pattern.

### Modified Capabilities
- None. `openspec/specs/` is currently empty (changes 1–4 have not been archived yet).

## Impact

- **New files**: `world/skills/__init__.py`, `world/skills/registry.py`, `world/skills/handler.py`,
  `world/skills/equipment.py`, `world/skills/tests/`.
- **Modified files**: `typeclasses/entities.py` — replaces the `skills`/`equipment` placeholder
  `AttributeProperty` declarations (change 3, D-10) with real handler-access properties, per that
  change's own anticipation of this exact replacement. No other file from change 3 or change 4 is
  modified.
- **Depends on**: change 3 (`entity-traits`) for `LivingEntity`, the `skills`/`equipment` seam
  attributes, and the base-value trait boundary (D-7). Transitively on change 2
  (`lore-world-data`) for `ELEMENT_REGISTRY`/`RANK_TITLE_REGISTRY`.
- **Satisfies a forward declaration from**: change 4 (`import-contract`), which reads
  `world.skills.registry.SKILL_REGISTRY` and self-arms its own skill-key validation from WARNING to
  REJECT the moment this module exists — no edit to change 4 is made or required.
- **Consumers deferred to later changes**: change 6 (`buffs-rulebook`) owns the rulebook YAML engine
  that will eventually interpret this change's opaque `effects: list[str]` effect IDs (other than the
  `stat_multiply:` convention this change interprets directly for its own multiplier resolution);
  change 8 (`action-resolver`) owns actually casting a skill — resource checks, targeting, effect
  resolution, and the 統御術 cast-time grant-creation path — reading `TargetSpec`/`SkillKind` from
  this change rather than redefining them.
