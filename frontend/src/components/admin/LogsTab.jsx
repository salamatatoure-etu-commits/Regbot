import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { getLogs } from "../../api/stats";

function formatTs(ts) {
  if (!ts) return "—";
  return new Date(ts).toLocaleString("fr-FR", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

export default function LogsTab({ token }) {
  const [logs,    setLogs]    = useState([]);
  const [loading, setLoading] = useState(true);
  const [error,   setError]   = useState("");

  useEffect(() => {
    getLogs(token, 50)
      .then(setLogs)
      .catch(() => setError("Erreur chargement logs"))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <p className="tab-loading">Chargement…</p>;

  return (
    <div className="tab-section">
      <div className="tab-toolbar">
        <div>
          <h2 className="tab-title">Logs d'activité</h2>
          <p className="tab-subtitle">Les 50 derniers messages échangés sur la plateforme.</p>
        </div>
        <span style={{ fontSize: "0.8rem", color: "#aaa" }}>{logs.length} entrées</span>
      </div>

      <AnimatePresence>
        {error && <motion.div className="tab-error" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>{error}</motion.div>}
      </AnimatePresence>

      <table className="admin-table">
        <thead>
          <tr><th>Horodatage</th><th>Type</th><th>Conv.</th><th>Contenu</th><th>Catégorie</th></tr>
        </thead>
        <tbody>
          <AnimatePresence>
            {logs.map((log, i) => (
              <motion.tr key={log.id}
                initial={{ opacity: 0, x: -8 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: Math.min(i * 0.015, 0.5) }}
              >
                <td style={{ fontSize: "0.78rem", color: "#888", whiteSpace: "nowrap" }}>{formatTs(log.timestamp)}</td>
                <td>
                  <span className={`badge ${log.type === "user" ? "badge-user" : "badge-bot"}`}>
                    {log.type === "user" ? "Employé" : "Bot"}
                  </span>
                </td>
                <td style={{ color: "#bbb", fontSize: "0.8rem" }}>#{log.conversation_id}</td>
                <td className="td-truncate" style={{ maxWidth: "320px" }}>{log.content}</td>
                <td>
                  {log.type_question && (
                    <span className="badge">{log.type_question}</span>
                  )}
                </td>
              </motion.tr>
            ))}
          </AnimatePresence>
          {logs.length === 0 && (
            <tr><td colSpan={5} className="table-empty">Aucun log disponible</td></tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
