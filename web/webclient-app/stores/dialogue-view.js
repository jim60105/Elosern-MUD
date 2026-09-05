// Dialogue surface view model (webclient-align-08-dialogue-surface): the ONE
// derived shape over the committed `dialogue` panel, consumed by the feed
// dialogue variant and the store's caption digit retarget
// (webclient-align-11-dialogue-ux: the dock's `dialogue.root` mirror form is
// deleted — the caption is the ONE presentation; feed rows and digit slots
// derive from this helper, neither ever re-fetches or keeps a copy).
//
// The view model reads ONLY the committed panel form (available `dialogue`
// panels); an unavailable or absent panel yields null and every consumer
// falls back (plain narrative, the shared degradation marker). Values are
// verbatim from the panel; the row shape below is byte-identical to the
// exploration scripted-keyword/freeform rows (`exploration_menu.js
// keywordMenuFor`) so activation routes through the same dispatch contract.

export const DIALOGUE_FREE_ROW_KEY = "dlg-free";

/**
 * Derive the dialogue view model from a committed `dialogue` panel.
 *
 * @param {object|null} panel — the committed panel (either form).
 * @returns {{host: {identity: *, displayName: string, portraitRef: string|null},
 *     bondStage: string|null, line: string, picks: object[], freeRow: object}
 *     | null} — null unless the panel is the available `dialogue` form.
 */
export function dialogueViewModel(panel) {
  if (!panel || panel.available !== true || panel.kind !== "dialogue") {
    return null;
  }
  const host = panel.host || {};
  const picks = (Array.isArray(panel.choices) ? panel.choices : []).map((choice) => ({
    key: `dlg-kw-${choice.keyword_id}`,
    label: choice.label,
    enabled: true,
    actionId: "explore.talk_scripted",
    payload: { npc_id: host.identity, keyword_id: choice.keyword_id },
    commandDisplay: { npcLabel: host.display_name, keywordLabel: choice.label },
  }));
  const freeRow = {
    key: DIALOGUE_FREE_ROW_KEY,
    label: "自由對話（輸入任意話語）→ 指令列",
    freeform: true,
    npcId: host.identity,
    npcLabel: host.display_name,
    actionId: null,
  };
  return {
    host: {
      identity: host.identity,
      displayName: host.display_name,
      portraitRef: host.portrait_ref ?? null,
    },
    // The stage NAME travels verbatim (the server never ships numbers).
    bondStage: panel.bond_stage ?? null,
    line: panel.line,
    picks,
    freeRow,
  };
}

export default { dialogueViewModel, DIALOGUE_FREE_ROW_KEY };
