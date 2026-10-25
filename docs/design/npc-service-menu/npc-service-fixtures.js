// Synthetic fixtures for the NPC service-menu prototype (reference only; no
// shipped character, item, or service data). Each NPC carries a plain name
// (no profession or title), the fixed talk row's state, the conditional
// interactions it offers, and the service descriptors it supplies. The
// service descriptor shape is a prototype assumption standing in for the
// server's per-NPC capability facts, not a wire contract: `{key, flow,
// label, available, reason}`, where `flow` names which demonstration pane
// opens ("trade" or "guild") and `label` is the player function.
import {
  ART_PANEL_SAMPLE,
  SCENE_SUBJECT,
  fixtureDigest,
  sceneBlock,
  sceneBundledResource,
  sceneDescriptor,
  sceneResource,
} from "../../../web/webclient-app/stories/fixtures.js";
import { explorationPanelFixture } from "../../../web/webclient-app/stories/fixtures/scene_overview.js";
import { localMapAround } from "../../../web/webclient-app/stories/fixtures/local_map.js";
import { railSummary } from "./npc-service-model.js";

export const NPC = Object.freeze({
  noServices: 301,
  merchant: 302,
  paused: 303,
  talkUnavailable: 304,
  guildCounter: 305,
  overflow: 306,
});

const trade = (key, label, extra = {}) => ({ key, flow: "trade", label, available: true, reason: null, ...extra });
const guild = (key, label, extra = {}) => ({ key, flow: "guild", label, available: true, reason: null, ...extra });

export const NPCS = [
  {
    identity: NPC.noServices,
    name: "蘿珊",
    portraitRef: null,
    talk: { enabled: true },
    conditional: [{ key: "invite", label: "邀請同行", enabled: true }],
    services: { state: "none" },
  },
  {
    identity: NPC.merchant,
    name: "托班",
    // The shared art sample's `"101"` entry, re-pointed below at a served
    // bitmap so the medallion and the standee render a real image.
    portraitRef: "101",
    talk: { enabled: true },
    conditional: [],
    services: { state: "ready", entries: [trade("goods", "買賣貨物")] },
  },
  {
    identity: NPC.paused,
    name: "米菈",
    portraitRef: null,
    talk: { enabled: true },
    conditional: [],
    services: {
      state: "ready",
      entries: [trade("goods", "買賣貨物", { available: false, reason: "今天清點貨架，櫃檯暫不做買賣。" })],
    },
  },
  {
    identity: NPC.talkUnavailable,
    name: "薇絲妲",
    portraitRef: null,
    talk: { enabled: false, reason: "她正低頭核對帳冊，沒有抬頭的意思。" },
    conditional: [],
    services: { state: "ready", entries: [guild("rank-exam", "申請晉級考核")] },
  },
  {
    identity: NPC.guildCounter,
    name: "艾德溫",
    portraitRef: null,
    talk: { enabled: true },
    // Supplied out of order on purpose: the card still lists invite first.
    conditional: [
      { key: "persona", label: "人物卡", enabled: true },
      { key: "invite", label: "邀請同行", enabled: false, reason: "他得守著櫃檯，走不開。" },
    ],
    services: {
      state: "ready",
      entries: [
        guild("rank-exam", "申請晉級考核"),
        guild("commission-take", "承接公會委託"),
        guild("commission-report", "回報委託成果", { available: false, reason: "結算帳冊送去覆核了，晚點再來。" }),
      ],
    },
  },
  {
    identity: NPC.overflow,
    name: "哈洛",
    portraitRef: null,
    talk: { enabled: true },
    conditional: [
      { key: "possess", label: "附身", enabled: false, reason: "此刻無法附身於他。" },
      { key: "invite", label: "邀請同行", enabled: true },
      { key: "persona", label: "人物卡", enabled: true },
    ],
    // A stress fixture: more rows than the nine digits address.
    services: {
      state: "ready",
      entries: [
        trade("goods", "買賣貨物"),
        trade("loot", "出售戰利品"),
        guild("rank-exam", "申請晉級考核"),
        guild("commission-take", "承接公會委託"),
        guild("commission-report", "回報委託成果"),
        guild("merit-exchange", "兌換公會功績", { available: false, reason: "兌換名冊今天已經額滿。" }),
        guild("training-yard", "預約訓練場"),
        guild("license-reissue", "補辦冒險者證"),
      ],
    },
  },
];

export function npcById(identity) {
  return NPCS.find((npc) => npc.identity === identity) || null;
}

// The presence rail's entries in the production `presenceEntries` shape,
// every person an interact target.
export function railEntries(npcs) {
  return npcs.map((npc) => ({
    key: `target-${npc.identity}`,
    presence: "target",
    identity: npc.identity,
    label: npc.name,
    portraitRef: npc.portraitRef,
    summary: railSummary(npc),
    enabled: true,
    actionId: null,
    payload: null,
  }));
}

// The shared art sample with its `"101"` face re-pointed at a served committed
// bitmap (as the PresenceRail story does) and the scene painted by a bundled
// illustration the showcase serves under `/art/scenes/`.
const FACE = ART_PANEL_SAMPLE.portrait_catalog["101"];
const STORY_FACE = {
  ...FACE,
  artwork: {
    ...FACE.artwork,
    attempts: [
      {
        ...FACE.artwork.attempts[0],
        resource: {
          ...FACE.artwork.attempts[0].resource,
          resource_id: "defaults/man.webp",
          version: "m".repeat(64),
          url: "/art/defaults/man.webp",
        },
      },
    ],
  },
};

export const STORY_ART = {
  ...ART_PANEL_SAMPLE,
  scene: sceneBlock(
    { label: "冒險者公會大廳", alt: "燈火通明的公會大廳" },
    sceneDescriptor({
      revision: fixtureDigest("npc-service-scene"),
      attempts: [
        {
          type: "image",
          source_id: `scene.generated:${SCENE_SUBJECT}`,
          rank: 20,
          resource: sceneResource({ version: fixtureDigest("npc-service-hall"), url: "/art/scenes/tavern_interior.webp" }),
        },
        { type: "image", source_id: "scene.bundled:river_dawn", rank: 40, resource: sceneBundledResource("river_dawn") },
      ],
    }),
  ),
  portrait_catalog: { ...ART_PANEL_SAMPLE.portrait_catalog, 101: STORY_FACE },
};

// The room's exits and minimap, for the compass and the island column.
export const ROOM = explorationPanelFixture({
  exits: [
    { ref: "n", label: "北", destination: "town:guild:0:1" },
    { ref: "e", label: "東", destination: "town:guild:1:0" },
  ],
});

export const LOCAL_MAP = localMapAround({
  layer: "grid",
  current: ["town:guild:0:0", "冒險者公會大廳", 0, 0],
  neighbours: [
    ["town:guild:0:1", "公會街", 0, 1],
    ["town:guild:1:0", "訓練場", 1, 0],
  ],
});
