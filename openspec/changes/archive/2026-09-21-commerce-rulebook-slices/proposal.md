## Why

`commerce.yaml` is 471 lines today. The settlement build adds roughly 250 more — adornments, remedies, the sanctum's thirteen goods, and the village's two new bundles — putting one file past 700 lines of hand-maintained balance data.

It is also a serialization point. Three separate content changes need to add sections to it, and because they all edit one file they cannot be worked in parallel even though their sections never touch.

Every other registry in this area already solved this. `PLACE_REGISTRY` assembles from per-settlement slices, `ITEM_REGISTRY` assembles from per-topic data modules. The commerce rulebook is the one that stayed monolithic.

## What Changes

- Replace `rulebook/commerce.yaml` with a `rulebook/commerce/` directory read as a set: one file per settlement, plus one carrying the cross-settlement `price_scales`.
- Merge at load: `assortments:` and `shops:` lists concatenate, `price_scales:` mappings merge. A key declared in two files SHALL fail load naming both files — the whole point of splitting is that ownership is clear, and a silent last-file-wins merge would destroy that.
- File discovery is sorted by name so the load order is deterministic, matching how the place registry's slice order is deliberate rather than incidental.
- **No content changes.** Every assortment, offer and shop row moves verbatim. The resolved catalog after this change is byte-for-byte what it was before.

## Capabilities

### Modified Capabilities
- `commerce-assortments`: the rulebook's location changes from one file to a directory, and cross-file duplicate keys become a named load error.

## Impact

- `world/rules/rulebook/commerce.yaml` — deleted, split into `rulebook/commerce/altoria.yaml`, `rulebook/commerce/ciaran.yaml` and `rulebook/commerce/scales.yaml`.
- `world/rules/guild_config.py` — the single `yaml.safe_load` of that path becomes a sorted directory read plus a merge with duplicate rejection.
- No other module reads the file.
