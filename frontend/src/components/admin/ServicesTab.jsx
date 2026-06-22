import { useState, useEffect, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { listServices, createService, updateService, deleteService } from "../../api/services";

function ServiceActionMenu({ serviceId, onDelete, onEdit }) {
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
      <motion.button
        ref={btnRef}
        className="btn-menu-dots"
        onClick={handleOpen}
        whileHover={{ scale: 1.1 }}
        whileTap={{ scale: 0.92 }}
        title="Actions"
      >
        ⋮
      </motion.button>
      <AnimatePresence>
        {open && (
          <motion.div
            className="doc-action-menu"
            style={dropUp ? { bottom: "calc(100% + 4px)", top: "auto" } : {}}
            initial={{ opacity: 0, y: dropUp ? 6 : -6, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, scale: 0.95 }}
            transition={{ duration: 0.15 }}
          >
            <button
              className="doc-action-item"
              onClick={() => { setOpen(false); onEdit(serviceId); }}
            >
              ✏️ Modifier
            </button>
            <button
              className="doc-action-item doc-action-delete"
              onClick={() => { setOpen(false); onDelete(serviceId); }}
            >
              🗑 Supprimer
            </button>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

export default function ServicesTab({ token }) {
  const [services, setServices] = useState([]);
  const [loading,  setLoading]  = useState(true);
  const [error,    setError]    = useState("");
  const [showForm, setShowForm] = useState(false);
  const [nom,      setNom]      = useState("");
  const [creating, setCreating] = useState(false);
  const [search,   setSearch]   = useState("");
  const [editingId, setEditingId] = useState(null);
  const [editNom,   setEditNom]   = useState("");
  const [saving,    setSaving]    = useState(false);
  const editInputRef = useRef(null);

  useEffect(() => { load(); }, []);

  useEffect(() => {
    if (editingId !== null && editInputRef.current) {
      editInputRef.current.focus();
      editInputRef.current.select();
    }
  }, [editingId]);

  async function load() {
    setLoading(true);
    try {
      const data = await listServices(token);
      setServices(data.sort((a, b) => a.nom.localeCompare(b.nom, "fr")));
    }
    catch { setError("Erreur chargement services"); }
    finally { setLoading(false); }
  }

  async function handleCreate(e) {
    e.preventDefault();
    if (!nom.trim()) return;
    setError("");
    setCreating(true);
    try {
      await createService(token, { nom: nom.trim() });
      setNom("");
      setShowForm(false);
      await load();
    } catch (err) {
      setError(err.message);
    } finally {
      setCreating(false);
    }
  }

  function handleEdit(id) {
    const s = services.find(s => s.serviceId === id);
    if (!s) return;
    setEditingId(id);
    setEditNom(s.nom);
    setError("");
  }

  async function handleSaveEdit(id) {
    if (!editNom.trim()) return;
    setSaving(true);
    setError("");
    try {
      await updateService(token, id, { nom: editNom.trim() });
      setEditingId(null);
      await load();
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  }

  function handleCancelEdit() {
    setEditingId(null);
    setEditNom("");
  }

  async function handleDelete(id) {
    if (!confirm("Supprimer ce service ?")) return;
    try { await deleteService(token, id); await load(); }
    catch { setError("Erreur suppression"); }
  }

  const visible = services.filter(s =>
    s.nom.toLowerCase().includes(search.toLowerCase())
  );

  if (loading) return <p className="tab-loading">Chargement…</p>;

  return (
    <div className="tab-section">
      <div className="tab-toolbar" style={{ alignItems: "flex-start" }}>
        <div>
          <h2 className="tab-title">Services</h2>
          <p className="tab-subtitle">Gérez et organisez les services de votre organisation.</p>
        </div>

        <div className="doc-toolbar-right">
          <div className="doc-search-wrap">
            <span className="doc-search-icon">🔍</span>
            <input
              className="doc-search-input"
              placeholder="Rechercher un service…"
              value={search}
              onChange={e => setSearch(e.target.value)}
            />
            {search && (
              <button className="doc-search-clear" onClick={() => setSearch("")}>✕</button>
            )}
          </div>

          <motion.button
            className="btn-primary"
            onClick={() => { setShowForm(v => !v); setNom(""); setError(""); }}
            whileHover={{ scale: 1.03 }} whileTap={{ scale: 0.97 }}
          >
            {showForm ? "Annuler" : "+ Créer"}
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
            transition={{ duration: 0.22 }}
            style={{ overflow: "hidden" }}
          >
            <div className="form-row" style={{ alignItems: "flex-end" }}>
              <div className="form-group">
                <label>Nom du service</label>
                <input
                  className="inline-input"
                  value={nom}
                  onChange={e => setNom(e.target.value)}
                  placeholder="ex : Ressources Humaines"
                  required
                />
              </div>
              <motion.button className="btn-primary" type="submit" disabled={creating}
                whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.97 }}>
                {creating ? "Création…" : "Créer le service"}
              </motion.button>
            </div>
          </motion.form>
        )}
      </AnimatePresence>

      <AnimatePresence>
        {error && (
          <motion.div className="tab-error"
            initial={{ opacity: 0, y: -6 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}>
            {error}
          </motion.div>
        )}
      </AnimatePresence>

      <table className="admin-table">
        <thead>
          <tr><th>ID</th><th>Nom</th><th style={{ textAlign: "right" }}>Actions</th></tr>
        </thead>
        <tbody>
          <AnimatePresence>
            {visible.map((s, i) => (
              <motion.tr key={s.serviceId}
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: 10 }}
                transition={{ delay: i * 0.04 }}
              >
                <td style={{ width: "70px" }}>
                  <span className="service-id-badge">#{s.serviceId}</span>
                </td>
                <td>
                  {editingId === s.serviceId ? (
                    <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                      <input
                        ref={editInputRef}
                        className="inline-input"
                        value={editNom}
                        onChange={e => setEditNom(e.target.value)}
                        onKeyDown={e => {
                          if (e.key === "Enter") handleSaveEdit(s.serviceId);
                          if (e.key === "Escape") handleCancelEdit();
                        }}
                        style={{ maxWidth: "220px" }}
                      />
                      <motion.button
                        className="btn-primary"
                        onClick={() => handleSaveEdit(s.serviceId)}
                        disabled={saving}
                        whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.97 }}
                        style={{ padding: "0.3rem 0.75rem", fontSize: "0.82rem" }}
                      >
                        {saving ? "…" : "Sauvegarder"}
                      </motion.button>
                      <motion.button
                        className="btn-secondary"
                        onClick={handleCancelEdit}
                        whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.97 }}
                        style={{ padding: "0.3rem 0.75rem", fontSize: "0.82rem" }}
                      >
                        Annuler
                      </motion.button>
                    </div>
                  ) : (
                    <strong>{s.nom}</strong>
                  )}
                </td>
                <td style={{ textAlign: "right" }}>
                  {editingId !== s.serviceId && (
                    <ServiceActionMenu
                      serviceId={s.serviceId}
                      onDelete={handleDelete}
                      onEdit={handleEdit}
                    />
                  )}
                </td>
              </motion.tr>
            ))}
          </AnimatePresence>
          {visible.length === 0 && (
            <tr><td colSpan={3} className="table-empty">
              {services.length === 0 ? "Aucun service" : "Aucun résultat"}
            </td></tr>
          )}
        </tbody>
      </table>

      {services.length > 0 && (
        <p className="tab-total-count">≡ {services.length} service{services.length > 1 ? "s" : ""} au total</p>
      )}
    </div>
  );
}
