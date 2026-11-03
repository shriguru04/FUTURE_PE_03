import { useState } from "react";
import { del, patch, post } from "../services/api";
import { useApp } from "../context/AppContext";
import { Confirm, Field, list, useAction } from "../components/ui";

const blank = { name: "", website_url: "", niche: "", services: "", audience: "", country: "", city: "", brand_voice: "", conversion_goal: "", competitors: "", target_keywords: "" };

export default function Businesses() {
  const { businesses, loadBusinesses, notify, setBid } = useApp();
  const [f, setF] = useState(blank);
  const [editing, setEditing] = useState(null);
  const [busy, run] = useAction(notify);
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });
  const payload = () => ({ ...f, website_url: f.website_url || null, services: list(f.services), competitors: list(f.competitors), target_keywords: list(f.target_keywords) });
  const save = (e) => { e.preventDefault(); if (!f.name.trim()) return notify("Business name is required", "err");
    run(async () => { const b = editing ? await patch(`/businesses/${editing}`, payload()) : await post("/businesses", payload()); await loadBusinesses(); setBid(b.id); setF(blank); setEditing(null); }, "Business saved"); };
  const edit = (b) => { setEditing(b.id); setF({ ...blank, ...b, website_url: b.website_url || "", services: b.services.join(", "), competitors: b.competitors.join(", "), target_keywords: b.target_keywords.join(", ") }); };
  return (<><h2>Business profiles</h2>
    <form className="card form" onSubmit={save}>
      <div className="cols">
        <Field label="Business name *"><input value={f.name} onChange={set("name")} /></Field>
        <Field label="Website URL"><input value={f.website_url} onChange={set("website_url")} placeholder="https://" /></Field>
        <Field label="Industry / niche"><input value={f.niche} onChange={set("niche")} /></Field>
        <Field label="Services (comma separated)"><input value={f.services} onChange={set("services")} /></Field>
        <Field label="Target audience"><input value={f.audience} onChange={set("audience")} /></Field>
        <Field label="Country"><input value={f.country} onChange={set("country")} /></Field>
        <Field label="City / service area"><input value={f.city} onChange={set("city")} /></Field>
        <Field label="Brand voice"><input value={f.brand_voice} onChange={set("brand_voice")} /></Field>
        <Field label="Primary conversion goal"><input value={f.conversion_goal} onChange={set("conversion_goal")} /></Field>
        <Field label="Competitors (comma separated)"><input value={f.competitors} onChange={set("competitors")} /></Field>
        <Field label="Target keywords (comma separated)"><input value={f.target_keywords} onChange={set("target_keywords")} /></Field>
      </div>
      <div><button className="btn primary" disabled={busy}>{editing ? "Update business" : "Create business"}</button>
        {editing && <button type="button" className="btn" onClick={() => { setEditing(null); setF(blank); }}>Cancel</button>}</div>
    </form>
    {businesses.length === 0 ? <p className="empty">No businesses yet.</p> : businesses.map((b) => (
      <div className="card row" key={b.id}>
        <div><b>{b.name}</b><div className="muted">{b.niche} · {b.city} · context: {b.context_source === "crawled" ? "homepage fetched" : "manual only"}</div></div>
        <div className="actions">
          <button className="btn" onClick={() => edit(b)}>Edit</button>
          {b.website_url && <button className="btn" disabled={busy} onClick={() => run(async () => { const r = await post(`/businesses/${b.id}/analyze-website`); await loadBusinesses(); notify(r.note); })}>Fetch homepage</button>}
          <Confirm text="Delete this business and all its content?" onYes={() => run(async () => { await del(`/businesses/${b.id}`); await loadBusinesses(); }, "Deleted")}>Delete</Confirm>
        </div></div>))}</>);
}
