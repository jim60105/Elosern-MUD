# WP6 disposition: equipment and shop membership with the military exception (tasks 6.1-6.6)

Baseline `master` = `9c3c14f7`; handover branch tip = `b968aeeb`; WP6 tip before this
closeout commit = `450d0f1b`. This file records what tasks 6.1-6.6 removed, what
replaced it, the data-only membership proof, the twelve deliberately named military
keys and their examiner dependency, the precedence evidence for the non-sellable and
keepsake routes, the one retired requirement id and its re-attachment sites, and the
two independent critiques with every finding dispositioned. It is evidence, not a plan.
No delta spec, no main spec and no other change directory was edited.

## 1. What was removed, and what replaced it

| Removed (expected-content pin) | Where it lived | Replacement (registry-derived) |
| --- | --- | --- |
| The 123-key expected item roster | `world/lore/tests/test_items.py` | Every current entry must carry complete typed metadata, resolve its own `price_table_key`, declare `sellable` and (if roled) be equipment; add/rename/retire is a data edit |
| `len(ITEM_REGISTRY) == 123` and the 13-key `SHOP_REGISTRY` snapshot | `test_guild_config/test_item_offer_definitions.py` | Non-empty registry, per-item metadata loop, and per-shop "references at least one assortment + every derived key resolves" |
| `PRE_SPLIT_OFFERED_KEYS` (58 keys), `SANCTUM_ADDED_KEYS` (12), `MILITARY_ADDED_KEYS`, the capital-union/partition equality, the 13-key assortment roster list, the 4-key elven/shared tuple and the two accessory-bundle exchange rates | `world/lore/tests/test_assortments.py` | Keyed frozen registry self-consistency, every assortment item resolves, every member satisfies its own declared shelf policy, every capital shop exposes exactly its referenced assortment union, and `ShopDefinition` carries no hand-listed key field |
| `NEW_ITEM_KEYS` (10 keys) and its stocking test | `world/rules/tests/test_equipment_effect_rulebook.py` | Every registered equipment item is complete/bijective/price-resolvable, plus `test_stocking_is_authored_data_not_a_registration_consequence` (offers are a subset of registered items; 27 shipped equipment items are unstocked yet still load their rule) |
| `CHURCH_VESTMENTS_AND_EMBLEMS` / `CHURCH_SANCTUARY_DEVICES` name tuples | `world/rules/tests/test_equipment_effect_rulebook.py` | `_role_members(LiturgicalRole.X)` discovered from item lore; the two sub-sets are asserted to partition exactly the roled items |
| The five-subrace lineage item table and the `wooden_club` prohibited-item blacklist | `world/lore/tests/test_starting_kits.py` | Registry reference closure plus the kit's own declared `max_rarity` ceiling; commoner rarity equality and the noble inherited arm are derived/named-scenario assertions |
| `commerce_catalog_baseline.json` (851 lines), the pre-split resolved-catalog equality test, the 18-key `before` price table and the 11/6/13 offer counts | `test_guild_config/test_commerce_rulebook_slices.py` | Deleted; replaced by a structural shipped-directory test and `test_at_par_slice_offers_travel_field_for_field`, which recomputes every resolved five-field offer against the **authored assortment rows** for at-par shops with no `price_scale`/`overrides` (`checked > 0` guards vacuity) |

`world/rules/tests/test_settlements.py`'s `PRE_SPLIT_PLACE_CAPTURE` is a WP4 place-row
guard (keys/order/coordinates/exteriors), deliberately untouched here.

## 2. Data-only membership change proof (6.1)

`test_guild_config/test_assortment_shop_rules.py::ShopMembershipRouteTests`

- `test_a_valid_new_equipment_item_can_be_stocked`: a file-local synthetic equipment
  item is added to `ITEM_REGISTRY`, given one line of shelf membership (the key
  appended to `common_arms.item_keys`) and one complete offer row; `validate_shop_configs`
  then resolves it onto every shop that references `common_arms`. **No spec, no
  shop-specific approval table, no expected-key list is edited** — the change is data.
- `test_every_shop_resolves_its_authored_union_minus_removals_plus_additions` proves the
  other direction on live data: for every shipped shop, the resolved offer set equals
  `union(referenced assortments) - place.excluded_item_keys + place.extra_item_keys`.
