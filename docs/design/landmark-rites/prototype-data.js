// Mock data for the landmark rite prototype. Reference only: the lines are
// the design document's own shape example, not shipped content.

export const DISTRICT = { key: "border_source_highlands", name: "界源高地", landmark: "源泉石龕" };
export const CITY_DISTRICT = { key: "capital_core", name: "王都核心", landmark: "王都中央廣場" };

export const GUARDIAN = { name: "泉之聲", form: "水面映出的聲音，只在有人俯身時開口。" };
export const CITY_GUARDIAN = { name: "廣場的目光", form: "石磚記得每一個站上來的人，也讓所有人都看得見。" };

export const ART = "/art/scenes/shrine_interior.webp";
export const CITY_ART = "/art/scenes/city_street.webp";

const self = (key, lines) => ({ scene_id: `rite.spring.${key}.self`, revision: "r1", lines });
const watch = (key, lines) => ({ scene_id: `rite.spring.${key}.watch`, revision: "r1", lines });

export function riteOptions({ watchScenes = true, third = false } = {}) {
  const options = [
    {
      key: "drink",
      label: "俯身飲下",
      seconds: 180,
      self: self("drink", [
        { kind: "narration", text: "石龕裡的水冷得像刀，映出你低頭的臉。" },
        { kind: "speech", speaker: "actor", text: "「你還在這裡嗎？」" },
        { kind: "speech", speaker: "host", text: "「喝了，就看得見這片地。」" },
        { kind: "narration", text: "水面貼上你的脣，像有一隻手從底下扶住你。" },
      ]),
      watch: watchScenes
        ? (name) =>
            watch("drink", [
              { kind: "narration", text: `${name}俯身，石龕的水面映出一張低垂的臉。` },
              { kind: "speech", speaker: "host", text: "「喝下去的人，會看見你們要走的路。」" },
              { kind: "narration", text: `${name}的肩沉下去，水面在脣邊碎開。` },
            ])
        : null,
    },
    {
      key: "bathe",
      label: "浸入池中",
      seconds: 300,
      self: self("bathe", [
        { kind: "narration", text: "你踏進石龕下的淺池，水沒過腳踝，再沒過膝。" },
        { kind: "speech", speaker: "host", text: "「再往下一點。這片地的形狀，在水底。」" },
        { kind: "narration", text: "水溫忽然變了，像有什麼從池底托住你的背。" },
      ]),
      // A solo-only ritual: no watch scene, so no companion may perform it.
      watch: null,
    },
  ];
  if (third) {
    options.push({
      key: "listen",
      label: "把耳貼上水面",
      seconds: 240,
      self: self("listen", [
        { kind: "narration", text: "你側過臉，耳廓碰到水面的那一刻，四周的風聲都退開了。" },
        { kind: "speech", speaker: "host", text: "「聽。高地的每一條溪，都從這裡開始。」" },
      ]),
      watch: watchScenes
        ? (name) =>
            watch("listen", [
              { kind: "narration", text: `${name}側過臉，把耳貼上水面。` },
              { kind: "speech", speaker: "host", text: "「聽得見的人，才帶得了路。」" },
            ])
        : null,
    });
  }
  return options;
}
