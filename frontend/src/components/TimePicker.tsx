import { useEffect, useRef, useState } from "react";

interface Props {
  value: string; // HH:MM
  onChange: (value: string) => void;
  className?: string;
  clearable?: boolean;
}

// Allowed window matching the UNASP picker: hours 05–23 are selectable; 00–04
// are shown greyed/blocked. Minutes accept any value from 00 to 59.
const MIN_HOUR = 5;
const MAX_HOUR = 23;

const CLOCK_SIZE = 224;
const CENTER = CLOCK_SIZE / 2;
const R_OUTER = 92;
const R_INNER = 58;
const R_MINUTE = 92;

function splitValue(value: string): { hour: string; minute: string } {
  const m = /^(\d{2}):(\d{2})$/.exec(value);
  if (!m) return { hour: "", minute: "" };
  return { hour: m[1], minute: m[2] };
}

function pad(n: number): string {
  return String(n).padStart(2, "0");
}

// Position on the clock face for an angle measured in degrees clockwise from
// the top (12 o'clock).
function posFromAngle(
  angleDeg: number,
  radius: number
): { x: number; y: number } {
  const rad = (angleDeg - 90) * (Math.PI / 180);
  return {
    x: CENTER + radius * Math.cos(rad),
    y: CENTER + radius * Math.sin(rad),
  };
}

// Position on the clock face for a 1..12 dial slot.
function dialPos(slot: number, radius: number): { x: number; y: number } {
  return posFromAngle(slot * 30, radius);
}

function hourEnabled(num: number): boolean {
  return num >= MIN_HOUR && num <= MAX_HOUR;
}

interface ClockItem {
  label: string;
  num: number;
  x: number;
  y: number;
  enabled: boolean;
}

function hourItems(): ClockItem[] {
  const items: ClockItem[] = [];
  // Outer ring: 1..12.
  for (let slot = 1; slot <= 12; slot++) {
    const num = slot;
    const { x, y } = dialPos(slot, R_OUTER);
    items.push({ label: pad(num), num, x, y, enabled: hourEnabled(num) });
  }
  // Inner ring: 13..23 and 00 (at the top slot).
  for (let slot = 1; slot <= 12; slot++) {
    const num = slot === 12 ? 0 : slot + 12;
    const { x, y } = dialPos(slot, R_INNER);
    items.push({ label: pad(num), num, x, y, enabled: hourEnabled(num) });
  }
  return items;
}

function minuteItems(): ClockItem[] {
  const items: ClockItem[] = [];
  for (let slot = 1; slot <= 12; slot++) {
    const num = (slot % 12) * 5; // slot 12 -> 0, slot 6 -> 30
    const { x, y } = dialPos(slot, R_MINUTE);
    items.push({ label: pad(num), num, x, y, enabled: true });
  }
  return items;
}

const HOUR_ITEMS = hourItems();
const MINUTE_ITEMS = minuteItems();

// Clock geometry for a selected hour: which ring and slot it sits on.
function hourGeometry(h: number): { angle: number; radius: number } {
  const isOuter = h >= 1 && h <= 12;
  const slot = isOuter ? (h === 12 ? 12 : h) : h === 0 ? 12 : h - 12;
  return { angle: slot * 30, radius: isOuter ? R_OUTER : R_INNER };
}

