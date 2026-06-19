const BASE = "http://localhost:8001";

export async function listServices(token) {
  const res = await fetch(`${BASE}/services/`, { headers: { Authorization: `Bearer ${token}` } });
  if (!res.ok) throw new Error("Erreur chargement services");
  return res.json();
}

export async function createService(token, data) {
  const res = await fetch(`${BASE}/services/`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || "Erreur création service");
  }
  return res.json();
}

export async function deleteService(token, serviceId) {
  const res = await fetch(`${BASE}/services/${serviceId}`, {
    method: "DELETE",
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error("Erreur suppression service");
}
