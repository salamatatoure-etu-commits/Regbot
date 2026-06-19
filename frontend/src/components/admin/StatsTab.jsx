import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { getStats, getStatsByService } from "../../api/stats";

function BarChart({ daily }) {
  if (!daily?.length) return <p style={{ color: "#bbb", fontSize: "0.85rem", textAlign: "center", padding: "2rem" }}>Aucune donnée</p>;
  const max = Math.max(...daily.map(d => d.count), 1);
  return (
    <div className="bar-chart">
      {daily.map((d, i) => (
        <div key={i} className="bar-col">
          <div className="bar-wrap">
            <motion.div
              className="bar-fill"
              initial={{ height: 0 }}
              animate={{ height: `${(d.count / max) * 100}%` }}
              transition={{ delay: i * 0.05, duration: 0.4 }}
            />
          </div>
          <span className="bar-label">{d.date?.slice(5)}</span>
          <span className="bar-value">{d.count}</span>
        </div>
      ))}
    </div>
  );
}

export default function StatsTab({ token }) {
  const [stats,      setStats]      = useState(null);
  const [byService,  setByService]  = useState([]);
  const [loading,    setLoading]    = useState(true);
  const [error,      setError]      = useState("");

  useEffect(() => {
    Promise.all([
      getStats(token),
      getStatsByService(token).catch(() => []),
    ])
      .then(([s, bs]) => { setStats(s); setByService(bs); })
      .catch(() => setError("Erreur chargement statistiques"))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <p className="tab-loading">Chargement…</p>;
  if (error)   return <div className="tab-error">{error}</div>;

  const KPI_LIST = [
    { label: "Questions aujourd'hui", value: stats.questions_today,     color: "#5c4ed8", bg: "rgba(92,78,216,0.08)" },
    { label: "Cette semaine",         value: stats.questions_week,      color: "#0ea5e9", bg: "rgba(14,165,233,0.08)" },
    { label: "Total questions",       value: stats.total_questions,     color: "#10b981", bg: "rgba(16,185,129,0.08)" },
    { label: "Conversations actives", value: stats.active_conversations, color: "#f59e0b", bg: "rgba(245,158,11,0.08)" },
  ];

  return (
    <div className="tab-section">
      <div>
        <h2 className="tab-title">Statistiques</h2>
        <p className="tab-subtitle">Vue d'ensemble de l'utilisation de la plateforme.</p>
      </div>

      <div className="kpi-row">
        {KPI_LIST.map((k, i) => (
          <motion.div key={k.label} className="kpi-card"
            initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.07 }} whileHover={{ y: -3 }}>
            <div className="kpi-icon-wrap" style={{ background: k.bg, color: k.color }}>
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
                <path d="M3 18l6-6 4 4 8-8" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
            </div>
            <div className="kpi-value" style={{ color: k.color }}>{k.value ?? "—"}</div>
            <div className="kpi-label">{k.label}</div>
          </motion.div>
        ))}
      </div>

      <div className="stats-card">
        <h3 className="stats-card-title">Questions / jour (7 derniers jours)</h3>
        <BarChart daily={stats.daily} />
      </div>

      {byService.length > 0 && (
        <div className="stats-card">
          <h3 className="stats-card-title">Questions par service</h3>
          <div className="service-stats-list">
            {byService.map((s, i) => {
              const max = byService[0].questions;
              return (
                <motion.div key={s.service} className="service-stat-row"
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: i * 0.06 }}>
                  <span className="service-stat-name">{s.service}</span>
                  <div className="service-stat-bar-wrap">
                    <motion.div
                      className="service-stat-bar-fill"
                      initial={{ width: 0 }}
                      animate={{ width: `${(s.questions / max) * 100}%` }}
                      transition={{ delay: i * 0.06 + 0.1, duration: 0.5 }}
                    />
                  </div>
                  <span className="service-stat-count">{s.questions}</span>
                </motion.div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