export default function TimePicker({
  value,
  onChange,
  className,
  clearable = true,
}: Props) {
  const [open, setOpen] = useState(false);
  const [tab, setTab] = useState<"hour" | "minute">("hour");
  const { hour: initialHour, minute: initialMinute } = splitValue(value);
  const [hour, setHour] = useState(initialHour);
  const [minute, setMinute] = useState(initialMinute);
  const [dragging, setDragging] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const clockRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const { hour: h, minute: m } = splitValue(value);
    setHour(h);
    setMinute(m);
  }, [value]);

  useEffect(() => {
    if (!open) return;
    const onClick = (e: MouseEvent) => {
      if (
        containerRef.current &&
        !containerRef.current.contains(e.target as Node)
      ) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, [open]);

  const openPicker = () => {
    setTab("hour");
    setOpen(true);
  };

  const confirm = () => {
    if (hour && minute) {
      onChange(`${hour}:${minute}`);
    }
    setOpen(false);
  };

  const clear = (e: React.MouseEvent) => {
    e.stopPropagation();
    onChange("");
  };

  // Translate a pointer position over the clock face into a value, updating the
  // relevant state. Returns the chosen value, or null if it landed on a
  // disabled slot (so callers can avoid advancing the phase).
  const updateFromPoint = (clientX: number, clientY: number): string | null => {
    const rect = clockRef.current?.getBoundingClientRect();
    if (!rect) return null;
    const dx = clientX - rect.left - CENTER;
    const dy = clientY - rect.top - CENTER;
    const angle = (Math.atan2(dy, dx) * 180) / Math.PI + 90;
    const norm = ((angle % 360) + 360) % 360;

    if (tab === "hour") {
      const slot = Math.round(norm / 30) % 12; // 0 represents the top slot
      const dist = Math.hypot(dx, dy);
      const isOuter = dist >= (R_INNER + R_OUTER) / 2;
      let num: number;
      if (isOuter) {
        num = slot === 0 ? 12 : slot;
      } else {
        num = slot === 0 ? 0 : slot + 12;
      }
      if (!hourEnabled(num)) return null;
      const label = pad(num);
      setHour(label);
      return label;
    }

    const m = Math.round(norm / 6) % 60;
    const label = pad(m);
    setMinute(label);
    return label;
  };

  const onPointerDown = (e: React.PointerEvent) => {
    e.preventDefault();
    setDragging(true);
    clockRef.current?.setPointerCapture(e.pointerId);
    updateFromPoint(e.clientX, e.clientY);
  };

  const onPointerMove = (e: React.PointerEvent) => {
    if (!dragging) return;
    updateFromPoint(e.clientX, e.clientY);
  };

  const endDrag = (e: React.PointerEvent) => {
    if (!dragging) return;
    setDragging(false);
    if (clockRef.current?.hasPointerCapture(e.pointerId)) {
      clockRef.current.releasePointerCapture(e.pointerId);
    }
    if (tab === "hour") {
      const v = updateFromPoint(e.clientX, e.clientY);
      if (v !== null) setTab("minute");
    }
  };

  const items = tab === "hour" ? HOUR_ITEMS : MINUTE_ITEMS;
  const selectedNum =
    tab === "hour"
      ? hour === ""
        ? null
        : Number(hour)
      : minute === ""
        ? null
        : Number(minute);

  // Hand endpoint: for hours it snaps to the slot/ring; for minutes it can
  // point anywhere on the circle (any 0–59 value).
  let hand: { x: number; y: number } | null = null;
  if (selectedNum !== null) {
    if (tab === "hour") {
      const g = hourGeometry(selectedNum);
      hand = posFromAngle(g.angle, g.radius);
    } else {
      hand = posFromAngle(selectedNum * 6, R_MINUTE);
    }
  }

  return (
    <div className="relative" ref={containerRef}>
      <div className="relative">
        <input
          className={`input cursor-pointer ${clearable && value ? "pr-9" : ""} ${className ?? ""}`}
          type="text"
          readOnly
          placeholder="--:--"
          value={value}
          onClick={openPicker}
        />
        {clearable && value && (
          <button
            type="button"
            aria-label="Limpar horário"
            className="absolute right-2 top-1/2 -translate-y-1/2 rounded-full px-1 text-slate-400 hover:bg-slate-100 hover:text-slate-600"
            onClick={clear}
          >
            ×
          </button>
        )}
      </div>

      {open && (
        <div className="absolute z-50 mt-1 w-64 rounded-xl border border-slate-200 bg-white p-3 shadow-lg">
          <div className="mb-2 flex rounded-lg bg-slate-100 p-1 text-sm">
            <button
              type="button"
              className={`flex-1 rounded-md py-1 font-medium transition ${
                tab === "hour" ? "bg-white text-brand shadow-sm" : "text-slate-500"
              }`}
              onClick={() => setTab("hour")}
            >
              Hora {hour && `· ${hour}`}
            </button>
            <button
              type="button"
              className={`flex-1 rounded-md py-1 font-medium transition ${
                tab === "minute" ? "bg-white text-brand shadow-sm" : "text-slate-500"
              }`}
              onClick={() => setTab("minute")}
            >
              Minuto {minute && `· ${minute}`}
            </button>
          </div>

          <div
            ref={clockRef}
            className="relative mx-auto touch-none select-none rounded-full bg-slate-50"
            style={{ width: CLOCK_SIZE, height: CLOCK_SIZE }}
            onPointerDown={onPointerDown}
            onPointerMove={onPointerMove}
            onPointerUp={endDrag}
            onPointerLeave={endDrag}
          >
            <svg
              className="pointer-events-none absolute inset-0"
              width={CLOCK_SIZE}
              height={CLOCK_SIZE}
            >
              {hand && (
                <>
                  <line
                    x1={CENTER}
                    y1={CENTER}
                    x2={hand.x}
                    y2={hand.y}
                    stroke="#1d4ed8"
                    strokeWidth={2}
                  />
                  <circle cx={hand.x} cy={hand.y} r={14} fill="#1d4ed8" opacity={0.18} />
                  <circle cx={CENTER} cy={CENTER} r={3} fill="#1d4ed8" />
                </>
              )}
            </svg>

            {items.map((it) => {
              const isSelected = it.num === selectedNum;
              return (
                <span
                  key={`${tab}-${it.num}`}
                  className={`pointer-events-none absolute flex h-8 w-8 -translate-x-1/2 -translate-y-1/2 items-center justify-center rounded-full text-xs ${
                    isSelected
                      ? "font-semibold text-brand"
                      : it.enabled
                        ? "text-slate-700"
                        : "text-slate-300"
                  }`}
                  style={{ left: it.x, top: it.y }}
                >
                  {it.label}
                </span>
              );
            })}
          </div>

          <div className="mt-3 flex justify-end gap-2">
            <button
              type="button"
              className="btn-secondary px-3 py-1 text-sm"
              onClick={() => setOpen(false)}
            >
              Cancelar
            </button>
            <button
              type="button"
              className="btn-primary px-3 py-1 text-sm"
              onClick={confirm}
              disabled={!hour || !minute}
            >
              Definir
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
