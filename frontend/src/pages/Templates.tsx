import { useEffect, useState } from "react";
import ExitForm, { formatPayloadSummary } from "../components/ExitForm";
import TimePicker from "../components/TimePicker";
import {
  createTemplate,
  deleteTemplate,
  listTemplates,
  updateTemplate,
} from "../services/api";
import type { ExitPayload, Template, WeeklyTimes } from "../types";

const WEEKDAYS = [
  "Segunda",
  "Terça",
  "Quarta",
  "Quinta",
  "Sexta",
  "Sábado",
  "Domingo",
];

function payloadFromTemplate(tpl: Template) {
  const { hora_saida = "", hora_retorno = "", weekly_times, ...rest } =
    tpl.payload as ExitPayload & { weekly_times?: WeeklyTimes };
  return {
    payload: rest as ExitPayload,
    horaSaida: hora_saida,
    horaRetorno: hora_retorno,
    weekly: Boolean(weekly_times && Object.keys(weekly_times).length > 0),
    weeklyTimes: (weekly_times ?? {}) as WeeklyTimes,
  };
}

export default function Templates() {
  const [templates, setTemplates] = useState<Template[]>([]);
  const [name, setName] = useState("");
  const [payload, setPayload] = useState<ExitPayload>({});
  const [horaSaida, setHoraSaida] = useState("");
  const [horaRetorno, setHoraRetorno] = useState("");
  const [weekly, setWeekly] = useState(false);
  const [weeklyTimes, setWeeklyTimes] = useState<WeeklyTimes>({});
  const [editingId, setEditingId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const load = () =>
    listTemplates()
      .then(setTemplates)
      .catch(() => setLoadError("Não foi possível carregar os tipos de saída."));

  useEffect(() => {
    load();
  }, []);

  const resetForm = () => {
    setEditingId(null);
    setName("");
    setPayload({});
    setHoraSaida("");
    setHoraRetorno("");
    setWeekly(false);
    setWeeklyTimes({});
  };

  const handleWeeklyToggle = (on: boolean) => {
    if (on) {
      const seeded: WeeklyTimes = {};
      for (let idx = 0; idx < WEEKDAYS.length; idx++) {
        seeded[String(idx)] = {
          hora_saida: horaSaida,
          hora_retorno: horaRetorno,
        };
      }
      setWeeklyTimes(seeded);
    }
    setWeekly(on);
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

  const buildBody = (): Record<string, unknown> => {
    let body: Record<string, unknown> = {
      ...payload,
      hora_saida: horaSaida,
      hora_retorno: horaRetorno,
    };
    if (weekly) {
      const filled: WeeklyTimes = {};
      for (const [day, t] of Object.entries(weeklyTimes)) {
        if (t.hora_saida && t.hora_retorno) filled[day] = t;
      }
      body = { ...body, weekly_times: filled };
    }
    return body;
  };

  const save = async () => {
    setError(null);
    if (!name.trim()) {
      setError("Dê um nome ao tipo de saída");
      return;
    }
    setBusy(true);
    try {
      const body = buildBody();
      if (editingId !== null) {
        await updateTemplate(editingId, name, body);
      } else {
        await createTemplate(name, body);
      }
      resetForm();
      load();
    } catch (err: unknown) {
      const detail =
        err && typeof err === "object" && "response" in err
          ? (err as { response?: { data?: { detail?: string } } }).response?.data
              ?.detail
          : undefined;
      setError(detail || "Erro ao salvar");
    } finally {
      setBusy(false);
    }
  };

  const startEdit = (tpl: Template) => {
    const parsed = payloadFromTemplate(tpl);
    setEditingId(tpl.id);
    setName(tpl.name);
    setPayload(parsed.payload);
    setHoraSaida(parsed.horaSaida);
    setHoraRetorno(parsed.horaRetorno);
    setWeekly(parsed.weekly);
    setWeeklyTimes(parsed.weeklyTimes);
    setError(null);
  };

  const remove = async (id: number) => {
    await deleteTemplate(id);
    if (editingId === id) resetForm();
    load();
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-bold">Tipos de Saída</h1>
        <p className="text-sm text-slate-500">
          Salve combinações de saída usadas com frequência para reutilizar.
        </p>
      </div>

      {loadError && <p className="text-sm text-red-600">{loadError}</p>}

      <div className="card space-y-4">
        <h2 className="font-semibold">
          {editingId !== null ? "Editar tipo de saída" : "Novo tipo de saída"}
        </h2>
        <div>
          <label className="label">Nome do tipo de saída</label>
          <input
            className="input"
            placeholder="Ex: Saída de fim de semana"
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
        </div>

        <div>
          <p className="label">Horário padrão</p>
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
        </div>

        <label className="flex items-center gap-2 text-sm text-slate-700">
          <input
            type="checkbox"
            checked={weekly}
            onChange={(e) => handleWeeklyToggle(e.target.checked)}
          />
          Tipo semanal (horários por dia da semana)
        </label>

        <ExitForm
          value={payload}
          onChange={setPayload}
          excludeFields={["hora_saida", "hora_retorno"]}
        />

        {weekly && (
          <div className="space-y-2 rounded-lg border border-slate-200 p-3">
            <p className="label">Horários por dia</p>
            {WEEKDAYS.map((day, idx) => (
              <div
                key={day}
                className="grid grid-cols-[5rem,1fr,1fr] items-center gap-2"
              >
                <span className="text-sm text-slate-600">{day}</span>
                <TimePicker
                  value={weeklyTimes[String(idx)]?.hora_saida ?? ""}
                  onChange={(v) => setDayTime(idx, "hora_saida", v)}
                />
                <TimePicker
                  value={weeklyTimes[String(idx)]?.hora_retorno ?? ""}
                  onChange={(v) => setDayTime(idx, "hora_retorno", v)}
                />
              </div>
            ))}
          </div>
        )}
        {error && <p className="text-sm text-red-600">{error}</p>}
        <div className="flex justify-end gap-2">
          {editingId !== null && (
            <button className="btn-secondary" onClick={resetForm} disabled={busy}>
              Cancelar
            </button>
          )}
          <button className="btn-primary" onClick={save} disabled={busy}>
            {busy ? "Salvando..." : editingId !== null ? "Atualizar" : "Salvar tipo de saída"}
          </button>
        </div>
      </div>

      <div className="space-y-3">
        <h2 className="font-semibold">Seus tipos de saída</h2>
        {templates.length === 0 && (
          <p className="text-sm text-slate-400">
            Nenhum tipo de saída salvo ainda.
          </p>
        )}
        {templates.map((t) => (
          <div key={t.id} className="card flex items-start justify-between gap-4">
            <div>
              <p className="font-medium">{t.name}</p>
              <p className="mt-1 text-xs text-slate-500">
                {formatPayloadSummary(t.payload) || "Sem campos"}
              </p>
            </div>
            <div className="flex shrink-0 gap-2">
              <button
                className="btn-secondary text-xs"
                onClick={() => startEdit(t)}
              >
                Editar
              </button>
              <button className="btn-danger text-xs" onClick={() => remove(t.id)}>
                Excluir
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
