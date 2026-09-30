## Why

The WebClient's monospace token `--f-mono` (`web/webclient-app/styles/tokens.css`) is the only type stack
with no bundled face: `ui-monospace, "DejaVu Sans Mono", "JetBrains Mono", "Noto Sans TC", monospace`
resolves to whatever the player's machine has installed. The command line, keycaps, dialogue option
numbers, party badges, local-map node / edge-marker labels, and box-drawing map art therefore look
different on every machine, and their text-driven heights drift between environments. The display,
serif, and sans stacks are already self-hosted as unicode-range woff2 slices (Iansui, Noto Serif TC,
Noto Sans TC), so monospace is the one gap left in the "fully served from the project origin" design
contract. The project picks Hack (https://github.com/source-foundry/Hack, MIT + Bitstream Vera
license) as the monospace face.

## What Changes

- Vendor Hack v3.003 Regular and Bold into `web/webclient-app/fonts/hack/` as small unicode-range woff2
  slices (latin, latin-ext, greek-cyrillic, box, symbols per weight; each slice well under 40 KB), next
  to the upstream license text.
- Add a reproducible, pinned slice generator (`tools/gen_hack_font_slices.py`, a uv inline-metadata
  script) that downloads the upstream release, verifies its checksum, cuts the slices with fontTools, and
  writes the matching `@font-face` stylesheet; the generated artifacts are committed.
- Add the Hack `@font-face` rules as a generated stylesheet, imported by the app entry and by the
  Storybook preview beside `fonts.css`.
- Change `--f-mono` to `"Hack", "Noto Sans TC", monospace`: Hack draws Latin, digits, punctuation,
  arrows, and box drawing; the bundled Noto Sans TC draws CJK in monospace contexts; the machine
  font list (`ui-monospace`, DejaVu Sans Mono, JetBrains Mono) is removed.
- Update the browser tests that assert monospace rendering so they check the rendered face is the
  bundled Hack web font, not only that the computed family string contains `monospace`. Add a
  Python contract test that checks the Hack slices exist, stay small, and are referenced only
  relatively. It also checks that each slice's declared unicode ranges do not overlap and together cover
  every Hack glyph. Requirement-traceability decorators are added at archive time, together with the
  spec sync.
- Re-verify the local-map lattice label budget and edge-marker ascent (`use-map-lattice-geometry.js`,
  `use-map-lattice-render.js` `MARKER_NAME_ASCENT`) against Hack's measured metrics, and check the map
  surfaces, command line, help overlay, dialogue choices, and party strip for layout breakage with
  agent-browser screenshots at 1440×900 and 1280×720.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `webclient-vue-application`: adds a requirement that the monospace type role is a self-hosted,
  unicode-range-sliced Hack face with a bundled CJK fallback, so no monospace glyph in the UI's own
  vocabulary depends on a machine-installed font.

## Impact

- **Assets**: new `web/webclient-app/fonts/hack/` (10 woff2 slices, about 250 KB total, plus
  `LICENSE.md`); the Vite build copies them into `web/static/webclient/app/dist/assets/` like the
  existing slices.
- **Styles**: `web/webclient-app/styles/tokens.css` (`--f-mono`), a new generated
  `web/webclient-app/styles/fonts-hack.css`, `web/webclient-app/main.js`, `.storybook/preview.js`.
- **Tooling**: new `tools/gen_hack_font_slices.py` (uv inline-metadata script pinning fontTools and
  brotli; not a project dependency, so `uv.lock` is unchanged).
- **Tests**: `web/tests/browser/test_vue_typography.py`, `web/tests/browser/test_vue_foundation.py`,
  new slice-contract and generator unit tests under `tests/`, and re-runs of the map geometry / legibility browser tests.
- **Docs**: `docs/development/frontend-developer-guide.md` and
  `docs/development/frontend-vue-architecture.md` font listings.
- **Layout risk**: Hack's `line-height: normal` is about 1.164 em, so monospace boxes that use the
  default line height may shift by about 1px on machines that previously used a taller system face. Hack
  is a DejaVu Sans Mono derivative with the same 0.602 em advance and vertical metrics, so CI machines
  that already rendered DejaVu Sans Mono see almost no geometry change.
