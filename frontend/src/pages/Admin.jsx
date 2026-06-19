import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import OverviewTab      from "../components/admin/OverviewTab";
import DocumentsTab     from "../components/admin/DocumentsTab";
import ServicesTab      from "../components/admin/ServicesTab";
import UsersTab         from "../components/admin/UsersTab";
import BotsTab          from "../components/admin/BotsTab";
import ConversationsTab from "../components/admin/ConversationsTab";
import StatsTab         from "../components/admin/StatsTab";
import LogsTab          from "../components/admin/LogsTab";
import { listDocuments }     from "../api/documents";
import { listUsers }         from "../api/users";
import { listServices }      from "../api/services";
import { listConversations } from "../api/conversations";
import { listBots }          from "../api/bots";
import "./Admin.css";

const NAV = [
  {
    group: null,
    items: [
      { id: "overview", label: "Vue d'ensemble", icon: <svg width="16" height="16" viewBox="0 0 16 16" fill="none"><rect x="1" y="1" width="6" height="6" rx="1.5" stroke="currentColor" strokeWidth="1.5"/><rect x="9" y="1" width="6" height="6" rx="1.5" stroke="currentColor" strokeWidth="1.5"/><rect x="1" y="9" width="6" height="6" rx="1.5" stroke="currentColor" strokeWidth="1.5"/><rect x="9" y="9" width="6" height="6" rx="1.5" stroke="currentColor" strokeWidth="1.5"/></svg> },
      { id: "stats",    label: "Statistiques",   icon: <svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M2 12l4-4 3 3 5-6" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/></svg> },
    ],
  },
  {
    group: "Gestion",
    items: [
      { id: "users",     label: "Utilisateurs", kpi: "users",    icon: <svg width="16" height="16" viewBox="0 0 16 16" fill="none"><circle cx="6" cy="5" r="2.5" stroke="currentColor" strokeWidth="1.5"/><path d="M1 13c0-2.5 2-4 5-4s5 1.5 5 4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/><path d="M11 7c1.5 0 3 1 3 3" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/><circle cx="12" cy="4.5" r="1.5" stroke="currentColor" strokeWidth="1.5"/></svg> },
      { id: "documents", label: "Documents",    kpi: "docs",     icon: <svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M4 2h6l4 4v8H4V2z" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round"/><path d="M10 2v4h4" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round"/></svg> },
      { id: "services",  label: "Services",     kpi: "services", icon: <svg width="16" height="16" viewBox="0 0 16 16" fill="none"><rect x="2" y="5" width="12" height="9" rx="1.5" stroke="currentColor" strokeWidth="1.5"/><path d="M5 5V4a1 1 0 011-1h4a1 1 0 011 1v1" stroke="currentColor" strokeWidth="1.5"/></svg> },
      { id: "bots",      label: "Bots",         kpi: "bots",     icon: <svg width="16" height="16" viewBox="0 0 16 16" fill="none"><rect x="3" y="5" width="10" height="8" rx="2" stroke="currentColor" strokeWidth="1.5"/><path d="M6 5V3.5a2 2 0 014 0V5" stroke="currentColor" strokeWidth="1.5"/><circle cx="6" cy="9" r="1" fill="currentColor"/><circle cx="10" cy="9" r="1" fill="currentColor"/></svg> },
    ],
  },
  {
    group: "Système",
    items: [
      { id: "conversations", label: "Conversations", kpi: "convs", icon: <svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M14 10a2 2 0 01-2 2H5l-3 3V4a2 2 0 012-2h8a2 2 0 012 2v6z" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round"/></svg> },
      { id: "logs",          label: "Logs",                        icon: <svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M2 4h12M2 8h8M2 12h6" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/></svg> },
    ],
  },
];

const TITLES = { overview: "Vue d'ensemble", stats: "Statistiques", users: "Utilisateurs", documents: "Documents", services: "Services", bots: "Bots", conversations: "Conversations", logs: "Logs d'activité" };

function getInitials(name) {
  if (!name) return "?";
  return name.split(" ").map(w => w[0]).join("").slice(0, 2).toUpperCase();
}

function KpiCard({ label, value, color, bg, icon }) {
  return (
    <motion.div className="kpi-card"
      initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}
      whileHover={{ y: -3, boxShadow: "0 8px 24px rgba(0,0,0,0.1)" }}>
      <div className="kpi-icon-wrap" style={{ background: bg, color }}>{icon}</div>
      <div className="kpi-value" style={{ color }}>{value ?? "—"}</div>
      <div className="kpi-label">{label}</div>
    </motion.div>
  );
}

export default function Admin({ user, token, onLogout }) {
  const [tab,         setTab]         = useState("overview");
  const [kpis,        setKpis]        = useState({});
  const [showUserMenu, setShowUserMenu] = useState(false);

  useEffect(() => {
    Promise.all([
      listDocuments(token).catch(() => []),
      listUsers(token).catch(() => []),
      listServices(token).catch(() => []),
      listConversations(token).catch(() => []),
      listBots(token).catch(() => []),
    ]).then(([docs, users, services, convs, bots]) => {
      setKpis({ docs: docs.length, users: users.length, services: services.length, convs: convs.length, bots: bots.length });
    });
  }, []);

  const TABS = {
    overview:      <OverviewTab token={token} />,
    stats:         <StatsTab         token={token} />,
    documents:     <DocumentsTab     token={token} />,
    users:         <UsersTab         token={token} />,
    services:      <ServicesTab      token={token} />,
    bots:          <BotsTab          token={token} />,
    conversations: <ConversationsTab token={token} />,
    logs:          <LogsTab          token={token} />,
  };

  return (
    <div className="admin-layout">
      <aside className="admin-sidebar">
        <div className="admin-sidebar-logo">
          <svg width="26" height="28" viewBox="0 0 40 44" fill="none">
            <path d="M20 1L3 8.5V22c0 10.5 7.5 19.5 17 21.5C30.5 41.5 38 32.5 38 22V8.5L20 1z" fill="#5c4ed8"/>
            <rect x="11" y="14" width="15" height="2.5" rx="1.25" fill="rgba(255,255,255,0.9)"/>
            <rect x="11" y="20" width="11" height="2.5" rx="1.25" fill="rgba(255,255,255,0.9)"/>
            <rect x="11" y="26" width="7" height="2.5" rx="1.25" fill="rgba(255,255,255,0.9)"/>
          </svg>
          <span className="admin-sidebar-brand">RegBot</span>
          <span className="admin-logo-tag">Admin</span>
        </div>

        <nav className="admin-nav">
          {NAV.map((section, si) => (
            <div key={si} className="admin-nav-group">
              {section.group && <span className="admin-nav-group-label">{section.group}</span>}
              {section.items.map((item, ii) => (
                <motion.button key={item.id}
                  className={`admin-nav-item ${tab === item.id ? "active" : ""}`}
                  onClick={() => setTab(item.id)}
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: (si * 4 + ii) * 0.04 }}
                  whileTap={{ scale: 0.97 }}
                >
                  <span className="admin-nav-icon">{item.icon}</span>
                  <span className="admin-nav-label">{item.label}</span>
                </motion.button>
              ))}
            </div>
          ))}
        </nav>

        <div className="admin-sidebar-user-wrap">
          <button className="admin-sidebar-user" onClick={() => setShowUserMenu(v => !v)}>
            <div className="admin-avatar">{getInitials(user?.nom || user?.email)}</div>
            <div className="admin-sidebar-user-info">
              <span className="admin-user-name">{user?.nom || user?.email}</span>
              <span className="admin-user-role">Accès complet</span>
            </div>
            <svg width="14" height="14" viewBox="0 0 16 16" fill="none" style={{ flexShrink: 0, color: "#aaa" }}>
              <path d={showUserMenu ? "M4 10l4-4 4 4" : "M4 6l4 4 4-4"} stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </button>

          <AnimatePresence>
            {showUserMenu && (
              <motion.div
                className="admin-user-menu"
                initial={{ opacity: 0, y: 6, scale: 0.97 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                exit={{ opacity: 0, y: 6, scale: 0.97 }}
                transition={{ duration: 0.15 }}
              >
                <button className="admin-user-menu-item admin-user-menu-logout"
                  onClick={() => { setShowUserMenu(false); onLogout(); }}>
                  <svg width="14" height="14" viewBox="0 0 16 16" fill="none">
                    <path d="M6 14H3a1 1 0 01-1-1V3a1 1 0 011-1h3M10 11l3-3-3-3M13 8H6"
                      stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
                  </svg>
                  Se déconnecter
                </button>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </aside>

      <div className="admin-main">
        <header className="admin-topbar">
          <div className="admin-breadcrumb">
            <span className="admin-breadcrumb-root">Admin</span>
            <span className="admin-breadcrumb-sep">/</span>
            <span className="admin-breadcrumb-page">{TITLES[tab]}</span>
          </div>
        </header>

        <div className="admin-content">
          <AnimatePresence mode="wait">
            <motion.div key={tab}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -6 }}
              transition={{ duration: 0.18 }}
            >
              {TABS[tab]}
            </motion.div>
          </AnimatePresence>
        </div>
      </div>
    </div>
  );
}
