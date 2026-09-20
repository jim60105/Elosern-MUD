// Deterministic offline showcase fixtures — public facade.
//
// The values live in ./fixtures/<domain>.js slices (verbatim moves; each
// slice keeps its own section-comment banner). This module re-exports the
// whole surface so every `import { … } from "../fixtures.js"` /
// `"../stories/fixtures.js"` consumer keeps working unchanged.
//
// Slice map:
//   core.js               — B1 core-family (narrative, status slice, prompt,
//                           command history, roster)
//   action_dock.js        — B2 action-dock family (context_actions v5)
//   status_panels.js      — B3 `status` panel family
//   character_panels.js   — B3 `character` v7 panel family
//   skills.js             — B3 skills slice
//   local_map.js          — B4 `local_map` v1 lattice family + localMapModelFor
//   art_panels.js         — B4 `art` panel family
//   services_panels.js    — B4 `services` panel family
//   creation_panels.js    — B5 `creation` v5 wizard family
//   party_panels.js       — align-05 party panel family
//   objectives_panels.js  — objectives panel family
//   lore_codex_panels.js  — `lore_codex` panel v1 family
//   quest_log_panels.js   — `quest_log` panel read-model family

export * from './fixtures/core.js';
export * from './fixtures/action_dock.js';
export * from './fixtures/status_panels.js';
export * from './fixtures/character_panels.js';
export * from './fixtures/skills.js';
export * from './fixtures/local_map.js';
export * from './fixtures/art_panels.js';
export * from './fixtures/services_panels.js';
export * from './fixtures/creation_panels.js';
export * from './fixtures/party_panels.js';
export * from './fixtures/objectives_panels.js';
export * from './fixtures/lore_codex_panels.js';
export * from './fixtures/quest_log_panels.js';