- Unstocked validity: `test_unstocked_equipment_item_loads_clean` (rulebook),
  `test_catalog_load_accepts_registered_items_not_offered_by_any_shop` (catalog) and
  `world/skills/tests/test_equipment.py::test_unstocked_equipment_item_equips_and_applies_adjustments`
  (real equip/applies) were retained unchanged.

## 3. The twelve deliberately named military keys (6.5)

`world/lore/tests/test_assortments.py::MilitaryPairMembershipTests` names exactly:

`military_{e,d,c,b,a,s}_sword` (6) and `military_{e,d,c,b,a,s}_armor` (6).

`test_the_twelve_named_pairs_are_registered_and_stocked` asserts the set of all
`military_*` registry keys equals those twelve, and that each is registered sellable
equipment whose modifier key is its own key and which some shop stocks;
`test_each_pair_rides_its_named_capital_shelf` asserts the swords sit in `common_arms`
and the armor in `common_outfits`.

**Examiner dependency (the reason for the exception):** the class docstring records
that `world/rules/rulebook/guild_exam_restrictions.yaml` names the B/A/S pairs as the
rank gear a restricted examination must wear, and that the E-S examination kits depend
on the whole family, so this one membership contract stays a narrow tagged test. The
retained named military tests in `test_equipment_effect_rulebook.py`
(`MilitaryAuthoringContractTests`, `MilitaryRuntimeSmokeTests`, and the named
`military_s_sword` budget case) are unchanged, and the examiner-facing statements and
tests (`world/rules/tests/test_guild_exam_restrictions.py`) are untouched. Since the
new `common_arms` shelf policy admits `{WEAPON, TOOL} × {weapon_main, weapon_off}`, the
pair family is additionally protected at catalog load.

## 4. Non-sellable and keepsake precedence (6.4)

Load time — a keepsake (`relic` band) can no longer reach a counter by any route:

| Route | Guard | Evidence |
| --- | --- | --- |
| Assortment membership | `validate_assortment_configs` (pre-existing) | retained `test_keepsake_band_item_is_rejected_at_any_price` |
| Place addition (`extra_item_keys`) | new gate over the resolved `offered` set in `_resolve_shop_offers` | `test_a_place_addition_cannot_smuggle_a_keepsake_onto_a_counter` (complete five-field override + patched place) |
| Override / hand-supplied offer mapping | same gate | `test_a_hand_listed_offer_route_cannot_carry_a_keepsake_either` (`validate_shop_configs` accepts a caller-supplied offer mapping, so the gate lives in resolution, not only in the assortment validator) |

Trade time — `world/rules/tests/test_shop_economy.py::test_a_listed_keepsake_refuses_both_directions_before_any_write`
lists a file-local keepsake-band item (band floor 999 999, `sellable=False`) in a
synthetic shop and asserts that `sell` and `buy` both raise
`TradeReason.UNSELLABLE`, and that a six-part snapshot is byte-identical afterwards:
`wallet`, `inventory`, `quest_log` (acquisition progress), the parsed merchant stock,
the affinity record's existence **and its affinity value**. The held keepsake stays
holdable and inspectable (`list_items`, `display_name_zh`, non-empty
`presentation.summary_zh`). The pre-existing non-sellable test
(`test_non_sellable_item_refuses_trade_and_outranks_shop_listing`) is retained.

## 5. Shelf eligibility and the liturgical role (6.2)

- `AssortmentDefinition` gains two immutable closed-vocabulary policy sets,
  `allowed_item_kinds` and `allowed_equipment_slots` (empty = unrestricted on that
  axis). All 13 shipped rows declare their kinds; the weapon/armor/adornment/sanctum
  rows additionally declare slots. `assortment_membership_violation()` is a pure
  function; `validate_assortment_configs` raises `GuildConfigError` naming the
  assortment and the item, so a missing reference and a kind/slot shelf mismatch both
  fail load.
- `LiturgicalRole` (`VESTMENT_OR_EMBLEM`, `SANCTUARY_DEVICE`) is declared on the seven
  current Church items as item-lore (`ItemDefinition.liturgical_role`), preserving the
  current classification exactly (4 vestment/emblem, 3 sanctuary device). A non-member
  value and a role on a non-equipment item are rejected at construction.
