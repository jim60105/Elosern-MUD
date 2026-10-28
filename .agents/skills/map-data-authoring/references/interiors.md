# Interiors and editor layouts

## `content/maps/interiors/<interior_id>.yaml`

An interior is one permanent indoor room graph with no physical coordinates:
a shop, a home, the palace, a guild hall. It has no metres, no distances and
no route lengths. The file stem equals `id`.

```yaml
version: 1
kind: interior
id: ciaran_shelter
rooms:
  ciaran_shelter:                 # room id: unique across ALL interiors, never renamed
    name_zh: 共食棚                # room name
    desc_zh: 寬寬一片編枝的屋頂……   # zh-TW prose (may be empty string, but write it)
    scene_archetype: tavern_interior   # nullable; registered scene archetype
    art_key: ciaran_shelter       # optional, nullable; see below
connections:                      # DIRECTED named exits between rooms of THIS interior
  - source: hall
    destination: kitchen
    label: 廚房                    # the exit name, non-blank, no surrounding spaces
interior_links:                   # optional: exits into ANOTHER interior's room
  - source_room: hall
    target_interior: altoria_guild_hall
    target_room: altoria_guild_hall
    label: 公會大廳
    return_label: 後門             # nullable: a name makes it two-way IN THIS ONE RECORD
exterior:                         # nullable but required key: the door to the street
  settlement: village_ciaran
  node: village_plaza             # settlement node the doorway opens from
  room: ciaran_shelter            # room of this interior the doorway leads into
  doorway_key: 共食棚              # exit name on the street side
  doorway_aliases: [shelter, communal shelter]
```

### Rules

- **Room IDs are global.** The game gives a permanent room one identity
  across every interior. The editor refuses (`duplicate_room_identity`) a
  room ID that already exists in another interior file. Before you add a
  room, check with `grep -rn "^  <room_id>:" content/maps/interiors/`.
- **Service rooms.** Many room IDs are joined by Python lore. The `places`
  in `world/lore/settlements/places_*.py` and the `service_hosts` in
  `world/rules/guild_config/` (the NPC who runs the shop) both join on the room
  ID, as listed in `content/map-reference-context.json` under
  `incoming_references["interior_room:<interior>:<room>"]`. Editing the
  name, prose, scene or art of such a room is fine. Renaming or deleting it
  is not. A new standalone interior needs **no** service, NPC or economy
  record.
- **Connections** are directed. A two-way passage is two entries, normally
  with each side's own label. Endpoints must be rooms of this document, a
  connection cannot loop to its own room, and the ordered triple
  `(source, destination, label)` is unique. The core allows two exits of one
  room with the same label, but the inspector flags them. Avoid that.
- **Interior links** join a room here to a room in any other interior,
  including a different settlement's building. The relationship lives only
  in **this** file, even when `return_label` makes it two-way. Never add a
  mirror record in the target file.
- **Exterior**: one per interior at most. It is stored in the interior, never
  in the settlement, so adding a building to a street does not touch the
  settlement YAML. The game refuses two interiors that open from the **same
  node** with the **same `doorway_key`** (aliases are not compared). Use
  `doorway_aliases` for the English or short names that players type.
- `scene_archetype` must be one of the reference index's `scene_archetypes`:
  `cave_interior`, `city_street`, `coastal_path`, `dungeon_interior`,
  `forest_path`, `mountain_path`, `ruin_interior`, `shrine_interior`,
  `tavern_interior` and `wilderness_path` at the time of writing. Re-read
  `content/map-reference-context.json` for the current set.
- `art_key` names per-room artwork. The vocabulary of room-art keys is the
  set of `art_key` values the interiors declare. By convention it equals the
  room ID, and it is never inferred from a name. Leave it absent (or empty)
  for a new room unless the user says matching artwork exists. Without it
  the room renders its scene archetype's art.

### Creating an interior

1. Create the new file with `version`, `kind`, `id`, at least one room,
   `connections: []`, and `exterior` (or `exterior:` empty for a standalone
   interior). Add `interior_links` only if needed.
2. If it has an exterior, make sure `settlement` and `node` exist, and that
   no other interior on that node already uses the `doorway_key`.
3. Interiors are **not** partition inputs, so no regeneration is needed. Run
   the check script.

### Deleting

Every guard below must be clear before the deletion. The order matters:
1. **A room.** Delete it only when nothing names it: no connection in either
   direction, not this file's `exterior.room`, no `interior_links` in any
   file (`grep -rn "target_room: <room>" content/maps/interiors/`), no
   district landmark and no external incoming reference.
2. **An interior file.** All of its rooms must pass the room check above.
   Its layout file may stay; it is cleaned up separately.

Removing a connection, link or exterior is always allowed. These are
relationships, not referenceable objects.

## `content/map-editor-layouts/<interior_id>.yaml`

These are editor-only card positions for interior rooms. The game never reads
them, and they are not a world source or a partition input. The directory
appears when the editor first saves a layout.

```yaml
version: 1
kind: layout
id: altoria_guild_hall          # = the interior id it lays out
positions:
  altoria_guild_hall: {x: 0, y: 0}   # integer canvas units, |value| ≤ 100000
  back_office: {x: 1, y: 0}
```

Rooms without a position are drawn at a list position `[index % 3,
index // 3]`. Do not add physical meaning to these values, and never copy
them into an interior document. Positions of a deleted room are harmless
leftovers.

## Editor equivalents

The editor offers these commands:
- `create_interior`, `delete_interior`;
- `create_room`, `duplicate_room`, `set_room_fields`, `delete_room`;
- `create_connection` (with an optional return), `set_connection`,
  `delete_connection`;
- `set_exterior`;
- `create_interior_link`, `set_interior_link`, `delete_interior_link`;
- `arrange_interior_layout`, which writes only the layout file.
