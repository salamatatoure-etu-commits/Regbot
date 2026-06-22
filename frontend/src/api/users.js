const BASE = "http://localhost:8001";

export async function listUsers(token) {
  const res = await fetch(`${BASE}/utilisateurs/`, { headers: { Authorization: `Bearer ${token}` } });
  if (!res.ok) throw new Error("Erreur chargement utilisateurs");
  return res.json();
}

export async function createUser(token, data) {
  const res = await fetch(`${BASE}/utilisateurs/`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || "Erreur création utilisateur");
  }
  return res.json();
}

export async function updateUser(token, userId, data) {
  const res = await fetch(`${BASE}/utilisateurs/${userId}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Erreur modification utilisateur");
  }
  return res.json();
}

export async function deleteUser(token, userId) {
  const res = await fetch(`${BASE}/utilisateurs/${userId}`, {
    method: "DELETE",
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error("Erreur suppression utilisateur");
}

export async function toggleUserActive(token, userId) {
  const res = await fetch(`${BASE}/utilisateurs/${userId}/toggle-active`, {
    method: "PUT",
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error("Erreur changement statut");
  return res.json();
}

export async function resetUserPassword(token, userId, new_password) {
  const res = await fetch(`${BASE}/utilisateurs/${userId}/reset-password`, {
    method: "PUT",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
    body: JSON.stringify({ new_password }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Erreur reset mot de passe");
  }
}
