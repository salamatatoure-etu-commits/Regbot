import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { listConversations, deleteConversation, cleanupConversations } from "../../api/conversations";

function formatDate(dt) {
  if (!dt) return "—";
  return new Date(dt).toLocaleString("fr-FR", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" });
}

export default function ConversationsTab({ token }) {
  const [convs,    setConvs]    = useState([]);
  const [loading,  setLoading]  = useState(true);
  const [cleaning, setCleaning] = useState(false);
  const [error,    setError]    = useState("");
  const [success,  setSuccess]  = useState("");

  useEffect(() => { load(); }, []);

  async function load() {
    setLoading(true);
    try { setConvs(await listConversations(token)); }
    catch { setError("Erreur chargement conversations"); }
    finally { setLoading(false); }
  }

  async function handleDelete(id) {
    if (!confirm(`Supprimer la conversation #${id} ?`)) return;
    setError("");
    try { await deleteConversation(token, id); await load(); }
    catch { setError("Erreur suppression"); }
  }

  async function handleCleanup() {
    if (!confirm("Supprimer tous les documents expirés et fermer les conversations terminées ?")) return;
    setCleaning(true);
    setError(""); setSuccess("");
    try {
      const res = await cleanupConversations(token);
      setSuccess(`Nettoyage terminé : ${res.documents_supprimes} doc(s) supprimé(s), ${res.conversations_fermees} conversation(s) fermée(s).`);
      await load();
    } catch (err) {
      setError(err.message);
    } finally {
      setCleaning(false);
    }
  }

  if (loading) return <p className="tab-loading">Chargement…</p>;

  return (
    <div className="tab-section">
      <div className="tab-toolbar">
        <div>
          <h2 className="tab-title">Conversations</h2>
          <p className="tab-subtitle">Historique des échanges entre les employés et les bots.</p>
        </div>
        <motion.button
          className="btn-warning"
          onClick={handleCleanup}
          disabled={cleaning}
          whileHover={{ scale: 1.03 }} whileTap={{ scale: 0.97 }}
        >
          <svg width="14" height="14" viewBox="0 0 16 16" fill="none">
            <path d="M2 4h12M6 4V2h4v2M13 4l-1 10H4L3 4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
          {cleaning ? "Nettoyage…" : "Nettoyer les expirés"}
        </motion.button>
      </div>

      <AnimatePresence>
        {error   && <motion.div className="tab-error"   initial={{ opacity: 0, y: -6 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}>{error}</motion.div>}
        {success && <motion.div className="tab-success" initial={{ opacity: 0, y: -6 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}>{success}</motion.div>}
      </AnimatePresence>

      <table className="admin-table">
        <thead>
          <tr><th>#</th><th>Utilisateur</th><th>Service</th><th>Début</th><th>Dernière activité</th><th>Statut</th><th></th></tr>
        </thead>
        <tbody>
          <AnimatePresence>
            {convs.map((c, i) => (
              <motion.tr key={c.conversationid}
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: 10 }}
                transition={{ delay: i * 0.02 }}
              >
                <td style={{ color: "#bbb" }}>#{c.conversationid}</td>
                <td>{c.utilisateur_id ?? "—"}</td>
                <td>{c.service_id ?? "—"}</td>
                <td style={{ color: "#888", fontSize: "0.8rem" }}>{formatDate(c.start_time)}</td>
                <td style={{ color: "#888", fontSize: "0.8rem" }}>{formatDate(c.last_activity)}</td>
                <td><span className={`badge ${c.status === "active" ? "badge-active" : ""}`}>{c.status}</span></td>
                <td>
                  <motion.button className="btn-danger-sm"
                    onClick={() => handleDelete(c.conversationid)}
                    whileHover={{ scale: 1.1 }} whileTap={{ scale: 0.9 }}>
                    ✕
                  </motion.button>
                </td>
              </motion.tr>
            ))}
          </AnimatePresence>
          {convs.length === 0 && (
            <tr><td colSpan={7} className="table-empty">Aucune conversation</td></tr>
          )}
        </tbody>
      </table>

      {convs.length > 0 && (
        <p className="tab-total-count">≡ {convs.length} conversation{convs.length > 1 ? "s" : ""} au total</p>
      )}
    </div>
  );
}