- `world/rules/equipment_effects.py::validate_church_doctrine` runs at the end of
  `validate_equipment_effect_rules`: vestment/emblem need non-negative `exposure_bias`,
  an **explicit** non-negative `pleasure_gain`, a non-negative declared `heal_gain`, and
  positive healing or an immunity; sanctuary devices need non-negative `exposure_bias`
  and positive `pleasure_gain`. Ordinary combat trade-offs stay permitted.
- Reclassification is impossible from the effect side: the entry schema is closed, so a
  `liturgical_role` key on an entry is an unknown-field rejection
  (`test_an_effect_entry_cannot_declare_a_liturgical_role`), and a vestment that drops
  its healing/immunity (or its `pleasure_gain`) is refused by the loader
  (`test_the_loader_rejects_a_vestment_that_drops_its_obligation`,
  `test_absent_pleasure_gain_is_not_an_exemption`). A newly authored role-bearing item
  joins coverage with no list edit
  (`test_a_role_bearing_item_joins_doctrine_coverage_automatically`), and a roled item
  without a loaded entry is refused by name
  (`test_a_role_without_a_loaded_entry_is_refused`).

## 6. Starting-kit lineage eligibility (6.3)

`SubraceStartingKit` gains `max_rarity: ItemRarity | None` (a declaration, not a
selection list): the three commoner bloodlines declare `COMMON`, `human_royal` and
`human_noble` declare `UNCOMMON`, every other kit is undeclared. `_validate_starting_kit`
rejects a malformed ceiling and any selection above the ceiling, naming the kit, the
item and the ceiling.

`world/lore/tests/test_starting_kits.py` asserts: kit keys still cover the subrace
registry exactly; every selection is registered equipment with a wearable loadout
(retained `validate_wearable_loadout` collision/accessory-cap coverage); the
**derived** commoner set (kits declaring the `COMMON` ceiling) has one identical,
all-COMMON rarity profile; the two noble bloodlines keep an UNCOMMON
`weapon_main` inherited arm; and a synthetic above-ceiling kit (plus a malformed
ceiling) fails at load. No subrace key and no current selection changed.

## 7. Docs, annotations and freeze/seed reasons (6.6)

`docs/development/adding-items.md`: the data-domain table gains
`guild_property`/`liturgical_role` and the shelf-policy row; Step 2c documents
`liturgical_role` and the doctrine obligations; Step 4 documents the shelf policy and
the full non-sellable/keepsake precedence; Step 4b documents
`SUBRACE_STARTING_KIT_REGISTRY` and its `max_rarity`; the construction-rejection table
gains the `liturgical_role` rows; five common-errors rows were added; the stale
"registry currently has three items" phrasing was replaced with a count-free sentence.

Ledger reasons, hand-edited **consistently in both** `tools/test_data_lint_seed.json`
and `tools/test_data_freeze.json` (the pattern the earlier packages used), for exactly
the two paths WP1's metadata map named:

| Path | New reason |
| --- | --- |
| `world/lore/tests/test_items.py` | `item registry registration/metadata/reference contract` |
| `world/rules/tests/test_equipment_effect_rulebook.py` | `equipment effect rulebook and item-lore liturgical-role contract` |

Every other touched file's reason is unchanged (they already describe the post-cutover
claim) and no file moved into or out of `debt`/`seedDebtPaths`. A wholesale
`test_data_lint seed` regeneration was deliberately **not** committed: it rewrites 412
lines, moves `contract` 97→96 and reshapes `debt` 14→336, i.e. exactly the
94-vs-93-style drift WP1's metadata-map Table C records as pre-existing and warns
against regenerating.

## 8. Verification actually executed

