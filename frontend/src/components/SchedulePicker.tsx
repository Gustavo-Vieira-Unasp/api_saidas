import type { DateStrategy, TriggerType } from "../types";

export interface ScheduleConfig {
  trigger_type: TriggerType;
  run_at?: string;
  hour?: number;
  minute?: number;
  cron?: string;
  date_strategy?: DateStrategy;
}

const dateStrategyOptions: { value: DateStrategy; label: string }[] = [
  { value: "today", label: "Dia da execução (hoje)" },
  { value: "tomorrow", label: "Dia seguinte (amanhã)" },
  { value: "fixed", label: "Usar a data do tipo de saída" },
];

interface Props {
  value: ScheduleConfig;
  onChange: (cfg: ScheduleConfig) => void;
}

const triggerOptions: { value: TriggerType; label: string }[] = [
  { value: "once", label: "Uma vez (data específica)" },
  { value: "daily", label: "Todos os dias" },
  { value: "weekdays", label: "Dias de semana (seg-sex)" },
  { value: "cron", label: "Avançado (cron)" },
];

export default function SchedulePicker({ value, onChange }: Props) {
  const set = (patch: Partial<ScheduleConfig>) => onChange({ ...value, ...patch });

  return (
    <div className="space-y-4">
      <div>
        <label className="label">Frequência</label>
        <select
          className="input"
          value={value.trigger_type}
          onChange={(e) => set({ trigger_type: e.target.value as TriggerType })}
        >
          {triggerOptions.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>
      </div>

      {value.trigger_type === "once" && (
        <div>
          <label className="label">Data e hora</label>
          <input
            className="input"
            type="datetime-local"
            value={value.run_at || ""}
            onChange={(e) => set({ run_at: e.target.value })}
          />
        </div>
      )}

      {(value.trigger_type === "daily" || value.trigger_type === "weekdays") && (
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="label">Hora</label>
            <input
              className="input"
              type="number"
              min={0}
              max={23}
              value={value.hour ?? ""}
              onChange={(e) => set({ hour: Number(e.target.value) })}
            />
          </div>
          <div>
            <label className="label">Minuto</label>
            <input
              className="input"
              type="number"
              min={0}
              max={59}
              value={value.minute ?? 0}
              onChange={(e) => set({ minute: Number(e.target.value) })}
            />
          </div>
        </div>
      )}

      {value.trigger_type === "cron" && (
        <div>
          <label className="label">Expressão cron</label>
          <input
            className="input font-mono"
            placeholder="0 18 * * 1-5"
            value={value.cron || ""}
            onChange={(e) => set({ cron: e.target.value })}
          />
          <p className="mt-1 text-xs text-slate-400">
            minuto hora dia mês dia-da-semana. Ex: "0 18 * * 1-5" = 18:00 de seg a sex.
          </p>
        </div>
      )}

      {value.trigger_type !== "once" && (
        <div>
          <label className="label">Data da saída</label>
          <select
            className="input"
            value={value.date_strategy || "today"}
            onChange={(e) =>
              set({ date_strategy: e.target.value as DateStrategy })
            }
          >
            {dateStrategyOptions.map((o) => (
              <option key={o.value} value={o.value}>
                {o.label}
              </option>
            ))}
          </select>
          <p className="mt-1 text-xs text-slate-400">
            Define qual data é preenchida quando o agendamento roda.
          </p>
        </div>
      )}
    </div>
  );
}
