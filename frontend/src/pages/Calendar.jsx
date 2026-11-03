import { useCallback, useEffect, useState } from "react";
import { del, get, patch, post } from "../services/api";
import { useApp } from "../context/AppContext";
import { Confirm, Empty, Field, NeedBusiness, useAction } from "../components/ui";

const STATUSES = ["idea", "planned", "outline", "draft", "in_review", "approved", "published", "archived"];

export default function Calendar() {
  const { business, notify } = useApp();
  const [rows, setRows] = useState(null);
  const [arts, setArts] = useState([]);
  const [f, setF] = useState({ topic: "", planned_date: "", article_id: "", priority: 50 });
  const [busy, run] = useAction(notify);
  const load = useCallback(() => { if (!business) return;
    get(`/calendar?business_id=${business.id}`).then(setRows).catch((e) => notify(e.message, "err"));
    get(`/content/articles?business_id=${business.id}`).then(setArts).catch(() => {}); }, [business, notify]);
  useEffect(load, [load]);
  const add = (e) => { e.preventDefault(); const art = arts.find((a) => a.id === Number(f.article_id));
    run(async () => { await post("/calendar", { business_id: business.id, topic: f.topic || art?.title || "", article_id: art?.id ?? null, cluster_id: art?.cluster_id ?? null,
      primary_keyword: art?.primary_keyword || "", priority: Number(f.priority), planned_date: f.planned_date ? new Date(f.planned_date).toISOString() : null });
      setF({ topic: "", planned_date: "", article_id: "", priority: 50 }); load(); }, "Entry added"); };
  return (<NeedBusiness business={business}><h2>Content calendar</h2>
    <form className="card form" onSubmit={add}><div className="cols"><Field label="Topic"><input value={f.topic} onChange={(e) => setF({ ...f, topic: e.target.value })} /></Field>
      <Field label="Article (optional)"><select value={f.article_id} onChange={(e) => setF({ ...f, article_id: e.target.value })}><option value="">—</option>{arts.map((a) => <option key={a.id} value={a.id}>{a.title}</option>)}</select></Field>
      <Field label="Planned date"><input type="date" value={f.planned_date} onChange={(e) => setF({ ...f, planned_date: e.target.value })} /></Field>
      <Field label="Priority (0-100)"><input type="number" min={0} max={100} value={f.priority} onChange={(e) => setF({ ...f, priority: e.target.value })} /></Field></div>
      <button className="btn primary" disabled={busy || (!f.topic && !f.article_id)}>Add to calendar</button></form>
    {!rows ? null : rows.length === 0 ? <Empty>Nothing scheduled.</Empty> : <div className="scroll"><table><thead><tr><th>Date</th><th>Topic</th><th>Keyword</th><th>Priority</th><th>Status</th><th>Published</th><th /></tr></thead><tbody>
      {rows.map((r) => <tr key={r.id}><td>{r.planned_date ? r.planned_date.slice(0, 10) : "Unscheduled"}</td><td>{r.topic}</td><td>{r.primary_keyword}</td><td>{r.priority}</td>
        <td><select value={r.status} onChange={(e) => run(async () => { await patch(`/calendar/${r.id}`, { status: e.target.value }); load(); })}>{STATUSES.map((s) => <option key={s}>{s}</option>)}</select></td>
        <td>{r.published_date ? r.published_date.slice(0, 10) : "—"}</td><td><Confirm text="Remove?" onYes={() => run(async () => { await del(`/calendar/${r.id}`); load(); })}>Remove</Confirm></td></tr>)}</tbody></table></div>}</NeedBusiness>);
}
