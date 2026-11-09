// Dock glyph table (H3 webclient-hud-03-action-dock, task 4.2): the fixed
// glyph map keyed by stable server keys — the exploration/combat root item
// keys, the look-entity `kind`, the canonical direction words, and the
// participant `team`. Unmapped keys render no icon (the tab bar's label
// carries the text). Every glyph is `aria-hidden` beside the real text
// label.
export const GLYPHS = {
  letters: "M3 5h18v14H3ZM3 5l9 7 9-7",
  // Exploration root item keys (the G2 stable keys). The `d` values for
  // move/look/interact are copied verbatim from
  // `docs/design/elosern-redesign/index.html` (the binding visual reference);
  // `look` folds the reference's eye outline plus pupil circle into one
  // multi-subpath string (the pupil as two arc subpaths).
  move: "M12 5v14M12 5 7 10M12 5l5 5",
  look: "M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7-10-7-10-7Z M9 12a3 3 0 1 0 6 0a3 3 0 1 0 -6 0",
  interact: "M4 5h16v11H8l-4 4V5Z",
  character: "M12 2a5 5 0 1 1 0 10 5 5 0 0 1 0-10zm-7 22v-1c0-3.9 3.1-7 7-7s7 3.1 7 7v1h-14z",
  quests: "M6 3h12v2h2v5h-2v9a2 2 0 0 1-2 2H9a2 2 0 0 1-2-2V5H5V3h1z",
  // The reference's 背包 ‧ 裝備 drawer-head backpack outline
  // (docs/design/elosern-redesign/index.html:958), the identical string the
  // combat `items` tab carries — one backpack glyph for 背包 semantics
  // across the dock tab and the drawer head (align-drawer-chrome-symbols).
  inventory: "M4 8h16v11H4zM8 8V6a4 4 0 0 1 8 0v2",
  // The reference's 同伴 ‧ 隊伍 drawer head icon (index.html:1040).
  party: "M2 20c0-4 3.5-6 7-6M14 20c0-3 2-5 5-5 M9 4.5a3.5 3.5 0 1 0 0 7 3.5 3.5 0 0 0 0-7z M16 6a3 3 0 1 0 0 6 3 3 0 0 0 0-6z",
  wait: "M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20zm1 4v7l5 3-1.5 2.4L11 14V7h2z",
  // The travel leg panel's 紮營 (wilderness-travel-leg-ui): a ridge tent.
  camp: "M2.5 20 12 4l9.5 16ZM12 4v16M8.5 20 12 13.5 15.5 20M1.5 20h21",
  // The reference's own get-icon (the command line's 拿 chip,
  // docs/design/elosern-redesign/index.html:870).
  get: "M6 11V7a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2v4M4 11h16v9H4z",
  // Combat root item keys (same reference source, combat-root section).
  attack: "M5 19 19 5M5 19h4M5 19v-4",
  skills: "M12 3l1.9 5.6L19.5 10l-5.6 1.9L12 17l-1.9-5.1L4.5 10l5.6-1.4L12 3Z",
  items: "M4 8h16v11H4zM8 8V6a4 4 0 0 1 8 0v2",
  defend: "M12 3 4 6v6c0 5 3.5 8 8 9 4.5-1 8-4 8-9V6l-8-3Z",
  // The party-scope exit rows (webclient-party-exit-confirmation): the
  // reference's flee arrow and forfeit flag drawings now key on the wire
  // operations the rows request.
  retreat: "M13 5l7 7-7 7M4 12h16",
  surrender: "M6 2h12l-5 8v6M9 2l1 7",
  // Look-entity kinds (the look panel's entity.kind values).
  npc: "M12 2a5 5 0 1 1 0 10 5 5 0 0 1 0-10zm-7 22v-1c0-3.9 3.1-7 7-7s7 3.1 7 7v1H5z",
  monster: "M12 2l4 4 4-1 1 4 4 4-4 3 1 4-4 1-3 4-3-4-4-1 1-4-4-3-4-4 1-4 4-1 3-4 3 4z",
  object: "M12 2l10 6v8l-10 6-10-6V8l10-6z",
  // Canonical direction words (H3 design D9: the exit chips read these
  // directly; the renderer never re-parses the label).
  north: "M12 2l5 8H7l5-8z",
  south: "M12 22l-5-8h10l-5 8z",
  east: "M2 12l8-5v10l-8-5z",
  west: "M22 12l-8 5V7l8 5z",
  northeast: "M21 3l-9.5 9.5M21 3v7M21 3h-7",
  northwest: "M3 3l9.5 9.5M3 3v7M3 3h7",
  southeast: "M21 21l-9.5-9.5M21 21v-7M21 21h-7",
  southwest: "M3 21l9.5-9.5M3 21v-7M3 21h7",
  up: "M12 4l7 14H5l7-14z",
  down: "M12 20L5 6h14l-7 14z",
  // Participant teams (the combat participant frame, task 6.1).
  allies: "M12 2l4 4 4-1 1 4 4 4-4 3 1 4-4 1-3 4-3-4-4-1 1-4-4-3-4-4 1-4 4-1 3-4 3 4z",
  foes: "M3 3l18 18M21 3L3 21",
  // Reference-surface keys (webclient-drawer-frame-unification): the top
  // navigation's map/settings controls and its 工具 group draw these, and the
  // shared DrawerHeader draws the same key for the surface each one opens, so
  // a header always matches its opener. Circles and the ellipse are written
  // as two-arc subpaths so every glyph is a single `d` string. `shop` is the
  // storefront awning of the 商店 drawer head.
  map: "m3 5 6-2 6 2 6-2v16l-6 2-6-2-6 2ZM9 3v16M15 5v16",
  settings: "m9 3-1 3-3 1 1 3-2 2 2 2-1 3 3 1 1 3h6l1-3 3-1-1-3 2-2-2-2 1-3-3-1-1-3ZM12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8",
  lineage: "M9.8 5a2.2 2.2 0 1 0 4.4 0a2.2 2.2 0 1 0 -4.4 0 M3.3 18.5a2.2 2.2 0 1 0 4.4 0a2.2 2.2 0 1 0 -4.4 0 M16.3 18.5a2.2 2.2 0 1 0 4.4 0a2.2 2.2 0 1 0 -4.4 0 M12 7.2v4.3M12 11.5 6.6 16.6M12 11.5l5.4 5.1",
  lore: "M3.5 12a8.5 8.5 0 1 0 17 0a8.5 8.5 0 1 0 -17 0 M8.2 12a3.8 8.5 0 1 0 7.6 0a3.8 8.5 0 1 0 -7.6 0 M3.5 12h17",
  codex: "M5 4h11a3 3 0 0 1 3 3v13H8a3 3 0 0 1-3-3z M5 17h14 M12 7l.9 1.9 2.1.3-1.5 1.5.4 2-1.9-1-1.9 1 .4-2L9 9.2l2.1-.3z",
  gallery: "M5 3h14a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2z M7 8.5a1.5 1.5 0 1 0 3 0a1.5 1.5 0 1 0 -3 0 M21 15l-5-5L5 21",
  help: "M2 12a10 10 0 1 0 20 0a10 10 0 1 0 -20 0 M9.5 9a2.5 2.5 0 1 1 3.7 2.2c-.7.4-.7 1.3-.7 2.3M12 16h.01",
  shop: "M4 9h16l-1.6-5H5.6L4 9Z M4 9c0 1.7 1.8 2.5 4 2.5S12 10.7 12 9c0 1.7 1.8 2.5 4 2.5S20 10.7 20 9 M5 11.3V20h14v-8.7 M10 20v-5h4v5",
  // The full log's header medallion: a ruled page.
  log: "M6 3h12a1 1 0 0 1 1 1v16a1 1 0 0 1-1 1H6a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1z M8.5 8h7M8.5 12h7M8.5 16h4.5",
  // The NPC author editor's header medallion (npc-persona-editor-window): a
  // quill over a written line.
  quill: "M19.5 3.5C13 4 8.5 8.6 7.2 15.3L6 19l3.6-1.3C16 16.2 20 11.5 20.5 4.5ZM7.2 15.3 13.5 9 M4 21h9",
  // The drawer chrome's close glyph (the reference's `.closebtn` X,
  // docs/design/elosern-redesign/index.html).
  close: "M6 6l12 12M18 6 6 18",
  // Quest drawer redesign glyphs (quest-drawer-ui-primitives, design
  // Decision 7), copied from the approved prototype's `ICONS` map
  // (docs/design/quest-drawer-redesign/QuestDrawerPrototype.vue). First-level
  // tabs: the quest book and the guild counter.
  quest_book: "M6 3.5h11a2 2 0 0 1 2 2v13a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2zM6 3.5a2 2 0 0 0-2 2V8h2M9.5 8.5h6M9.5 12h6M9.5 15.5h3.5",
  guild_counter: "M12 2.8 4.5 5.6v6c0 4.8 3.2 8 7.5 9.6 4.3-1.6 7.5-4.8 7.5-9.6v-6zM12 7v9.5M8.5 10.5h7",
  // The quest book's state rail: hourglass, circled check, circled cross.
  quest_in_progress: "M7 3h10M7 21h10M8 3c0 5 8 5 8 9s-8 4-8 9M16 3c0 5-8 5-8 9s8 4 8 9M10 18.5h4",
  quest_completed: "M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18zM8 12.4l2.8 2.8 5.4-5.6",
  quest_failed: "M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18zM9 9l6 6M15 9l-6 6",
  // One glyph per quest category (採集, 討伐, 護衛, 探索, 緊急).
  cat_gather: "M6 18c0-7 5-12 13-12 0 8-5 13-12 13M6 18l7-7",
  cat_defeat: "M19.5 4.5v3.2L10.4 16.8 7.2 13.6l9.1-9.1zM5.3 11.7l7 7M8.8 15.2l-4.3 4.3",
  cat_escort: "M12 3 5 6v5.5c0 4.5 3 7.5 7 9 4-1.5 7-4.5 7-9V6z",
  cat_explore: "M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18zM15.5 8.5l-2 5-5 2 2-5z",
  cat_emergency: "M12 3 2.5 20h19zM12 9.5v5M12 17.2v.3",
  // The tracked-quest flag, the reward cells (copper coin, merit star,
  // item flask), and the deadline clock.
  track_flag: "M6.5 21V4h11l-2.4 4 2.4 4h-11",
  reward_copper: "M12 4a8 8 0 1 0 0 16 8 8 0 0 0 0-16zM12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8z",
  reward_merit: "M12 3l2.6 5.6 6 .7-4.5 4.1 1.2 6L12 16.4 6.7 19.4l1.2-6L3.4 9.3l6-.7z",
  reward_item: "M9 3h6M10 3v4.5L6 15a4 4 0 0 0 3.6 6h4.8A4 4 0 0 0 18 15l-4-7.5V3",
  deadline: "M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18zM12 7v5l3 2",
  // A padlock (shackle, body, keyhole): the prototype drew its locked-grade
  // mark as a CSS box, so this path is new, drawn at the set's weight.
  lock: "M8 11V8a4 4 0 0 1 8 0v3M5.5 11h13v9.5h-13zM12 14.5v2.5",
  // Party member management glyphs (webclient-window-primitives), copied
  // verbatim from the approved prototype's `NEW_GLYPHS`
  // (docs/design/party-member-management/glyphs.js). Party window tabs:
  member: "M12 20.5s-7.5-4.6-7.5-10.1A4.3 4.3 0 0 1 12 7.6a4.3 4.3 0 0 1 7.5 2.8c0 5.5-7.5 10.1-7.5 10.1z",
  status: "M4 5h16M4 10h16M4 15h10M4 20h7",
  // Item icons (consumables, weapons, armor, accessories, materials).
  potion: "M10 3h4M10.5 3v5L6 15.5A3.5 3.5 0 0 0 9 21h6a3.5 3.5 0 0 0 3-5.5L13.5 8V3M7.5 14h9",
  sword: "M19.5 4.5v3.2L10.4 16.8 7.2 13.6l9.1-9.1zM5.3 11.7l7 7M8.8 15.2l-4.3 4.3",
  hammer: "M5 4h9l3 3-2 2-3-1H5zM10 8l-6.5 11.5 1.8 1L12 9.5",
  bow: "M6 3c6 3 9 8 9 9s-3 6-9 9M6 3v18M15 12H3M3 12l3-2M3 12l3 2",
  shield: "M12 3 4.5 6v5.5c0 4.5 3 7.7 7.5 9.5 4.5-1.8 7.5-5 7.5-9.5V6z",
  armor: "M8 3 4 5.5V11l3 1v9h10v-9l3-1V5.5L16 3c-.6 1.8-2.1 3-4 3s-3.4-1.2-4-3z",
  staff: "M7 21 17 5M15.5 3.5a2.5 2.5 0 1 0 3.5 3.5",
  amulet: "M7 3c0 4 2.2 6.5 5 7 2.8-.5 5-3 5-7M12 10l-3.5 4 3.5 6 3.5-6z",
  ration: "M4 13h16l-1.5 6h-13zM7 13c0-3 2.2-5 5-5s5 2 5 5M12 5v3",
  scroll: "M7 4h11v13a3 3 0 0 1-3 3H6a3 3 0 0 1-3-3v-1h11v1a3 3 0 0 0 3 3M7 4a2 2 0 0 0-2 2v10",
  herb: "M12 21V9M12 13c-4 0-6-3-6-7 4 0 6 3 6 7zM12 11c3.5 0 5.5-2.5 5.5-6-3.5 0-5.5 2.5-5.5 6z",
  // Skill elements and condition shapes.
  holy: "M12 3v18M6 9h12",
  ice: "M12 2.5v19M3.8 7.2l16.4 9.6M3.8 16.8l16.4-9.6M9.5 4.2 12 6.5l2.5-2.3M9.5 19.8 12 17.5l2.5 2.3",
  wind: "M3 9h11a3 3 0 1 0-3-3M3 14h15a3 3 0 1 1-3 3M3 19h7",
  buff: "M12 4l2.2 5.1 5.3.4-4 3.6 1.3 5.4L12 15.6 7.2 18.5l1.3-5.4-4-3.6 5.3-.4z",
  debuff: "M12 3 2.5 20h19zM12 9.5v5M12 17.2v.3",
  // Controls: the empty equipment slot, the quantity stepper, the give
  // arrow, and the member rail's knocked-out chevron (▼ 倒地).
  slot_empty: "M5 5h14v14H5z",
  plus: "M12 5v14M5 12h14",
  minus: "M5 12h14",
  give: "M4 12h13M13 7l5 5-5 5",
  knocked_out: "M6 9l6 6 6-6",
  // The handbook emblems (handbook-primitives, design D3): one per title
  // category, the epithet, the ballot, and the unknown fallback, copied from
  // the approved prototype (docs/design/handbook-codex-titles/CodexEmblem.vue).
  // CodexEmblem.vue draws them as `emblem_<name>`.
  emblem_combat: "M4.5 4.5 15 15M15 15l1.5-.5L19.5 17.5l-2 2L14.5 16.5zM19.5 4.5 9 15M9 15l-1.5-.5-3 3 2 2 3-3z",
  emblem_spell: "M12 2.5 14 9.6 21 12l-7 2.4-2 7.1-2-7.1L3 12l7-2.4z",
  emblem_explore: "M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18zM15.5 8.5l-2 5-5 2 2-5zM12 3v2M12 19v2M3 12h2M19 12h2",
  emblem_guild: "M12 2.8 4.5 5.6v6c0 4.8 3.2 8 7.5 9.6 4.3-1.6 7.5-4.8 7.5-9.6v-6zM8 11h8M12 7v10M9.5 14.5h5",
  emblem_clergy: "M12 3v18M7 8h10M12 3a2 2 0 0 0 0 0M8.5 21h7M5.5 12.5c2 1.5 4.2 2.2 6.5 2.2s4.5-.7 6.5-2.2",
  emblem_romance: "M12 20.5s-7.5-4.6-7.5-10.1A4.3 4.3 0 0 1 12 7.6a4.3 4.3 0 0 1 7.5 2.8c0 5.5-7.5 10.1-7.5 10.1zM12 7.6V4M10 3.5h4",
  emblem_epithet: "M19.5 3.5C13 4 8.5 8.6 7.2 15.3L6 19l3.6-1.3C16 16.2 20 11.5 20.5 4.5ZM7.2 15.3 13.5 9M4 21h9",
  emblem_ballot: "M4 6h16v13H4zM4 6l8 6.5L20 6M8 3h8",
  emblem_unknown: "M9.2 9a2.8 2.8 0 1 1 4.1 2.5c-.8.4-1.3 1.2-1.3 2.1v.6M12 17.2v.3",
  // The codex category emblems (handbook-codex-tab, design D4), from the same
  // prototype; the codex `guild` shares the title category's emblem_guild.
  emblem_monster: "M4 20c1-6 3-9 6-11M9 20c1-5 3-8 6-10M14 20c1-4 3-6 6-8M6 4l2 3M11 3l1 3.5M16 4l-1 3",
  emblem_race: "M12 3.5a3.5 3.5 0 1 1 0 7 3.5 3.5 0 0 1 0-7zM5 20.5c.6-4.5 3.4-7 7-7s6.4 2.5 7 7M3 10.5l2.5 1M21 10.5l-2.5 1",
  emblem_nation: "M4 20.5h16M5.5 20.5V11l3-2 3 2V7l3-3 3 3v4l1.5 1v8.5M14.5 4V1.8l3 1-3 1M9 20.5v-3.5h3v3.5",
  emblem_region: "M2.5 19.5 8.5 9l3.5 6 2.5-4 7 8.5zM8.5 9l1.8 3.2M15.5 6.5a1.6 1.6 0 1 0 0-.1",
  emblem_anchor: "M12 21s-6.5-6.4-6.5-11.2A6.5 6.5 0 0 1 18.5 9.8C18.5 14.6 12 21 12 21zM12 7a2.8 2.8 0 1 0 0 5.6A2.8 2.8 0 0 0 12 7z",
  emblem_element: "M12 2.8c2.5 3.5 5.5 6.3 5.5 10.2a5.5 5.5 0 0 1-11 0c0-2 1-3.6 2.2-4.8.2 1.8 1 2.8 2.1 3.2C10.3 8.6 10.8 5.6 12 2.8z",
  emblem_magic: "M12 2.5 14 9.6 21 12l-7 2.4-2 7.1-2-7.1L3 12l7-2.4zM18.5 3.5l.8 1.7 1.7.8-1.7.8-.8 1.7-.8-1.7-1.7-.8 1.7-.8z",
};

