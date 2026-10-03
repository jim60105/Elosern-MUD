const bounds = { scale: [0.2, 2], x: [-0.5, 0.5], y: [-0.5, 0.5] };
const identity = { scale: 1, x: 0, y: 0 };

export function clampStage(stage) {
  return Object.fromEntries(Object.entries(bounds).map(([field, [min, max]]) => {
    const value = stage?.[field];
    return [field, typeof value === "number" && Number.isFinite(value) ? Math.min(max, Math.max(min, value)) : identity[field]];
  }));
}

export function moveStage(stage, dx, dy) {
  const current = clampStage(stage);
  return clampStage({ ...current, x: current.x + (Number.isFinite(dx) ? dx : 0), y: current.y + (Number.isFinite(dy) ? dy : 0) });
}

export function editStageField(stage, field, value) {
  const current = clampStage(stage);
  if (!Object.hasOwn(bounds, field) || typeof value !== "number" || !Number.isFinite(value)) return current;
  return clampStage({ ...current, [field]: value });
}
