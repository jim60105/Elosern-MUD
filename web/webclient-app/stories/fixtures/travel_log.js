// Synthetic travel_log v1 notices (wilderness-travel-log-ui) in the exact
// wire shape, for the TravelLog stories and the travel log suites. Every
// batch passes the real protocol validator; nothing names shipped content.

let serial = 0;

/** One wire entry of `kind` with its exact params. */
export function travelEntry(kind, params, { day = 12, time = "07:40", text, id } = {}) {
  serial += 1;
  return {
    id: id ?? `${"f".repeat(32)}:story${String(serial).padStart(3, "0")}.0`,
    kind,
    tick: (day - 1) * 86400 + Number(time.slice(0, 2)) * 3600 + Number(time.slice(3)) * 60,
    day,
    time,
    text,
    params,
  };
}

/** The exact available panel over `entries`. */
export function travelLogPanel(entries) {
  return { schema_version: 1, available: true, entries };
}

/** A morning-to-dusk stretch of one leg, one notice of most kinds. */
export function travelJourney() {
  return [
    travelEntry("region_entered", { name: "合成東麓" }, { day: 12, time: "06:10", text: "進入合成東麓。" }),
    travelEntry("woodland_entered", { name: "合成東麓" }, { day: 12, time: "07:40", text: "走進合成東麓的林地。" }),
    travelEntry("ford_crossed", { name: "合成東麓" }, { day: 12, time: "09:05", text: "涉過合成東麓的淺灘。" }),
    travelEntry("hostile_sighted", { name: "合成灰狼", count: 3, threat: null }, { day: 12, time: "10:20", text: "發現合成灰狼 ×3。" }),
    travelEntry(
      "look",
      { prose: "林間的霧氣還沒散。\n北方有一道低矮的山脊，石縫裡長著苔蘚。\n溪水在腳邊流過。" },
      { day: 12, time: "11:00", text: "環顧四周：林間的霧氣還沒散。" },
    ),
    travelEntry(
      "fatigue_stage",
      { member_id: "302", name: "合成伊蓮", stage: "light", label: "微倦" },
      { day: 12, time: "14:30", text: "合成伊蓮：微倦。" },
    ),
    travelEntry(
      "landmark_reached",
      { arrival_node: "wild:elosern:60:80", name: "合成古哨塔", lit_district: "合成古哨塔", prose: "風從塔頂的缺口灌進來。", artwork: null },
      { day: 12, time: "16:50", text: "抵達合成古哨塔。合成古哨塔已探明。" },
    ),
    travelEntry("dusk", {}, { day: 12, time: "18:00", text: "暮色降臨。" }),
    travelEntry("nightfall", {}, { day: 12, time: "19:30", text: "入夜了。" }),
    travelEntry("camp_result", { summary: "一夜無事，眾人都睡得不錯。" }, { day: 13, time: "06:00", text: "一夜無事，眾人都睡得不錯。" }),
  ];
}
