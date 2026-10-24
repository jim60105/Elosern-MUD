// Display-only numeric formatting shared by the panels. The server's
// authoritative totals arrive as JSON numbers, so a percentage fold such as
// `6 × (1 − 5%)` arrives as 5.699999999999999 in IEEE-754. Panels print such
// a value at two decimals, which strips the binary float noise while a real
// fractional grant (2.5, 12.75) stays exact. The payload number itself is
// never rewritten: combat and resolution keep the full precision.
export function formatDisplayNumber(value) {
  const n = Number(value);
  if (!Number.isFinite(n)) return String(value ?? "");
  return String(Math.round(n * 100) / 100);
}
