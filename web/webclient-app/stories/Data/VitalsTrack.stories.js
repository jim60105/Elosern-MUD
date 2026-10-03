import { h, ref } from "vue";
import VitalsTrack from "../../components/VitalsTrack.vue";
import ShopPanel from "../../components/ShopPanel.vue";
import { SERVICES_PANEL_SAMPLE, STATUS_PANEL_SAMPLE } from "../fixtures.js";

// VitalsTrack (H2, webclient-hud-02-status-islands, design D4/D5;
// vitals-bar-redesign design D2): the dock's three compact bars with the
// numerals on each track, framed at the dock's 25vw width on the dock's ink —
// full / damaged / low / empty for each of hp/mp/sp,
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

// The dock frame: VitalsTrack is transparent; StatusPanel's root carries the
// dock chrome, so the stories show the bars on the same ink.
const DOCK_FRAME = "width: 25vw; min-width: 320px; box-sizing: border-box; padding: 10px 18px 10px 26px; background: var(--panel);";

const renderVitals = (args) => ({
  render: () =>
    h("div", { style: DOCK_FRAME }, [h(VitalsTrack, args)]),
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
        "At the `reduced` or `off` motion level the block in " +
        "styles/tokens.css resolves the trail and fill tokens to 0ms, so " +
        "the fill and the trailing (ghost) bar snap without a visible " +
        "transition. The numerals and the 危險 text marker still render, " +
        "so no information is lost when the motion is disabled.",
    },
  },
};

// A playing combat round's displayed hit points (webclient-combat-beat-queue
// D7): the numerals, the fill, and the trailing bar's ratio all follow the
// beat's `hp_after`, and the committed value returns once the round ends.
export const DisplayedHp = {
  render: renderVitals,
  args: {
    status: statusWith(DAMAGED_RESOURCES, false),
    lowHp: false,
    displayHp: 60,
    revision: 4,
    epoch: 0,
  },
};

// Real resource and price updates, including unequal digit counts. No timers:
// reviewers can compare both states under full, reduced, or off motion.
export const ChangingNumerals = {
  render: () => ({
    setup() {
      const changed = ref(false);
      return () => {
        const resources = {
          hp: { current: changed.value ? 139 : 9, maximum: 405 },
          mp: { current: changed.value ? 888 : 111, maximum: 999 },
          sp: { current: changed.value ? 88 : 11, maximum: 99 },
        };
        const services = {
          ...SERVICES_PANEL_SAMPLE,
          shop: {
            ...SERVICES_PANEL_SAMPLE.shop,
            stock: SERVICES_PANEL_SAMPLE.shop.stock.map((row, index) => ({
              ...row,
              buy_copper: changed.value ? (index ? 888 : 1399) : (index ? 111 : 9),
              sell_copper: changed.value ? 88 : 11,
            })),
          },
        };
        return h("section", { style: "max-width: 680px; padding: 16px;" }, [
          h("button", {
            class: "ui-btn",
            "data-testid": "change-numerals",
            onClick: () => { changed.value = !changed.value; },
          }, "Change values"),
          h("div", { style: `${DOCK_FRAME} margin: 16px 0;` }, [
            h(VitalsTrack, { status: statusWith(resources), revision: changed.value ? 2 : 1, epoch: 0 }),
          ]),
          h(ShopPanel, { services }),
        ]);
      };
    },
  }),
};
