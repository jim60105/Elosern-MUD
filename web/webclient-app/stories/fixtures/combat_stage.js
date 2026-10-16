import { fixtureDigest } from "./art_panels.js";

// ---- The foe line-up (webclient-combat-foes-on-stage) ----
// Committed combat participants and their `art` catalog entries for the
// line-up's stories. Deterministic offline art: the committed built-in
// fallbacks under `/art/defaults/` stand in for generated portraits, chosen
// for their mix of light and dark backdrops so the depth shadow and the
// gauges are reviewed over both.

// builtin-silhouette-stage-fallback: every stage-eligible catalog entry
// carries the decorative built-in silhouette the server resolved for the
// subject as its own alpha TERMINAL (key + committed /art/defaults/ identity +
// rectangle). The line-up fixtures already point at committed defaults, so the
// key is the URL's stem. Each catalog value is exactly `{artwork, context}`.
function foeEntry(ref, url, name) {
  const key = url.slice("/art/defaults/".length, -".webp".length);
  return {
    artwork: {
      subject_id: `npc_${ref}`,
      revision: fixtureDigest(`foe-${ref}`),
      generation_subject: `npc_${ref}`,
      generation_state: "done",
      attempts: [
        {
          type: "image",
          source_id: `portrait.default:npc_${ref}`,
          rank: 30,
          resource: {
            resource_id: url,
            version: fixtureDigest(`foe-resource-${ref}`),
            url,
            origin: "runtime",
            geometry: {
              image_size: null,
              face_rect: { x: 0.3, y: 0.06, w: 0.4, h: 0.36 },
              stage: { scale: 1, x: 0, y: 0 },
              aspect_ratio: "3:4",
            },
          },
        },
      ],
      terminal: {
        kind: "alpha_mask",
        source_id: `portrait.alpha:${key}`,
        rank: 100,
        resource: {
          resource_id: url,
          version: fixtureDigest(`foe-terminal-${ref}`),
          url,
          origin: "silhouette",
          geometry: {
            image_size: null,
            face_rect: { x: 0.3, y: 0.06, w: 0.4, h: 0.36 },
            stage: null,
            aspect_ratio: "3:4",
          },
        },
      },
      retention_sources: [],
    },
    context: { name, role: "敵方" },
  };
}

// The foes in presenter order: identity, token, name, portrait, hit points.
const FOE_ROSTER = [
  [31, "e1", "灰袍盜賊", "/art/defaults/monster_anon.webp", 42, 60],
  [32, "e2", "盜賊頭目", "/art/defaults/man.webp", 90, 90],
  [33, "e3", "蒙面刺客", "/art/defaults/woman.webp", 18, 50],
  [34, "e4", "見習盜賊", "/art/defaults/boy.webp", 30, 30],
  [35, "e5", "銷贓商人", "/art/defaults/elder.webp", 40, 40],
  // The formation stories stand up to fifteen foes (webclient-combat-
  // formation); three share a name, so their plates carry session tokens.
  [36, "e6", "哥布林", "/art/defaults/monster_anon.webp", 24, 24],
  [37, "e7", "哥布林", "/art/defaults/monster_anon.webp", 9, 24],
  [38, "e8", "哥布林", "/art/defaults/monster_anon.webp", 24, 24],
  [39, "e9", "狼", "/art/defaults/girl.webp", 32, 40],
  [40, "e10", "盜賊斥候", "/art/defaults/boy.webp", 28, 28],
  [41, "e11", "盜賊弓手", "/art/defaults/woman.webp", 20, 35],
  [42, "e12", "盜賊術士", "/art/defaults/man.webp", 35, 35],
  [43, "e13", "雇傭劍士", "/art/defaults/elder.webp", 50, 50],
  [44, "e14", "雇傭槍兵", "/art/defaults/man.webp", 48, 50],
  [45, "e15", "看門惡犬", "/art/defaults/monster_anon.webp", 30, 30],
];

export const FOE_PORTRAIT_CATALOG = Object.freeze(
  Object.fromEntries(FOE_ROSTER.map(([identity, , name, url]) => [String(identity), foeEntry(String(identity), url, name)])),
);

// The first `count` foes as committed combat participants (all active).
export function foeParticipants(count, overrides = {}) {
  return FOE_ROSTER.slice(0, count).map(([identity, token, name, , hp, max]) => ({
    identity,
    token,
    display_name: name,
    team: "foes",
    state: "active",
    hp_current: hp,
    hp_maximum: max,
    portrait_ref: String(identity),
    conditions: [],
    ...(overrides[identity] || {}),
  }));
}

// The player's side as the combat panel lists it.
export const PARTY_PARTICIPANTS = Object.freeze([
  { identity: 1, token: "a1", display_name: "艾莉亞", team: "party", state: "active", hp_current: 80, hp_maximum: 100, portrait_ref: null, conditions: [] },
  { identity: 8, token: "a2", display_name: "同行劍士", team: "party", state: "active", hp_current: 100, hp_maximum: 100, portrait_ref: null, conditions: [] },
]);

