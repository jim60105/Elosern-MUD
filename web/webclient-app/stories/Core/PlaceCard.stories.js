import { h, onBeforeUnmount, onMounted, ref } from "vue";
import PlaceCard from "../../components/PlaceCard.vue";

// PlaceCard (webclient-avg-place-card-top-bar design D3): the stage's place
// card. Props: locationLabel (the store's resolved place name — the
// `local_map` current-node label, else the status location) and timeLabel
// (the committed world time); null renders the `位置：--` / `時間：--`
// placeholders. Display-only: no control and no emitted events. The frame
// below sizes it like its `place` anchor at the 1920x1080 reference
// (`--left-column` 330px minus the 16px gutters, `--place-h` tall).

const renderCard = (args) => ({
  render: () =>
    h(
      "div",
      { style: "width:298px;height:var(--place-h);padding:0;" },
      [h(PlaceCard, args)],
    ),
});

export default {
  title: "Core/PlaceCard",
  component: PlaceCard,
};

export const Default = {
  render: renderCard,
  args: { locationLabel: "測試起點", timeLabel: "春季 3 日 · 12:00" },
};

export const WildernessRegion = {
  render: renderCard,
  args: { locationLabel: "西部丘陵與谷地", timeLabel: "夏季 12 日 · 06:40" },
};

export const Placeholders = {
  render: renderCard,
  args: { locationLabel: null, timeLabel: null },
};

export const LongLabel = {
  render: renderCard,
  args: {
    locationLabel: "伊洛瑟恩王都外城區・商人公會附屬倉庫的地下儲藏室",
    timeLabel: "秋季 28 日 · 23:59",
  },
};

// A location change (webclient-scene-transitions, design D3): every few
// seconds the location moves on — the new name slides in from the left as
// the old one fades — and in between only the world time ticks, which swaps
// the time line with no transition.
const WALK = ["石板廣場", "北岸大道", "西風酒館", "伊洛瑟恩王都外城區・商人公會附屬倉庫的地下儲藏室"];

function renderLocationChange() {
  return {
    setup() {
      const tick = ref(0);
      let timer = null;
      onMounted(() => {
        timer = setInterval(() => {
          tick.value += 1;
        }, 1500);
      });
      onBeforeUnmount(() => clearInterval(timer));
      return () => {
        const place = WALK[Math.floor(tick.value / 2) % WALK.length];
        const minute = String((tick.value * 5) % 60).padStart(2, "0");
        return h("div", { style: "width:298px;height:var(--place-h);padding:0;" }, [
          h(PlaceCard, { locationLabel: place, timeLabel: `春季 3 日 · 12:${minute}` }),
        ]);
      };
    },
  };
}

export const LocationChange = {
  render: renderLocationChange,
};
