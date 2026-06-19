import { useState, useEffect, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { listUsers, createUser, deleteUser, resetUserPassword, toggleUserActive } from "../../api/users";
import { listServices } from "../../api/services";

const EMPTY = { nom: "", email: "", mot_de_passe: "", role: "employe", service_id: "" };

function UserActionMenu({ userId, userName, onDelete, onReset }) {
  const [open, setOpen] = useState(false);
  const [dropUp, setDropUp] = useState(false);
  const ref = useRef(null);
  const btnRef = useRef(null);

  useEffect(() => {
    if (!open) return;
    function handleClick(e) {
      if (ref.current && !ref.current.contains(e.target)) setOpen(false);
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, [open]);

  function handleOpen() {
    if (btnRef.current) {
      const rect = btnRef.current.getBoundingClientRect();
      setDropUp(rect.bottom + 100 > window.innerHeight);
    }
    setOpen(v => !v);
  }

  return (
    <div ref={ref} style={{ position: "relative", display: "inline-block" }}>
      <motion.button ref={btnRef} className="btn-menu-dots" onClick={handleOpen}
        whileHover={{ scale: 1.1 }} whileTap={{ scale: 0.92 }} title="Actions">
        ⋮
      </motion.button>
      <AnimatePresence>
        {open && (
          <motion.div className="doc-action-menu"
            style={dropUp ? { bottom: "calc(100% + 4px)", top: "auto" } : {}}
            initial={{ opacity: 0, y: dropUp ? 6 : -6, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, scale: 0.95 }}
            transition={{ duration: 0.15 }}>
            <button className="doc-action-item"
              onClick={() => { setOpen(false); onReset(userId); }}>
              🔑 Réinitialiser le mot de passe
            </button>
            <button className="doc-action-item doc-action-delete"
              onClick={() => { setOpen(false); onDelete(userId, userName); }}>
              🗑 Supprimer
            </button>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

export default function UsersTab({ token }) {
  const [users,      setUsers]      = useState([]);
  const [services,   setServices]   = useState([]);
  const [loading,    setLoading]    = useState(true);
  const [showForm,   setShowForm]   = useState(false);
  const [form,       setForm]       = useState(EMPTY);
  const [creating,   setCreating]   = useState(false);
  const [error,      setError]      = useState("");
  const [search,     setSearch]     = useState("");
  const [filterSvc,  setFilterSvc]  = useState("");
  const [success,    setSuccess]    = useState("");
  const [resetId,    setResetId]    = useState(null);
  const [resetPwd,   setResetPwd]   = useState("");
  const [resetLoading, setResetLoading] = useState(false);

  useEffect(() => { load(); }, []);

  async function load() {
    setLoading(true);
    try {
      const [u, s] = await Promise.all([listUsers(token), listServices(token)]);
      setUsers(u.sort((a, b) => a.nom.localeCompare(b.nom, "fr")));
      setServices(s);
    } catch {
      setError("Erreur chargement");
    } finally {
      setLoading(false);
    }
  }

  async function handleCreate(e) {
    e.preventDefault();
    setError(""); setSuccess("");
    if (!form.service_id) { setError("Veuillez sélectionner un service."); return; }
    setCreating(true);
    try {
      await createUser(token, { ...form, service_id: parseInt(form.service_id) });
      setSuccess(`Utilisateur "${form.nom}" créé avec succès.`);
      setForm(EMPTY);
      setShowForm(false);
      await load();
    } catch (err) {
      setError(err.message);
    } finally {
      setCreating(false);
    }
  }

  async function handleDelete(id, nom) {
    if (!confirm(`Supprimer l'utilisateur "${nom}" ?`)) return;
    setError("");
    try { await deleteUser(token, id); await load(); }
    catch { setError("Erreur suppression"); }
  }

  async function handleToggleActive(id) {
    try {
      const updated = await toggleUserActive(token, id);
      setUsers(prev => prev.map(u => u.utilisateurId === id ? { ...u, is_active: updated.is_active } : u));
    } catch {
      setError("Erreur changement statut");
    }
  }

  async function handleReset(e) {
    e.preventDefault();
    setResetLoading(true);
    setError(""); setSuccess("");
    try {
      await resetUserPassword(token, resetId, resetPwd);
      setSuccess("Mot de passe réinitialisé avec succès.");
      setResetId(null);
      setResetPwd("");
    } catch (err) {
      setError(err.message);
    } finally {
      setResetLoading(false);
    }
  }

  const visible = users.filter(u => {
    const q = search.toLowerCase();
    if (q && !u.nom.toLowerCase().includes(q) && !u.email.toLowerCase().includes(q)) return false;
    if (filterSvc && String(u.service_id) !== filterSvc) return false;
    return true;
  });

  if (loading) return <p className="tab-loading">Chargement…</p>;

  return (
    <div className="tab-section">
      <div className="tab-toolbar">
        <div>
          <h2 className="tab-title">Utilisateurs</h2>
          <p className="tab-subtitle">Gérez les comptes et les accès des employés.</p>
        </div>
        <div className="doc-toolbar-right">
          <div className="doc-search-wrap">
            <span className="doc-search-icon">🔍</span>
            <input
              className="doc-search-input"
              placeholder="Rechercher un utilisateur…"
              value={search}
              onChange={e => setSearch(e.target.value)}
            />
            {search && <button className="doc-search-clear" onClick={() => setSearch("")}>✕</button>}
          </div>

          <select
            className="doc-search-input"
            value={filterSvc}
            onChange={e => setFilterSvc(e.target.value)}
            style={{ width: "160px", cursor: "pointer" }}
          >
            <option value="">Tous les services</option>
            {services.map(s => (
              <option key={s.serviceId} value={String(s.serviceId)}>{s.nom}</option>
            ))}
          </select>

        <motion.button
          className="btn-primary"
          onClick={() => { setShowForm(v => !v); setError(""); setSuccess(""); }}
          whileHover={{ scale: 1.03 }} whileTap={{ scale: 0.97 }}
        >
          {showForm ? "Annuler" : "+ Créer un utilisateur"}
        </motion.button>
        </div>
      </div>

      <AnimatePresence>
        {showForm && (
          <motion.form
            className="create-user-form"
            onSubmit={handleCreate}
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.25 }}
            style={{ overflow: "hidden" }}
          >
            <div className="form-row">
              <div className="form-group">
                <label>Nom complet</label>
                <input className="inline-input" value={form.nom}
                  onChange={e => setForm(f => ({ ...f, nom: e.target.value }))}
                  placeholder="Fatima Benali" required />
              </div>
              <div className="form-group">
                <label>Email</label>
                <input className="inline-input" type="email" value={form.email}
                  onChange={e => setForm(f => ({ ...f, email: e.target.value }))}
                  placeholder="fatima@entreprise.ma" required />
              </div>
            </div>
            <div className="form-row">
              <div className="form-group">
                <label>Mot de passe</label>
                <input className="inline-input" type="password" value={form.mot_de_passe}
                  onChange={e => setForm(f => ({ ...f, mot_de_passe: e.target.value }))}
                  placeholder="••••••••" minLength={6} required />
              </div>
              <div className="form-group">
                <label>Rôle</label>
                <select className="inline-input" value={form.role}
                  onChange={e => setForm(f => ({ ...f, role: e.target.value }))}>
                  <option value="employe">Employé</option>
                  <option value="admin">Admin</option>
                </select>
              </div>
              <div className="form-group">
                <label>Service</label>
                <select className="inline-input" value={form.service_id}
                  onChange={e => setForm(f => ({ ...f, service_id: e.target.value }))} required>
                  <option value="">— Choisir —</option>
                  {services.map(s => (
                    <option key={s.serviceId} value={s.serviceId}>{s.nom}</option>
                  ))}
                </select>
              </div>
            </div>
            <motion.button className="btn-primary" type="submit" disabled={creating}
              whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.97 }}>
              {creating ? "Création…" : "Créer l'utilisateur"}
            </motion.button>
          </motion.form>
        )}
      </AnimatePresence>

      <AnimatePresence>
        {error   && <motion.div className="tab-error"   initial={{ opacity: 0, y: -6 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}>{error}</motion.div>}
        {success && <motion.div className="tab-success" initial={{ opacity: 0, y: -6 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}>{success}</motion.div>}
      </AnimatePresence>

      <table className="admin-table">
        <thead>
          <tr><th>Nom</th><th>Email</th><th>Service</th><th>Rôle</th><th>Statut</th><th></th></tr>
        </thead>
        <tbody>
          <AnimatePresence>
            {visible.map((u, i) => (
              <>
                <motion.tr key={u.utilisateurId}
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: 10 }}
                  transition={{ delay: i * 0.03 }}
                >
                  <td><strong>{u.nom}</strong></td>
                  <td style={{ color: "#888" }}>{u.email}</td>
                  <td>{services.find(s => s.serviceId === u.service_id)?.nom ?? "—"}</td>
                  <td>
                    <span className={`badge ${u.role === "admin" ? "badge-admin" : ""}`}>
                      {u.role === "admin" ? "Admin" : "Employé"}
                    </span>
                  </td>
                  <td>
                    <motion.button
                      className={`badge-toggle ${u.is_active ? "badge-toggle-active" : "badge-toggle-inactive"}`}
                      onClick={() => handleToggleActive(u.utilisateurId)}
                      whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}
                      title="Cliquer pour changer le statut"
                    >
                      {u.is_active ? "● actif" : "○ inactif"}
                    </motion.button>
                  </td>
                  <td style={{ textAlign: "right" }}>
                    <UserActionMenu
                      userId={u.utilisateurId}
                      userName={u.nom}
                      onDelete={handleDelete}
                      onReset={(id) => { setResetId(resetId === id ? null : id); setResetPwd(""); }}
                    />
                  </td>
                </motion.tr>

                <AnimatePresence>
                  {resetId === u.utilisateurId && (
                    <motion.tr key={`reset-${u.utilisateurId}`}
                      initial={{ opacity: 0, height: 0 }}
                      animate={{ opacity: 1, height: "auto" }}
                      exit={{ opacity: 0, height: 0 }}
                    >
                      <td colSpan={6} style={{ background: "#fafbff", padding: "0.75rem 1rem" }}>
                        <form className="inline-form" onSubmit={handleReset}>
                          <input
                            className="inline-input"
                            type="password"
                            placeholder="Nouveau mot de passe (6 car. min.)"
                            value={resetPwd}
                            onChange={e => setResetPwd(e.target.value)}
                            minLength={6}
                            required
                            style={{ maxWidth: 280 }}
                          />
                          <motion.button className="btn-primary" type="submit"
                            disabled={resetLoading}
                            whileHover={{ scale: 1.03 }} whileTap={{ scale: 0.97 }}>
                            {resetLoading ? "…" : "Réinitialiser"}
                          </motion.button>
                          <button type="button" className="btn-danger-sm"
                            onClick={() => { setResetId(null); setResetPwd(""); }}>
                            Annuler
                          </button>
                        </form>
                      </td>
                    </motion.tr>
                  )}
                </AnimatePresence>
              </>
            ))}
          </AnimatePresence>
          {visible.length === 0 && (
            <tr><td colSpan={6} className="table-empty">{users.length === 0 ? "Aucun utilisateur" : "Aucun résultat"}</td></tr>
          )}
        </tbody>
      </table>

      {users.length > 0 && (
        <p className="tab-total-count">
          {(search || filterSvc)
            ? `≡ ${visible.length} / ${users.length} utilisateur${users.length > 1 ? "s" : ""}`
            : `≡ ${users.length} utilisateur${users.length > 1 ? "s" : ""} au total`}
        </p>
      )}
    </div>
  );
}
