# Elosern brand mark

`elosern-mark.svg` is the game's favicon master: the bottom band's lozenge
ornament (`--band-ornament` in `web/webclient-app/styles/tokens.css`, also used
by the GM navigation and empty states) redrawn on a 64x64 square in a single
colour, gold-500 (`#b99a60`). The side rules, lozenge outline, and centre dot
keep the ornament's layout; the strokes are thicker so the mark still reads at
16px.

## Favicon pack

The served pack under `web/static/favicon/` is generated, never hand-edited.
Regenerate it after changing the master or the settings:

```sh
pnpm run favicon
```

That runs `npx realfavicon generate` (RealFaviconGenerator's Node CLI, pinned
in the script) with `realfavicon-settings.json` and writes:

| File | Use |
|---|---|
| `favicon.svg` | Modern browsers. Darkened toward gold-600 on light browser chrome and lightened toward gold-400 on dark chrome via `prefers-color-scheme`. |
| `favicon-96x96.png`, `favicon.ico` | Raster fallbacks for browsers without SVG favicon support. |
| `apple-touch-icon.png` | iOS home screen: the mark on an ink-900 (`#101216`) tile. |
| `web-app-manifest-192x192.png`, `web-app-manifest-512x512.png`, `site.webmanifest` | Installed web app icons and metadata. |

The generator also writes `favicon-markups.json`, the reference markup. The
Django include `web/templates/brand/favicon.html` mirrors it through the
`{% static %}` tag and is used by the game webclient (`webclient/base.html`)
and the GM portal (`gm/index.html`, `gm/forbidden.html`). Storybook takes
`favicon.svg` through a `staticDirs` entry in `.storybook/main.js`. When the
generated markups change, update the include to match.

`site.webmanifest` stores absolute `/static/favicon/` icon URLs, set by the
`path` field in `realfavicon-settings.json`; keep it in step with
`STATIC_URL`.
