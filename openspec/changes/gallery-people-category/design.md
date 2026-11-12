# Design: the people gallery category

## Context

- `gallery_categories.py` (`gallery-category-sources`): `CATEGORY_KEYS`,
  `DISABLED_REASONS = {"people": ..., "scene": ...}`, `GalleryGroup(key,
  label, seen, total, subjects)`, `category_groups`, `is_subject_admitted`.
- `world/rules/met_people.py` (`met-person-record`): `met_people(character)`
  → `MetPerson(stable_key, npc, place, tick, seq)` newest first, vanished
  skipped; `place_label(place)`.
- v4 projection in `gallery.py` sets `expanded: True` for every group;
  `_resolve_view` picks the remembered or default subject.
- v4 validator already accepts collapsed groups (`gallery-v4-validators`).

## Goals / Non-Goals

**Goals:** people listing, place grouping, one expanded group.

**Non-Goals:** `gallery.group.select` and clickable headings
(`gallery-group-expansion`); NPC persistence (out of scope per design).

## Decisions

### D1. Source

```python
def _people_groups(actor):
    owner = gallery_owner(actor)
    party_ids = {c.pk for c in live_companions(owner)}
    by_place = {}                                  # insertion order = recency
    for person in met_people(owner):               # newest seq first
        if person.place is None or person.npc.pk in party_ids:
            continue
        if not isinstance(person.npc, NPC):       # never a player character
            continue
        subject = character_subject_for(person.npc)  # still named
        if subject is None:
            continue
        by_place.setdefault(person.place, []).append(
            GallerySubjectRef(subject, person.npc, str(person.npc.key)[:64], False))
    return tuple(GalleryGroup(place, place_label(place), None, None, tuple(refs))
                 for place, refs in by_place.items())
```

Remove `people` from `DISABLED_REASONS`. Admission already walks every group,
so collapsed places are admitted.

### D2. Store field

`GalleryViewSelection.expanded: tuple[tuple[str, str], ...] = ()` —
`(category, group_key)` pairs; `gallery_view_snapshot` copies it unchanged.
A helper `remembered_group(view, category) -> str | None`.

### D3. Projection

In the builder, for `category == "people"`: `expanded_key = remembered if it
is a current group key else groups[0].key` (no groups → nothing expanded).
Each group row: `expanded = (key == expanded_key)`, `count =
len(group.subjects)`, `subjects` only when expanded. For every other
category, every group stays expanded as before. `_resolve_view` chooses the
selected subject among the expanded group's subjects only (remembered, else
first).

## Risks / Trade-offs

- [One very large place could pass the 256-subject ceiling] → the panel takes
  the unavailable form by design; recorded as a known limit (the design's
  "one place per panel" bound).
