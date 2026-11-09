import { h } from "vue";
import HandbookPrototype from "./HandbookPrototype.vue";
import { CODEX_EMPTY, CODEX_POPULATED, TITLES, TITLES_NO_BALLOT } from "./prototype-data.js";
import { atFullHd, atReference, windowViewportParameters } from "../../../web/webclient-app/stories/window-viewports.js";

// Design/Handbook: the quest window renamed 手帳, with the world codex as an
// MHW-style tile wall (圖鑑) and the title book as a medal wall (稱號) beside
// the existing 任務簿 and 公會櫃檯. Reference only, synthetic fixtures; not
// imported by the app. Monster tiles use the art pipeline's own offline
// fallback image. See
// docs/superpowers/specs/2026-11-09-handbook-codex-titles-design.md.

const render = (args, context) => ({
  render: () => h(HandbookPrototype, { ...args, scope: context.id, key: `${context.id}:${JSON.stringify(args)}` }),
});

export default {
  title: "Design/Handbook",
  component: HandbookPrototype,
  parameters: { layout: "fullscreen", ...windowViewportParameters },
  render,
  args: { codex: CODEX_POPULATED, titles: TITLES },
};

// 圖鑑 › 魔物: a defeated species selected — research complete, variants listed.
export const CodexMonsterDefeated = { ...atReference, args: { tab: "codex", codexEntry: "tide_lamp_crab" } };
// A sighted-only species: the defeated-stage fields are dashed 擊敗後解鎖 boxes.
export const CodexMonsterSighted = { ...atReference, args: { tab: "codex", codexEntry: "ridge_burrow_hare" } };
// A scene-art category (regions use their declared scene archetype).
export const CodexRegion = { ...atReference, args: { tab: "codex", codexCategory: "region" } };
// An emblem category (no art): the emblem is the tile and the hero.
export const CodexElement = { ...atReference, args: { tab: "codex", codexCategory: "element" } };
// Nothing recorded yet: the full silhouette wall and the empty guidance.
export const CodexEmpty = { ...atReference, args: { tab: "codex", codex: CODEX_EMPTY } };

// 稱號 › 公會: the equipped medal selected; the full title at the head's end.
export const TitlesGuild = { ...atReference, args: { tab: "titles" } };
// A locked medal: name and hint stay readable (D9); 裝備 disabled with its reason.
export const TitlesLocked = { ...atReference, args: { tab: "titles", titlesSelection: "g_e_rank" } };
// 異名: a removable epithet selected (移除… then 裝備).
export const TitlesEpithet = { ...atReference, args: { tab: "titles", titlesRail: "epithet", titlesSelection: "破城先鋒" } };
// The armed removal: the bar turns into the caution strip (Escape/✕ cancel it).
export const TitlesRemoveConfirm = {
  ...atReference,
  args: { tab: "titles", titlesRail: "epithet", titlesSelection: "破城先鋒", titlesConfirming: true },
};
// 提名: the pending ballot with the hot count on its rail tab.
export const TitlesBallot = { ...atReference, args: { tab: "titles", titlesRail: "ballot" } };
// No ballot pending: the 提名 tab is absent.
export const TitlesNoBallot = { ...atReference, args: { tab: "titles", titles: TITLES_NO_BALLOT, titlesRail: "combat" } };

// In combat only 圖鑑 and 稱號 exist.
export const InCombat = { ...atReference, args: { tab: "codex", combat: true } };
// The existing quest book under the renamed window.
export const QuestBookUnchanged = { ...atReference, args: { tab: "book" } };

// The same codex at 1920×1080.
export const CodexMonsterFullHd = { ...atFullHd, args: { tab: "codex", codexEntry: "tide_lamp_crab" } };
export const TitlesGuildFullHd = { ...atFullHd, args: { tab: "titles" } };