| Command | Observed result |
| --- | --- |
| `evennia test … world.lore.tests.test_items test_assortments test_starting_kits` (one run) | `Ran 37 tests … OK` |
| `evennia test … world.rules.tests.test_equipment_effect_rulebook` | `Ran 66 tests … OK` (67 after the closeout test) |
| `evennia test … world.rules.tests.test_guild_config.test_assortment_shop_rules test_item_offer_definitions test_catalog_loading test_commerce_rulebook_slices test_price_scaling` | `Ran 90 tests … OK` |
| `evennia test … world.rules.tests.test_guild_exam_restrictions test_shop_economy` | `Ran 46 tests … OK` |
| `evennia test … world.lore.tests.test_settlements test_registry_index_contract test_sync world.skills.tests.test_equipment` | `Ran 60 tests … OK` |
| `evennia test … world.rules.tests.test_guild_economy_sync` | `Ran 83 tests … OK` (221.8 s) |
| `evennia test … world.lore.tests.test_items test_assortments test_starting_kits test_registry_index_contract test_settlements` (post-fix re-run) | `Ran 82 tests … OK` |
| `uv run --locked python -m tools.test_data_lint check` | `scanned=1253 flagged=99 universe=1219+38 quantity-pins=9 violations=0` |
| Live registry probes (read-only) | zero shelf-eligibility violations over all 13 assortments; exactly 7 liturgical roles on the current Church items; 27 unstocked equipment items still resolve their rule |

Focused batches only. The integrated Python/JS/browser gates, `openspec validate`,
`tools.spec_traceability check/verify` and `tools.contract_gate` remain WP7's.

One observed pre-existing hazard, not introduced here: running
`world.rules.tests.test_shop_economy` **alone** fails
`test_bought_item_can_be_given` with `RestrictionError: invalid restriction weapon`,
because `CmdGive` lazily imports `world.rules.npc_intents` →
`world.rules.guild_exam_restrictions`, whose module-level load validates the shipped
military keys against the LIVE `ITEM_REGISTRY` that `ShopRegistryIsolation` has
swapped for the synthetic kit. Run together with
`world.rules.tests.test_guild_exam_restrictions` all 46 tests pass, so it is an
import-order/scope hazard in the test harness.

## 9. Retired ids and their re-attachment sites

Exactly one WP6-family heading is REMOVED by the delta:
`equipment-effects::the-new-equipment-roster-is-registered-and-tradeable`. Its only
annotation site (`test_new_items_are_registered_offered_and_price_resolvable`) was
replaced by two tests in
`world/rules/tests/test_equipment_effect_rulebook.py::EquipmentRosterCoverageTests`
(`test_every_registered_equipment_item_is_complete_and_price_resolvable`,
`test_stocking_is_authored_data_not_a_registration_consequence`), both annotated with
the ADDED id `equipment-effects::equipment-membership-and-stocking-are-authored-data`;
`test_every_equipment_price_table_key_resolves` was retargeted to the retained
`equipment-effects::registration-and-tradeability-are-independent`. No retired id
remains anywhere in this package's files.

Re-attached retained ids:

