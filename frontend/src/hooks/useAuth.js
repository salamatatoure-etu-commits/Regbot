import { useState, useEffect } from "react";
import { getMe, logout, refreshToken } from "../api/auth";

export function useAuth() {
  const [user, setUser]     = useState(null);
  const [token, setToken]   = useState(() => localStorage.getItem("access_token"));
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!token) { setLoading(false); return; }
    getMe(token)
      .then(setUser)
      .catch(async () => {
        const rt = localStorage.getItem("refresh_token");
        if (!rt) { signOut(); return; }
        try {
          const tokens = await refreshToken(rt);
          localStorage.setItem("access_token", tokens.access_token);
          localStorage.setItem("refresh_token", tokens.refresh_token);
          setToken(tokens.access_token);
          const me = await getMe(tokens.access_token);
          setUser(me);
        } catch {
          signOut();
        }
      })
      .finally(() => setLoading(false));
  }, [token]);

  function signIn(access_token, refresh_token) {
    localStorage.setItem("access_token", access_token);
    localStorage.setItem("refresh_token", refresh_token);
    setToken(access_token);
  }

  function signOut() {
    if (token) logout(token).catch(() => {});
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    setUser(null);
    setToken(null);
    setLoading(false);
  }

  return { user, token, loading, signIn, signOut };
}
