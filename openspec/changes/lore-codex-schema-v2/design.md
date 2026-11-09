# Design: lore-codex-schema-v2

## Context

Source of truth: `docs/superpowers/specs/2026-11-09-handbook-codex-titles-design.md` §4.2, D4, D6 and D7. This change builds on `lore-species-research`, which provides the species-backed `CODE_CATEGORIES["monster"]`, `list_species_defeated(player, tolerant=…)` and the `lore_species_defeated` attribute.

Current state (observed):

- `web/webclient/presentation/lore_codex.py` holds the v1 constants (`LORE_CODEX_MAX_ENTRIES_PER_CATEGORY = 32`, `LORE_CODEX_MAX_TOTAL_ENTRIES = 256`, the card, key, title, label and field bounds), `validate_lore_codex` and `lore_codex_presenter`. The presenter reads `list_discovered(actor, tolerant=True)`, omits unresolvable keys, renders with `lore_card`, and raises `PanelUnavailableError` on `LoreRecordError`. It closes with `json_byte_size(result) > MAX_CANONICAL_JSON_BYTES` (65 536).
- The JS mirror is `web/static/webclient/js/elosern/protocol/panels/exotic.js` with constants in `protocol/constants.js`. `tests/test_lore_codex_parity_contract.py` pins equal constants by regex (`^NAME\s*=\s*(\d+)` in Python, `var NAME\s*=\s*(\d+)` in JS) and the category order. `tests/test_panel_schema_version_parity_contract.py` pins the schema version.
- Art: `world.art.presenter.describe_portrait(subject, entity=None)` and `describe_scene(target)` are the read-only descriptor builders. `world.art.subjects.monster_subject_for(key)` builds the monster subject, which the gallery already calls per species key. `world.lore.monster_visuals.is_registered_monster_visual_key(key)` decides visual admission (species keys are visual keys through `adapt_combat_species`). `world.rules.art_view.SceneTarget(identity, trusted_identity, archetype, room_art_key, room_binding_invalid)` is the frozen scene input. `web.webclient.presentation.artwork.validate_artwork` and JS `protocol/artwork.js` `validateArtwork` are the shared descriptor validators.
- Geography: `world.maps.geography.current()` exposes `regions[key].scene_archetype` (`WildernessRegion`) and `locations.locations[key].scene_archetype` (the authored declaration; the composed `Anchor` does not carry it).
- `MonsterSpecies` fields: `display_name_zh`, `published_description_zh`, `published_appearance_zh`, `published_ecology_zh`, `habitat_tags` (region keys), three `author_*` fields, `default_variant_key`. `MonsterVariant` fields: `species_key`, `display_name_zh`, `threat_tier`, `ordinary_variant`, `danger_grade` (a guild rank key or `None`).
- The only client consumer is `web/webclient-app/components/LoreCodexDrawer.vue`, which reads `categories[].entries` and `categories[].count`.

## Goals / Non-Goals

**Goals:** the v2 wire and presenter of `specs/webclient-lore-codex-panel/spec.md`, the canonical `species_card`, the JS mirror, and a minimal v2 read in the old drawer.

**Non-Goals:**

- No new UI. The tile wall, hero art and research track are `handbook-codex-tab`.
- No new art subject kind, generator, queue or push. Art descriptors reflect whatever the existing pipelines already recorded. The codex panel is not re-pushed when a portrait finishes; it refreshes on its next push.
- No pagination and no client-side recomputation of totals.
- No change to `lore_card`, the `lore` command or the v1 card fields of non-monster categories.

## Decisions

### D1. `species_card` in `lore_knowledge.py` (canonical renderer)

```python
SIGHTED_FIELDS = ("display_name_zh", "published_appearance_zh", "threat_tier")
DEFEATED_FIELDS = ("published_description_zh", "published_ecology_zh", "habitat_tags", "variants")

def species_card(species_key: str, stage: str) -> tuple[dict[str, str], tuple[str, ...]]:
    """Return (card, locked_fields) for one species at "sighted" or "defeated".
    Unknown key -> LoreKeyError; unknown stage -> ValueError."""
```

Field values:

- `display_name_zh`, `published_appearance_zh`, `published_description_zh`, `published_ecology_zh`: the species attribute, verbatim.
- `threat_tier`: `MONSTER_TIER_REGISTRY[default_variant.threat_tier].display_name_zh`, where `default_variant = MONSTER_VARIANT_REGISTRY[species.default_variant_key]`.
- `habitat_tags`: the `display_name_zh` of each tag that resolves in `world.maps.geography.current().regions`, in tag order, joined with `、`. Unresolvable tags are skipped. A raw tag key is never emitted.
- `variants`: one line per variant in `MONSTER_VARIANT_REGISTRY` order whose `species_key` matches and whose `ordinary_variant` is true, joined with `\n`. A line is `display_name_zh` alone, or `f"{display_name_zh}・{GUILD_RANK_REGISTRY[danger_grade].display_name_zh}"` when `danger_grade` is set and resolves.

