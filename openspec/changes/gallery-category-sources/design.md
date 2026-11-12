# Design: gallery category sources and subject admission

## Context

- Today `web/webclient/presentation/gallery.py::gallery_subjects(actor)` builds
  one rail: puppet, companions, every other `LivingEntity` with a gallery
  subject (scanned from `ObjectDB`), then up to 23 visual species. It is
  replaced in `gallery-v4-cutover`; this change does not touch it.
- `world/rules/account_roster.build_account_roster(actor)` already resolves a
  possessed puppet to its bound owner and returns `characters` rows with
  `identity`, `name`, `current`, `pending` (bounded by `MAX_ROSTER_ROWS`).
- `world/rules/party.live_companions(player)` returns live companions in the
  stored party order; `bound_owner_of(npc)` resolves a possessed companion.
- `lore_codex_presenter` reads `list_discovered(context.actor, tolerant=True)`
  and groups species by `MONSTER_VARIANT_REGISTRY[species.default_variant_key].threat_tier`
  in `MONSTER_TIER_REGISTRY` order (`_monster_groups`).
- After `remove-baseline-visual-species`, every visual species is a combat
  species, so the codex registry and the visual registry have the same keys.

## Goals / Non-Goals

**Goals:** one pure module answering "which groups does category X hold for
this actor" and "is subject S admitted for this actor".

**Non-Goals:** artwork, card counts, payload shape, selection, validation
(those are `gallery-v4-presenter` / `gallery-v4-validators`); the people and
scene sources (`gallery-people-category`, `gallery-scene-category` enable
them).

## Decisions

### D1. Module contract (verbatim)

`web/webclient/presentation/gallery_categories.py`:

```python
CATEGORY_KEYS = ("mine", "party", "people", "monster", "scene")
DISABLED_REASONS = {"people": "人物分類尚未開放。", "scene": "背景分類尚未開放。"}

class GalleryCategoryError(Exception): ...   # owner/roster cannot be resolved

@dataclass(frozen=True)
class GallerySubjectRef:
    subject: ArtSubject          # typed subject
    entity: Any | None           # live character entity; None for registry kinds
    display_name: str            # <= 64 code points
    is_current: bool             # True only for the live character in `mine`

@dataclass(frozen=True)
class GalleryGroup:
    key: str                     # "mine" / "party" / tier key
    label: str | None            # None for unlabeled groups
    seen: int | None             # monster tiers only
    total: int | None            # monster tiers only
    subjects: tuple[GallerySubjectRef, ...]

@dataclass(frozen=True)
class GalleryCategory:
    key: str
    count: int                   # number of subjects over all its groups
    enabled: bool
    reason: str | None           # None when enabled

def gallery_owner(actor) -> Any
def category_groups(actor, key: str) -> tuple[GalleryGroup, ...]
def gallery_categories(actor) -> tuple[GalleryCategory, ...]
def category_of_subject(actor, subject_key: str) -> str | None
def is_subject_admitted(actor, subject_key: str) -> bool
```

- `gallery_owner`: if `actor.db.possessed_by` is set, return
  `bound_owner_of(actor)` and raise `GalleryCategoryError` when it is `None`
  or its pk differs; else `actor`.
- `category_groups` for a disabled key returns `()`; for an unknown key raises
  `KeyError`.
- `category_of_subject` returns the first enabled category in `CATEGORY_KEYS`
  order whose groups list `subject_key`, else `None`.
  `is_subject_admitted` is `category_of_subject(...) is not None`.

### D2. `mine`

Call `build_account_roster(actor)` (raises `AccountRosterError` → re-raise as
`GalleryCategoryError`). Resolve each row's entity with
`ObjectDB.objects.filter(id=row.identity).first()`; skip a missing one. Subject:
`character_subject_for(entity)` when it returns a subject, else
`ArtSubject(ArtSubjectKind.CHARACTER, str(entity.pk))` (every account character
is eligible; the old "numeric record must exist" rule is not carried over
because the account owner always manages their own characters). An
`ArtSubjectError` from `character_subject_for` logs `gallery_subject_invalid`
and falls back to the numeric subject. Order: the `current` row first, then
the rest by identity. One group `GalleryGroup("mine", None, None, None, ...)`.

### D3. `party`

`live_companions(gallery_owner(actor))` in returned order; subject from
`character_subject_for(entity)`; `None` or `ArtSubjectError` skips that
companion only. One group with key `party`, no label.

### D4. `monster`

Holder = `actor` (the same object `lore_codex_presenter` reads).
`seen_keys = {key for cat, key in list_discovered(actor, tolerant=True) if cat == "monster"}`;
a `LoreRecordError` yields an empty seen set (logged `gallery_category_failed`).
Iterate `get_monster_visual_registry()` in insertion order; tier from
`MONSTER_SPECIES_REGISTRY[key].default_variant_key` →
`MONSTER_VARIANT_REGISTRY[...].threat_tier`; a species whose tier is not in
`MONSTER_TIER_REGISTRY` is skipped with one `gallery_category_failed` warning.
Emit groups in `MONSTER_TIER_REGISTRY` order for tiers with at least one
species: key = tier key, label = `tier.display_name_zh`, `total` = species in
tier, `seen` = sighted species in tier, subjects = sighted species via
`monster_subject_for(key)` with `display_name = registry[key].display_label`.

### D5. Read-only

No function writes; every log goes through `world.observability.log_warn`.

## Risks / Trade-offs

- [Admission recomputes every enabled category per call] → bounded by the
  authored registries and the account/party limits; one call per mutation.
- [A named NPC that is not a companion is no longer reachable until the people
  category ships] → intended by the design's delivery order.
