// Synthetic S5 save payloads for stories and tests (gm-portal-s5-saves).
const clock = (tick, year, season, day, hour, minute) => ({ tick, year, season, day, hour, minute });

export const SAVES = Object.freeze([
  {
    id: "20261007T061530-3fa9c2",
    label: "決戰之前：港口倉庫的密會",
    kind: "manual",
    created_at: "2026-10-07T06:15:30.120000+00:00",
    clock: clock(1987200, 1, "夏", 4, 21, 40),
    players: [{ name: "艾琳", location: "harbor_warehouse" }],
    migrations: { narrative: "0011_synthetic" },
    file_count: 312,
    size_bytes: 88_473_600,
    deletable: true,
    pending: false,
  },
  {
    id: "20261007T055002-a1b2c3",
    label: "讀取「港口初到」前",
    kind: "auto_restore",
    created_at: "2026-10-07T05:50:02.004000+00:00",
    clock: clock(1900800, 1, "夏", 3, 8, 5),
    players: [
      { name: "艾琳", location: "guild_hall" },
      { name: "洛斯", location: "guild_hall" },
      { name: "米雅", location: "market_square" },
    ],
    migrations: { narrative: "0011_synthetic" },
    file_count: 298,
    size_bytes: 84_201_472,
    deletable: false,
    pending: false,
  },
  {
    id: "20261006T221044-0d9e8f",
    label: "",
    kind: "auto_intervention",
    created_at: "2026-10-06T22:10:44.500000+00:00",
    clock: clock(864000, 1, "春", 11, 0, 0),
    players: [],
    migrations: { narrative: "0010_synthetic" },
    file_count: 120,
    size_bytes: 41_943_040,
    deletable: false,
    pending: false,
  },
  {
    id: "20261006T090000-77aa11",
    label: "港口初到",
    kind: "manual",
    created_at: "2026-10-06T09:00:00.000000+00:00",
    clock: null,
    players: [{ name: "艾琳", location: null }],
    migrations: { narrative: "0009_synthetic" },
    file_count: 1,
    size_bytes: 2_097_152,
    deletable: true,
    pending: false,
  },
]);

export const SAVES_LISTING = Object.freeze({
  saves: SAVES,
  restore_result: {
    save: "20261006T090000-77aa11",
    kind: "manual",
    label: "港口初到",
    outcome: "restored",
    reason: null,
    finished_at: "2026-10-07T05:52:11+00:00",
  },
  pending: null,
  autosave_keep: 10,
});

export const FAILED_RESULT = Object.freeze({
  save: "20261006T221044-0d9e8f",
  kind: "auto_intervention",
  label: "",
  outcome: "failed",
  reason: "size mismatch: forest.webp",
  finished_at: "2026-10-07T05:52:11+00:00",
});
