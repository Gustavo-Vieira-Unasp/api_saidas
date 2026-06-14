import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import DateInput from "../components/DateInput";
import ExitForm, { validatePayload } from "../components/ExitForm";
import SuccessToast from "../components/SuccessToast";
import TimePicker from "../components/TimePicker";
import { useAuth } from "../context/AuthContext";
import { batchExit, listTemplates } from "../services/api";
import { MAX_BATCH_ITEMS } from "../constants/limits";
import { countMatchingDays } from "../utils/batchDays";
import type {
  ExitBatchResult,
  ExitPayload,
  Template,
  WeeklyTimes,
} from "../types";

// Python weekday() order: Monday = 0 ... Sunday = 6.
const WEEKDAY_CHIPS = [
  { idx: 0, label: "Seg" },
  { idx: 1, label: "Ter" },
  { idx: 2, label: "Qua" },
  { idx: 3, label: "Qui" },
  { idx: 4, label: "Sex" },
  { idx: 5, label: "Sáb" },
  { idx: 6, label: "Dom" },
];

export default function Batch() {
  const { user } = useAuth();
  const [templates, setTemplates] = useState<Template[]>([]);
  const [selectedTemplate, setSelectedTemplate] = useState<number | "">("");
  const [payload, setPayload] = useState<ExitPayload>({});
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [weekdays, setWeekdays] = useState<number[]>([0, 1, 2, 3, 4]);
  const [horaSaida, setHoraSaida] = useState("");
  const [horaRetorno, setHoraRetorno] = useState("");
  const [perDayTimes, setPerDayTimes] = useState(false);
  const [weeklyTimes, setWeeklyTimes] = useState<WeeklyTimes>({});
  const [mode, setMode] = useState<"now" | "schedule">("schedule");
  const [scheduleAt, setScheduleAt] = useState("07:00");
  const [dryRun, setDryRun] = useState(true);
  const [confirmReal, setConfirmReal] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<ExitBatchResult | null>(null);
  const [toast, setToast] = useState<string | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);

  const plannedCount = countMatchingDays(startDate, endDate, weekdays);
  const overLimit = plannedCount > MAX_BATCH_ITEMS;

  useEffect(() => {
    listTemplates()
      .then(setTemplates)
      .catch(() => setLoadError("Não foi possível carregar os tipos de saída."));
  }, []);

  const applyTemplate = (id: number | "") => {
    setSelectedTemplate(id);
    if (id === "") return;
    const tpl = templates.find((t) => t.id === id);
    if (tpl) setPayload({ ...tpl.payload });
  };

  const toggleWeekday = (idx: number) => {
    setWeekdays((prev) =>
      prev.includes(idx)
        ? prev.filter((d) => d !== idx)
        : [...prev, idx].sort((a, b) => a - b)
    );
  };

  const handlePerDayToggle = (on: boolean) => {
    if (on) {
      // Start from the standard times so each day initially follows them; the
      // user can then override individual days.
      const seeded: WeeklyTimes = {};
      for (const idx of weekdays) {
        seeded[String(idx)] = {
          hora_saida: horaSaida,
          hora_retorno: horaRetorno,
        };
      }
      setWeeklyTimes(seeded);
    }
    setPerDayTimes(on);
  };

  const setDayTime = (
    dayIdx: number,
    field: "hora_saida" | "hora_retorno",
    val: string
  ) => {
    const key = String(dayIdx);
    setWeeklyTimes((prev) => ({
      ...prev,
      [key]: {
        hora_saida: prev[key]?.hora_saida ?? "",
        hora_retorno: prev[key]?.hora_retorno ?? "",
        [field]: val,
      },
    }));
  };

  const plan = async (confirmed = false) => {
    const missing = validatePayload(payload, [
      "data_saida",
      "hora_saida",
      "hora_retorno",
    ]);
    if (missing.length > 0) {
      setConfirmReal(false);
      return setError(`Preencha os campos obrigatórios: ${missing.join(", ")}`);
    }
    if (!startDate || !endDate) {
      setConfirmReal(false);
      return setError("Informe o intervalo de datas");
    }
    if (weekdays.length === 0) {
      setConfirmReal(false);
      return setError("Selecione ao menos um dia da semana");
    }
    if (!horaSaida || !horaRetorno) {
      setConfirmReal(false);
      return setError("Informe a hora de saída e de retorno");
    }
    const plannedCount = countMatchingDays(startDate, endDate, weekdays);
    if (plannedCount > MAX_BATCH_ITEMS) {
      setConfirmReal(false);
      return setError(
        `Máximo de ${MAX_BATCH_ITEMS} saídas por operação (selecionadas: ${plannedCount}). Reduza o intervalo ou os dias da semana.`
      );
    }
    if (mode === "now" && !dryRun && !confirmed) {
      setConfirmReal(true);
      return;
    }
    setConfirmReal(false);
    setError(null);
    setResult(null);
    setBusy(true);
    try {
      const usingTemplate =
        selectedTemplate !== "" && Object.keys(payload).length === 0;

      // Per-day times ride inside the payload under `weekly_times` (same key the
      // backend already pops and applies). Keep only days with both times set.
      let outboundPayload: Record<string, unknown> | undefined = usingTemplate
        ? undefined
        : { ...payload };
      if (perDayTimes && outboundPayload) {
        const filled: WeeklyTimes = {};
        for (const idx of weekdays) {
          const t = weeklyTimes[String(idx)];
          if (t?.hora_saida && t?.hora_retorno) filled[String(idx)] = t;
        }
        outboundPayload = { ...outboundPayload, weekly_times: filled };
      }

      const res = await batchExit({
        template_id: usingTemplate ? selectedTemplate : undefined,
        payload: outboundPayload as ExitPayload | undefined,
        start_date: startDate,
        end_date: endDate,
        weekdays,
        hora_saida: perDayTimes ? undefined : horaSaida || undefined,
        hora_retorno: perDayTimes ? undefined : horaRetorno || undefined,
        schedule_at: mode === "schedule" ? scheduleAt : undefined,
        dry_run: mode === "now" ? dryRun : undefined,
      });
      setResult(res);
      const parts: string[] = [];
      if (res.scheduled.length > 0) {
        parts.push(`${res.scheduled.length} agendamento(s) criado(s)`);
      }
      if (res.sent.length > 0) {
        parts.push(`${res.sent.length} envio(s) processado(s)`);
      }
      setToast(parts.length > 0 ? `${parts.join(" · ")}.` : "Plano concluído.");
    } catch (err: any) {
      setError(err.response?.data?.detail || "Erro ao planejar");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-bold">Planejar semana</h1>
        <p className="text-sm text-slate-500">
          Crie várias saídas de uma vez em um intervalo de datas, enviando agora
          ou agendando cada dia.
        </p>
      </div>

      {loadError && <p className="text-sm text-red-600">{loadError}</p>}

      {!user?.has_unasp_credentials && (
        <div className="rounded-lg border border-amber-300 bg-amber-50 p-4 text-sm text-amber-800">
          Você ainda não cadastrou suas credenciais do UNASP.{" "}
          <Link to="/settings" className="font-medium underline">
            Cadastre em Configurações
          </Link>
          .
        </div>
      )}

      <div className="card space-y-4">
        {templates.length > 0 && (
          <div>
            <label className="label">Usar um tipo de saída (opcional)</label>
            <select
              className="input"
              value={selectedTemplate}
              onChange={(e) =>
                applyTemplate(e.target.value === "" ? "" : Number(e.target.value))
              }
            >
              <option value="">-- Preencher manualmente --</option>
              {templates.map((t) => (
                <option key={t.id} value={t.id}>
                  {t.name}
                </option>
              ))}
            </select>
          </div>
        )}

        <ExitForm
          value={payload}
          onChange={setPayload}
          excludeFields={["data_saida", "hora_saida", "hora_retorno"]}
        />

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div>
            <label className="label">Data inicial</label>
            <DateInput value={startDate} onChange={setStartDate} />
          </div>
          <div>
            <label className="label">Repetir até</label>
            <DateInput value={endDate} onChange={setEndDate} />
          </div>
        </div>

        <div>
          <div className="flex items-center justify-between">
            <label className="label">Dias da semana</label>
            <span className="space-x-3 text-xs">
              <button
                type="button"
                className="text-brand hover:underline"
                onClick={() => setWeekdays([0, 1, 2, 3, 4, 5, 6])}
              >
                Todos
              </button>
              <button
                type="button"
                className="text-slate-400 hover:underline"
                onClick={() => setWeekdays([])}
              >
                Nenhum
              </button>
            </span>
          </div>
          <div className="flex flex-wrap gap-2">
            {WEEKDAY_CHIPS.map(({ idx, label }) => {
              const active = weekdays.includes(idx);
              return (
                <button
                  key={idx}
                  type="button"
                  onClick={() => toggleWeekday(idx)}
                  className={`rounded-full px-3 py-1 text-sm font-medium transition ${
                    active
                      ? "bg-brand text-white"
                      : "bg-slate-100 text-slate-600 hover:bg-slate-200"
                  }`}
                >
                  {active && <span className="mr-1 text-xs">✓</span>}
                  {label}
                </button>
              );
            })}
          </div>
          {plannedCount > 0 && (
            <p
              className={`mt-2 text-xs ${overLimit ? "text-red-600" : "text-slate-400"}`}
            >
              {plannedCount} saída(s) serão criadas
              {overLimit &&
                ` — máximo permitido: ${MAX_BATCH_ITEMS}. Reduza o intervalo ou os dias.`}
            </p>
          )}
        </div>

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div>
            <label className="label">Hora de saída</label>
            <TimePicker
              value={horaSaida}
              onChange={setHoraSaida}
              clearable={false}
            />
          </div>
          <div>
            <label className="label">Hora de retorno</label>
            <TimePicker
              value={horaRetorno}
              onChange={setHoraRetorno}
              clearable={false}
            />
          </div>
        </div>

        <label className="flex items-center gap-2 text-sm text-slate-700">
          <input
            type="checkbox"
            checked={perDayTimes}
            onChange={(e) => handlePerDayToggle(e.target.checked)}
          />
          Horários diferentes por dia
        </label>

        {perDayTimes && (
          <div className="space-y-2 rounded-lg border border-slate-200 p-3">
            <p className="label">Horários por dia</p>
            {weekdays.length === 0 && (
              <p className="text-xs text-slate-400">
                Selecione ao menos um dia da semana acima.
              </p>
            )}
            {WEEKDAY_CHIPS.filter(({ idx }) => weekdays.includes(idx)).map(
              ({ idx, label }) => (
                <div
                  key={idx}
                  className="grid grid-cols-[4rem,1fr,1fr] items-center gap-2"
                >
                  <span className="text-sm text-slate-600">{label}</span>
                  <TimePicker
                    value={weeklyTimes[String(idx)]?.hora_saida ?? ""}
                    onChange={(v) => setDayTime(idx, "hora_saida", v)}
                  />
                  <TimePicker
                    value={weeklyTimes[String(idx)]?.hora_retorno ?? ""}
                    onChange={(v) => setDayTime(idx, "hora_retorno", v)}
                  />
                </div>
              )
            )}
            <p className="text-xs text-slate-400">
              Cada dia começa seguindo o horário padrão acima; ajuste apenas os
              dias que precisam de horários diferentes.
            </p>
          </div>
        )}

        <div>
          <label className="label">Quando enviar</label>
          <select
            className="input"
            value={mode}
            onChange={(e) => setMode(e.target.value as "now" | "schedule")}
          >
            <option value="schedule">Agendar cada dia</option>
            <option value="now">Enviar todos agora</option>
          </select>
        </div>

        {mode === "schedule" && (
          <div>
            <label className="label">Horário do agendamento (cada dia)</label>
            <TimePicker
              value={scheduleAt}
              onChange={setScheduleAt}
              clearable={false}
            />
          </div>
        )}

        {mode === "now" && (
          <label className="flex items-center gap-2 text-sm text-slate-700">
            <input
              type="checkbox"
              checked={dryRun}
              onChange={(e) => setDryRun(e.target.checked)}
            />
            Modo teste (preenche, não envia)
          </label>
        )}

        {error && <p className="text-sm text-red-600">{error}</p>}

        <div className="flex justify-end">
          <button
            className="btn-primary"
            onClick={() => plan()}
            disabled={busy || !user?.has_unasp_credentials || overLimit}
          >
            {busy ? "Processando..." : "Planejar"}
          </button>
        </div>
      </div>

      {confirmReal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <div className="card max-w-md space-y-4">
            <h2 className="font-semibold">Envio real</h2>
            <p className="text-sm text-slate-600">
              Isto fará envios REAIS no site do UNASP para cada dia selecionado.
              Continuar?
            </p>
            <div className="flex justify-end gap-2">
              <button className="btn-secondary" onClick={() => setConfirmReal(false)}>
                Cancelar
              </button>
              <button className="btn-primary" onClick={() => plan(true)}>
                Continuar
              </button>
            </div>
          </div>
        </div>
      )}

      {result && (
        <div className="card space-y-2 text-sm">
          {result.failed.length > 0 && (
            <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-red-800">
              <p className="font-medium">
                {result.failed.length} dia(s) com falha:
              </p>
              <ul className="mt-1 list-inside list-disc text-sm">
                {result.failed.map((f) => (
                  <li key={f.date}>
                    {f.date}: {f.error}
                  </li>
                ))}
              </ul>
            </div>
          )}
          {result.scheduled.length > 0 && (
            <p className="text-slate-700">
              {result.scheduled.length} agendamento(s) criado(s). Veja em{" "}
              <Link to="/schedules" className="text-brand">
                Agendamentos
              </Link>
              .
            </p>
          )}
          {result.sent.length > 0 && (
            <p className="text-slate-700">
              {result.sent.length} envio(s) processado(s). Veja em{" "}
              <Link to="/history" className="text-brand">
                Histórico
              </Link>
              .
            </p>
          )}
        </div>
      )}

      {toast && (
        <SuccessToast message={toast} onClose={() => setToast(null)} />
      )}
    </div>
  );
}
