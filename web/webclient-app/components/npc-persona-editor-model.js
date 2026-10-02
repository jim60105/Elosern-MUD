// The NPC author editor's pure view model (npc-persona-editor-window D4/D5a):
// the field catalogue, draft <-> read-data conversion, and the local
// validation/budget report every state renders. All counting and bounds come
// from the shared card-contract mirror (lib/npc_persona_card.js), so the
// figures the window shows are the figures the server counts.
import NpcPersonaCard from "../lib/npc_persona_card.js";

export const { LEAF_LIMIT, IDENTITY_SECTION_LIMIT, CARD_BLOCK_LIMIT, OFFLINE_GREETING_LIMIT } = NpcPersonaCard;

// The draft keys in render order. `identity.public` / `identity.hidden` are
// separate controls inside the identity section; `offline_greeting` follows
// the card and is not a card leaf.
export const CARD_FIELDS = [
  {
    key: "identity.public",
    section: "identity",
    label: "公開身分",
    required: true,
    hint: "旁人看得見的身分與立場，例如職業、所屬與在地方上的角色。",
  },
  {
    key: "identity.hidden",
    section: "identity",
    label: "隱秘身分",
    required: false,
    hint: "只有作者與角色自己知道的真相；留空表示沒有。",
  },
  {
    key: "appearance",
    section: "appearance",
    label: "外觀",
    required: true,
    hint: "一眼可見的樣貌與衣著。",
  },
  {
    key: "personality",
    section: "personality",
    label: "性格",
    required: true,
    hint: "性情、價值觀，以及待人處事的傾向。",
  },
  {
    key: "speech_style",
    section: "speech_style",
    label: "說話風格",
    required: true,
    hint: "用詞與語氣、句子節奏、稱呼別人的習慣。",
  },
  {
    key: "life_story",
    section: "life_story",
    label: "人生經歷",
    required: true,
    hint: "與世界設定一致的簡短過往。",
  },
  {
    key: "habit",
    section: "habit",
    label: "習慣",
    required: true,
    hint: "具體的習慣、喜好或厭惡。",
  },
  {
    key: "social_connection",
    section: "social_connection",
    label: "人脈",
    required: false,
    hint: "與既有人物的關係；只是描述，不會改變實際的關係數值。",
  },
];

export const GREETING_FIELD = {
  key: "offline_greeting",
  label: "離線問候語",
  required: false,
};

export const FIELD_KEYS = [...CARD_FIELDS.map((field) => field.key), GREETING_FIELD.key];

export function fieldLabel(key) {
  if (key === "identity") return "身分";
  if (key === GREETING_FIELD.key) return GREETING_FIELD.label;
  const field = CARD_FIELDS.find((row) => row.key === key);
  return field ? field.label : null;
}

export function emptyDraft() {
  return Object.fromEntries(FIELD_KEYS.map((key) => [key, ""]));
}

function text(value) {
  return typeof value === "string" ? value : "";
}

// Flatten the read data's nested card plus the greeting into one flat draft.
export function draftFromData(data) {
  const persona = (data && data.persona) || {};
  const identity = persona.identity || {};
  return {
    "identity.public": text(identity.public),
    "identity.hidden": text(identity.hidden),
    appearance: text(persona.appearance),
    personality: text(persona.personality),
    speech_style: text(persona.speech_style),
    life_story: text(persona.life_story),
    habit: text(persona.habit),
    social_connection: text(persona.social_connection),
    offline_greeting: text(data && data.offline_greeting),
  };
}

export function personaFromDraft(draft) {
  return {
    identity: { public: draft["identity.public"], hidden: draft["identity.hidden"] },
    appearance: draft.appearance,
    personality: draft.personality,
    speech_style: draft.speech_style,
    life_story: draft.life_story,
    habit: draft.habit,
    social_connection: draft.social_connection,
  };
}

export function sameDraft(a, b) {
  if (!a || !b) return false;
  return FIELD_KEYS.every((key) => a[key] === b[key]);
}

export function changedFields(draft, baseline) {
  if (!draft || !baseline) return [];
  return FIELD_KEYS.filter((key) => draft[key] !== baseline[key]);
}

