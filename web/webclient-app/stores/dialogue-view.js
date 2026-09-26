// Dialogue surface view model (webclient-align-08-dialogue-surface): the ONE
// derived shape over the committed `dialogue` panel, consumed by the message
// window's name plate, the stage's host actor, the dialogue choice list
// (webclient-dialogue-choices-overlay), and the store's free-form borrow.
// Every consumer derives from this helper; none re-fetches or keeps a copy.
//
// The view model reads ONLY the committed panel form (available `dialogue`
// panels); an unavailable or absent panel yields null and every consumer
// falls back (plain narrative, the shared degradation marker). Values are
// verbatim from the panel; the row shape below reuses the exploration rows'
// `{key, label, enabled, actionId, payload}` contract so activation routes
// through the same dispatch path. `host.portraitRef` is the server-authored
// art portrait-catalog key of the host or null (dialogue panel v2): it is an
// opaque lookup key into the committed `art` panel, never a key this module
// or any consumer builds from the host identity.

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
