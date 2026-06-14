import { useEffect } from "react";

interface Props {
  message: string;
  onClose: () => void;
}

export default function SuccessToast({ message, onClose }: Props) {
  useEffect(() => {
    const t = setTimeout(onClose, 4000);
    return () => clearTimeout(t);
  }, [onClose]);

  return (
    <div className="fixed bottom-4 right-4 z-50 flex max-w-sm items-start gap-3 rounded-lg border border-green-300 bg-green-50 px-4 py-3 text-sm text-green-800 shadow-lg">
      <span className="mt-0.5 font-bold text-green-600">✓</span>
      <span className="flex-1">{message}</span>
      <button
        type="button"
        aria-label="Fechar"
        className="text-green-600 hover:text-green-800"
        onClick={onClose}
      >
        ×
      </button>
    </div>
  );
}
