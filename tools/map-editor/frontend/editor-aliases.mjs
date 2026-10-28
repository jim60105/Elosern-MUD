// Import aliases of the standalone map editor build, repo-relative. The single
// source for vite.config.js and the import-boundary scanner
// (scripts/import-boundary.mjs), so an aliased specifier resolves to the same
// file the bundler loads before the allowlist is applied. Each game-tree alias
// names exactly one allowlisted file.
export const EDITOR_ALIASES = Object.freeze({
  "@game/tokens.css": "web/webclient-app/styles/tokens.css",
  "@game/fonts.css": "web/webclient-app/styles/fonts.css",
  "@game/fonts-mono.css": "web/webclient-app/styles/fonts-mono.css",
  "@game/ui_scale.js": "web/webclient-app/lib/ui_scale.js",
});

// Allowed game-tree files, anchored and relative to web/webclient-app.
export const EDITOR_ALLOWED_GAME_FILES = Object.freeze([
  /^styles\/tokens\.css$/,
  /^styles\/fonts[A-Za-z0-9_-]*\.css$/,
  /^lib\/ui_scale\.js$/,
]);
