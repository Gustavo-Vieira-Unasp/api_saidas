import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { register } from "../services/api";

const PROFILES = ["Funcionário", "Aluno Graduação", "Aluno Educação Básica"];

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [ra, setRa] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [profile, setProfile] = useState(PROFILES[1]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      if (mode === "register") {
        await register(ra, password, profile, fullName);
      }
      await login(ra, password);
      navigate("/");
    } catch (err: any) {
      setError(err.response?.data?.detail || "Erro ao autenticar");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center px-4">
      <div className="w-full max-w-sm">
        <div className="mb-6 text-center">
          <h1 className="text-2xl font-bold text-brand">UNASP Saídas</h1>
          <p className="text-sm text-slate-500">Automação de autorizações de saída</p>
        </div>
        <form onSubmit={submit} className="card space-y-4">
          {mode === "register" && (
            <div>
              <label className="label">Nome completo (opcional)</label>
              <input
                className="input"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
              />
            </div>
          )}
          <div>
            <label className="label">RA</label>
            <input
              className="input"
              type="text"
              placeholder="Número de Matrícula"
              value={ra}
              onChange={(e) => setRa(e.target.value)}
              required
            />
          </div>
          <div>
            <label className="label">Senha do UNASP</label>
            <input
              className="input"
              type="password"
              placeholder="Senha do UNASP"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </div>
          {mode === "register" && (
            <div>
              <label className="label">Perfil de acesso</label>
              <select
                className="input"
                value={profile}
                onChange={(e) => setProfile(e.target.value)}
              >
                {PROFILES.map((p) => (
                  <option key={p} value={p}>
                    {p}
                  </option>
                ))}
              </select>
            </div>
          )}

          {error && <p className="text-sm text-red-600">{error}</p>}

          <button className="btn-primary w-full" disabled={busy}>
            {busy ? "Aguarde..." : mode === "login" ? "Entrar" : "Criar conta"}
          </button>

          <p className="text-center text-sm text-slate-500">
            {mode === "login" ? "Não tem conta?" : "Já tem conta?"}{" "}
            <button
              type="button"
              className="font-medium text-brand"
              onClick={() => {
                setMode(mode === "login" ? "register" : "login");
                setError(null);
              }}
            >
              {mode === "login" ? "Cadastre-se" : "Entrar"}
            </button>
          </p>
        </form>
      </div>
    </div>
  );
}
