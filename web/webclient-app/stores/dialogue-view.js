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
 * @param {object|null} reading — the memory-only reading slice
 *   (`view.dialogueReading`): its transient pure-chain reveal, the saved
 *   revision/completions and the pending acknowledgement status. The revealed
 *   successor is already-delivered bytes the client may present before the
 *   server has saved the predecessor; it never edits `picks`, so no qualified
 *   row is ever unhidden by it.
 * @returns {{host: {identity: *, displayName: string, portraitRef: string|null},
 *     bondStage: string|null, line: string, picks: object[], freeRow: object,
 *     readingRevision: number, completedTopicIds: string[],
 *     pureChain: object[], readingPending: number}
 *     | null} — null unless the panel is the available `dialogue` form.
 */
export function dialogueViewModel(panel, reading = null) {
  if (!panel || panel.available !== true || panel.kind !== "dialogue") {
    return null;
  }
  const host = panel.host || {};
  // Locked topics (authored-dialogue-locked-ui): the server's availability
  // and requirement hint travel verbatim. Only `open` and `locked` rows exist
  // client-side: a `hidden` (or any unknown) availability is dropped, fail
  // closed, so a hidden topic never renders a label, hint or row. A locked
  // row stays ENABLED — selecting it dispatches its own action payload and
  // the server plays the authored refusal — so it is never an operationally
  // disabled row. The client evaluates no condition and never unlocks a row
  // itself; the topic identity (static or generated, up to 2048 characters)
  // is opaque and keys the row so focus follows it across refreshes.
  const picks = (Array.isArray(panel.choices) ? panel.choices : [])
    .filter((choice) => (choice.availability ?? "open") === "open" || choice.availability === "locked")
    .map((choice, index) => {
      const locked = choice.availability === "locked";
      const hint = locked && typeof choice.requirement_hint === "string" ? choice.requirement_hint.trim() : "";
      return {
        key: `dlg-topic-${choice.topic_id ?? choice.keyword_id ?? `#${index}`}`,
        label: choice.label,
        enabled: true,
        availability: locked ? "locked" : "open",
        locked,
        hint: hint || null,
        // The server's durable unread marker (authored-dialogue-unread-
        // notices); the choice list draws it, and a locked row never does.
        unread: !locked && choice.unread === true,
        keywordId: choice.keyword_id ?? null,
        topicId: choice.topic_id ?? null,
        actionId: "explore.talk_scripted",
        payload: choice.action_payload || { npc_id: host.identity, topic_id: choice.topic_id, context_id: panel.context_id },
        commandDisplay: { npcLabel: host.display_name, keywordLabel: choice.label },
      };
    });
  const freeRow = {
    key: DIALOGUE_FREE_ROW_KEY,
    label: "自由對話（輸入任意話語）→ 指令列",
    freeform: true,
    npcId: host.identity,
    npcLabel: host.display_name,
    actionId: null,
  };
  const actor = panel.actor || null;
  // The optimistic pure-chain reveal replaces the presented delivery while it
  // is current; a different context (or a server-committed new delivery, which
  // the store clears the reveal for) falls back to the canonical panel.
  const revealed = reading && reading.revealed ? reading.revealed.delivery : null;
  const delivery =
    revealed && revealed.context_id === panel.context_id
      ? revealed
      : panel.delivery ?? null;
  return {
    host: {
      identity: host.identity,
      displayName: host.display_name,
      portraitRef: host.portrait_ref ?? null,
    },
    // The acting body (Shared contract v2): the controlled figure whose
    // speech an authored scene attributes to "actor" — a possessed
    // companion when control is borrowed, so no second renderer exists.
    actor: actor
      ? { identity: actor.identity, displayName: actor.display_name, portraitRef: actor.portrait_ref ?? null }
      : null,
    contextId: panel.context_id ?? null,
    // The stage NAME travels verbatim (the server never ships numbers).
    bondStage: panel.bond_stage ?? null,
    line: panel.line ?? (delivery?.lines?.[delivery.lines.length - 1]?.text ?? ""),
    delivery,
    // The reading projection travels verbatim (Shared contract v2): the saved
    // revision, the saved formal topics and the pre-delivered public chain.
    readingRevision: Number.isInteger(panel.reading_revision) ? panel.reading_revision : 0,
    completedTopicIds: Array.isArray(panel.completed_topic_ids)
      ? panel.completed_topic_ids.slice(0, 16)
      : [],
    pureChain: Array.isArray(panel.pure_chain) ? panel.pure_chain : [],
    readingPending: reading && Number.isInteger(reading.pendingCount) ? reading.pendingCount : 0,
    picks,
    freeRow,
  };
}

export default { dialogueViewModel, DIALOGUE_FREE_ROW_KEY };
