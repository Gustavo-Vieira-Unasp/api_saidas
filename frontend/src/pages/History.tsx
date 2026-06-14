import { useCallback, useEffect, useState } from "react";
import { formatPayloadSummary } from "../components/ExitForm";
import Screenshot from "../components/Screenshot";
import StatusBadge from "../components/StatusBadge";
import { listExits } from "../services/api";
import type { ExitRequest, SubmissionStatus } from "../types";
import { fmtDateTime } from "../utils/fmt";

const SOURCE_LABELS: Record<string, string> = {
  manual: "Manual",
  batch: "Lote",
  schedule: "Agendado",
};

const STATUS_OPTIONS: { value: string; label: string }[] = [
  { value: "", label: "Todos" },
  { value: "sent", label: "Enviados" },
  { value: "failed", label: "Falhas" },
  { value: "pending", label: "Pendentes" },
];

export default function History() {
  const [exits, setExits] = useState<ExitRequest[]>([]);
  const [openShot, setOpenShot] = useState<number | null>(null);
  const [statusFilter, setStatusFilter] = useState("");
  const [loadError, setLoadError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoadError(null);
    try {
      const data = await listExits(
        100,
        statusFilter || undefined
      );
      setExits(data);
    } catch {
      setLoadError("Não foi possível carregar o histórico.");
    }
  }, [statusFilter]);

  useEffect(() => {
    load();
    const interval = setInterval(load, 30_000);
    return () => clearInterval(interval);
  }, [load]);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold">Histórico</h1>
          <p className="text-sm text-slate-500">Todas as tentativas de envio.</p>
        </div>
        <div className="flex items-center gap-2">
          <label className="text-sm text-slate-600" htmlFor="status-filter">
            Status
          </label>
          <select
            id="status-filter"
            className="input w-auto"
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
          >
            {STATUS_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>
                {o.label}
              </option>
            ))}
          </select>
          <button className="btn-secondary text-sm" onClick={load} type="button">
            Atualizar
          </button>
        </div>
      </div>

      {loadError && <p className="text-sm text-red-600">{loadError}</p>}

      {exits.length === 0 && !loadError && (
        <p className="text-sm text-slate-400">Nenhum envio registrado ainda.</p>
      )}

      <div className="space-y-3">
        {exits.map((e) => (
          <div key={e.id} className="card space-y-2">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div className="flex items-center gap-3">
                <StatusBadge status={e.status as SubmissionStatus} />
                <span className="text-xs text-slate-400">
                  {fmtDateTime(e.created_at)}
                </span>
                <span className="rounded bg-slate-100 px-2 py-0.5 text-xs text-slate-500">
                  {SOURCE_LABELS[e.source] ?? e.source}
                </span>
              </div>
              {e.screenshot_path && (
                <button
                  className="text-xs font-medium text-brand"
                  onClick={() => setOpenShot(openShot === e.id ? null : e.id)}
                >
                  {openShot === e.id ? "Ocultar comprovante" : "Ver comprovante"}
                </button>
              )}
            </div>
            {e.message && <p className="text-sm text-slate-600">{e.message}</p>}
            <p className="text-xs text-slate-500">
              {formatPayloadSummary(e.payload) || "Sem campos"}
            </p>
            {openShot === e.id && e.screenshot_path && (
              <Screenshot
                exitId={e.id}
                className="max-w-full rounded-lg border border-slate-200"
              />
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
