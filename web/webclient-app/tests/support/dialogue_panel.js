// Shared dialogue panel v3 fixtures (Shared contract v2): the exact available
// field set, one choice row per keyword, and the scene/native delivery forms.
// Tests build every committed `dialogue` panel through these helpers so a
// later schema change edits one place.

export const DIALOGUE_SCHEMA_VERSION = 3;

export function choiceRow(keywordId, { hostId = 41, contextId = "ctx-1", label = null, topicId = null } = {}) {
  const topic = topicId ?? `host.${keywordId}`;
  return {
    topic_id: topic,
    keyword_id: keywordId,
    label: label ?? keywordId,
    availability: "open",
    requirement_hint: null,
    unread: false,
    predecessors: [],
    action_payload: { npc_id: hostId, topic_id: topic, context_id: contextId },
  };
}

// A native one-host-line delivery (opening greeting or freeform reply).
export function nativeDelivery(text, { deliveryId = "line-1", contextId = "ctx-1" } = {}) {
  return {
    delivery_id: deliveryId,
    context_id: contextId,
    topic_id: null,
    scene_id: "native_line",
    scene_revision: "r1",
    phase_revision: null,
    kind: "opening",
    lines: [{ kind: "speech", speaker: "host", text }],
  };
}

// A complete authored scene delivery (static or generated: same shape).
export function sceneDelivery(lines, {
  deliveryId = "dlv-1",
  contextId = "ctx-1",
  topicId = "host.fare",
  sceneId = "host.fare_scene",
  revision = "r1",
  kind = "formal",
} = {}) {
  return {
    delivery_id: deliveryId,
    context_id: contextId,
    topic_id: topicId,
    scene_id: sceneId,
    scene_revision: revision,
    phase_revision: null,
    kind,
    lines,
  };
}

export const speech = (speaker, text) => ({ kind: "speech", speaker, text });
export const narration = (text) => ({ kind: "narration", text });

export function dialoguePanel({
  hostId = 41,
  hostName = "灰婆婆",
  hostPortraitRef = null,
  actorId = 1,
  actorName = "測試者",
  actorPortraitRef = null,
  bondStage = "親睦",
  contextId = "ctx-1",
  line = "「渡河要五枚銅板。」",
  delivery,
  keywords = ["fare", "smell"],
  labels = null,
  choices = null,
} = {}) {
  return {
    schema_version: DIALOGUE_SCHEMA_VERSION,
    available: true,
    kind: "dialogue",
    host: { identity: hostId, display_name: hostName, portrait_ref: hostPortraitRef },
    actor: { identity: actorId, display_name: actorName, portrait_ref: actorPortraitRef },
    bond_stage: bondStage,
    context_id: contextId,
    delivery: delivery === undefined ? (line == null ? null : nativeDelivery(line, { contextId })) : delivery,
    choices:
      choices ??
      keywords.map((keyword, index) =>
        choiceRow(keyword, { hostId, contextId, label: labels ? labels[index] : keyword }),
      ),
    pure_chain: [],
    reading_revision: 0,
    completed_topic_ids: [],
    unlock_batch: null,
  };
}

export function unavailableDialoguePanel(message = "對話目前無法顯示") {
  return {
    schema_version: DIALOGUE_SCHEMA_VERSION,
    available: false,
    reason: { code: "dialogue_unavailable", message },
  };
}
