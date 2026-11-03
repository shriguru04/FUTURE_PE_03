import { useCallback, useEffect, useState } from "react";
import { get, patch, post } from "../services/api";
import { useApp } from "../context/AppContext";
import { Badge, Empty, Field, Loading, NeedBusiness, useAction } from "../components/ui";

const INTENTS = ["informational", "navigational", "commercial_investigation", "transactional"];

export default function Keywords() {
  const { business, notify } = useApp();
  const [rows, setRows] = useState(null);
  const [f, setF] = useState({ seed: "", service: "", audience: "", location: "", use_ai: false });
  const [filter, setFilter] = useState({ intent: "", q: "" });
  const [busy, run] = useAction(notify);
  const load = useCallback(() => {
    if (!business) return;
    const qs = new URLSearchParams({ business_id: business.id, ...(filter.intent && { intent: filter.intent }), ...(filter.q && { q: filter.q }) });
    get("/keywords?" + qs).then(setRows).catch((e) => notify(e.message, "err"));
  }, [business, filter, notify]);
  useEffect(load, [load]);
  const research = (e) => { e.preventDefault(); run(async () => { const r = await post("/keywords/research", { business_id: business.id, ...f });
    notify(`${r.created.length} new keywords. ${r.source_note}`); load(); }); };
  const onFile = (e) => { const file = e.target.files[0]; if (!file) return;
    if (file.size > 400_000) return notify("CSV too large (400 KB max)", "err");
    const rd = new FileReader(); rd.onload = () => run(async () => { const r = await post("/keywords/import", { business_id: business.id, csv_text: rd.result });
      notify(`Imported ${r.imported}, skipped ${r.skipped_duplicates}${r.errors.length ? `, ${r.errors.length} row errors` : ""}`); load(); }); rd.readAsText(file); e.target.value = ""; };
  const setIntent = (k, intent) => run(async () => { await patch(`/keywords/${k.id}`, { intent }); load(); }, "Intent corrected");
  const cluster = () => run(async () => { await post("/clusters/generate", { business_id: business.id }); }, "Clusters generated — see Content clusters");
  return (<NeedBusiness business={business}><h2>Keyword research</h2>
    <p className="muted">Suggestions come from template expansion (and an LLM if enabled), not search-engine data. Volume, difficulty and CPC are shown as “Unavailable”.</p>
    <form className="card form" onSubmit={research}><div className="cols">
      <Field label="Seed keyword"><input value={f.seed} onChange={(e) => setF({ ...f, seed: e.target.value })} /></Field>
      <Field label="Service / product" hint="Defaults to the profile's services"><input value={f.service} onChange={(e) => setF({ ...f, service: e.target.value })} /></Field>
      <Field label="Audience"><input value={f.audience} onChange={(e) => setF({ ...f, audience: e.target.value })} /></Field>
      <Field label="Location"><input value={f.location} onChange={(e) => setF({ ...f, location: e.target.value })} /></Field></div>
      <label><input type="checkbox" checked={f.use_ai} onChange={(e) => setF({ ...f, use_ai: e.target.checked })} /> Also ask the AI provider for ideas</label>
      <div><button className="btn primary" disabled={busy}>Generate suggestions</button> <label className="btn">Import CSV<input type="file" accept=".csv,text/csv" hidden onChange={onFile} /></label>
        <button type="button" className="btn" disabled={busy || !rows?.length} onClick={cluster}>Build clusters</button></div></form>
    <div className="filters"><select value={filter.intent} onChange={(e) => setFilter({ ...filter, intent: e.target.value })}><option value="">All intents</option>{INTENTS.map((i) => <option key={i}>{i}</option>)}</select>
      <input placeholder="Search…" value={filter.q} onChange={(e) => setFilter({ ...filter, q: e.target.value })} /></div>
    {!rows ? <Loading /> : rows.length === 0 ? <Empty>No keywords yet.</Empty> :
      <div className="scroll"><table><thead><tr><th>Keyword</th><th>Intent (editable)</th><th>Funnel</th><th>Relevance</th><th>Content type</th><th>Priority</th><th>Source</th><th>Volume / KD</th></tr></thead><tbody>
        {rows.map((k) => <tr key={k.id}><td>{k.phrase}{k.is_local && <Badge>local</Badge>}</td>
          <td><select value={k.intent} title={k.intent_explanation} onChange={(e) => setIntent(k, e.target.value)}>{INTENTS.map((i) => <option key={i}>{i}</option>)}</select>{k.intent_overridden && <Badge>manual</Badge>}
            <details><summary>why?</summary><small>{k.intent_explanation}</small></details></td>
          <td>{k.funnel_stage}</td><td>{k.relevance}</td><td>{k.content_type}</td><td>{k.priority}</td><td>{k.source}</td><td>Unavailable</td></tr>)}</tbody></table></div>}</NeedBusiness>);
}
