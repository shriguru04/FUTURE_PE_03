import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { get, post } from "../services/api";
import { useApp } from "../context/AppContext";
import { Badge, Empty, Loading, NeedBusiness, useAction } from "../components/ui";

export default function Clusters() {
  const { business, notify } = useApp();
  const nav = useNavigate();
  const [cl, setCl] = useState(null);
  const [busy, run] = useAction(notify);
  const load = () => business && get(`/clusters?business_id=${business.id}`).then(setCl).catch((e) => notify(e.message, "err"));
  useEffect(() => { load(); }, [business]); // eslint-disable-line
  const regen = () => run(async () => { await post("/clusters/generate", { business_id: business.id }); await load(); }, "Clusters regenerated");
  return (<NeedBusiness business={business}><h2>Content clusters</h2>
    <p className="muted">Clusters are grouped by word overlap (heuristic). Review pillar choices and cannibalization warnings before publishing.</p>
    <button className="btn" onClick={regen} disabled={busy}>Regenerate from keywords</button>
    {!cl ? <Loading /> : cl.length === 0 ? <Empty>No clusters yet. Add keywords, then build clusters.</Empty> :
      cl.map((c) => (<div className="card" key={c.id}><h3>{c.name} <small className="muted">pillar keyword: {c.pillar_keyword}</small></h3>
        {c.cannibalization.map((w, i) => <div className="warn" key={i}>⚠ Possible cannibalization: <b>{w.keywords.join(" / ")}</b>. {w.explanation}</div>)}
        <ul className="tree">{c.articles.map((a) => <li key={a.id} className={a.is_pillar ? "pillar" : ""}>
          {a.is_pillar ? <Badge kind="info">pillar</Badge> : <Badge>cluster</Badge>} <button className="link" onClick={() => nav(`/articles?open=${a.id}`)}>{a.title}</button>
          <small className="muted"> · {a.primary_keyword} · {a.intent.replace("_", " ")} · /{a.slug} · {a.status}</small></li>)}</ul></div>))}</NeedBusiness>);
}