Sighted returns the three sighted fields and `DEFEATED_FIELDS` as `locked_fields`. Defeated returns all seven fields in `SIGHTED_FIELDS + DEFEATED_FIELDS` order and `()`. The `author_*` attributes are never read. This keeps the "canonical renderer, never composed by the presenter" rule. `lore_card("monster", key)` (used by the `lore` command) keeps rendering the two declared sighted fields, which are the first two `species_card` fields. The `lore` command intentionally shows no defeated-stage data, and changing it is out of scope. Alternative considered: composing monster cards in the presenter. Rejected because it breaks that requirement.

### D2. Presenter algorithm (`lore_codex_presenter`)

1. Raise `PanelUnavailableError` when `context.actor is None`.
2. Read `discovered = list_discovered(actor, tolerant=True)` and `defeated = set(list_species_defeated(actor, tolerant=True))`. Any `LoreRecordError` raises `PanelUnavailableError`.
3. For each category in `CODE_CATEGORIES` order, iterate `codex.registry` in mapping order. A key in `discovered` becomes an entry slot. Every other key becomes `{"placeholder": True}`. Recorded keys absent from the registry produce nothing (they are never iterated).
4. Entry slot: `{"key", "title", "stage", "art", "card", "locked_fields"}`. For monster: `stage = "defeated" if key in defeated else "sighted"` and `card, locked = species_card(key, stage)`. For others: `stage = None`, `card = lore_card(cat, key)` and `locked = ()`. `title = card["display_name_zh"]`, `card` = `[{"name", "value"}]` in order, and `locked_fields = list(locked)`.
5. Groups. Monster: `tier = MONSTER_VARIANT_REGISTRY[species.default_variant_key].threat_tier`. Groups follow `MONSTER_TIER_REGISTRY` order, keeping only tiers with ≥ 1 species, as `{"key": tier, "label": MONSTER_TIER_REGISTRY[tier].display_name_zh, "slots": [...]}`. Others: `[{"key": cat, "label": None, "slots": [...]}]`.
6. Category: `{"key", "label": CATEGORY_LABELS[cat], "discovered", "total", "groups"}`. `total` is the registry size and `discovered` the entry-slot count. Top level: `{"schema_version": 2, "available": True, "discovered_total", "total", "categories"}`.
7. Trimming, in two stages. Stage 1: while `json_byte_size(payload) > MAX_CANONICAL_JSON_BYTES`, delete the last placeholder found scanning categories in reverse, groups in reverse and slots in reverse. Stage 2, once no placeholder is left: set `art` to `None` on the last entry slot (same reverse scan) whose `art` is not `None`, and repeat. If neither stage can trim further, raise `LoreCodexPanelError("lore_codex payload exceeds the OOB envelope limit")`. Counts are not touched. Compute the size once, then subtract each removed element's `json_byte_size` plus its separator, so the loop stays linear.
8. Return `validate_lore_codex(payload)`.

Art helper `_slot_art(category, key)`. Its body runs inside `try`, and any exception returns `None` after `log_warn("lore_codex_art_failed", exc=error, context={"char": str(actor.pk), "category": category, "key": key})` (a facade import in `lore_codex.py`). An art-subsystem fault therefore never blanks the codex:

- `monster`: `describe_portrait(monster_subject_for(key))` when `is_registered_monster_visual_key(key)`, else `None`.
- `region`: `archetype = current().regions[key].scene_archetype`.
- `anchor`: `archetype = current().locations.locations[key].scene_archetype` (guard the missing-key case to `None`).
- For region and anchor with an archetype present in `SCENE_ARCHETYPE_REGISTRY`: `describe_scene(SceneTarget(identity=f"codex:{category}:{key}", trusted_identity=False, archetype=archetype, room_art_key=None, room_binding_invalid=False))`, else `None`.
- Every other category: `None`.

`identity` stays within `MAX_SCENE_IDENTITY_CODE_POINTS` (128), because keys are ≤ 64. `trusted_identity=False` means the scene chain never authorizes retained room content for a codex entry.

### D3. Constants (exact, both languages)

Python `lore_codex.py` and JS `protocol/constants.js`, all as plain integer assignments so the parity regex matches:

```
LORE_CODEX_SCHEMA_VERSION = 2
LORE_CODEX_MAX_SLOTS_PER_CATEGORY = 128
LORE_CODEX_MAX_TOTAL_SLOTS = 512
LORE_CODEX_MAX_GROUPS_PER_CATEGORY = 16
LORE_CODEX_MAX_CARD_FIELDS = 8
LORE_CODEX_MAX_VARIANT_LINES = 8
LORE_CODEX_MAX_KEY_CODE_POINTS = 64
LORE_CODEX_MAX_TITLE_CODE_POINTS = 64
LORE_CODEX_MAX_LABEL_CODE_POINTS = 32
LORE_CODEX_MAX_FIELD_NAME_CODE_POINTS = 64
LORE_CODEX_MAX_FIELD_VALUE_CODE_POINTS = 1024
```

Delete `LORE_CODEX_MAX_ENTRIES_PER_CATEGORY` and `LORE_CODEX_MAX_TOTAL_ENTRIES` in both languages. Replace `_LORE_CODEX_CONSTANTS` in `tests/test_lore_codex_parity_contract.py` with exactly this list. In JS, export the new names from `exotic.js` beside the existing exports.

