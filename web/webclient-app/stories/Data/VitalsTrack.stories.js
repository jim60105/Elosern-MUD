import { h } from "vue";
import VitalsTrack from "../../components/VitalsTrack.vue";
import { STATUS_PANEL_SAMPLE } from "../fixtures.js";

// VitalsTrack (H2, webclient-hud-02-status-islands, design D4/D5): the
// vitals island stories — full / damaged / low / empty for each of hp/mp/sp,
// plus a reduced-motion note (the token block in tokens.css disables the
// motion; the numerals and the 危險 marker still render).

function statusWith(resources, lowHp) {
  return { ...STATUS_PANEL_SAMPLE, resources };
}

const FULL_RESOURCES = STATUS_PANEL_SAMPLE.resources;
const DAMAGED_RESOURCES = {
  hp: { current: 120, maximum: 405 },
  mp: { current: 139, maximum: 420 },
  sp: { current: 68, maximum: 68 },
};
const LOW_RESOURCES = {
  hp: { current: 100, maximum: 405 },
  mp: FULL_RESOURCES.mp,
  sp: FULL_RESOURCES.sp,
};
const EMPTY_RESOURCES = {};

const renderVitals = (args) => ({
  render: () =>
    h("div", { style: "width: 262px;" }, [h(VitalsTrack, args)]),
});

export default {
  title: "Data/VitalsTrack",
  component: VitalsTrack,
};

export const Full = {
  render: renderVitals,
  args: {
    status: statusWith(FULL_RESOURCES, false),
    lowHp: false,
    revision: 1,
    epoch: 0,
  },
};

export const Damaged = {
  render: renderVitals,
  args: {
    status: statusWith(DAMAGED_RESOURCES, false),
    lowHp: false,
    revision: 2,
    epoch: 0,
  },
};

export const Low = {
  render: renderVitals,
  args: {
    status: statusWith(LOW_RESOURCES, true),
    lowHp: true,
    revision: 3,
    epoch: 0,
  },
};

export const Empty = {
  render: renderVitals,
  args: {
    status: statusWith(EMPTY_RESOURCES, false),
    lowHp: false,
    revision: 1,
    epoch: 0,
  },
};

export const ReducedMotion = {
  render: renderVitals,
  args: {
    status: statusWith(LOW_RESOURCES, true),
    lowHp: true,
    revision: 3,
    epoch: 0,
  },
  parameters: {
    docs: {
      description:
        "With `prefers-reduced-motion` set, the reduced-motion block in " +
        "styles/tokens.css collapses every `--motion-*` token to 1ms, so " +
        "the fill and the trailing (ghost) bar snap without a visible " +
        "transition. The numerals and the 危險 text marker still render, " +
        "so no information is lost when the motion is disabled.",
    },
  },
};
