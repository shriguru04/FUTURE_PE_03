import { useCallback, useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { del, get, patch, post } from "../services/api";
import { useApp } from "../context/AppContext";
import { Badge, Confirm, Empty, Field, Loading, NeedBusiness, useAction } from "../components/ui";

const STATUSES = ["idea", "planned", "outline", "draft", "in_review", "approved", "published", "archived"];
const LABEL = { passed: "Passed", needs_improvement: "Needs improvement", not_checked: "Not checked", requires_review: "Requires human review" };
const METHOD = { verified: "automatically verified", heuristic: "heuristic", ai_assisted: "AI-assisted", manual: "manual review" };

function AuditPanel({ audit }) {
  if (!audit) return <Empty>No audit yet. Click “Run SEO audit”.</Empty>;
  return (<div className="card"><h3>SEO checklist {audit.score != null && <Badge kind="info">internal score {audit.score}/100</Badge>}</h3>
    <small className="muted">{audit.disclaimer}</small>
    {["needs_improvement", "requires_review", "not_checked", "passed"].map((st) => { const items = audit.checks.filter((c) => c.status === st); return items.length ? (
      <div key={st}><h4>{LABEL[st]} ({items.length})</h4>{items.map((c) => <details key={c.id} className={`check ${st}`}><summary>{c.label} <Badge>{METHOD[c.method]}</Badge></summary>
        <p>{c.explanation}</p>{c.flagged?.length > 0 && <ul>{c.flagged.map((f, i) => <li key={i}>{f}</li>)}</ul>}</details>)}</div>) : null; })}</div>);
}

export default function Articles() {
  const { business, notify } = useApp();
  const [params, setParams] = useSearchParams();
  const [rows, setRows] = useState(null);
  const [filter, setFilter] = useState({ status: "", q: "" });
  const [a, setA] = useState(null);
  const [outlineText, setOutlineText] = useState("");
  const [audit, setAudit] = useState(null);
  const [opts, setOpts] = useState({ target_words: 1200, tone: "professional, clear", reading_level: "general adult" });
  const [newKw, setNewKw] = useState("");
  const [busy, run] = useAction(notify);

  const load = useCallback(() => {
    if (!business) return;
    const qs = new URLSearchParams({ business_id: business.id, ...(filter.status && { status: filter.status }), ...(filter.q && { q: filter.q }) });
    get("/content/articles?" + qs).then(setRows).catch((e) => notify(e.message, "err"));
  }, [business, filter, notify]);
  useEffect(load, [load]);
  const open = useCallback(async (id) => {
    const art = await get(`/content/articles/${id}`); setA(art); setOutlineText(art.outline && Object.keys(art.outline).length ? JSON.stringify(art.outline, null, 2) : "");
    const audits = await get(`/seo/audits?article_id=${id}`); setAudit(audits[0] ? await get(`/seo/audits/${audits[0].id}`) : null); }, []);
  useEffect(() => { const id = params.get("open"); if (id) open(id).catch((e) => notify(e.message, "err")); }, [params, open, notify]);

  const set = (k) => (e) => setA({ ...a, [k]: e.target.value });
  const save = () => run(async () => {
    let outline; if (outlineText.trim()) { try { outline = JSON.parse(outlineText); } catch { throw new Error("Outline JSON is invalid"); } }
    const r = await patch(`/content/articles/${a.id}`, { title: a.title, seo_title: a.seo_title, meta_description: a.meta_description, slug: a.slug, status: a.status,
      body_markdown: a.body_markdown, cta_text: a.cta_text, target_url: a.target_url || null, ...(outline && { outline }) });
    setA(r); load(); }, "Saved");
  const genOutline = () => run(async () => { const r = await post("/content/outlines/generate", { article_id: a.id }); setA(r); setOutlineText(JSON.stringify(r.outline, null, 2)); load(); }, "Outline generated");
  const genArticle = () => run(async () => { if (outlineText.trim()) await save2(); const r = await post("/content/articles/generate", { article_id: a.id, ...opts }); setA(r.article); setAudit(r.audit); load(); }, "Article generated and audited");
  const save2 = async () => { const o = JSON.parse(outlineText); await patch(`/content/articles/${a.id}`, { outline: o }); };
  const runAudit = () => run(async () => { await save(); setAudit(await post("/seo/audit", { article_id: a.id })); }, "Audit complete");
  const create = () => run(async () => { const r = await post("/content/briefs", { business_id: business.id, primary_keyword: newKw }); setNewKw(""); load(); setParams({ open: r.id }); }, "Brief created");

  return (<NeedBusiness business={business}><h2>Articles &amp; editor</h2>
    {!a ? (<>
      <div className="filters"><select value={filter.status} onChange={(e) => setFilter({ ...filter, status: e.target.value })}><option value="">All statuses</option>{STATUSES.map((s) => <option key={s}>{s}</option>)}</select>
        <input placeholder="Search title or keyword" value={filter.q} onChange={(e) => setFilter({ ...filter, q: e.target.value })} />
        <input placeholder="New brief: primary keyword" value={newKw} onChange={(e) => setNewKw(e.target.value)} /><button className="btn" disabled={!newKw.trim() || busy} onClick={create}>Create brief</button></div>
      {!rows ? <Loading /> : rows.length === 0 ? <Empty>No articles. Build clusters or create a brief.</Empty> :
        <div className="scroll"><table><thead><tr><th>Title</th><th>Keyword</th><th>Status</th><th>Intent</th><th /></tr></thead><tbody>{rows.map((r) => <tr key={r.id}><td>{r.title}{r.is_pillar && <Badge kind="info">pillar</Badge>}</td>
          <td>{r.primary_keyword}</td><td><Badge>{r.status}</Badge></td><td>{r.intent.replace("_", " ")}</td><td><button className="btn" onClick={() => setParams({ open: r.id })}>Open</button></td></tr>)}</tbody></table></div>}
    </>) : (<>
      <button className="link" onClick={() => { setA(null); setAudit(null); setParams({}); }}>← All articles</button>
      {a.generation_meta?.mock && <div className="warn">Generated in MOCK mode: this is a scaffold, not finished prose. Configure AI_PROVIDER for real drafts.</div>}
      <div className="card form"><div className="cols">
        <Field label="Title / H1 working title"><input value={a.title} onChange={set("title")} /></Field>
        <Field label={`SEO title (${a.seo_title.length})`}><input value={a.seo_title} onChange={set("seo_title")} /></Field>
        <Field label={`Meta description (${a.meta_description.length})`}><input value={a.meta_description} onChange={set("meta_description")} /></Field>
        <Field label="URL slug"><input value={a.slug} onChange={set("slug")} /></Field>
        <Field label="Target URL (only if known)"><input value={a.target_url || ""} onChange={set("target_url")} /></Field>
        <Field label="CTA"><input value={a.cta_text} onChange={set("cta_text")} /></Field>
        <Field label="Status"><select value={a.status} onChange={set("status")}>{STATUSES.map((s) => <option key={s}>{s}</option>)}</select></Field></div>
        <p className="muted">Primary keyword: <b>{a.primary_keyword}</b> · intent: {a.intent.replace("_", " ")} · secondary: {a.secondary_keywords.join(", ") || "—"}</p>
        <Field label="Outline (JSON — editable; the article is generated from this)"><textarea rows={8} value={outlineText} onChange={(e) => setOutlineText(e.target.value)} /></Field>
        <div className="cols"><Field label="Target words"><input type="number" min={300} max={4000} value={opts.target_words} onChange={(e) => setOpts({ ...opts, target_words: Number(e.target.value) })} /></Field>
          <Field label="Tone"><input value={opts.tone} onChange={(e) => setOpts({ ...opts, tone: e.target.value })} /></Field>
          <Field label="Reading level"><input value={opts.reading_level} onChange={(e) => setOpts({ ...opts, reading_level: e.target.value })} /></Field></div>
        <div className="actions"><button className="btn" disabled={busy} onClick={genOutline}>1. Generate outline</button><button className="btn" disabled={busy || !outlineText} onClick={genArticle}>2. Generate article</button>
          <button className="btn primary" disabled={busy} onClick={save}>Save</button><button className="btn" disabled={busy} onClick={runAudit}>Run SEO audit</button>
          <button className="btn" disabled={busy} onClick={() => run(async () => { const d = await post(`/content/articles/${a.id}/duplicate`); setParams({ open: d.id }); }, "Duplicated")}>Duplicate</button>
          <Confirm text="Delete this article?" onYes={() => run(async () => { await del(`/content/articles/${a.id}`); setA(null); setParams({}); load(); }, "Deleted")}>Delete</Confirm></div>
        <Field label="Article body (Markdown — exactly one H1)"><textarea rows={22} value={a.body_markdown} onChange={set("body_markdown")} /></Field>
        {a.sources_to_verify?.length > 0 && <div className="warn"><b>Sources to verify by hand (existence not checked):</b><ul>{a.sources_to_verify.map((s, i) => <li key={i}>{s}</li>)}</ul></div>}
        {a.editorial_notes?.length > 0 && <div className="note"><b>Editorial notes</b><ul>{a.editorial_notes.map((s, i) => <li key={i}>{s}</li>)}</ul></div>}</div>
      <AuditPanel audit={audit} /></>)}</NeedBusiness>);
}
