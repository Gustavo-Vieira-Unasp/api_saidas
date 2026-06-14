import { useState } from "react";
import { useAuth } from "../context/AuthContext";
import { updatePassword, updateProfile } from "../services/api";

const PROFILES = ["Funcionário", "Aluno Graduação", "Aluno Educação Básica"];

export default function Settings() {
  const { user, refresh } = useAuth();
  const [profile, setProfile] = useState(user?.unasp_profile || PROFILES[1]);
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const saveProfile = async () => {
    setMessage(null);
    setError(null);
    setBusy(true);
    try {
      await updateProfile(profile);
      await refresh();
      setMessage("Perfil atualizado.");
    } catch (err: unknown) {
      const detail =
        err && typeof err === "object" && "response" in err
          ? (err as { response?: { data?: { detail?: string } } }).response?.data
              ?.detail
          : undefined;
      setError(detail || "Erro ao salvar");
    } finally {
      setBusy(false);
    }
  };

  const savePassword = async () => {
    setMessage(null);
    setError(null);
    if (!currentPassword || !newPassword) {
      setError("Preencha a senha atual e a nova senha.");
      return;
    }
    setBusy(true);
    try {
      await updatePassword(currentPassword, newPassword);
      await refresh();
      setCurrentPassword("");
      setNewPassword("");
      setMessage("Senha atualizada.");
    } catch (err: unknown) {
      const detail =
        err && typeof err === "object" && "response" in err
          ? (err as { response?: { data?: { detail?: string } } }).response?.data
              ?.detail
          : undefined;
      setError(detail || "Erro ao atualizar senha");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-bold">Configurações</h1>
        <p className="text-sm text-slate-500">
          Sua conta usa o RA e a senha do UNASP. A senha é criptografada e
          usada para enviar as autorizações automaticamente.
        </p>
      </div>

      <div className="card space-y-4">
        <h2 className="font-semibold">Conta do UNASP</h2>
        <div>
          <label className="label">RA (matrícula)</label>
          <input className="input" value={user?.ra || ""} disabled readOnly />
        </div>

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

        <div className="flex justify-end">
          <button className="btn-primary" onClick={saveProfile} disabled={busy}>
            {busy ? "Salvando..." : "Salvar perfil"}
          </button>
        </div>
      </div>

      <div className="card space-y-4">
        <h2 className="font-semibold">Alterar senha</h2>
        <div>
          <label className="label">Senha atual</label>
          <input
            className="input"
            type="password"
            value={currentPassword}
            onChange={(e) => setCurrentPassword(e.target.value)}
            autoComplete="current-password"
          />
        </div>
        <div>
          <label className="label">Nova senha</label>
          <input
            className="input"
            type="password"
            value={newPassword}
            onChange={(e) => setNewPassword(e.target.value)}
            autoComplete="new-password"
          />
        </div>

        {message && <p className="text-sm text-green-600">{message}</p>}
        {error && <p className="text-sm text-red-600">{error}</p>}

        <div className="flex justify-end">
          <button className="btn-primary" onClick={savePassword} disabled={busy}>
            {busy ? "Salvando..." : "Atualizar senha"}
          </button>
        </div>
      </div>
    </div>
  );
}
