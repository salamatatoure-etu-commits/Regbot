import { useState, useEffect, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { listBots, createBot, deleteBot, updateBotPrompt } from "../../api/bots";
import { listServices } from "../../api/services";

const EMPTY = { nom: "", service_id: "", langue: "fr", prompt: "" };

function BotActionMenu({ botId, botNom, onDelete, onEditPrompt }) {
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
      setDropUp(rect.bottom + 120 > window.innerHeight);
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
              onClick={() => { setOpen(false); onEditPrompt(botId); }}
            >
              ✏️ Modifier le prompt
            </button>
            <button
              className="doc-action-item doc-action-delete"
              onClick={() => { setOpen(false); onDelete(botId, botNom); }}
            >
              🗑 Supprimer
            </button>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

export default function BotsTab({ token }) {
  const [bots,      setBots]      = useState([]);
  const [services,  setServices]  = useState([]);
  const [loading,   setLoading]   = useState(true);
  const [showForm,  setShowForm]  = useState(false);
  const [form,      setForm]      = useState(EMPTY);
  const [creating,  setCreating]  = useState(false);
  const [error,     setError]     = useState("");
  const [success,   setSuccess]   = useState("");

  // prompt editing
  const [editPromptId,  setEditPromptId]  = useState(null);
  const [promptDraft,   setPromptDraft]   = useState("");
  const [savingPrompt,  setSavingPrompt]  = useState(false);
  const [promptSuccess, setPromptSuccess] = useState("");

  useEffect(() => { load(); }, []);

  async function load() {
    setLoading(true);
    try {
      const [b, s] = await Promise.all([listBots(token), listServices(token)]);
      setBots(b);
      setServices(s);
    } catch {
      setError("Erreur chargement");
    } finally {
      setLoading(false);
    }
  }

  async function handleCreate(e) {
    e.preventDefault();
    if (!form.service_id) { setError("Veuillez sélectionner un service."); return; }
    setCreating(true); setError(""); setSuccess("");
    try {
      await createBot(token, { ...form, service_id: parseInt(form.service_id), prompt: form.prompt || null });
      setSuccess(`Bot "${form.nom}" créé avec succès.`);
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
    if (!confirm(`Supprimer le bot "${nom}" ?`)) return;
    try { await deleteBot(token, id); await load(); }
    catch { setError("Erreur suppression"); }
  }

  function openEditPrompt(botId) {
    const bot = bots.find(b => b.botId === botId);
    setEditPromptId(botId);
    setPromptDraft(bot?.prompt || "");
    setPromptSuccess("");
  }

  async function handleSavePrompt(e) {
    e.preventDefault();
    setSavingPrompt(true);
    setPromptSuccess("");
    try {
      const updated = await updateBotPrompt(token, editPromptId, promptDraft);
      setBots(prev => prev.map(b => b.botId === editPromptId ? { ...b, prompt: updated.prompt } : b));
      setPromptSuccess("Prompt mis à jour.");
      setTimeout(() => { setEditPromptId(null); setPromptSuccess(""); }, 1200);
    } catch {
      setError("Erreur mise à jour prompt");
    } finally {
      setSavingPrompt(false);
    }
  }

  if (loading) return <p className="tab-loading">Chargement…</p>;

  return (
    <div className="tab-section">
      <div className="tab-toolbar">
        <div>
          <h2 className="tab-title">Bots</h2>
          <p className="tab-subtitle">Gérez les assistants IA de votre organisation.</p>
        </div>
        <motion.button className="btn-primary"
          onClick={() => { setShowForm(v => !v); setError(""); setSuccess(""); }}
          whileHover={{ scale: 1.03 }} whileTap={{ scale: 0.97 }}>
          {showForm ? "Annuler" : "+ Créer un bot"}
        </motion.button>
      </div>

      <AnimatePresence>
        {showForm && (
          <motion.form className="create-user-form" onSubmit={handleCreate}
            initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }} transition={{ duration: 0.22 }}
            style={{ overflow: "hidden" }}>
            <div className="form-row">
              <div className="form-group">
                <label>Nom du bot</label>
                <input className="inline-input" value={form.nom}
                  onChange={e => setForm(f => ({ ...f, nom: e.target.value }))}
                  placeholder="Bot RH" required />
              </div>
              <div className="form-group">
                <label>Service</label>
                <select className="inline-input" value={form.service_id}
                  onChange={e => setForm(f => ({ ...f, service_id: e.target.value }))} required>
                  <option value="">— Choisir —</option>
                  {services.map(s => <option key={s.serviceId} value={s.serviceId}>{s.nom}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Langue</label>
                <select className="inline-input" value={form.langue}
                  onChange={e => setForm(f => ({ ...f, langue: e.target.value }))}>
                  <option value="fr">Français</option>
                  <option value="en">English</option>
                </select>
              </div>
            </div>
            <div className="form-group" style={{ width: "100%" }}>
              <label>Prompt système (optionnel)</label>
              <textarea className="inline-input" value={form.prompt}
                onChange={e => setForm(f => ({ ...f, prompt: e.target.value }))}
                placeholder="Tu es un assistant spécialisé en ressources humaines…"
                rows={3} style={{ resize: "vertical", fontFamily: "inherit" }} />
            </div>
            <motion.button className="btn-primary" type="submit" disabled={creating}
              whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.97 }}>
              {creating ? "Création…" : "Créer le bot"}
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
          <tr><th>Nom</th><th>Service</th><th>Langue</th><th>Prompt</th><th style={{ textAlign: "right" }}>Actions</th></tr>
        </thead>
        <tbody>
          <AnimatePresence>
            {bots.map((b, i) => (
              <>
                <motion.tr key={b.botId}
                  initial={{ opacity: 0, x: -10 }} animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: 10 }} transition={{ delay: i * 0.04 }}>
                  <td><strong>{b.nom}</strong></td>
                  <td>{services.find(s => s.serviceId === b.service_id)?.nom ?? "—"}</td>
                  <td><span className="badge">{b.langue?.toUpperCase() || "FR"}</span></td>
                  <td className="td-prompt-preview">
                    {b.prompt
                      ? <span title={b.prompt}>{b.prompt.length > 60 ? b.prompt.slice(0, 60) + "…" : b.prompt}</span>
                      : <span style={{ color: "#ccc" }}>—</span>}
                  </td>
                  <td style={{ textAlign: "right" }}>
                    <BotActionMenu
                      botId={b.botId}
                      botNom={b.nom}
                      onDelete={handleDelete}
                      onEditPrompt={openEditPrompt}
                    />
                  </td>
                </motion.tr>

                <AnimatePresence>
                  {editPromptId === b.botId && (
                    <motion.tr key={`prompt-${b.botId}`}
                      initial={{ opacity: 0, height: 0 }}
                      animate={{ opacity: 1, height: "auto" }}
                      exit={{ opacity: 0, height: 0 }}>
                      <td colSpan={5} style={{ background: "#fafbff", padding: "0.85rem 1rem" }}>
                        <form onSubmit={handleSavePrompt}>
                          <label style={{ fontSize: "0.8rem", color: "#888", display: "block", marginBottom: "0.4rem" }}>
                            Prompt système — <strong>{b.nom}</strong>
                          </label>
                          <textarea
                            className="inline-input"
                            value={promptDraft}
                            onChange={e => setPromptDraft(e.target.value)}
                            rows={3}
                            style={{ width: "100%", resize: "vertical", fontFamily: "inherit", marginBottom: "0.6rem" }}
                            placeholder="Tu es un assistant spécialisé en…"
                          />
                          <div style={{ display: "flex", gap: "0.6rem", alignItems: "center" }}>
                            <motion.button className="btn-primary" type="submit" disabled={savingPrompt}
                              whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.97 }}>
                              {savingPrompt ? "Enregistrement…" : "Enregistrer"}
                            </motion.button>
                            <button type="button" className="btn-danger-sm"
                              onClick={() => { setEditPromptId(null); setPromptDraft(""); }}>
                              Annuler
                            </button>
                            {promptSuccess && <span style={{ fontSize: "0.82rem", color: "#27ae60" }}>✓ {promptSuccess}</span>}
                          </div>
                        </form>
                      </td>
                    </motion.tr>
                  )}
                </AnimatePresence>
              </>
            ))}
          </AnimatePresence>
          {bots.length === 0 && (
            <tr><td colSpan={5} className="table-empty">Aucun bot — créez-en un ci-dessus</td></tr>
          )}
        </tbody>
      </table>

      {bots.length > 0 && (
        <p className="tab-total-count">≡ {bots.length} bot{bots.length > 1 ? "s" : ""} au total</p>
      )}
    </div>
  );
}
