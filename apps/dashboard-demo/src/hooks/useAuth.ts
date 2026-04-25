import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";

export function useAuth() {
  const [token, setToken] = useState<string | null>(() => {
    if (typeof window !== "undefined") {
      return localStorage.getItem("auth_token");
    }
    return null;
  });
  const navigate = useNavigate();

  const login = (newToken: string) => {
    localStorage.setItem("auth_token", newToken);
    setToken(newToken);
    navigate("/overview");
  };

  const logout = () => {
    localStorage.removeItem("auth_token");
    setToken(null);
    navigate("/login");
  };

  // Listen for storage changes in case of logout from another tab
  useEffect(() => {
    const handleStorageChange = () => {
      setToken(localStorage.getItem("auth_token"));
    };
    window.addEventListener("storage", handleStorageChange);
    return () => window.removeEventListener("storage", handleStorageChange);
  }, []);

  return { token, login, logout, isAuthenticated: !!token };
}
