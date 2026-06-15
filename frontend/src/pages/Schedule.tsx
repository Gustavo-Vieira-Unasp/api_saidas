import { useEffect, useState } from "react";
import SchedulePicker, {
  type ScheduleConfig,
} from "../components/SchedulePicker";
import SuccessToast from "../components/SuccessToast";
import {
  createSchedule,
  deleteSchedule,
  listSchedules,
  listTemplates,
  runScheduleNow,
  runSchedulesBulk,
  updateSchedule,
} from "../services/api";
import { MAX_BATCH_ITEMS } from "../constants/limits";
import type { Schedule, Template } from "../types";
import { fmtDateTime } from "../utils/fmt";

type SortKey = "name" | "run_at" | "last_run_at" | "enabled";

function compareSchedules(a: Schedule, b: Schedule, key: SortKey): number {
  switch (key) {
    case "name":
      return a.name.localeCompare(b.name, "pt-BR");
    case "run_at": {
      // Earliest scheduled date first; recurring schedules (no run_at) last.
      const av = a.run_at ? new Date(a.run_at).getTime() : Infinity;
      const bv = b.run_at ? new Date(b.run_at).getTime() : Infinity;
      return av - bv;
    }
    case "last_run_at": {
      const av = a.last_run_at ? new Date(a.last_run_at).getTime() : -Infinity;
      const bv = b.last_run_at ? new Date(b.last_run_at).getTime() : -Infinity;
      return av - bv;
    }
    case "enabled":
      return Number(b.enabled) - Number(a.enabled);
  }
}

function describe(s: Schedule): string {
  const time =
    s.hour != null
      ? `${String(s.hour).padStart(2, "0")}:${String(s.minute ?? 0).padStart(2, "0")}`
      : "";
  switch (s.trigger_type) {
    case "once":
      return `Uma vez em ${s.run_at ? fmtDateTime(s.run_at) : "?"}`;
    case "daily":
      return `Todos os dias às ${time}`;
    case "weekdays":
      return `Seg a sex às ${time}`;
    case "cron":
      return `Cron: ${s.cron}`;
    default:
      return s.trigger_type;
  }
}

