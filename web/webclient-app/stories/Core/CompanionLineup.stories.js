import { computed, h, ref } from "vue";
import CompanionLineup from "../../components/CompanionLineup.vue";
import HudFrame from "../../components/HudFrame.vue";
import { companionFigures } from "../../components/companion-lineup.js";
import { portraitFor } from "../../components/party-helpers.js";
import { COMPANION_PORTRAIT_CATALOG, PARTY_PANEL_FULL_SAMPLE } from "../fixtures/party_panels.js";

export default {
  title: "Core/CompanionLineup", component: CompanionLineup,
  parameters: { layout: "fullscreen" },
};
const player = {
  identity: 1, displayName: "測試主角",
  portrait: { ...COMPANION_PORTRAIT_CATALOG["103"], url: "/art/defaults/man.webp" },
};
const renderLineup = (args) => ({
  setup() {
    const possessing = ref(!!args.possession);
    const speaking = ref(!!args.speaking);
    const slots = computed(() => companionFigures({
      player: args.placeholders ? { ...player, portrait: null } : player,
      companions: PARTY_PANEL_FULL_SAMPLE.slots.slice(0, args.companions).map((row) => ({
        ...row, portrait_ref: args.placeholders ? null : String(row.identity),
      })),
      actorIdentity: possessing.value ? "102" : "1", possessing: possessing.value,
      artPanel: { portrait_catalog: COMPANION_PORTRAIT_CATALOG }, portraitFor,
    }));
    return () => h("div", { style: "height:100vh;position:relative;background:var(--ink-900)" }, [
      h(HudFrame, { mode: "exploration", motionLevel: args.motionLevel || "full" }, {
        "actor-left": () => h(CompanionLineup, { slots: slots.value, dimmed: speaking.value, speakingIdentity: speaking.value ? 102 : null, motionLevel: args.motionLevel || "full" }),
      }),
      ...(args.possession ? [h("button", {
        type: "button", style: "position:absolute;top:var(--header-h);left:50%;z-index:5",
        onClick: () => { possessing.value = !possessing.value; },
      }, possessing.value ? "解除附身" : "附身")] : []),
      ...(args.speaking ? [h("button", {
        type: "button", style: "position:absolute;top:var(--header-h);left:50%;z-index:5",
        onClick: () => { speaking.value = !speaking.value; },
      }, "切換說話角色")] : []),
    ]);
  },
});
export const Solo = { render: renderLineup, args: { companions: 0 } };
export const OneCompanion = { render: renderLineup, args: { companions: 1 } };
export const TwoCompanions = { render: renderLineup, args: { companions: 2 } };
export const FourCompanions = { render: renderLineup, args: { companions: 4 } };
export const PossessionSwap = { render: renderLineup, args: { companions: 4, possession: true } };
export const PlaceholderOnly = { render: renderLineup, args: { companions: 4, placeholders: true } };
export const MotionOff = { render: renderLineup, args: { companions: 4, possession: true, motionLevel: "off" } };
export const CompanionSpeaks = { render: renderLineup, args: { companions: 4, speaking: true } };
