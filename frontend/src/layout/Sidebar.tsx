import { NavLink } from "react-router-dom";
import { navItems } from "../data/nav";
import { useTheme } from "../hooks/useTheme";

export function Sidebar() {
  const { theme, toggleTheme } = useTheme();
  return (
    <aside className="sidebar">
      <div className="sidebar__brand">
        <div className="sidebar__logo">L</div>
        <div>
          <strong>Ledger</strong>
          <p>Governance Console</p>
        </div>
      </div>

      <nav className="sidebar__nav" aria-label="Primary navigation">
        {navItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            className={({ isActive }) =>
              `sidebar__link ${isActive ? "is-active" : ""}`
            }
          >
            <span className="sidebar__icon">{item.icon}</span>
            <span>{item.label}</span>
          </NavLink>
        ))}
      </nav>

      <div className="sidebar__footer">
        <div className="workspace-chip">Forge / Production</div>
        <button className="btn btn-secondary btn-block" onClick={toggleTheme}>
          {theme === "light" ? "Dark Mode" : "Light Mode"}
        </button>
      </div>
    </aside>
  );
}
