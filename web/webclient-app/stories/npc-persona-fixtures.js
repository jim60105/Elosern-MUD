// Deterministic offline fixtures for the NPC author editor stories
// (npc-persona-editor-window D7). Each builder returns the exact view-model
// shape `use-npc-persona-editor.js` publishes, computed through the same pure
// model (and therefore the shared card-contract mirror), so every figure a
// story shows is a figure the live client would show. Illustrative prose only.
import { changedFields, draftFromData, validateDraft } from "../components/npc-persona-editor-model.js";

export const NPC_PERSONA_READ_SAMPLE = {
  npc_id: 4127,
  display_name: "葛蘭特",
  npc_title: "灰石渡口的擺渡人",
  persona_version: 3,
  persona: {
    identity: {
      public: "在灰石渡口撐了二十年船的擺渡人，熟悉兩岸每一處淺灘與暗流。",
      hidden: "年輕時是邊境守備隊的逃兵，至今仍在躲避昔日長官的追查。",
    },
    appearance: "斗笠壓得很低，蓑衣下是洗到發白的粗布短褂；雙手長滿老繭，左手少了一截小指。",
    personality: "寡言而謹慎，對陌生人保持距離；一旦認定對方值得信任，便會默默替對方擋下麻煩。",
    speech_style: "句子短，常以「嗯」或「得看天」開頭；不用敬語，稱旅人為「客人」，談到過去就轉移話題。",
    life_story: "二十年前來到渡口，跟著前任擺渡人學撐船；老人過世後接下這條船，從此沒離開過灰石渡口。",
    habit: "收錢前先抬頭看天色；收工後會在船頭擦拭一把從不示人的舊短刀。",
    social_connection: "與對岸茶攤的老闆娘相熟，每逢雨天便替她把茶具搬上岸。",
  },
  offline_greeting: "",
  default_greeting: "「上船吧，客人。今天水勢穩，得看天。」",
};

function baseEditor(overrides = {}) {
  const data = overrides.data || NPC_PERSONA_READ_SAMPLE;
  const baseline = draftFromData(data);
  const draft = { ...baseline, ...(overrides.edits || {}) };
  const loaded = overrides.state !== "loading" && !overrides.readFailed;
  const dirtyFields = loaded ? changedFields(draft, baseline) : [];
  const validation = validateDraft(loaded ? draft : baseline);
  const state =
    overrides.state ||
    (dirtyFields.length ? "ready_dirty" : "ready_clean");
  const canSave =
    (state === "ready_dirty" || state === "rejected") && dirtyFields.length > 0 && validation.valid;
  return {
    open: true,
    state,
    npcId: data.npc_id,
    displayName: loaded ? data.display_name : "",
    npcTitle: loaded ? data.npc_title : "",
    version: loaded ? data.persona_version : null,
    draft: loaded ? draft : { ...baseline },
    baseline: loaded ? baseline : null,
    defaultGreeting: loaded ? data.default_greeting : "",
    validation,
    dirty: dirtyFields.length > 0,
    dirtyFields,
    busy: state === "saving" || state === "loading" || !!overrides.busy,
    canSave,
    rejection: overrides.rejection || null,
    conflict: overrides.conflict || null,
    unavailable: overrides.unavailable || null,
    announcement: overrides.announcement || "",
    focusRequest: null,
  };
}

export const npcPersonaEditorStates = {
  loading: () => baseEditor({ state: "loading" }),
  clean: () => baseEditor({ announcement: "已載入葛蘭特的人物設定（第 3 版）。" }),
  dirty: () => baseEditor({ edits: { speech_style: "語氣比平常輕快，仍稱旅人為客人。" } }),
  dirtyOverBudget: () =>
    baseEditor({
      edits: {
        speech_style: `${NPC_PERSONA_READ_SAMPLE.persona.speech_style}${"偶爾會用船槳敲兩下船舷代替回答，".repeat(36)}`,
        life_story: `${NPC_PERSONA_READ_SAMPLE.persona.life_story}${"那年冬天河面結了冰，他一個人守著渡口直到開春。".repeat(22)}`,
        appearance: `${NPC_PERSONA_READ_SAMPLE.persona.appearance}${"雨天會在斗笠外再罩一層油布。".repeat(38)}`,
        personality: `${NPC_PERSONA_READ_SAMPLE.persona.personality}${"對孩子格外溫和，".repeat(30)}`,
        habit: "",
      },
    }),
  saving: () =>
    baseEditor({
      state: "saving",
      edits: { offline_greeting: "「又是你啊，客人。坐穩了，今天逆風。」" },
      announcement: "儲存中……",
    }),
  rejected: () =>
    baseEditor({
      state: "rejected",
      edits: { personality: "寡言，對陌生人保持距離。" },
      rejection: {
        code: "npc_persona.leaf_too_long.personality",
        message: "性格長度超過上限。",
        field: "personality",
      },
      announcement: "性格：性格長度超過上限。",
    }),
  conflict: () =>
    baseEditor({
      state: "conflict",
      edits: { appearance: "斗笠換成了新編的竹笠，蓑衣上別著一枚褪色的徽章。" },
      conflict: {
        version: null,
        message: "這位角色的設定已在其他地方更新（目前第 4 版），請重新載入後再編輯。",
      },
      announcement: "這位角色的設定已在其他地方更新（目前第 4 版），請重新載入後再編輯。",
    }),
  departed: () =>
    baseEditor({
      state: "unavailable",
      edits: { habit: "收工後會在船頭擦拭一把舊短刀，再把它藏回船板下。" },
      unavailable: { kind: "departed", message: "對方已不在這裡。草稿會保留，但目前無法儲存。" },
    }),
  readFailed: () =>
    baseEditor({
      state: "unavailable",
      readFailed: true,
      unavailable: { kind: "read_failed", message: "此角色的設定目前無法讀取或尚未初始化。" },
    }),
  freeFormNoDefault: () =>
    baseEditor({
      data: {
        ...NPC_PERSONA_READ_SAMPLE,
        npc_id: 5003,
        display_name: "無名旅人",
        npc_title: "",
        persona_version: 1,
        default_greeting: "",
        offline_greeting: "「……路過而已，別在意。」",
      },
    }),
};