// The combat panel's committed skill categories for the stage stories
// (webclient-combat-command-window): 武技 (basic attack, whose server-listed
// candidates put the ally before the foes, and a second strike) and 元素魔法
// with two sub-groups, so the command window shows its counts and its
// category → group → skill path.
// The v6 target polarity of the damage skills below.
const HOSTILE = Object.freeze({ hostile: true });

export function combatSkills(participants) {
  const foes = participants.filter((p) => p.team === "foes").map((p) => p.identity);
  const allies = participants.filter((p) => p.team === "party" && p.identity !== 1).map((p) => p.identity);
  const skill = (key, label, description, cost, target_spec, targets, extra = {}) => ({
    key,
    label,
    description,
    cost,
    target_spec,
    element: null,
    enabled: true,
    disabled_reason: null,
    targets,
    shorthands: [],
    hostile: false,
    beneficial: false,
    ...extra,
  });
  return [
    {
      category: "martial_arts",
      label: "武技",
      groups: [
        {
          group: null,
          label: null,
          skills: [
            skill("basic_attack", "普通攻擊", "以手中武器攻擊一名目標。", {}, "single", [...allies, ...foes], HOSTILE),
            skill("heavy_slash", "重斬", "蓄力一擊，對單一敵人造成較重的傷害。", { sp: 6 }, "single", foes, HOSTILE),
          ],
        },
      ],
    },
    {
      category: "elemental_magic",
      label: "元素魔法",
      groups: [
        {
          group: "fire",
          label: "火",
          skills: [
            skill("firebolt", "火矢", "射出一道火焰箭矢。", { mp: 10 }, "single", foes, HOSTILE),
            // A mastered skill (webclient-combat-command-card-centred): its
            // 威力 step opens before the target frame.
            skill("fireball", "火球", "凝聚火焰魔力，化作熾熱的火球擊向單一敵人。", { mp: 14 }, "single", foes, {
              ...HOSTILE,
              element: "fire",
              freeform_scales: [
                { scale: 0.25, label: "1/4", mp_cost: 4 },
                { scale: 0.5, label: "1/2", mp_cost: 7 },
                { scale: 1, label: "1", mp_cost: 14 },
                { scale: 2, label: "2", mp_cost: 28 },
                { scale: 4, label: "4", mp_cost: 56 },
              ],
            }),
            // An AREA skill: its target frame is the two-column token grid.
            skill("firestorm", "火風暴", "喚起席捲戰場的烈焰，灼燒選定的多名敵人。", { mp: 30 }, "area", foes, { ...HOSTILE, element: "fire" }),
          ],
        },
        {
          group: "water",
          label: "水",
          skills: [
            skill("mend_glow", "微光治癒", "以柔和的水光治癒自己。", { mp: 11 }, "self", [], {
              beneficial: true,
              enabled: false,
              disabled_reason: { code: "insufficient_mp", message: "魔力不足。" },
            }),
          ],
        },
      ],
    },
  ];
}

// ---- Plate conditions (webclient-combat-figure-plates) ----
// Participant condition rows exactly as the v6 combat panel carries them
// (code, label, severity), and a deterministic spread over a roster: no
// condition, one, two, three, five (a `+2` on a full plate) and eight (the
// panel's bound), with every third figure at or below the 25% alarm.
export const PLATE_CONDITIONS = Object.freeze({
  poison: { code: "poison", label: "中毒", severity: "harmful" },
  bless: { code: "bless", label: "祝福", severity: "beneficial" },
  stun: { code: "stun", label: "暈眩", severity: "critical" },
  slow: { code: "slow", label: "遲緩", severity: "warning" },
  fog: { code: "fog", label: "迷霧", severity: "informational" },
  haste: { code: "haste", label: "疾風", severity: "beneficial" },
  bleed: { code: "bleed", label: "流血", severity: "harmful" },
  fear: { code: "fear", label: "恐懼", severity: "warning" },
});
const C = PLATE_CONDITIONS;
const CONDITION_SPREAD = [
  [C.poison],
  [],
  [C.poison, C.bless],
  [C.stun, C.slow, C.bless],
  [],
  [C.poison, C.haste, C.fog, C.stun, C.slow],
  [C.bless],
  [C.poison, C.bless, C.stun, C.slow, C.fog, C.haste, C.bleed, C.fear],
];
export function withPlateConditions(participants) {
  return participants.map((p, index) => {
    if (p.identity === 1) return p;
    const low = index % 3 === 1;
    return {
      ...p,
      conditions: CONDITION_SPREAD[index % CONDITION_SPREAD.length],
      hp_current: low ? Math.max(1, Math.floor(p.hp_maximum * 0.2)) : p.hp_current,
    };
  });
}
