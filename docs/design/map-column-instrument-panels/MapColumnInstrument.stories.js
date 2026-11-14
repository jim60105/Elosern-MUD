// Design prototype: the right-hand island column (PlaceCard, LocalMap,
// ObjectiveTracker) restated in the instrument panel style of
// docs/development/hud-instrument-panels.md: three separate instrument
// panels, each with no box, its own feathered ink ground and its own brass
// fitting at its top-right corner. Reference only: mock
// data, not wired to any payload; the live components are untouched.
//
// Try it: flip `layout` between `instrument`, `current` and `compare`; hover
// or Tab to the two place actions for the brass tick; switch `backdrop` to
// judge the feathered ground over dark and bright art.
import { h } from "vue";
import {
  LOCAL_MAP_INTERIOR_SAMPLE,
  LOCAL_MAP_ORDINARY_SAMPLE,
  LOCAL_MAP_UNAVAILABLE_SAMPLE,
  LOCAL_MAP_WILDERNESS_METRIC_SAMPLE,
  OBJECTIVES_PANEL_SAMPLE,
  STATUS_PANEL_SAMPLE,
  localMapModelFor,
} from "../../../web/webclient-app/stories/fixtures.js";
import MapColumnPrototype from "./MapColumnPrototype.vue";

const render = (args) => ({ render: () => h(MapColumnPrototype, args) });

const counted = (progress, quantity) => ({
  quest_id: "q_progress",
  display_name: "討伐水妖",
  objective_line: "討伐渡口水妖",
  stage_index: 1,
  stage_total: 1,
  stage_progress: progress,
  objective_quantity: quantity,
  reward_copper: 200,
  deadline_line: null,
});

const base = {
  layout: "instrument",
  backdrop: "city_street",
  locationLabel: "城門廣場",
  timeLabel: "春季 3 日 ‧ 12:00",
  actionsEnabled: true,
  localMap: localMapModelFor(LOCAL_MAP_ORDINARY_SAMPLE),
  rows: [counted(3, 10), ...OBJECTIVES_PANEL_SAMPLE.rows],
  status: STATUS_PANEL_SAMPLE,
  visible: true,
  motionLevel: "full",
};

export default {
  title: "Design/MapColumnInstrument",
  component: MapColumnPrototype,
  render,
  argTypes: {
    layout: { control: "inline-radio", options: ["instrument", "current", "compare"] },
    backdrop: { control: "select", options: ["city_street", "coastal_path", "cave_interior"] },
    motionLevel: { control: "inline-radio", options: ["full", "reduced", "off"] },
  },
};

// The proposal on the exploration stage, with the vitals dock lower-left.
export const Exploration = { args: { ...base } };
// The live column at the same position, for an A/B flip.
export const Current = { args: { ...base, layout: "current" } };
// Both columns on one stage.
export const Compare = { args: { ...base, layout: "compare" } };
// Bright art behind the feathered ground.
export const BrightBackdrop = { args: { ...base, backdrop: "coastal_path" } };

// The place lines alone, as the travel stage mounts the card.
export const PlaceOnly = {
  args: { ...base, localMap: null, rows: [], actionsEnabled: false, locationLabel: "西部丘陵與谷地", timeLabel: "夏季 12 日 ‧ 06:40" },
};
// An overlong place name truncates; the heading keeps the full text.
export const LongPlaceName = {
  args: { ...base, locationLabel: "伊洛瑟恩王都外城區‧商人公會附屬倉庫的地下儲藏室", timeLabel: "秋季 28 日 ‧ 23:59" },
};
// Nothing committed: the two placeholders.
export const Placeholders = {
  args: { ...base, locationLabel: null, timeLabel: null, actionsEnabled: false, rows: [] },
};

// A reached objective: the filled lozenge with its check.
export const ObjectiveDone = { args: { ...base, rows: [OBJECTIVES_PANEL_SAMPLE.rows[0]] } };
// A reward objective with further rows: `+80` beside the stacked-lines count.
export const ObjectiveReward = {
  args: { ...base, rows: [OBJECTIVES_PANEL_SAMPLE.rows[1], OBJECTIVES_PANEL_SAMPLE.rows[2]] },
};
// A counted objective completed: every tick reached.
export const ObjectiveCountedDone = { args: { ...base, rows: [counted(5, 5)] } };
// A quantity above the tick limit: one continuous tapered stroke.
export const ObjectiveLargeQuantity = { args: { ...base, rows: [counted(17, 40)] } };
// A long objective line truncates inside the column.
export const ObjectiveLongLine = {
  args: {
    ...base,
    rows: [
      {
        ...OBJECTIVES_PANEL_SAMPLE.rows[1],
        objective_line: "在第三個滿月之前，把灰婆婆託付的封蠟信件交給北岸燈塔的守望人",
      },
      OBJECTIVES_PANEL_SAMPLE.rows[2],
    ],
  },
};

// The radial (graph) minimap of an interior.
export const InteriorMap = { args: { ...base, localMap: localMapModelFor(LOCAL_MAP_INTERIOR_SAMPLE) } };
// The metric wilderness minimap with its scale caption.
export const WildernessMap = {
  args: { ...base, backdrop: "coastal_path", localMap: localMapModelFor(LOCAL_MAP_WILDERNESS_METRIC_SAMPLE) },
};
// The minimap's unavailable form.
export const MapUnavailable = { args: { ...base, localMap: localMapModelFor(LOCAL_MAP_UNAVAILABLE_SAMPLE) } };

// The reveal: toggle `visible` to watch the column drop out of the top edge.
export const Reveal = { args: { ...base, visible: true } };
