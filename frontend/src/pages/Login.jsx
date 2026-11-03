import { useState } from "react";
import { post } from "../services/api";
import { useApp } from "../context/AppContext";
import { Field } from "../components/ui";

export default function Login() {
  const { setUser } = useApp();
  const [mode, setMode] = useState("login");
  const [f, setF] = useState({ email: "", password: "", role: "business_owner" });
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);
  const submit = async (e) => {
    e.preventDefault(); setErr("");
    if (!/^\S+@\S+\.\S+$/.test(f.email)) return setErr("Enter a valid email address.");
    if (mode === "register" && f.password.length < 10) return setErr("Password must be at least 10 characters.");
    setBusy(true);
    try { setUser(await post(mode === "login" ? "/auth/login" : "/auth/register", mode === "login" ? { email: f.email, password: f.password } : f)); }
    catch (e2) { setErr(e2.message); } finally { setBusy(false); }
  };
  return (
    <div className="auth"><form className="card" onSubmit={submit}>
      <h2>{mode === "login" ? "Sign in" : "Create account"}</h2>
      <Field label="Email"><input type="email" value={f.email} onChange={(e) => setF({ ...f, email: e.target.value })} required autoComplete="email" /></Field>
      <Field label="Password"><input type="password" value={f.password} onChange={(e) => setF({ ...f, password: e.target.value })} required autoComplete={mode === "login" ? "current-password" : "new-password"} /></Field>
      {mode === "register" && <Field label="I am a"><select value={f.role} onChange={(e) => setF({ ...f, role: e.target.value })}><option value="business_owner">Business owner</option><option value="seo_professional">SEO professional</option></select></Field>}
      {err && <p className="error" role="alert">{err}</p>}
      <button className="btn primary" disabled={busy}>{busy ? "Please wait…" : mode === "login" ? "Sign in" : "Register"}</button>
      <button type="button" className="link" onClick={() => { setMode(mode === "login" ? "register" : "login"); setErr(""); }}>{mode === "login" ? "Need an account? Register" : "Have an account? Sign in"}</button>
    </form></div>
  );
}
