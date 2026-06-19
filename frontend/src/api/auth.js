const BASE = "http://localhost:8001";

export async function login(email, password) {
  const body = new URLSearchParams({ username: email, password });
  const res = await fetch(`${BASE}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body,
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || "Erreur de connexion");
  }
  return res.json();
}

export async function refreshToken(refresh_token) {
  const res = await fetch(`${BASE}/auth/refresh`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token }),
  });
  if (!res.ok) throw new Error("Session expirée");
  return res.json();
}

export async function logout(token) {
  await fetch(`${BASE}/auth/logout`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
  });
}

export async function getMe(token) {
  const res = await fetch(`${BASE}/auth/me`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error("Session expirée");
  return res.json();
}

export async function changePassword(token, old_password, new_password) {
  const res = await fetch(`${BASE}/auth/change-password`, {
    method: "PUT",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
    body: JSON.stringify({ old_password, new_password }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Erreur changement mot de passe");
  }
}
