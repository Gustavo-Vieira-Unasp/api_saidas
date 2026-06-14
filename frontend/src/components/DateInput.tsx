import { useEffect, useRef, useState } from "react";

interface Props {
  value: string; // stored as YYYY-MM-DD
  onChange: (isoDate: string) => void;
  className?: string;
}

const MONTHS = [
  "Janeiro",
  "Fevereiro",
  "Março",
  "Abril",
  "Maio",
  "Junho",
  "Julho",
  "Agosto",
  "Setembro",
  "Outubro",
  "Novembro",
  "Dezembro",
];
const WEEKDAY_LABELS = ["Dom", "Seg", "Ter", "Qua", "Qui", "Sex", "Sáb"];

function isoToBr(iso: string): string {
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(iso);
  if (!m) return "";
  return `${m[3]}/${m[2]}/${m[1]}`;
}

function parseIso(iso: string): Date | null {
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(iso);
  if (!m) return null;
  const d = new Date(Number(m[1]), Number(m[2]) - 1, Number(m[3]));
  if (
    d.getFullYear() !== Number(m[1]) ||
    d.getMonth() !== Number(m[2]) - 1 ||
    d.getDate() !== Number(m[3])
  ) {
    return null;
  }
  return d;
}

function toIso(year: number, month: number, day: number): string {
  const mm = String(month + 1).padStart(2, "0");
  const dd = String(day).padStart(2, "0");
  return `${year}-${mm}-${dd}`;
}

function sameDay(a: Date, b: Date): boolean {
  return (
    a.getFullYear() === b.getFullYear() &&
    a.getMonth() === b.getMonth() &&
    a.getDate() === b.getDate()
  );
}

export default function DateInput({ value, onChange, className }: Props) {
  const [open, setOpen] = useState(false);
  const [showYearGrid, setShowYearGrid] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  const today = new Date();
  const selected = parseIso(value);
  // The month currently displayed in the calendar header.
  const [viewYear, setViewYear] = useState(
    (selected ?? today).getFullYear()
  );
  const [viewMonth, setViewMonth] = useState((selected ?? today).getMonth());

  useEffect(() => {
    const d = parseIso(value);
    if (d) {
      setViewYear(d.getFullYear());
      setViewMonth(d.getMonth());
    }
  }, [value]);

  useEffect(() => {
    if (!open) return;
    const onClick = (e: MouseEvent) => {
      if (
        containerRef.current &&
        !containerRef.current.contains(e.target as Node)
      ) {
        setOpen(false);
        setShowYearGrid(false);
      }
    };
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, [open]);

  const openPicker = () => {
    const d = parseIso(value) ?? today;
    setViewYear(d.getFullYear());
    setViewMonth(d.getMonth());
    setShowYearGrid(false);
    setOpen(true);
  };

  const prevMonth = () => {
    setViewMonth((m) => {
      if (m === 0) {
        setViewYear((y) => y - 1);
        return 11;
      }
      return m - 1;
    });
  };

  const nextMonth = () => {
    setViewMonth((m) => {
      if (m === 11) {
        setViewYear((y) => y + 1);
        return 0;
      }
      return m + 1;
    });
  };

  const pickDate = (d: Date) => {
    onChange(toIso(d.getFullYear(), d.getMonth(), d.getDate()));
    setOpen(false);
    setShowYearGrid(false);
  };

  // Build a 6x7 grid of dates for the current month view.
  const firstOfMonth = new Date(viewYear, viewMonth, 1);
  const startOffset = firstOfMonth.getDay(); // 0 = Sunday
  const gridStart = new Date(viewYear, viewMonth, 1 - startOffset);
  const cells: Date[] = [];
  for (let i = 0; i < 42; i++) {
    cells.push(
      new Date(gridStart.getFullYear(), gridStart.getMonth(), gridStart.getDate() + i)
    );
  }

  const yearRange = Array.from({ length: 12 }, (_, i) => viewYear - 6 + i);

  return (
    <div className="relative" ref={containerRef}>
      <input
        className={`input cursor-pointer ${className ?? ""}`}
        type="text"
        readOnly
        placeholder="DD/MM/AAAA"
        value={isoToBr(value)}
        onClick={openPicker}
      />

      {open && (
        <div className="absolute z-50 mt-1 w-72 rounded-xl border border-slate-200 bg-white p-3 shadow-lg">
          <div className="mb-2 flex items-center justify-between">
            <button
              type="button"
              className="rounded-md px-2 py-1 text-slate-500 hover:bg-slate-100"
              onClick={prevMonth}
            >
              ‹
            </button>
            <button
              type="button"
              className="rounded-md px-2 py-1 text-sm font-medium text-slate-700 hover:bg-slate-100"
              onClick={() => setShowYearGrid((s) => !s)}
            >
              {MONTHS[viewMonth]} {viewYear}
            </button>
            <button
              type="button"
              className="rounded-md px-2 py-1 text-slate-500 hover:bg-slate-100"
              onClick={nextMonth}
            >
              ›
            </button>
          </div>

          {showYearGrid ? (
            <div className="space-y-3">
              <div className="grid grid-cols-4 gap-1">
                {yearRange.map((y) => (
                  <button
                    key={y}
                    type="button"
                    className={`rounded-md py-1.5 text-sm transition ${
                      y === viewYear
                        ? "bg-brand text-white"
                        : "text-slate-700 hover:bg-slate-100"
                    }`}
                    onClick={() => setViewYear(y)}
                  >
                    {y}
                  </button>
                ))}
              </div>
              <div className="grid grid-cols-3 gap-1">
                {MONTHS.map((mName, idx) => (
                  <button
                    key={mName}
                    type="button"
                    className={`rounded-md py-1.5 text-xs transition ${
                      idx === viewMonth
                        ? "bg-brand text-white"
                        : "text-slate-700 hover:bg-slate-100"
                    }`}
                    onClick={() => {
                      setViewMonth(idx);
                      setShowYearGrid(false);
                    }}
                  >
                    {mName.slice(0, 3)}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <>
              <div className="mb-1 grid grid-cols-7 text-center text-xs font-medium text-slate-400">
                {WEEKDAY_LABELS.map((w) => (
                  <span key={w}>{w}</span>
                ))}
              </div>
              <div className="grid grid-cols-7 gap-0.5">
                {cells.map((d) => {
                  const inMonth = d.getMonth() === viewMonth;
                  const isToday = sameDay(d, today);
                  const isSelected = selected ? sameDay(d, selected) : false;
                  return (
                    <button
                      key={d.toISOString()}
                      type="button"
                      className={`h-9 rounded-md text-sm transition ${
                        isSelected
                          ? "bg-brand text-white"
                          : inMonth
                            ? "text-slate-700 hover:bg-slate-100"
                            : "text-slate-300 hover:bg-slate-50"
                      } ${
                        isToday && !isSelected
                          ? "ring-1 ring-inset ring-brand"
                          : ""
                      }`}
                      onClick={() => pickDate(d)}
                    >
                      {d.getDate()}
                    </button>
                  );
                })}
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}
