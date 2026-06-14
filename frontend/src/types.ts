export interface User {
  id: number;
  ra: string;
  full_name: string | null;
  has_unasp_credentials: boolean;
  unasp_profile: string | null;
  created_at: string;
}

export type ExitPayload = Record<string, string>;

// Per-weekday time overrides stored inside a template's payload under the
// `weekly_times` key. Keys are Python weekday() indices ("0" = Monday).
export type WeeklyTimes = Record<
  string,
  { hora_saida: string; hora_retorno: string }
>;

export interface Template {
  id: number;
  name: string;
  payload: ExitPayload;
  created_at: string;
}

export type SubmissionStatus = "pending" | "sent" | "failed";

export interface ExitRequest {
  id: number;
  schedule_id: number | null;
  payload: ExitPayload;
  status: SubmissionStatus;
  message: string | null;
  source: string;
  screenshot_path: string | null;
  created_at: string;
}

export type TriggerType = "once" | "daily" | "weekdays" | "cron";

export type DateStrategy = "fixed" | "today" | "tomorrow";

export interface Schedule {
  id: number;
  name: string;
  template_id: number | null;
  payload: ExitPayload | null;
  trigger_type: TriggerType;
  run_at: string | null;
  hour: number | null;
  minute: number | null;
  cron: string | null;
  date_strategy: DateStrategy;
  enabled: boolean;
  last_run_at: string | null;
  created_at: string;
}

export interface ExitBatchResult {
  sent: ExitRequest[];
  scheduled: Schedule[];
  failed: { date: string; error: string }[];
}