// The local validation/budget report. Every figure counts the NORMALIZED text
// (the server's normalization), never truncates, and never throws.
export function validateDraft(draft) {
  const count = NpcPersonaCard.countCodePoints;
  const norm = NpcPersonaCard.normalizeText;
  const normalized = Object.fromEntries(FIELD_KEYS.map((key) => [key, norm(draft[key])]));
  const fields = {};
  for (const field of CARD_FIELDS) {
    const used = count(normalized[field.key]);
    const emptyRequired = field.required && used === 0;
    const over = used > LEAF_LIMIT;
    fields[field.key] = {
      used,
      limit: LEAF_LIMIT,
      remaining: LEAF_LIMIT - used,
      over,
      emptyRequired,
      error: emptyRequired
        ? `${field.label}為必填欄位，不能留空。`
        : over
          ? `${field.label}超過 ${LEAF_LIMIT} 字上限 ${used - LEAF_LIMIT} 字。`
          : null,
    };
  }
  const identityUsed = count(
    NpcPersonaCard.renderIdentitySection(normalized["identity.public"], normalized["identity.hidden"]),
  );
  const identity = {
    used: identityUsed,
    limit: IDENTITY_SECTION_LIMIT,
    remaining: IDENTITY_SECTION_LIMIT - identityUsed,
    over: identityUsed > IDENTITY_SECTION_LIMIT,
  };
  identity.error = identity.over
    ? `身分區塊（含標籤）超過 ${IDENTITY_SECTION_LIMIT} 字上限 ${identityUsed - IDENTITY_SECTION_LIMIT} 字。`
    : null;
  const card = {
    identity: { public: normalized["identity.public"], hidden: normalized["identity.hidden"] },
    appearance: normalized.appearance,
    personality: normalized.personality,
    speech_style: normalized.speech_style,
    life_story: normalized.life_story,
    habit: normalized.habit,
    social_connection: normalized.social_connection,
  };
  const totalUsed = count(NpcPersonaCard.renderCardBlock(card));
  const total = {
    used: totalUsed,
    limit: CARD_BLOCK_LIMIT,
    remaining: CARD_BLOCK_LIMIT - totalUsed,
    over: totalUsed > CARD_BLOCK_LIMIT,
  };
  total.error = total.over
    ? `整張人物設定（含標籤）超過 ${CARD_BLOCK_LIMIT} 字總上限 ${totalUsed - CARD_BLOCK_LIMIT} 字。`
    : null;
  const greetingText = normalized.offline_greeting;
  const greetingUsed = count(greetingText);
  const multiline = greetingText.indexOf("\n") !== -1;
  const greeting = {
    used: greetingUsed,
    limit: OFFLINE_GREETING_LIMIT,
    remaining: OFFLINE_GREETING_LIMIT - greetingUsed,
    over: greetingUsed > OFFLINE_GREETING_LIMIT,
    multiline,
  };
  greeting.error = multiline
    ? "離線問候語只能是一個段落，請移除換行。"
    : greeting.over
      ? `離線問候語超過 ${OFFLINE_GREETING_LIMIT} 字上限 ${greetingUsed - OFFLINE_GREETING_LIMIT} 字。`
      : null;
  // The authoritative decision is the mirror's own contract check.
  let contractError = null;
  try {
    NpcPersonaCard.normalizeCard(personaFromDraft(draft));
  } catch (error) {
    contractError = error.code || "invalid";
  }
  try {
    NpcPersonaCard.normalizeOfflineGreeting(text(draft.offline_greeting));
  } catch (error) {
    contractError = contractError || error.code || "invalid";
  }
  const errors = [
    ...CARD_FIELDS.filter((field) => fields[field.key].error).map((field) => ({
      key: field.key,
      message: fields[field.key].error,
    })),
    ...(identity.error ? [{ key: "identity.public", message: identity.error }] : []),
    ...(total.error ? [{ key: null, message: total.error }] : []),
    ...(greeting.error ? [{ key: "offline_greeting", message: greeting.error }] : []),
  ];
  return {
    fields,
    identity,
    total,
    greeting,
    errors,
    valid: contractError === null && errors.length === 0,
  };
}

// Map a server rejection code to the control it names (or null).
//   npc_persona.<reason>.<leaf> -> <leaf>; npc_persona.greeting_invalid ->
//   offline_greeting; identity_section_too_long.identity -> identity section.
export function rejectionField(code) {
  if (typeof code !== "string" || !code.startsWith("npc_persona.")) return null;
  if (code === "npc_persona.greeting_invalid") return GREETING_FIELD.key;
  const parts = code.split(".");
  if (parts.length < 3) return null;
  const leaf = parts.slice(2).join(".");
  if (leaf === "identity") return "identity";
  return FIELD_KEYS.includes(leaf) ? leaf : null;
}
