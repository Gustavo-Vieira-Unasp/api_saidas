// Count how many exits a batch plan would create, mirroring backend _date_range.
export function countMatchingDays(
  startDate: string,
  endDate: string,
  weekdays: number[]
): number {
  const start = parseIso(startDate);
  const end = parseIso(endDate);
  if (!start || !end || end < start || weekdays.length === 0) return 0;

  const selected = new Set(weekdays);
  let count = 0;
  const current = new Date(start);
  while (current <= end) {
    // JS getDay(): Sun=0 … Sat=6 → Python weekday(): Mon=0 … Sun=6
    const pyWeekday = (current.getDay() + 6) % 7;
    if (selected.has(pyWeekday)) count++;
    current.setDate(current.getDate() + 1);
  }
  return count;
}

function parseIso(iso: string): Date | null {
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(iso);
  if (!m) return null;
  const d = new Date(Number(m[1]), Number(m[2]) - 1, Number(m[3]));
  if (
    d.getFullYear() !== Number(m[1]) ||
    d.getMonth() !== Number(m[2]) - 1 ||
    d.getDate() !== Number(m[3])
  ) {
    return null;
  }
  return d;
}
