// Import aliases of the GM build (gm-portal-s1-foundation), repo-relative.
// The single source for vite.gm.config.js and the dependency-boundary scanner
// (scripts/gm-import-boundary.mjs), so an aliased specifier is resolved to
// the same file the bundler would load before the allowlist is applied.
export const GM_ALIASES = Object.freeze({
  "@gm": "web/admin-app",
  "@elosern/styles": "web/webclient-app/styles",
});
