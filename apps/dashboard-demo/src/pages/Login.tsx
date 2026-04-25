import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";
import { Button } from "../components/ui/Button";

export function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();

  // Demo: auto-login immediately
  useEffect(() => {
    login("demo-token");
    navigate("/", { replace: true });
  }, [login, navigate]);

  return (
    <div className="login-shell">
      <div className="login-card">
        <div className="login-brand">
          <div className="login-logo">L</div>
          <h2>Citadel Demo</h2>
          <p>Logging you in automatically...</p>
        </div>
        <Button type="button" variant="primary" className="btn-block" disabled>
          Entering Demo...
        </Button>
      </div>
    </div>
  );
}
