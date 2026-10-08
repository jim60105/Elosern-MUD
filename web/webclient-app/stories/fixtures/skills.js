// Story fixture slices: see stories/fixtures.js (facade) for the public surface.

// The character's skill data as the SkillBook consumes it: the character
// payload's actives/passives grouping, with the rows the C1 getter backs from
// the character presenter's registry enrichment — `cost` (a bounded object,
// the empty object being the free form), `target_spec`, the
// `usable_out_of_combat` boolean, and the optional `freeform_scales` array
// (the exact optional fields the character row validator accepts). Rows the
// getter has no descriptor for stay the
// character payload's own `{key, label}` shape: `flee` shows the free-cost
// form, and the unregistered-key `legacy_stance` row (the character payload's
// own unknown-key degradation) proves detail cells render only when the
// backing data provides the field.
export const SKILLS_SLICE_SAMPLE = {
  actives: [
    {
      category: "elemental_magic",
      label: "元素魔法",
      groups: [
        {
          group: "fire",
          label: "火",
          skills: [
            {
              key: "firebolt",
              label: "火矢",
              cost: { mp: 10 },
              target_spec: "single",
              usable_out_of_combat: true,
            },
            {
              key: "fireball",
              label: "火球",
              cost: { mp: 14 },
              target_spec: "single",
              usable_out_of_combat: false,
              freeform_scales: [
                { scale: 0.25, label: "1/4", mp_cost: 4 },
                { scale: 0.5, label: "1/2", mp_cost: 7 },
                { scale: 1, label: "1", mp_cost: 14 },
                { scale: 2, label: "2", mp_cost: 28 },
                { scale: 4, label: "4", mp_cost: 56 },
              ],
            },
            {
              key: "firestorm",
              label: "火風暴",
              cost: { mp: 30, sp: 5 },
              target_spec: "area",
              usable_out_of_combat: false,
            },
          ],
        },
        {
          group: "water",
          label: "水",
          skills: [
            {
              key: "mend_glow",
              label: "微光治癒",
              cost: { mp: 11 },
              target_spec: "self",
              usable_out_of_combat: true,
            },
          ],
        },
        {
          group: "wind",
          label: "風",
          skills: [
            {
              key: "gale_dash",
              label: "疾風突進",
              cost: { sp: 8 },
              target_spec: "self",
              usable_out_of_combat: true,
            },
          ],
        },
        {
          group: "earth",
          label: "土",
          skills: [
            {
              key: "quake",
              label: "震地",
              cost: { mp: 24 },
              target_spec: "area",
              usable_out_of_combat: false,
            },
          ],
        },
      ],
    },
    {
      category: "martial_arts",
      label: "武技",
      groups: [
        {
          group: null,
          label: null,
          skills: [
            {
              key: "basic_attack",
              label: "基本攻擊",
              cost: {},
              target_spec: "single",
              usable_out_of_combat: true,
            },
            {
              key: "light_blade",
              label: "輕劍式",
              cost: { sp: 6 },
              target_spec: "single",
              usable_out_of_combat: false,
            },
            {
              key: "flee",
              label: "逃跑",
              cost: {},
              target_spec: "none",
              usable_out_of_combat: false,
            },
            { key: "legacy_stance", label: "legacy_stance" },
          ],
        },
      ],
    },
    {
      category: "sexual_act",
      label: "性愛行為",
      groups: [
        {
          group: "solo",
          label: "獨處",
          skills: [
            {
              key: "solace",
              label: "自我撫慰",
              cost: {},
              target_spec: "self",
              usable_out_of_combat: true,
            },
          ],
        },
      ],
    },
  ],
  passives: [
    {
      category: "enhancement",
      label: "強化",
      groups: [
        {
          group: null,
          label: null,
          skills: [
            { key: "hardened_body", label: "強化身體" },
            { key: "guard_instinct", label: "防衛本能" },
          ],
        },
        {
          group: "天賦",
          label: "天賦",
          skills: [{ key: "elf_longevity", label: "精靈長壽" }],
        },
      ],
    },
  ],
};