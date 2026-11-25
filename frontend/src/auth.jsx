import { createContext, useContext, useEffect, useState } from "react";
import { api } from "./api.js";

const Ctx = createContext(null);
export const useAuth = () => useContext(Ctx);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(!!localStorage.getItem("token"));

  useEffect(() => {
    if (!localStorage.getItem("token")) return;
    api("/auth/me").then(setUser).catch(() => localStorage.removeItem("token")).finally(() => setLoading(false));
  }, []);

  const accept = (data) => {
    localStorage.setItem("token", data.access_token);
    setUser(data.user);
    return data.user;
  };
  const login = async (email, password) => accept(await api("/auth/login", { method: "POST", body: { email, password } }));
  const register = async (full_name, email, password) =>
    accept(await api("/auth/register", { method: "POST", body: { full_name, email, password } }));
  const logout = () => {
    localStorage.removeItem("token");
    setUser(null);
  };

  return <Ctx.Provider value={{ user, loading, login, register, logout }}>{children}</Ctx.Provider>;
}
