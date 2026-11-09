import { createContext, useContext, useState } from "react";
import { api, saveSession, clearSession, errorText } from "./api.js";

const AuthContext = createContext(null);
export const useAuth = () => useContext(AuthContext);

export function AuthProvider({ children }) {
  const [username, setUsername] = useState(localStorage.getItem("username"));

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
  }

  function logout() {
    clearSession();
    setUsername(null);
  }

  return (
    <AuthContext.Provider value={{ username, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}