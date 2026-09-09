## Why

The resolution chain now ends at a seam that returns nothing, so a fresh database
with every external service offline still shows "尚未生成" everywhere. The hard
project requirement is that the game is fully playable with all LLM and Stable
Diffusion services down; "playable" should include *looking* like a game, not a
grid of empty frames.

A small set of built-in, license-clear images committed to the repository fixes
that permanently: every character and monster resolves to something reasonable on
the very first boot, before any generation, any seed art, and any operator action.

## What Changes

- New in-repo directory `web/static/art/defaults/` holding one image per fallback
  key. The keys are a closed vocabulary: `man`, `woman`, `boy`, `girl`, `elder`,
  `monster_anon`. These are the only art files this project commits to git.
- New `world/art/gallery_fallback.py`: the key vocabulary, the per-key face-rect
  constant map, and the deterministic resolver.
- Resolution order for a key: an explicit declaration on the subject's registry
  entry (player presets and the NPC/monster registries MAY declare one) wins;
  otherwise the subject's sex and apparent age select a band, and the subject's
  full key is hashed into that band's key pool. Monster subjects always resolve
  `monster_anon`. The same subject resolves the same image across restarts.
- `world/art/gallery_match.py::fallback_for` is implemented against this module,
  returning the `/art/defaults/<key>.<ext>` URL and the key's face rectangle. The
  chain itself is unchanged.
- New `gallery_fallback_used` boundary event.
- A contract test locks the vocabulary to the committed files in both directions:
  every key has exactly one committed file, and no file in the directory is
  outside the vocabulary.

The images themselves are an authoring dependency outside this repository's code:
this change cannot be completed until six license-clear images exist. Each must be
bounded in size and must depict no sexualized content — the `boy` and `girl` keys
in particular are ordinary child portraits.

No backward compatibility or data migration.

## Capabilities

### New Capabilities

- `art-gallery-fallback`: the closed fallback key vocabulary, the committed image
  set and its contract, the declaration-then-band-then-hash resolution, the
  per-key face rectangles, and the fallback boundary event.

### Modified Capabilities

None. `art-gallery-resolution` already defines the seam this change fills, and
`art-queue-worker`'s media route already serves the `defaults/` identity shape.

## Impact

- `web/static/art/defaults/` — new: six committed images (the only art in git).
- `world/art/gallery_fallback.py` — new module.
- `world/art/gallery_match.py` — `fallback_for` implemented (one function body).
- `world/lore/player_presets.py`, `world/lore/npc_tiers.py`,
  `world/lore/monsters.py` — an OPTIONAL declared fallback key field; every
  existing entry stays valid without one.
- `world/art/tests/` — resolution, determinism, band, and contract coverage.
- Unaffected: generation, the gallery write API, the chain's ordering, the wire
  payload shape, and every player-facing command.
