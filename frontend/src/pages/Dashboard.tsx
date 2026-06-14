import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import ExitForm, { validatePayload } from "../components/ExitForm";
import Screenshot from "../components/Screenshot";
import StatusBadge from "../components/StatusBadge";
import SuccessToast from "../components/SuccessToast";
import { useAuth } from "../context/AuthContext";
import { listTemplates, sendExit } from "../services/api";
import type { ExitPayload, ExitRequest, Template } from "../types";

export default function Dashboard() {
  const { user } = useAuth();
  const [templates, setTemplates] = useState<Template[]>([]);
  const [selectedTemplate, setSelectedTemplate] = useState<number | "">("");
  const [payload, setPayload] = useState<ExitPayload>({});
  const [result, setResult] = useState<ExitRequest | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [dryRun, setDryRun] = useState(true);
  const [confirmReal, setConfirmReal] = useState(false);
  const [toast, setToast] = useState<string | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);

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

  const send = async (confirmed = false) => {
    const missing = validatePayload(payload);
    if (missing.length > 0) {
      setConfirmReal(false);
      setError(`Preencha os campos obrigatórios: ${missing.join(", ")}`);
      return;
    }
    if (!dryRun && !confirmed) {
      setConfirmReal(true);
      return;
    }
    setConfirmReal(false);
    setError(null);
    setResult(null);
    setBusy(true);
    try {
      const body =
        selectedTemplate !== "" && Object.keys(payload).length === 0
          ? { template_id: selectedTemplate, dry_run: dryRun }
          : { payload, dry_run: dryRun };
      const res = await sendExit(body);
      setResult(res);
      setToast(
        dryRun
          ? "Teste concluído (nenhum envio real)."
          : `Solicitação enviada${res.message ? ` — ${res.message}` : "."}`
      );
    } catch (err: any) {
      setError(err.response?.data?.detail || "Erro ao enviar");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-bold">Enviar saída</h1>
        <p className="text-sm text-slate-500">
          Preencha o formulário e envie agora, ou{" "}
          <Link to="/schedules" className="text-brand">
            agende
          </Link>{" "}
          para depois.
        </p>
      </div>

      {loadError && <p className="text-sm text-red-600">{loadError}</p>}

      {!user?.has_unasp_credentials && (
        <div className="rounded-lg border border-amber-300 bg-amber-50 p-4 text-sm text-amber-800">
          Você ainda não cadastrou suas credenciais do UNASP.{" "}
          <Link to="/settings" className="font-medium underline">
            Cadastre em Configurações
          </Link>{" "}
          para poder enviar.
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

        <ExitForm value={payload} onChange={setPayload} />

        <label className="flex items-center gap-2 text-sm text-slate-700">
          <input
            type="checkbox"
            checked={dryRun}
            onChange={(e) => setDryRun(e.target.checked)}
          />
          Modo teste (preenche, não envia)
        </label>

        {error && <p className="text-sm text-red-600">{error}</p>}

        <div className="flex justify-end">
          <button
            className="btn-primary"
            onClick={() => send()}
            disabled={busy || !user?.has_unasp_credentials}
          >
            {busy ? "Enviando..." : dryRun ? "Testar envio" : "Enviar agora"}
          </button>
        </div>
      </div>

      {confirmReal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <div className="card max-w-md space-y-4">
            <h2 className="font-semibold">Envio real</h2>
            <p className="text-sm text-slate-600">
              Isto fará um envio REAL no site do UNASP. Continuar?
            </p>
            <div className="flex justify-end gap-2">
              <button className="btn-secondary" onClick={() => setConfirmReal(false)}>
                Cancelar
              </button>
              <button className="btn-primary" onClick={() => send(true)}>
                Continuar
              </button>
            </div>
          </div>
        </div>
      )}

      {result && (
        <div className="card space-y-3">
          <div className="flex items-center gap-3">
            <StatusBadge status={result.status} />
            <span className="text-sm text-slate-600">{result.message}</span>
          </div>
          {result.screenshot_path && (
            <div>
              <p className="label">Comprovante</p>
              <Screenshot
                exitId={result.id}
                className="max-w-full rounded-lg border border-slate-200"
              />
            </div>
          )}
        </div>
      )}

      {toast && (
        <SuccessToast message={toast} onClose={() => setToast(null)} />
      )}
    </div>
  );
}
