## 1. Investigate

- [x] 1.1 Check `world/lore/elements.py`'s `ELEMENT_REGISTRY` for a neutral/physical-only element token;
      if one exists and fits better than `dark`, use it for `dual_blade_mastery` instead

## 2. Label/description edits

- [x] 2.1 Update `guardian_instinct`'s label/description to 護主本能 flavor
- [x] 2.2 Update `blade_art_mastery`'s description to cover both 劍術 and 刀術
- [x] 2.3 Confirm neither skill's `key` or `effects` changed (diff review)

## 3. New skill

- [x] 3.1 Add `dual_blade_mastery` to `world/skills/registry.py` per the spec's field values

## 4. Tests

- [x] 4.1 `dual_blade_mastery` casts successfully via the existing `damage` handler
- [x] 4.2 Existing `skill-registry` scenario suite still passes for the two edited skills (effects
      unchanged, only display text differs)
