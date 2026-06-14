import { useEffect } from "react";
import DateInput from "./DateInput";
import TimePicker from "./TimePicker";
import type { ExitPayload } from "../types";

type FieldType = "text" | "time" | "date" | "select" | "radio" | "textarea";

export interface ExitField {
  key: string;
  label: string;
  type?: FieldType;
  placeholder?: string;
  options?: string[];
  fullWidth?: boolean;
}

// Exact dropdown options confirmed against the real UNASP form (field_map.py).
export const MOTIVO_OPTIONS = [
  "Passeio",
  "Trabalho",
  "Médico",
  "Visitar amigos",
  "Autoescola",
  "Pastel",
  "Estágio",
  "Compras",
  "Visitar família",
  "Pastoral",
  "Universitário",
  "Mercearia",
];

export const COM_QUEM_OPTIONS = ["Sozinho", "Amigo", "Familiar", "UNASP"];

// Logical fields - these keys must match field_map.py (FORM) on the backend.
export const EXIT_FIELDS: ExitField[] = [
  {
    key: "dormir_fora",
    label: "Vai dormir fora?",
    type: "radio",
    options: ["Sim", "Não"],
  },
  { key: "destino", label: "Destino", placeholder: "Ex: Casa, Shopping..." },
  { key: "motivo", label: "Motivo", type: "select", options: MOTIVO_OPTIONS },
  {
    key: "com_quem",
    label: "Com quem",
    type: "select",
    options: COM_QUEM_OPTIONS,
  },
  {
    key: "nome_pessoa",
    label: "Nome da pessoa",
    placeholder: "Quando aplicável (amigo/familiar)",
  },
  { key: "data_saida", label: "Data da saída", type: "date" },
  { key: "hora_saida", label: "Hora de saída", type: "time" },
  { key: "hora_retorno", label: "Hora de retorno", type: "time" },
  {
    key: "descricao",
    label: "Descrição",
    type: "textarea",
    placeholder: "Detalhes adicionais",
    fullWidth: true,
  },
];

export const FIELD_LABELS: Record<string, string> = Object.fromEntries(
  EXIT_FIELDS.map((f) => [f.key, f.label])
);

export function formatPayloadSummary(payload: Record<string, string>) {
  return Object.entries(payload)
    .filter(([k, v]) => v && k !== "weekly_times")
    .map(([k, v]) => `${FIELD_LABELS[k] ?? k}: ${v}`)
    .join("  •  ");
}

// Fields the user must fill in before a submission is allowed. `nome_pessoa`
// and `descricao` are intentionally optional.
export const REQUIRED_FIELDS = [
  "dormir_fora",
  "destino",
  "motivo",
  "com_quem",
  "data_saida",
  "hora_saida",
  "hora_retorno",
];

/** Returns the labels of any required fields still missing from the payload. */
export function validatePayload(
  payload: ExitPayload,
  exclude: string[] = []
): string[] {
  return REQUIRED_FIELDS.filter((key) => !exclude.includes(key))
    .filter((key) => !String(payload[key] ?? "").trim())
    .map((key) => FIELD_LABELS[key] ?? key);
}

interface Props {
  value: ExitPayload;
  onChange: (payload: ExitPayload) => void;
  excludeFields?: string[];
}

export default function ExitForm({ value, onChange, excludeFields }: Props) {
  const update = (key: string, v: string) => {
    const next = { ...value, [key]: v };
    // "Nome da pessoa" makes no sense for a solo exit; clear it.
    if (key === "com_quem" && v === "Sozinho") {
      next.nome_pessoa = "";
    }
    onChange(next);
  };

  const hidden = (key: string) => excludeFields?.includes(key) ?? false;

  // Selects no longer offer a blank option, so seed them with their first
  // value whenever they are empty (e.g. a fresh, manually-filled form).
  useEffect(() => {
    const defaults: Record<string, string> = {};
    for (const field of EXIT_FIELDS) {
      if (hidden(field.key)) continue;
      if (field.type === "select" && !value[field.key] && field.options?.length) {
        defaults[field.key] = field.options[0];
      }
    }
    if (Object.keys(defaults).length > 0) {
      onChange({ ...value, ...defaults });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [value, excludeFields]);

  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
      {EXIT_FIELDS.map((field) => {
        if (hidden(field.key)) return null;
        if (field.key === "nome_pessoa" && value["com_quem"] === "Sozinho") {
          return null;
        }
        return (
          <div key={field.key} className={field.fullWidth ? "sm:col-span-2" : ""}>
            <label className="label">{field.label}</label>
            {field.type === "radio" ? (
              <div className="flex gap-4 pt-1">
                {field.options?.map((opt) => (
                  <label
                    key={opt}
                    className="flex items-center gap-2 text-sm text-slate-700"
                  >
                    <input
                      type="radio"
                      name={field.key}
                      checked={value[field.key] === opt}
                      onChange={() => update(field.key, opt)}
                    />
                    {opt}
                  </label>
                ))}
              </div>
            ) : field.type === "select" ? (
              <select
                className="input"
                value={value[field.key] || field.options?.[0] || ""}
                onChange={(e) => update(field.key, e.target.value)}
              >
                {field.options?.map((opt) => (
                  <option key={opt} value={opt}>
                    {opt}
                  </option>
                ))}
              </select>
            ) : field.type === "date" ? (
              <DateInput
                value={value[field.key] || ""}
                onChange={(v) => update(field.key, v)}
              />
            ) : field.type === "time" ? (
              <TimePicker
                value={value[field.key] || ""}
                onChange={(v) => update(field.key, v)}
              />
            ) : field.type === "textarea" ? (
              <textarea
                className="input"
                rows={3}
                placeholder={field.placeholder}
                value={value[field.key] || ""}
                onChange={(e) => update(field.key, e.target.value)}
              />
            ) : (
              <input
                className="input"
                type={field.type || "text"}
                placeholder={field.placeholder}
                value={value[field.key] || ""}
                onChange={(e) => update(field.key, e.target.value)}
              />
            )}
          </div>
        );
      })}
    </div>
  );
}
