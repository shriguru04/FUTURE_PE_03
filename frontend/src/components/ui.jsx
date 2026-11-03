import { useState } from "react";

export const Field = ({ label, children, hint }) => (
  <label className="field"><span>{label}</span>{children}{hint && <small>{hint}</small>}</label>
);
export const Empty = ({ children }) => <div className="empty">{children}</div>;
export const Loading = () => <div className="empty">Loading…</div>;
export const Badge = ({ kind, children }) => <span className={`badge ${kind || ""}`}>{children}</span>;

export function useAction(notify) {
  const [busy, setBusy] = useState(false);
  const run = async (fn, okMsg) => {
    setBusy(true);
    try { const r = await fn(); if (okMsg) notify(okMsg); return r; }
    catch (e) { notify(e.message || "Something went wrong", "err"); }
    finally { setBusy(false); }
  };
  return [busy, run];
}

export function Confirm({ text, onYes, children, className = "btn danger" }) {
  const [open, setOpen] = useState(false);
  if (!open) return <button className={className} onClick={() => setOpen(true)}>{children}</button>;
  return (
    <span className="confirm"><span>{text}</span>
      <button className="btn danger" onClick={() => { setOpen(false); onYes(); }}>Yes, continue</button>
      <button className="btn" onClick={() => setOpen(false)}>Cancel</button></span>
  );
}
export const list = (s) => s.split(",").map((x) => x.trim()).filter(Boolean);
export const NeedBusiness = ({ business, children }) =>
  business ? children : <Empty>Create or select a business profile first (Businesses page).</Empty>;
