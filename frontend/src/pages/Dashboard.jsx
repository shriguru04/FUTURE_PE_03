import { useEffect, useState } from "react";
import { get } from "../services/api";
import { useApp } from "../context/AppContext";
import { Loading } from "../components/ui";

export default function Dashboard() {
  const { notify } = useApp();
  const [d, setD] = useState(null);
  useEffect(() => { get("/dashboard").then(setD).catch((e) => notify(e.message, "err")); }, [notify]);
  if (!d) return <Loading />;
  const s = d.by_status || {};
  const cards = [["Businesses", d.businesses], ["Total articles", d.articles_total], ["Planned", s.planned || 0], ["Drafts", s.draft || 0],
    ["Approved", s.approved || 0], ["Keyword clusters", d.clusters], ["Articles with SEO checks to fix", d.needs_attention]];
  return (<><h2>Dashboard</h2><p className="muted">All numbers are counted from your saved records.</p>
    <div className="grid">{cards.map(([k, v]) => <div className="card stat" key={k}><b>{v}</b><span>{k}</span></div>)}</div>
    {d.businesses === 0 && <p className="empty">Start by creating a business profile.</p>}</>);
}
