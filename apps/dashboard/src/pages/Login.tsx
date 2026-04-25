import { useState } from "react";
import { useAuth } from "../hooks/useAuth";
import { Button } from "../components/ui/Button";
import { Input } from "../components/ui/Input";

export function LoginPage() {
  const { login } = useAuth();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      const apiBase = import.meta.env.VITE_API_URL || "http://localhost:8000";
      const response = await fetch(`${apiBase}/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password }),
      });

      if (!response.ok) {
        throw new Error("Invalid operator credentials");
      }

      const data = await response.json();
      login(data.access_token);
    } catch (err: any) {
      setError(err.message || "Failed to authenticate");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-shell">
      <div className="login-card">
        <div className="login-brand">
          <div className="login-logo">L</div>
          <h2>Citadel Governance</h2>
          <p>Operator Authentication</p>
        </div>

        {error && <div className="login-error">{error}</div>}

        <form onSubmit={handleSubmit} className="login-form">
          <div className="field">
            <span>Operator ID</span>
            <Input 
              type="text" 
              placeholder="admin" 
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required 
            />
          </div>
          <div className="field">
            <span>Security Passcode</span>
            <Input 
              type="password" 
              placeholder="••••••••" 
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required 
            />
          </div>
          <Button type="submit" variant="primary" className="btn-block" disabled={loading}>
            {loading ? "Authenticating..." : "Authorize Session"}
          </Button>
        </form>
      </div>
    </div>
  );
}