- `sample-city-altoria::the-sample-city-s-xyzgrid-remains-thirteen-exterior-nodes-while-permanent-service-interiors-are-attached`
  → three tests in `world/lore/tests/test_assortments.py` (member eligibility, kind/slot
  negatives, capital union), which now carry a comment citing that requirement's
  merchandise scenarios ("Specialist shops do not narrow what the capital sells", the
  accessory partition, "an omitted accessory good is a gap; a non-accessory good is a
  leak", "the partition is stated as a set equality"), and
  `test_guild_config/test_commerce_rulebook_slices.py::test_at_par_slice_offers_travel_field_for_field`
  (the "Moving a good between shelves does not change its price" scenario). The
  grid/interior half of that requirement keeps its assertions in
  `world/maps/tests/test_service_interiors.py`.
- `commerce-assortments::commerce-balance-data-is-a-set-of-files-not-one-file` → moved
  onto `test_commerce_rulebook_slices.py::test_shipped_rulebook_is_a_directory_of_sorted_slices`
  after its baseline test was deleted.

## 10. Retained contracts untouched

Price bands and every numeric rulebook value are unchanged (this package asserts band
containment, never a price). Place keys/order/coordinates/exteriors/topology, the
clergy ladder and fixed guild titles, the skill/sexual catalogs, the balance values,
`military-equipment`, `guild-exam-restrictions` and `guild-rank-exams` keep their
statements, ids and assertions. No delta spec, main spec, deferred proposal or
`exploration-*` change was edited; the delta's own requirement texts already state
every behaviour implemented here (six week-one-family tasks, zero delta-spec
deviations).

## 11. Independent review dispositions

**Plan-stage critique (blocking pass, verdict `adjust`) — both blocking findings adopted:**

1. *`_expect_rejection` was not a doctrine-safe seam.* Adopted: the helper now takes an
   optional expected-reason substring; every church-item mutation site in the file was
   triaged (no existing negative pinned a doctrine behaviour, so none needed a reason
   change), and the two new loader-level negatives pin theirs.
2. *An absent `pleasure_gain` key passed the planned doctrine vacuously.* Adopted: the
   reading is now "**present** and non-negative" in production and in the independent
   oracle, pinned by `test_absent_pleasure_gain_is_not_an_exemption`.

Non-blocking findings adopted: shelf negatives target `item_keys` membership (an offers
row for a non-member is pre-empted by the unknown-item check); the override-route
keepsake negative uses a complete five-field row; the `liturgical_role`-on-an-entry
negative pins the unknown-field reason; `max_rarity` replaced a heavier
`allowed_rarities` set; keepsake rejection sits early in `_resolve_shop_offers`; both
new fields stay defaulted-trailing so `test_registry_index_contract.py` stays green
(verified passing); `world/lore/tests/test_registry_index_contract.py` added to the
checklist.

**Post-implementation critique (blocking pass, verdict `needs minor adjustments`) — one
blocking finding and five non-blocking findings, all adopted:**

1. *(blocking) `LiturgicalRole` was defined twice in `world/lore/items/vocab.py`* — an
   editing artifact from a mis-applied patch, invisible to every gate because the repo
   intentionally has no linter. **Adopted:** the duplicate block was deleted; the file
   now has exactly one `class LiturgicalRole` (verified by grep, line 71) and the
   vocabulary still loads. This is the reason the closeout commit exists.
2. *`_resolve_shop_offers` could raise a bare `KeyError` at the hand-supplied-offers
   seam.* **Adopted:** the gate now uses `ITEM_REGISTRY.get()` and raises
   `_commerce_error` for an unregistered resolved key, keeping the module's
   `GuildConfigError` contract type on every path.
3. *The doctrine "binds no loaded effect entry" branch was unasserted.* **Adopted:**
   `test_a_role_without_a_loaded_entry_is_refused` exercises it directly with a
   registry copy and a rules mapping missing the entry.
4. *`test_shipped_rulebook_is_a_directory_of_sorted_slices` froze the exact slice
   filenames*, contradicting the data-edit claim the moved id now leans on. **Adopted:**
   the exact roster was replaced by "non-empty, sorted, unique, all `.yaml`".
5. *The re-attached `sample-city-altoria` id sat on tests that did not name which part
   of that requirement they verify.* **Adopted:** comments at the re-attachment sites
   cite the requirement's merchandise scenarios and point the grid/interior half at
   `test_service_interiors.py`.
6. *6.4's affinity evidence was `has_record`-only.* **Adopted:** the snapshot now also
   captures the affinity value, so an existing record could not be mutated unnoticed.

The reviewer independently confirmed the other answers: the four retained contracts are
not weakened; deleting the baseline fixture plus its two snapshot tests is not a real
coverage loss (both replacements assert live relationships, and the
`commerce-balance-data` requirement keeps three real assertions); the doctrine pass
creates no hazard for the injectable registry seam or override documents; no fixed
counts or expected-content fixtures remain in the item/shop/assortment/kit families;
and the `max_rarity` reading is sound (type check before index lookup, absent = no
ceiling, commoner equality discovered rather than listed).

## 12. Left to WP7

- `openspec validate generalize-content-identity-contracts --strict`,
  `--specs --strict` and `--all --strict` totals (WP6 edited no spec, so no total moved).
- `tools.spec_traceability check`/`verify` and `tools.contract_gate`, and the
  zero-stale-id conclusion (WP6 retired exactly one id and re-attached it here).
- The integrated Python/JS/browser gates and the metadata/test-data gate once, plus the
  full-suite recording of the batches listed in §8 (the Evennia guard caps one focused
  command at 100 discovered tests, which is why `test_guild_config` and
  `world.lore.tests` were split).
- The pre-existing `test_shop_economy`-alone import-order hazard recorded in §8.