// Per-key stroke attributes copied selectively from the reference: `move`
// (cap+join), `interact` (join only), `attack`/`retreat` (cap only); every
// other key keeps the SVG defaults (the star glyph `skills` must NOT be
// rounded, so the reference omits the attributes there).
const STROKE_ATTRS = {
  move: { "stroke-linecap": "round", "stroke-linejoin": "round" },
  interact: { "stroke-linejoin": "round" },
  attack: { "stroke-linecap": "round" },
  retreat: { "stroke-linecap": "round" },
  // The close X must render with rounded caps, matching the reference.
  close: { "stroke-linecap": "round" },
  quill: { "stroke-linecap": "round", "stroke-linejoin": "round" },
  log: { "stroke-linecap": "round", "stroke-linejoin": "round" },
  lineage: { "stroke-linecap": "round" },
  lore: { "stroke-linecap": "round" },
  codex: { "stroke-linecap": "round", "stroke-linejoin": "round" },
  gallery: { "stroke-linejoin": "round" },
  help: { "stroke-linecap": "round" },
  shop: { "stroke-linejoin": "round" },
};

// The quest drawer redesign glyphs: the prototype rendered every one of them
// with round caps and joins.
for (const key of [
  "quest_book", "guild_counter", "quest_in_progress", "quest_completed", "quest_failed",
  "cat_gather", "cat_defeat", "cat_escort", "cat_explore", "cat_emergency",
  "track_flag", "reward_copper", "reward_merit", "reward_item", "deadline", "lock",
  // The party member management glyphs: the prototype's PmGlyph draws every
  // one of them with round caps and joins.
  "member", "status", "potion", "sword", "hammer", "bow", "shield", "armor", "staff",
  "amulet", "ration", "scroll", "herb", "holy", "ice", "wind", "buff", "debuff",
  "slot_empty", "plus", "minus", "give", "knocked_out",
  // The handbook emblems: the prototype's CodexEmblem rounds every stroke.
  "emblem_combat", "emblem_spell", "emblem_explore", "emblem_guild", "emblem_clergy",
  "emblem_romance", "emblem_epithet", "emblem_ballot", "emblem_unknown",
  "emblem_monster", "emblem_race", "emblem_nation", "emblem_region", "emblem_anchor",
  "emblem_element", "emblem_magic",
]) {
  STROKE_ATTRS[key] = { "stroke-linecap": "round", "stroke-linejoin": "round" };
}

