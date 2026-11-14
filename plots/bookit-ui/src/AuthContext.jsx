import { useState } from "react";
import { AuthContext } from "./auth.js";
import { useEffect } from "react";
import { api, saveSession, clearSession, errorText } from "./api.js";


export function AuthProvider({ children }) {
  const [username, setUsername] = useState(localStorage.getItem("username"));
  const [isManager, setIsManager] = useState(false);
  const [isMainManager, setIsMainManager] = useState(false);
  const [ready, setReady] = useState(!localStorage.getItem("access"));

  useEffect(() => {
    if (!localStorage.getItem("access")) return;
    api("/auth/me/").then((res) => res.ok ? res.json() : null).then((data) => {
      if (data) {
        setUsername(data.username);
        setIsManager(Boolean(data.is_manager));
        setIsMainManager(Boolean(data.is_main_manager));
      }
    }).finally(() => setReady(true));
  }, []);

  async function login(email, password) {
    const res = await api("/auth/login/", {
      method: "POST",
      auth: false,
      body: JSON.stringify({ email, password }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(errorText(data));
    saveSession(data);
    setUsername(data.username);
    setIsManager(Boolean(data.is_manager));
    setIsMainManager(Boolean(data.is_main_manager));
    return data;
  }

  async function register(name, email, password) {
    const res = await api("/auth/register/", {
      method: "POST",
      auth: false,
      body: JSON.stringify({ username: name, email, password }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(errorText(data));
    saveSession(data);
    setUsername(data.username);
    setIsManager(false);
    setIsMainManager(false);
    return data;
  }

  function logout() {
    clearSession();
    setUsername(null);
    setIsManager(false);
    setIsMainManager(false);
  }

  return (
    <AuthContext.Provider value={{ username, isManager, isMainManager, ready, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}
