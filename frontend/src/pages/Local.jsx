import { useState } from "react";
import { post } from "../services/api";
import { useApp } from "../context/AppContext";
import { Field, NeedBusiness, useAction } from "../components/ui";

export default function Local() {
  const { business, notify } = useApp();
  const [f, setF] = useState({ service: "", city: "", service_area: "", local_audience: "", primary_keyword: "", local_context: "", facts: "" });
  const [res, setRes] = useState(null);
  const [busy, run] = useAction(notify);
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });
  const submit = (e) => { e.preventDefault(); const facts = f.facts.split("\n").map((s) => s.trim()).filter(Boolean);
    if (f.local_context.length < 80 || facts.length < 2) return notify("Add ≥80 characters of local context and at least 2 specific local facts (one per line).", "err");
    run(async () => setRes(await post("/local-seo/generate", { business_id: business.id, service: f.service, city: f.city, service_area: f.service_area,
      local_audience: f.local_audience, primary_keyword: f.primary_keyword, local_context: f.local_context, local_facts: facts })), "Local assets generated"); };
  const Sec = ({ t, items }) => items?.length ? <div className="card"><h3>{t}</h3><ul>{items.map((x, i) => <li key={i}>{x}</li>)}</ul></div> : null;
  return (<NeedBusiness business={business}><h2>Local SEO</h2>
    <p className="muted">Requires real local facts so pages are not city-name swaps. Nothing here invents reviews, addresses, hours or availability.</p>
    <form className="card form" onSubmit={submit}><div className="cols"><Field label="Service"><input value={f.service} onChange={set("service")} required /></Field>
      <Field label="City"><input value={f.city} onChange={set("city")} required /></Field><Field label="Service area"><input value={f.service_area} onChange={set("service_area")} /></Field>
      <Field label="Local audience"><input value={f.local_audience} onChange={set("local_audience")} /></Field><Field label="Primary keyword"><input value={f.primary_keyword} onChange={set("primary_keyword")} /></Field></div>
      <Field label="Local context (min 80 chars)"><textarea rows={4} value={f.local_context} onChange={set("local_context")} /></Field>
      <Field label="Specific local facts (one per line, min 2)"><textarea rows={4} value={f.facts} onChange={set("facts")} /></Field>
      <button className="btn primary" disabled={busy}>Generate</button></form>
    {res && <>{res.mock && <div className="warn">Mock mode: scaffolds only.</div>}{res.warnings.map((w, i) => <div className="note" key={i}>{w}</div>)}
      <Sec t="Titles" items={res.titles} /><Sec t="Meta descriptions" items={res.meta_descriptions} /><Sec t="Service page outline" items={res.service_page_outline} />
      <Sec t="Local blog outline" items={res.blog_outline} /><Sec t="FAQs" items={res.faqs} /><Sec t="Content ideas" items={res.content_ideas} /><Sec t="CTAs" items={res.ctas} /></>}</NeedBusiness>);
}
