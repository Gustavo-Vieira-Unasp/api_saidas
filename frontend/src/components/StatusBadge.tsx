import type { SubmissionStatus } from "../types";

const styles: Record<SubmissionStatus, string> = {
  pending: "bg-amber-100 text-amber-700",
  sent: "bg-green-100 text-green-700",
  failed: "bg-red-100 text-red-700",
};

const labels: Record<SubmissionStatus, string> = {
  pending: "Pendente",
  sent: "Enviado",
  failed: "Falhou",
};

export default function StatusBadge({ status }: { status: SubmissionStatus }) {
  return (
    <span
      className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-medium ${styles[status]}`}
    >
      {labels[status]}
    </span>
  );
}
