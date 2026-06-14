import { NavLink, Outlet } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

const links = [
  { to: "/", label: "Início", end: true },
  { to: "/templates", label: "Tipos de Saída" },
  { to: "/batch", label: "Planejar semana" },
  { to: "/schedules", label: "Agendamentos" },
  { to: "/history", label: "Histórico" },
  { to: "/settings", label: "Configurações" },
];

export default function Layout() {
  const { user, logout } = useAuth();

  return (
    <div className="min-h-screen">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-4 py-3">
          <div className="flex items-center gap-2">
            <span className="text-lg font-bold text-brand">UNASP</span>
            <span className="text-sm text-slate-500">Automação de Saídas</span>
          </div>
          <div className="flex items-center gap-4">
            <span className="hidden text-sm text-slate-500 sm:inline">
              {user?.full_name || user?.ra}
            </span>
            <button onClick={logout} className="btn-secondary text-xs">
              Sair
            </button>
          </div>
        </div>
        <nav className="mx-auto flex max-w-5xl gap-1 overflow-x-auto px-4">
          {links.map((l) => (
            <NavLink
              key={l.to}
              to={l.to}
              end={l.end}
              className={({ isActive }) =>
                `whitespace-nowrap border-b-2 px-3 py-2 text-sm font-medium transition ${
                  isActive
                    ? "border-brand text-brand"
                    : "border-transparent text-slate-500 hover:text-slate-800"
                }`
              }
            >
              {l.label}
            </NavLink>
          ))}
        </nav>
      </header>
      <main className="mx-auto max-w-5xl px-4 py-6">
        <Outlet />
      </main>
    </div>
  );
}