// Return the reference's per-key stroke attributes for a stable key, or an
// empty object when the reference sets none for that glyph.
export function glyphAttrs(key) {
  if (typeof key !== "string") {
    return {};
  }
  return STROKE_ATTRS[key] || {};
}

// Return the SVG path `d` string for a stable key, or null when unmapped.
// Callers render the glyph `aria-hidden` beside the real text label.
export function glyphPath(key) {
  if (typeof key !== "string") {
    return null;
  }
  return GLYPHS[key] || null;
}

// A presentational glyph SVG element (the draft's `.ic` slot). `size` in
// pixels; the SVG carries no a11y role (the text label is the accessible
// name).
export function glyphSvg(key, size = 16) {
  const d = glyphPath(key);
  if (!d) {
    return null;
  }
  // The reference's tab-bar `.ic` icons all use `stroke-width="1.9"`.
  const pathProps = Object.assign(
    { d, stroke: "currentColor", "stroke-width": 1.9 },
    glyphAttrs(key),
  );
  return {
    tag: "svg",
    props: {
      width: size,
      height: size,
      viewBox: "0 0 24 24",
      fill: "none",
      "aria-hidden": "true",
    },
    children: [{ tag: "path", props: pathProps }, { tag: "circle", props: { cx: 12, cy: 12, r: 11, stroke: "currentColor", "stroke-width": 1.8, fill: "none" } }],
  };
}
