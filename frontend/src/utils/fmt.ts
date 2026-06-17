/** Backend schedules use America/Sao_Paulo — always display in Brasília time. */
const APP_TIMEZONE = "America/Sao_Paulo";
const BRT_OFFSET = "-03:00";

type AppTimeKind = "utc" | "brasilia";

function hasExplicitOffset(iso: string): boolean {
  return /[zZ]$/.test(iso) || /[+-]\d{2}:\d{2}$/.test(iso);
}

/** Parse API datetimes; naive strings follow backend convention (UTC vs Brasília). */
export function parseAppDateTime(iso: string, kind: AppTimeKind): Date {
  if (hasExplicitOffset(iso)) {
    return new Date(iso);
  }
  const normalized = iso.length === 16 ? `${iso}:00` : iso;
  if (kind === "utc") {
    return new Date(`${normalized}Z`);
  }
  return new Date(`${normalized}${BRT_OFFSET}`);
}

function formatInBrasilia(date: Date): string {
  return date.toLocaleString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
    timeZone: APP_TIMEZONE,
  });
}

/** UTC timestamps from the API (Histórico, último envio). */
export function fmtDateTime(iso: string): string {
  return formatInBrasilia(parseAppDateTime(iso, "utc"));
}

/** Scheduled run time — naive values are wall clock in Brasília. */
export function fmtScheduleDateTime(iso: string): string {
  return formatInBrasilia(parseAppDateTime(iso, "brasilia"));
}

export function fmtDate(iso: string): string {
  return parseAppDateTime(iso, "utc").toLocaleDateString("pt-BR", {
    timeZone: APP_TIMEZONE,
  });
}
