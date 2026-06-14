import { useEffect, useState } from "react";
import { fetchScreenshotBlob } from "../services/api";

interface Props {
  exitId: number;
  alt?: string;
  className?: string;
}

// Loads the comprovante image through axios so the JWT is sent, then renders the
// resulting object URL and revokes it on cleanup.
export default function Screenshot({ exitId, alt = "Comprovante", className }: Props) {
  const [url, setUrl] = useState<string | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    let objectUrl: string | null = null;
    let active = true;
    setError(false);
    setUrl(null);
    fetchScreenshotBlob(exitId)
      .then((u) => {
        objectUrl = u;
        if (active) setUrl(u);
        else URL.revokeObjectURL(u);
      })
      .catch(() => {
        if (active) setError(true);
      });
    return () => {
      active = false;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [exitId]);

  if (error) {
    return (
      <p className="text-xs text-slate-400">
        Não foi possível carregar o comprovante.
      </p>
    );
  }
  if (!url) {
    return <p className="text-xs text-slate-400">Carregando comprovante...</p>;
  }
  return <img src={url} alt={alt} className={className} />;
}
