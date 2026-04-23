import { Outlet } from "react-router-dom";
import { Sidebar } from "./Sidebar";
import { Topbar } from "./Topbar";
import { CommandBar } from "../components/ui/CommandBar";
import { useCommandBar } from "../hooks/useCommandBar";

export function DashboardLayout() {
  const { isOpen, open, close } = useCommandBar();

  return (
    <div className="dashboard-shell">
      <Sidebar />
      <div className="main-shell">
        <Topbar onOpenCommandBar={open} />
        <main className="main-content">
          <Outlet />
        </main>
      </div>
      <CommandBar isOpen={isOpen} onClose={close} />
    </div>
  );
}