export default function SchedulePage() {
  const [schedules, setSchedules] = useState<Schedule[]>([]);
  const [templates, setTemplates] = useState<Template[]>([]);
  const [name, setName] = useState("");
  const [templateId, setTemplateId] = useState<number | "">("");
  const [config, setConfig] = useState<ScheduleConfig>({
    trigger_type: "weekdays",
    hour: 18,
    minute: 0,
    date_strategy: "today",
  });
  const [error, setError] = useState<string | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [bulkBusy, setBulkBusy] = useState(false);
  const [toast, setToast] = useState<string | null>(null);
  // Default ordering: alphabetical by name (which also yields earliest-first
  // for the auto-generated "Planejado AAAA-MM-DD" names).
  const [sortBy, setSortBy] = useState<{ key: SortKey; dir: "asc" | "desc" }>({
    key: "name",
    dir: "asc",
  });

  const load = () => {
    setLoadError(null);
    Promise.all([listSchedules(), listTemplates()])
      .then(([s, t]) => {
        setSchedules(s);
        setTemplates(t);
      })
      .catch(() => setLoadError("Não foi possível carregar agendamentos."));
  };

  useEffect(() => {
    load();
  }, []);

  const create = async () => {
    setError(null);
    if (!name.trim()) return setError("Dê um nome ao agendamento");
    if (templateId === "") return setError("Selecione um tipo de saída");
    setBusy(true);
    try {
      await createSchedule({
        name,
        template_id: templateId,
        trigger_type: config.trigger_type,
        run_at: config.run_at,
        hour: config.hour,
        minute: config.minute,
        cron: config.cron,
        date_strategy: config.date_strategy,
        enabled: true,
      });
      setName("");
      setTemplateId("");
      setToast("Agendamento criado.");
      load();
    } catch (err: any) {
      setError(err.response?.data?.detail || "Erro ao agendar");
    } finally {
      setBusy(false);
    }
  };

  const toggle = async (s: Schedule) => {
    await updateSchedule(s.id, { enabled: !s.enabled });
    load();
  };

  const remove = async (id: number) => {
    await deleteSchedule(id);
    load();
  };

  const runNow = async (id: number) => {
    setError(null);
    try {
      await runScheduleNow(id);
      setToast("Envio iniciado. Acompanhe o resultado em Histórico (1–3 min).");
    } catch (err: unknown) {
      const detail =
        err && typeof err === "object" && "response" in err
          ? (err as { response?: { data?: { detail?: string } } }).response?.data
              ?.detail
          : undefined;
      setError(detail || "Erro ao disparar envio");
    }
  };

  const toggleSelected = (id: number) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const allSelected =
    schedules.length > 0 && selected.size === schedules.length;

  const toggleSelectAll = () => {
    setSelected(allSelected ? new Set() : new Set(schedules.map((s) => s.id)));
  };

  const ids = () => Array.from(selected);

  const toggleSort = (key: SortKey) => {
    setSortBy((prev) =>
      prev.key === key
        ? { key, dir: prev.dir === "asc" ? "desc" : "asc" }
        : { key, dir: "asc" }
    );
  };

  const sorted = [...schedules].sort((a, b) => {
    const cmp = compareSchedules(a, b, sortBy.key);
    return sortBy.dir === "asc" ? cmp : -cmp;
  });

  const sortArrow = (key: SortKey) =>
    sortBy.key === key ? (sortBy.dir === "asc" ? " ▲" : " ▼") : "";

  const bulkSetEnabled = async (enabled: boolean) => {
    setBulkBusy(true);
    try {
      await Promise.all(ids().map((id) => updateSchedule(id, { enabled })));
      setToast(
        `${selected.size} agendamento(s) ${enabled ? "ativado(s)" : "desativado(s)"}.`
      );
      setSelected(new Set());
      load();
    } finally {
      setBulkBusy(false);
    }
  };

  const bulkRun = async () => {
    const count = selected.size;
    if (count > MAX_BATCH_ITEMS) {
      setToast(
        `Máximo de ${MAX_BATCH_ITEMS} envios por vez (selecionados: ${count}).`
      );
      return;
    }
    setBulkBusy(true);
    try {
      await runSchedulesBulk(ids());
      setToast(`${count} envio(s) disparado(s). Veja em Histórico.`);
      setSelected(new Set());
    } catch (err: any) {
      setToast(err.response?.data?.detail || "Erro ao enviar em lote.");
    } finally {
      setBulkBusy(false);
    }
  };

  const bulkDelete = async () => {
    setBulkBusy(true);
    try {
      const count = selected.size;
      await Promise.all(ids().map((id) => deleteSchedule(id)));
      setToast(`${count} agendamento(s) excluído(s).`);
      setSelected(new Set());
      load();
    } finally {
      setBulkBusy(false);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-bold">Agendamentos</h1>
        <p className="text-sm text-slate-500">
          Programe envios automáticos a partir de um modelo salvo.
        </p>
      </div>

      {loadError && <p className="text-sm text-red-600">{loadError}</p>}

      <div className="card space-y-4">
        <h2 className="font-semibold">Novo agendamento</h2>
        {templates.length === 0 ? (
          <p className="text-sm text-amber-700">
            Crie um tipo de saída primeiro na aba Tipos de Saída.
          </p>
        ) : (
          <>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <div>
                <label className="label">Nome</label>
                <input
                  className="input"
                  placeholder="Ex: Saída diária academia"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                />
              </div>
              <div>
                <label className="label">Tipo de saída</label>
                <select
                  className="input"
                  value={templateId}
                  onChange={(e) =>
                    setTemplateId(
                      e.target.value === "" ? "" : Number(e.target.value)
                    )
                  }
                >
                  <option value="">-- Selecione --</option>
                  {templates.map((t) => (
                    <option key={t.id} value={t.id}>
                      {t.name}
                    </option>
                  ))}
                </select>
              </div>
            </div>
            <SchedulePicker value={config} onChange={setConfig} />
            {error && <p className="text-sm text-red-600">{error}</p>}
            <div className="flex justify-end">
              <button className="btn-primary" onClick={create} disabled={busy}>
                {busy ? "Salvando..." : "Criar agendamento"}
              </button>
            </div>
          </>
        )}
      </div>

      <div className="space-y-3">
        <h2 className="font-semibold">Seus agendamentos</h2>
        {schedules.length === 0 ? (
          <p className="text-sm text-slate-400">Nenhum agendamento ainda.</p>
        ) : (
          <div className="card overflow-x-auto p-0">
            <table className="w-full text-left text-sm">
              <thead className="border-b border-slate-200 text-xs uppercase text-slate-400">
                {selected.size > 0 ? (
                  <tr className="bg-slate-50">
                    <th className="px-4 py-2">
                      <input
                        type="checkbox"
                        checked={allSelected}
                        onChange={toggleSelectAll}
                      />
                    </th>
                    <th colSpan={5} className="px-4 py-2 normal-case">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="text-sm font-medium text-slate-600">
                          {selected.size} selecionado(s)
                          {selected.size > MAX_BATCH_ITEMS && (
                            <span className="ml-2 text-red-600">
                              (máx. {MAX_BATCH_ITEMS} para enviar)
                            </span>
                          )}
                        </span>
                        <div className="ml-auto flex gap-2">
                          <button
                            className="btn-secondary text-xs"
                            onClick={() => bulkSetEnabled(true)}
                            disabled={bulkBusy}
                          >
                            Ativar
                          </button>
                          <button
                            className="btn-secondary text-xs"
                            onClick={() => bulkSetEnabled(false)}
                            disabled={bulkBusy}
                          >
                            Desativar
                          </button>
                          <button
                            className="btn-secondary text-xs"
                            onClick={bulkRun}
                            disabled={bulkBusy || selected.size > MAX_BATCH_ITEMS}
                            title={
                              selected.size > MAX_BATCH_ITEMS
                                ? `Máximo de ${MAX_BATCH_ITEMS} envios por vez`
                                : undefined
                            }
                          >
                            Enviar agora
                          </button>
                          <button
                            className="btn-danger text-xs"
                            onClick={bulkDelete}
                            disabled={bulkBusy}
                          >
                            Excluir
                          </button>
                        </div>
                      </div>
                    </th>
                  </tr>
                ) : (
                  <tr>
                    <th className="px-4 py-2">
                      <input
                        type="checkbox"
                        checked={allSelected}
                        onChange={toggleSelectAll}
                      />
                    </th>
                    <th className="px-4 py-2">
                      <button
                        type="button"
                        className="font-medium uppercase hover:text-slate-600"
                        onClick={() => toggleSort("name")}
                      >
                        Nome{sortArrow("name")}
                      </button>
                    </th>
                    <th className="px-4 py-2">
                      <button
                        type="button"
                        className="font-medium uppercase hover:text-slate-600"
                        onClick={() => toggleSort("run_at")}
                      >
                        Descrição{sortArrow("run_at")}
                      </button>
                    </th>
                    <th className="px-4 py-2">
                      <button
                        type="button"
                        className="font-medium uppercase hover:text-slate-600"
                        onClick={() => toggleSort("last_run_at")}
                      >
                        Último envio{sortArrow("last_run_at")}
                      </button>
                    </th>
                    <th className="px-4 py-2">
                      <button
                        type="button"
                        className="font-medium uppercase hover:text-slate-600"
                        onClick={() => toggleSort("enabled")}
                      >
                        Status{sortArrow("enabled")}
                      </button>
                    </th>
                    <th className="px-4 py-2 text-right">Ações</th>
                  </tr>
                )}
              </thead>
              <tbody>
                {sorted.map((s) => (
                  <tr
                    key={s.id}
                    className="border-b border-slate-100 last:border-0"
                  >
                    <td className="px-4 py-2 align-top">
                      <input
                        type="checkbox"
                        checked={selected.has(s.id)}
                        onChange={() => toggleSelected(s.id)}
                      />
                    </td>
                    <td className="px-4 py-2 align-top font-medium">{s.name}</td>
                    <td className="px-4 py-2 align-top text-slate-500">
                      {describe(s)}
                    </td>
                    <td className="px-4 py-2 align-top text-slate-500">
                      {s.last_run_at ? fmtDateTime(s.last_run_at) : "—"}
                    </td>
                    <td className="px-4 py-2 align-top">
                      {s.enabled ? (
                        <span className="rounded bg-green-100 px-2 py-0.5 text-xs text-green-700">
                          Ativo
                        </span>
                      ) : (
                        <span className="rounded bg-slate-100 px-2 py-0.5 text-xs text-slate-500">
                          Desativado
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-2 align-top">
                      <div className="flex justify-end gap-2">
                        <button
                          className="btn-secondary text-xs"
                          onClick={() => runNow(s.id)}
                        >
                          Enviar
                        </button>
                        <button
                          className="btn-secondary text-xs"
                          onClick={() => toggle(s)}
                        >
                          {s.enabled ? "Desativar" : "Ativar"}
                        </button>
                        <button
                          className="btn-danger text-xs"
                          onClick={() => remove(s.id)}
                        >
                          Excluir
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {toast && (
        <SuccessToast message={toast} onClose={() => setToast(null)} />
      )}
    </div>
  );
}
