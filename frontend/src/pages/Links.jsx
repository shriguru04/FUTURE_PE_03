import { useEffect, useState } from "react";
import { get, post } from "../services/api";
import { useApp } from "../context/AppContext";
import { Badge, Empty, NeedBusiness, useAction } from "../components/ui";

export default function Links() {
  const { business, notify } = useApp();
  const [data, setData] = useState(null);
  const [complete, setComplete] = useState(false);
  const [busy, run] = useAction(notify);
  useEffect(() => { if (business) get(`/internal-links?business_id=${business.id}`).then((r) => setData({ recommendations: r, issues: [] })).catch(() => {}); }, [business]);
  const gen = () => run(async () => setData(await post("/internal-links/recommend", { business_id: business.id, sitemap_complete: complete })), "Recommendations generated");
  return (<NeedBusiness business={business}><h2>Internal-linking workspace</h2>
    <p className="muted">Targets without a published, user-entered URL are labelled “proposed future page”. No URLs are invented.</p>
    <label><input type="checkbox" checked={complete} onChange={(e) => setComplete(e.target.checked)} /> My saved pages/articles are the complete site inventory (enables “comprehensive” orphan wording)</label>{" "}
    <button className="btn primary" disabled={busy} onClick={gen}>Generate recommendations</button>
    {data?.coverage_note && <div className="note">{data.coverage_note}</div>}
    {data?.issues?.length > 0 && <div className="card"><h3>Issues</h3><ul>{data.issues.map((i, k) => <li key={k}><Badge>{i.type}</Badge> {i.message}</li>)}</ul></div>}
    {!data || data.recommendations.length === 0 ? <Empty>No recommendations yet (need at least two articles in a cluster).</Empty> :
      <div className="scroll"><table><thead><tr><th>Source</th><th>Target</th><th>Anchor</th><th>Section</th><th>Relation</th><th>Status</th><th>Reason</th></tr></thead><tbody>
        {data.recommendations.map((r, i) => <tr key={i}><td>#{r.source_article_id}</td><td>{r.target_url || (r.target_article_id ? `article #${r.target_article_id}` : `page #${r.target_page_id}`)}</td><td>{r.anchor_text}</td><td>{r.section}</td><td>{r.relation}</td>
          <td><Badge>{r.status.replaceAll("_", " ")}</Badge></td><td>{r.reason}</td></tr>)}</tbody></table></div>}</NeedBusiness>);
}
