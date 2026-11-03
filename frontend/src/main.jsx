import React from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { AppProvider, useApp } from "./context/AppContext";
import AppLayout from "./layouts/AppLayout";
import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import Businesses from "./pages/Businesses";
import Keywords from "./pages/Keywords";
import Clusters from "./pages/Clusters";
import Articles from "./pages/Articles";
import Links from "./pages/Links";
import Local from "./pages/Local";
import Calendar from "./pages/Calendar";
import Exports from "./pages/Exports";
import Settings from "./pages/Settings";
import "./styles/app.css";

function Gate() {
  const { user } = useApp();
  if (user === undefined) return <div className="empty">Loading…</div>;
  if (!user) return <Login />;
  return (
    <Routes>
      <Route element={<AppLayout />}>
        <Route index element={<Dashboard />} />
        <Route path="businesses" element={<Businesses />} />
        <Route path="keywords" element={<Keywords />} />
        <Route path="clusters" element={<Clusters />} />
        <Route path="articles" element={<Articles />} />
        <Route path="links" element={<Links />} />
        <Route path="local" element={<Local />} />
        <Route path="calendar" element={<Calendar />} />
        <Route path="exports" element={<Exports />} />
        <Route path="settings" element={<Settings />} />
        <Route path="*" element={<Navigate to="/" />} />
      </Route>
    </Routes>
  );
}
createRoot(document.getElementById("root")).render(<BrowserRouter><AppProvider><Gate /></AppProvider></BrowserRouter>);
