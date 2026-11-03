import { useState } from "react";
import { NavLink, Outlet } from "react-router-dom";
import { useApp } from "../context/AppContext";

const NAV = [["/", "Dashboard"], ["/businesses", "Businesses"], ["/keywords", "Keywords"], ["/clusters", "Content clusters"], ["/articles", "Articles & editor"],
  ["/links", "Internal links"], ["/local", "Local SEO"], ["/calendar", "Calendar"], ["/exports", "Exports"], ["/settings", "Settings"]];

export default function AppLayout() {
  const { user, businesses, bid, setBid, logout, toast } = useApp();
  const [open, setOpen] = useState(false);
  return (
    <div className="shell">
      <button className="burger" onClick={() => setOpen(!open)} aria-label="Menu">☰</button>
      <aside className={open ? "side open" : "side"}>
        <h1>SEO Cluster Studio</h1>
        <select value={bid ?? ""} onChange={(e) => setBid(Number(e.target.value))} aria-label="Business">
          {businesses.length === 0 && <option value="">No business yet</option>}
          {businesses.map((b) => <option key={b.id} value={b.id}>{b.name}</option>)}
        </select>
        <nav onClick={() => setOpen(false)}>{NAV.map(([to, label]) => <NavLink key={to} to={to} end={to === "/"}>{label}</NavLink>)}</nav>
        <div className="who"><small>{user.email} · {user.role.replace("_", " ")}</small><button className="btn" onClick={logout}>Sign out</button></div>
      </aside>
      <main><Outlet /></main>
      {toast && <div className={`toast ${toast.kind}`} role="status">{toast.message}</div>}
    </div>
  );
}
