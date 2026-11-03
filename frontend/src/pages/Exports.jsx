import { useCallback, useEffect, useState } from "react";
import { get, post } from "../services/api";
import { useApp } from "../context/AppContext";
import { Empty, Field, NeedBusiness, useAction } from "../components/ui";

const FORMATS = [["md", "Markdown (SEO Blog Pack)"], ["txt", "Plain text"], ["docx", "Word (.docx)"], ["pdf", "PDF"], ["csv_keywords", "CSV: keywords"], ["csv_calendar", "CSV: content calendar"]];

export default function Exports() {
  const { business, notify } = useApp();
  const [arts, setArts] = useState([]);
  const [hist, setHist] = useState([]);
  const [f, setF] = useState({ format: "md", article_id: "" });
  const [busy, run] = useAction(notify);
  const load = useCallback(() => { if (!business) return;
    get(`/content/articles?business_id=${business.id}`).then(setArts).catch(() => {});
    get(`/exports?business_id=${business.id}`).then(setHist).catch((e) => notify(e.message, "err")); }, [business, notify]);
  useEffect(load, [load]);
  return (<NeedBusiness business={business}><h2>Export SEO Blog Pack</h2>
    <p className="muted">Exports read the saved version of your content. Select an article to include its outline, body, audit and claims review.</p>
    <div className="card form"><div className="cols"><Field label="Format"><select value={f.format} onChange={(e) => setF({ ...f, format: e.target.value })}>{FORMATS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}</select></Field>
      <Field label="Article (for pack formats)"><select value={f.article_id} onChange={(e) => setF({ ...f, article_id: e.target.value })}><option value="">None (business-level sections only)</option>{arts.map((a) => <option key={a.id} value={a.id}>{a.title}</option>)}</select></Field></div>
      <button className="btn primary" disabled={busy} onClick={() => run(async () => { await post("/exports", { business_id: business.id, format: f.format, article_id: f.article_id ? Number(f.article_id) : null }); load(); }, "Export created")}>Create export</button></div>
    <h3>History</h3>{hist.length === 0 ? <Empty>No exports yet.</Empty> : <ul>{hist.map((h) => <li key={h.id}><a href={`/api/v1/exports/${h.id}`}>{h.filename}</a> <small className="muted">{h.format} · {(h.size / 1024).toFixed(1)} KB · {h.created_at.slice(0, 16).replace("T", " ")}</small></li>)}</ul>}</NeedBusiness>);
}
