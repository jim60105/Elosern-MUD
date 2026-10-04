# Proposal: face-crop-small-avatar-thumbnails

## Why

The character switcher's thumbnails and the party drawer's companion avatars already bind the shared `faceObjectPosition` mapping, but that mapping only recenters the cover-fit crop — at a 22–24px (switcher) or 42–52px (drawer) circular/rounded frame it can at best place the marked face's *center* inside a window that still spans most of a full-body portrait, so at small sizes the face region has almost no visual effect and players still see a torso, not a face. "Using the face region" genuinely means the frame should crop/zoom so the face rectangle substantially fills it.

## What Changes

- A second shared pure mapping, `faceCropStyle(rect)` in `web/webclient-app/components/face-rect.js`, converts the committed normalized `face_rect` into an explicit crop-and-zoom style for a small avatar frame: the image element is enlarged so the rect region maps to the frame's box (`width: 100/w %`, `height: 100/h %`) and offset so the rect's center coincides with the frame's center, retaining `object-fit: cover`. For a null/malformed rect — the exact validation set `faceObjectPosition` already rejects — it returns no crop properties, leaving the existing centered `50% 50%` cover crop as the fallback.
- The three small-avatar surfaces switch from the recenters-only mapping to the zoom mapping: the switcher pill thumb (`character-switcher__thumb`), the switcher popover row thumbs (`character-switcher__row-thumb`), and the party drawer avatar (`party-drawer__avatar`'s `av-img`). Their wrappers gain the `position: relative` (already satisfied where the avatar is `display: grid` + `overflow: hidden`) the offset positioning needs.
- Placeholder behavior is unchanged everywhere: a null-URL entry renders the existing label/glyph placeholder with no image element, and a URL-bearing entry with a missing or malformed rect still renders its image with the centered cover crop.
- Out of scope, deliberately unchanged: the gallery cards, gallery detail rail, combat participant frame, dialogue host avatar, interact/dock target avatars, and ReferenceArtwork keep the recenters-only `faceObjectPosition` treatment — this change is scoped to the two small-avatar surfaces the player asked about plus the shared helper they need. The stage render contract and every server-side face-rect rule are untouched; the server still stores rects verbatim and never crops.

## Capabilities

### New Capabilities

(None)

### Modified Capabilities

- `webclient-art-panel`: the requirement "The browser maps each framed portrait's carried face rectangle to a centered cover crop through one shared pure function" is the sole home of the crop contract, and it already names both surfaces at issue — the party drawer's avatar thumbnails and the top-bar character switcher. It is amended to split the contract in two: a **small-avatar** set (the switcher pill thumb, the switcher popover row thumbs, and the party drawer avatar) crops/zooms to the face rectangle through a new shared `faceCropStyle` mapping with the identical validation set and the identical centered-crop fallback, while every **other** framed-portrait surface retains the recenters-only `faceObjectPosition` rule verbatim. Placeholder (null-URL) entries are unchanged on both sides.

## Impact

- `web/webclient-app/components/face-rect.js` (new `faceCropStyle` export), `CharacterSwitcher.vue`, `PartyDrawer.vue` (style bindings + wrapper positioning).
- Tests: `web/webclient-app/tests/data/face_rect.test.js` (new `faceCropStyle` unit cases), `tests/core/character_switcher.test.js` (the existing face-rect thumbnail test moves from object-position equality to crop-style assertions), `tests/data/party_drawer.test.js` (avatar crop assertion), `tests/drawer_content_polish.test.js` and Storybook stories touched only if binding changes shift selectors.
- Storybook: `Core/AppShell.stories.js` switcher stories and `Overlays/PartyDrawer.stories.js` already carry face_rect fixtures; `build-storybook` and `showcase-coverage` (webclient package scripts) must stay green with no new required surface.
- No commands, payloads, or server code change; `docs/game` is unaffected.
