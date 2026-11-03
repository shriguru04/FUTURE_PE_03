import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { get, post } from "../services/api";

const Ctx = createContext(null);
export const useApp = () => useContext(Ctx);

export function AppProvider({ children }) {
  const [user, setUser] = useState(undefined); // undefined = loading, null = signed out
  const [businesses, setBusinesses] = useState([]);
  const [bid, setBid] = useState(null);
  const [toast, setToast] = useState(null);

  const notify = useCallback((message, kind = "ok") => { setToast({ message, kind }); setTimeout(() => setToast(null), 4500); }, []);
  const loadBusinesses = useCallback(async () => {
    const list = await get("/businesses");
    setBusinesses(list);
    setBid((cur) => (list.some((b) => b.id === cur) ? cur : list[0]?.id ?? null));
  }, []);

  useEffect(() => {
    get("/auth/me").then(setUser).catch(() => setUser(null));
  }, []);
  useEffect(() => { if (user) loadBusinesses().catch((e) => notify(e.message, "err")); }, [user, loadBusinesses, notify]);

  const logout = async () => { await post("/auth/logout"); setUser(null); setBusinesses([]); setBid(null); };
  const business = businesses.find((b) => b.id === bid) || null;
  return <Ctx.Provider value={{ user, setUser, businesses, business, bid, setBid, loadBusinesses, logout, notify, toast }}>{children}</Ctx.Provider>;
}
