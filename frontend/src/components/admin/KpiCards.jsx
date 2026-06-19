import { motion } from "framer-motion";

const CARDS = [
  {
    label: "Documents",
    key: "docs",
    color: "#5c4ed8",
    bg: "rgba(92,78,216,0.08)",
    icon: (
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none">
        <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8l-6-6z" stroke="currentColor" strokeWidth="1.7" strokeLinejoin="round"/>
        <path d="M14 2v6h6M16 13H8M16 17H8M10 9H8" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round"/>
      </svg>
    ),
  },
  {
    label: "Utilisateurs",
    key: "users",
    color: "#0ea5e9",
    bg: "rgba(14,165,233,0.08)",
    icon: (
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none">
        <circle cx="9" cy="7" r="4" stroke="currentColor" strokeWidth="1.7"/>
        <path d="M2 21c0-4 3-7 7-7s7 3 7 7" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round"/>
        <path d="M19 11v6M22 14h-6" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round"/>
      </svg>
    ),
  },
  {
    label: "Bots",
    key: "bots",
    color: "#f59e0b",
    bg: "rgba(245,158,11,0.08)",
    icon: (
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none">
        <rect x="4" y="8" width="16" height="12" rx="3" stroke="currentColor" strokeWidth="1.7"/>
        <path d="M9 8V6a3 3 0 016 0v2" stroke="currentColor" strokeWidth="1.7"/>
        <circle cx="9" cy="14" r="1.5" fill="currentColor"/>
        <circle cx="15" cy="14" r="1.5" fill="currentColor"/>
      </svg>
    ),
  },
];

export default function KpiCards({ docs, users, bots }) {
  const values = { docs, users, bots };

  return (
    <div className="kpi-row">
      {CARDS.map((c, i) => (
        <motion.div
          key={c.label}
          className="kpi-card"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: i * 0.08, duration: 0.35 }}
          whileHover={{ y: -3, boxShadow: "0 8px 24px rgba(0,0,0,0.1)" }}
        >
          <div className="kpi-icon-wrap" style={{ background: c.bg, color: c.color }}>
            {c.icon}
          </div>
          <motion.div
            className="kpi-value"
            style={{ color: c.color }}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: i * 0.08 + 0.2 }}
          >
            {values[c.key] ?? "—"}
          </motion.div>
          <div className="kpi-label">{c.label}</div>
        </motion.div>
      ))}
    </div>
  );
}
