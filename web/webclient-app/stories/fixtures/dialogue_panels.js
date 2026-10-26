// Story fixture slices: see stories/fixtures.js (facade) for the public surface.

// The committed `dialogue` panel while a conversation is open. The version-3
// form is available-only: the host, the actor, the bond stage name, the
// context, the delivered scene, and the keyword choices. Stories derive their
// view model through `dialogueViewModel`, exactly as AppClient does (the
// showcase derived-shape rule), so every fixture goes through this builder.
export function dialoguePanelFixture({
  hostId = 41,
  hostName = "灰婆婆",
  hostPortraitRef = null,
  actorId = 1,
  actorName = "旅人",
  actorPortraitRef = null,
  bondStage = "親睦",
  contextId = "ctx-1",
  line = "「渡河要五枚銅板，多一子我也不走。」她瞥了你一眼，「倒是你，身上聞起來有點……不對味。」",
  choices = [
    ["fare", "「就五枚，走嗎？」"],
    ["smell", "含糊帶過氣味"],
    ["chest", "直接問箱櫃下落"],
    ["silence", "保持沉默，觀察她下一步"],
  ],
} = {}) {
  return {
    schema_version: 3,
    available: true,
    kind: "dialogue",
    host: { identity: hostId, display_name: hostName, portrait_ref: hostPortraitRef },
    actor: { identity: actorId, display_name: actorName, portrait_ref: actorPortraitRef },
    bond_stage: bondStage,
    context_id: contextId,
    delivery: {
      delivery_id: "delivery-1",
      context_id: contextId,
      topic_id: null,
      scene_id: "native_line",
      scene_revision: "r1",
      phase_revision: null,
      kind: "opening",
      lines: [{ kind: "speech", speaker: "host", text: line }],
    },
    choices: choices.map(([keyword, label]) => ({
      topic_id: `host.${keyword}`,
      keyword_id: keyword,
      label,
      availability: "open",
      requirement_hint: null,
      unread: false,
      predecessors: [],
      action_payload: {
        npc_id: hostId,
        topic_id: `host.${keyword}`,
        context_id: contextId,
      },
    })),
    pure_chain: [],
    reading_revision: 0,
    completed_topic_ids: [],
    unlock_batch: null,
  };
}

export const DIALOGUE_PANEL_SAMPLE = dialoguePanelFixture();
