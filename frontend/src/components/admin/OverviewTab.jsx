import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { getStats, getStatsByService } from "../../api/stats";
import { listDocuments } from "../../api/documents";
import { listUsers } from "../../api/users";


function KpiCard({ label, value, color, bg, icon, sub }) {
  return (
    <motion.div className="kpi-card"
      initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}
      whileHover={{ y: -3, boxShadow: "0 8px 24px rgba(0,0,0,0.08)" }}>
      <div className="kpi-icon-wrap" style={{ background: bg, color }}>{icon}</div>
      <div className="kpi-value" style={{ color }}>{value ?? "—"}</div>
      <div className="kpi-label">{label}</div>
      {sub && <div className="kpi-sub">{sub}</div>}
    </motion.div>
  );
}

function HBarChart({ data }) {
  if (!data?.length) return <p style={{ color: "#ccc", fontSize: "0.85rem" }}>Aucune donnée</p>;
  const max = Math.max(...data.map(d => d.questions), 1);
  return (
    <div className="hbar-list">
      {data.map((d, i) => (
        <div key={d.service} className="hbar-row">
          <span className="hbar-label">{d.service}</span>
          <div className="hbar-track">
            <motion.div className="hbar-fill"
              initial={{ width: 0 }}
              animate={{ width: `${(d.questions / max) * 100}%` }}
              transition={{ delay: i * 0.07, duration: 0.5, ease: "easeOut" }}
            />
          </div>
          <span className="hbar-val">{d.questions}</span>
        </div>
      ))}
    </div>
  );
}

function WeekChart({ data }) {
  if (!data?.length) return <p style={{ color: "#ccc", fontSize: "0.85rem" }}>Aucune donnée</p>;
  const max = Math.max(...data.map(d => d.count), 1);
  return (
    <div className="week-chart">
      {data.map((d, i) => {
        const pct = Math.max((d.count / max) * 100, 4);
        const label = new Date(d.date).toLocaleDateString("fr-FR", { weekday: "short", day: "numeric" });
        return (
          <div key={d.date} className="week-col">
            <span className="week-count">{d.count}</span>
            <div className="week-bar-wrap">
              <motion.div className="week-bar-fill"
                initial={{ height: 0 }}
                animate={{ height: `${pct}%` }}
                transition={{ delay: i * 0.06, duration: 0.45, ease: "easeOut" }}
              />
            </div>
            <span className="week-day">{label}</span>
          </div>
        );
      })}
    </div>
  );
}

export default function OverviewTab({ token }) {
  const [stats,    setStats]    = useState(null);
  const [byService,setByService]= useState([]);
  const [counts,   setCounts]   = useState({ docs: "—", users: "—" });

  useEffect(() => {
    getStats(token).then(setStats).catch(() => {});
    getStatsByService(token).then(setByService).catch(() => {});
    Promise.all([
      listDocuments(token).catch(() => []),
      listUsers(token).catch(() => []),
    ]).then(([docs, users]) => setCounts({ docs: docs.length, users: users.length }));
  }, [token]);

  return (
    <div className="tab-section">
      <div style={{ marginBottom: "0.25rem" }}>
        <h2 className="tab-title">Vue d'ensemble</h2>
        <p className="tab-subtitle">Tableau de bord de la plateforme RegBot.</p>
      </div>

      {/* KPI row */}
      <div className="kpi-row">
        <KpiCard label="Questions totales"   value={stats?.total_questions}  color="#5c4ed8" bg="rgba(92,78,216,0.08)"
          sub={`+${stats?.questions_today ?? 0} aujourd'hui`}
          icon={<svg width="20" height="20" viewBox="0 0 24 24" fill="none"><path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2v10z" stroke="currentColor" strokeWidth="1.7" strokeLinejoin="round"/></svg>} />
        <KpiCard label="Cette semaine"       value={stats?.questions_week}   color="#10b981" bg="rgba(16,185,129,0.08)"
          sub="questions posées"
          icon={<svg width="20" height="20" viewBox="0 0 24 24" fill="none"><path d="M2 12l4-4 3 3 5-6" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round"/></svg>} />
        <KpiCard label="Documents indexés"  value={counts.docs}             color="#f59e0b" bg="rgba(245,158,11,0.08)"
          icon={<svg width="20" height="20" viewBox="0 0 24 24" fill="none"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8l-6-6z" stroke="currentColor" strokeWidth="1.7" strokeLinejoin="round"/><path d="M14 2v6h6" stroke="currentColor" strokeWidth="1.7" strokeLinejoin="round"/></svg>} />
        <KpiCard label="Utilisateurs"       value={counts.users}            color="#0ea5e9" bg="rgba(14,165,233,0.08)"
          icon={<svg width="20" height="20" viewBox="0 0 24 24" fill="none"><circle cx="9" cy="7" r="4" stroke="currentColor" strokeWidth="1.7"/><path d="M2 21c0-4 3-7 7-7s7 3 7 7" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round"/></svg>} />
      </div>

      {/* Charts row */}
      <div className="overview-charts-row">
        <div className="overview-chart-card">
          <h3 className="overview-card-title">Questions par service</h3>
          <HBarChart data={byService} />
        </div>
        <div className="overview-chart-card">
          <h3 className="overview-card-title">Activité — 7 derniers jours</h3>
          <WeekChart data={stats?.daily || []} />
        </div>
      </div>

    </div>
  );
}
