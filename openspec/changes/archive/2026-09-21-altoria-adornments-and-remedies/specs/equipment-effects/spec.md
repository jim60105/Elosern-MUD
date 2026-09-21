## MODIFIED Requirements

### Requirement: The new equipment roster is registered and tradeable
The roster SHALL add the ten designed equipment items — 淨化吊墜, 無懼胸針, 騎士全套板甲,
藥師珠串, 大術師補綴長袍, 誘蠱蕾絲內衣, 迷情絲頸環, 修女聖袍, 光輝聖徽, 聖女聖袍 — each
with a registry presentation identity, an existing price-table key, an effect binding, and a
listing in the offered keys of at least one Altoria shop.
<!-- Was "a listing in the existing general store's offered keys". altoria-adornments-and-
     remedies moves the roster's five accessory pieces to 聖潔王都首飾坊 (the armor pieces
     already sat with 聖潔王都裁縫坊), so the tradeable guarantee is per-roster, not
     per-shelf. The shipped behavioral test already asserts offered-by-some-capital-shop. -->

#### Scenario: New items are purchasable and fully bound
- **WHEN** the capital's shops are inspected after this change
- **THEN** each of the ten new item keys appears in at least one capital shop's offered keys
  with a resolvable price entry and a budget-checked rulebook entry
