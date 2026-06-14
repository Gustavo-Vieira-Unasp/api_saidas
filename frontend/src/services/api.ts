import axios from "axios";
import type {
  DateStrategy,
  ExitBatchResult,
  ExitRequest,
  Schedule,
  Template,
  TriggerType,
  User,
} from "../types";

const baseURL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export const api = axios.create({ baseURL });

const TOKEN_KEY = "unasp_token";

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string | null) {
  if (token) localStorage.setItem(TOKEN_KEY, token);
  else localStorage.removeItem(TOKEN_KEY);
}

api.interceptors.request.use((config) => {
  const token = getToken();
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

api.interceptors.response.use(
  (res) => res,
  (error) => {
    if (error.response?.status === 401) {
      setToken(null);
      if (window.location.pathname !== "/login") {
        window.location.href = "/login";
      }
    }
    return Promise.reject(error);
  }
);

// --- Auth ---
export async function register(
  ra: string,
  password: string,
  profile: string,
  fullName?: string
) {
  const { data } = await api.post<User>("/auth/register", {
    ra,
    password,
    profile,
    full_name: fullName || null,
  });
  return data;
}

export async function login(ra: string, password: string) {
  const form = new URLSearchParams();
  form.append("username", ra);
  form.append("password", password);
  const { data } = await api.post<{ access_token: string }>("/auth/login", form);
  setToken(data.access_token);
  return data;
}

export async function getMe() {
  const { data } = await api.get<User>("/auth/me");
  return data;
}

export async function updateProfile(profile: string) {
  const { data } = await api.put<User>("/auth/me/profile", { profile });
  return data;
}

export async function updatePassword(currentPassword: string, newPassword: string) {
  const { data } = await api.put<User>("/auth/me/password", {
    current_password: currentPassword,
    new_password: newPassword,
  });
  return data;
}

// --- Templates ---
export async function listTemplates() {
  const { data } = await api.get<Template[]>("/templates");
  return data;
}

export async function createTemplate(
  name: string,
  payload: Record<string, unknown>
) {
  const { data } = await api.post<Template>("/templates", { name, payload });
  return data;
}

export async function updateTemplate(
  id: number,
  name: string,
  payload: Record<string, unknown>
) {
  const { data } = await api.put<Template>(`/templates/${id}`, { name, payload });
  return data;
}

export async function deleteTemplate(id: number) {
  await api.delete(`/templates/${id}`);
}

// --- Exits ---
export async function sendExit(body: {
  template_id?: number;
  payload?: Record<string, string>;
  dry_run?: boolean;
}) {
  const { data } = await api.post<ExitRequest>("/exits/send", body);
  return data;
}

export async function listExits(limit = 50, status?: string) {
  const { data } = await api.get<ExitRequest[]>("/exits", {
    params: { limit, ...(status ? { status } : {}) },
  });
  return data;
}

export interface BatchPayload {
  template_id?: number | null;
  payload?: Record<string, string> | null;
  start_date: string;
  end_date: string;
  weekdays_only?: boolean;
  weekdays?: number[];
  hora_saida?: string | null;
  hora_retorno?: string | null;
  schedule_at?: string | null;
  dry_run?: boolean;
}

export async function batchExit(body: BatchPayload) {
  const { data } = await api.post<ExitBatchResult>("/exits/batch", body);
  return data;
}

export function screenshotUrl(exitId: number) {
  return `${baseURL}/exits/${exitId}/screenshot`;
}

// The screenshot endpoint requires the bearer token, which an <img src> cannot
// send. Fetch it as a blob (auth header attached by the interceptor) and return
// an object URL for the caller to render and later revoke.
export async function fetchScreenshotBlob(exitId: number) {
  const { data } = await api.get<Blob>(`/exits/${exitId}/screenshot`, {
    responseType: "blob",
  });
  return URL.createObjectURL(data);
}

// --- Schedules ---
export interface SchedulePayload {
  name: string;
  template_id?: number | null;
  payload?: Record<string, string> | null;
  trigger_type: TriggerType;
  run_at?: string | null;
  hour?: number | null;
  minute?: number | null;
  cron?: string | null;
  date_strategy?: DateStrategy;
  enabled?: boolean;
}

export async function listSchedules() {
  const { data } = await api.get<Schedule[]>("/schedules");
  return data;
}

export async function createSchedule(body: SchedulePayload) {
  const { data } = await api.post<Schedule>("/schedules", body);
  return data;
}

export async function updateSchedule(id: number, body: Partial<SchedulePayload>) {
  const { data } = await api.put<Schedule>(`/schedules/${id}`, body);
  return data;
}

export async function deleteSchedule(id: number) {
  await api.delete(`/schedules/${id}`);
}

export async function runScheduleNow(id: number) {
  const { data } = await api.post<ExitRequest>(`/schedules/${id}/run-now`);
  return data;
}

export async function runSchedulesBulk(scheduleIds: number[]) {
  const { data } = await api.post<ExitRequest[]>("/schedules/run-bulk", {
    schedule_ids: scheduleIds,
  });
  return data;
}
