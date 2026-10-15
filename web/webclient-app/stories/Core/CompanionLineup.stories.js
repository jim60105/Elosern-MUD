// The companion lineup renderer's own showcase. `speakingIdentity` is the one
// emphasis prop: the shell feeds it the committed dialogue host speaker or, in
// exploration, the rendered non-controlled companion whose verb card is open
// (reuse-lineup-person-focus D2). These stories are rendering fixtures — the
// wire acceptance of that join is the managed browser journey
// (web/tests/browser/test_browser_exploration_state.py) and the store-driven
// Vitest regressions; no story proves the live producer.
import { computed, h, ref } from "vue";
import CompanionLineup from "../../components/CompanionLineup.vue";
import HudFrame from "../../components/HudFrame.vue";
import { companionFigures } from "../../components/companion-lineup.js";
import { combatFormation } from "../../components/combat-formation.js";
import { portraitFor } from "../../components/party-helpers.js";
import { COMPANION_PORTRAIT_CATALOG, PARTY_PANEL_FULL_SAMPLE } from "../fixtures/party_panels.js";

export default {
  title: "Core/CompanionLineup", component: CompanionLineup,
  parameters: { layout: "fullscreen" },
};
// The player's own figure is a ROSTER position: the descriptor plus the
// committed roster panel that admitted it.
const ROSTER_PANEL = { schema_version: 3, available: true };
const player = {
  identity: 1, displayName: "測試主角",
  artwork: COMPANION_PORTRAIT_CATALOG["103"].artwork,
  panel: ROSTER_PANEL,
  hasReference: true,
};
// The art-panel slice the lineup renderer consumes: only `portrait_catalog`
// is read, but the panel is the registered v4 form, not the retired v3.
const ART_PANEL = { schema_version: 4, available: true, portrait_catalog: COMPANION_PORTRAIT_CATALOG };
// The combat formation's party side (webclient-combat-formation D1) for this
// window, against `foes` foes, from the shared token geometry.
function formationFor(partyCount, foes) {
  const S = Number(getComputedStyle(document.documentElement).getPropertyValue("--ui-scale")) || 1;
  const width = window.innerWidth;
  const height = window.innerHeight;
  const band = Math.max(190 * S, Math.min(400 * S, height * 0.2785));
  const header = 48 * S;
  return combatFormation({
    stageWidth: width, stageHeight: height, uiScale: S, bandTop: height - band,
    actorHeight: Math.min(height * 0.62, 680 * S, height - header - band), topBandBottom: header,
    vitalsDock: null, partyCount, foeCount: foes,
  });
}
const renderLineup = (args) => ({
  setup() {
    const possessing = ref(!!args.possession);
    const speaking = ref(!!args.speaking);
    const slots = computed(() => companionFigures({
      player: args.placeholders ? { ...player, artwork: null, hasReference: false } : player,
      companions: PARTY_PANEL_FULL_SAMPLE.slots.slice(0, args.companions).map((row) => ({
        ...row, portrait_ref: args.placeholders ? null : String(row.identity),
      })),
      actorIdentity: possessing.value ? "102" : "1", possessing: possessing.value,
      artPanel: ART_PANEL, portraitFor,
    }));
    return () => h("div", { style: "height:100vh;position:relative;background:var(--ink-900)" }, [
      h(HudFrame, { mode: args.formation ? "combat" : "exploration", formation: !!args.formation, motionLevel: args.motionLevel || "full" }, {
        "actor-left": () => h(CompanionLineup, {
          slots: slots.value, dimmed: speaking.value, speakingIdentity: speaking.value ? 102 : null,
          motionLevel: args.motionLevel || "full",
          formation: args.formation ? formationFor(slots.value.length, args.formation).party : null,
        }),
      }),
      ...(args.possession ? [h("button", {
        type: "button", style: "position:absolute;top:var(--header-h);left:50%;z-index:5",
        onClick: () => { possessing.value = !possessing.value; },
      }, possessing.value ? "解除附身" : "附身")] : []),
      ...(args.speaking ? [h("button", {
        type: "button", style: "position:absolute;top:var(--header-h);left:50%;z-index:5",
        onClick: () => { speaking.value = !speaking.value; },
      }, "切換焦點同伴")] : []),
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
// In combat the party stands in the shared-scale formation (here against one
// foe, and against eleven: the participant cap with a full party).
export const FormationFullPartyOneFoe = { render: renderLineup, args: { companions: 4, formation: 1 } };
export const FormationFullPartyElevenFoes = { render: renderLineup, args: { companions: 4, formation: 11 } };