### D4. Validator rules (Python and JS identical)

- Top level: exact fields `{schema_version, available, discovered_total, total, categories}`, `schema_version == 2`, `available is True`, and exactly 8 categories in `LORE_CODEX_CATEGORIES` order.
- Category: exact `{key, label, discovered, total, groups}`. `key` matches the expected key, `label` is non-empty and ≤ 32 code points, `groups` is a list of up to 16 items with unique `key`s (exactly 1 for non-monster categories, 0 to 16 for monster, so an empty species registry is legal), `discovered` equals the number of entry slots, the slot count is ≤ `total` ≤ 128, and `discovered` ≤ `total`.
- Group: exact `{key, label, slots}`. `key` is non-empty, ≤ 64 code points and colon-free. `label` is null for non-monster categories and a non-empty string ≤ 32 code points for monster. `slots` is a list.
- Placeholder: exactly `{placeholder: true}`.
- Entry slot: exact `{key, title, stage, art, card, locked_fields}`. `key` follows the v1 rules (non-empty, ≤ 64, colon-free, no lone surrogate) and is unique within the category. `title` is non-empty and ≤ 64. `stage` is `"sighted"` or `"defeated"` for monster and `null` otherwise. `art` is `null` or passes the shared artwork validator. `card` holds ≤ 8 `{name, value}` with unique names, and the v1 per-field rules apply. `locked_fields` holds unique strings ≤ 64 code points, disjoint from the card names, ≤ 8 items, and is empty unless `stage == "sighted"`. A card field named `variants` has at most 8 `\n`-separated lines.
- Totals: `discovered_total` equals the sum of `discovered`, `total` equals the sum of `total`, and the total slot count is ≤ 512. Finally the envelope check.
- Unpaired surrogate rejection applies to every string, as in v1.

### D5. JS mirror

Rewrite the lore block of `protocol/panels/exotic.js` to D4, importing `validateArtwork` from `../artwork.js` the way `panels/art.js` does. Update `web/static/webclient/js/tests/protocol_lore_codex.test.js` to v2. Cover: a valid synthetic payload; each rejection in the D4 list (identifying placeholder, `discovered` mismatch, slot count above total, monster stage null, non-monster stage set, `locked_fields` on a defeated slot, overlap between `locked_fields` and the card, a ninth variant line, the removed v1 fields `count` and `entries`).

### D6. Old drawer adaptation (keeps the tree green)

In `LoreCodexDrawer.vue` only:

- `category.count` becomes `category.discovered`.
- `category.entries` becomes `category.groups.flatMap((g) => g.slots).filter((s) => !s.placeholder)`.

The drawer shows no total, so its existing non-disclosure requirement still holds. Update `stories/fixtures/lore_codex_panels.js`, `tests/world/lore_codex_drawer.test.js`, `tests/drawer_content_polish.test.js`, `tests/store/store_slices.test.js` and `tests/app_client_drawers.test.js` to the v2 shape wherever they build a panel. Assertions stay the same.

### D7. Fixtures and builders

- `web/tests/browser/browser_helpers.py::valid_lore_codex_panel`: emit v2 with synthetic keys (one race entry, one anchor entry, placeholders elsewhere). Keep the existing `**overrides` contract.
- `web/tests/browser/incremental_sync_fixture.py::oversized_payload`: build v2 with `per_category = LORE_CODEX_MAX_TOTAL_SLOTS // len(LORE_CODEX_CATEGORIES)` entry slots (art `null`, non-monster `stage` `null`, monster `stage` `"defeated"`), then grow card values to the byte target exactly as today. It must end with `validate_lore_codex(payload)`.
- Every other v1-shaped fixture found by `git grep -n "\"entries\"\|'entries'" -- web/webclient/presentation/tests web/tests/browser web/static/webclient/js/tests web/webclient/tests | grep -i lore`: convert it to v2.

## Risks / Trade-offs

- [Art descriptors weigh more than cards, so a large discovered set could exceed 64 KiB even after trimming every placeholder] → Stage 2 trimming drops art from the last slots, and the client falls back to the emblem. The presenter fails closed only when the cards alone exceed the envelope. A presenter test proves both stages and the fail-closed path.
- [The design text says both "`discovered` and `total` must equal the counted slots" and "after trimming `total` still describes the untrimmed view"] → Resolved: `discovered` always equals the counted entry slots (entries are never trimmed), and `total` ≥ the counted slots, with equality whenever nothing was trimmed. The presenter test asserts equality on an untrimmed payload.
- [Between this change and `handbook-codex-tab` the old drawer shows species cards with fallback field names] → Accepted for the interim. The drawer is deleted by `handbook-codex-tab`.
- [`describe_portrait` logs a `gallery_fallback_used` info event for each fallback species on every build] → Accepted. It is the existing presenter's behavior, and no new logging path is added.

## Review document (human-reviewed)

This section is the named review document. A human reviews it and no requirement pins it: the `、` habitat separator, the `・` variant-grade separator, and the decision to show region display names in a defeated species' habitat.
