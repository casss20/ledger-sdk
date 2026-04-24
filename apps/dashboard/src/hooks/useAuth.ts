import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";

export function useAuth() {
  const [token, setToken] = useState<string | null>(() => {
    if (typeof window !== "undefined") {
      return localStorage.getItem("CITADEL-token");
    }
    return null;
  });
  const navigate = useNavigate();

  const login = (newToken: string) => {
    localStorage.setItem("CITADEL-token", newToken);
    setToken(newToken);
    navigate("/overview");
  };

  const logout = () => {
    localStorage.removeItem("CITADEL-token");
    setToken(null);
    navigate("/login");
  };

  // Listen for storage changes in case of logout from another tab
  useEffect(() => {
    const handleStorageChange = () => {
      setToken(localStorage.getItem("CITADEL-token"));
    };
    window.addEventListener("storage", handleStorageChange);
    return () => window.removeEventListener("storage", handleStorageChange);
  }, []);

  return { token, login, logout, isAuthenticated: !!token };
}
