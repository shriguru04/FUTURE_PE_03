import { useEffect, useState } from "react";
import { get, patch } from "../services/api";
import { useApp } from "../context/AppContext";

export default function Settings() {
  const { user, notify } = useApp();
  const [users, setUsers] = useState([]);
  const [health, setHealth] = useState(null);
  const isAdmin = user.role === "admin";
  const load = () => { get("/admin/users").then(setUsers).catch(() => {}); get("/admin/health").then(setHealth).catch(() => {}); };
  useEffect(() => { if (isAdmin) load(); }, [isAdmin]); // eslint-disable-line
  const upd = async (id, body) => { try { await patch(`/admin/users/${id}`, body); load(); notify("User updated"); } catch (e) { notify(e.message, "err"); } };
  return (<><h2>Settings</h2><div className="card"><p><b>{user.email}</b> · role: {user.role.replace("_", " ")}</p>
    <p className="muted">AI provider, model and API keys are configured through server environment variables, never in the browser or database.</p></div>
    {isAdmin && (<><h3>System</h3>{health && <div className="card">Database: {health.database} · AI provider: {health.ai_provider} · model: {health.ai_model || "—"} · key configured: {String(health.ai_key_configured)}</div>}
      <h3>Users</h3><div className="scroll"><table><thead><tr><th>Email</th><th>Role</th><th>Active</th></tr></thead><tbody>{users.map((u) => <tr key={u.id}><td>{u.email}</td>
        <td><select value={u.role} onChange={(e) => upd(u.id, { role: e.target.value })}><option value="business_owner">business_owner</option><option value="seo_professional">seo_professional</option><option value="admin">admin</option></select></td>
        <td><input type="checkbox" checked={u.is_active} onChange={(e) => upd(u.id, { is_active: e.target.checked })} /></td></tr>)}</tbody></table></div></>)}</>);
}
