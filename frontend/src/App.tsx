import { Navigate, NavLink, Outlet, Route, Routes, useNavigate } from "react-router-dom";

import { AuthProvider, useAuth } from "./auth/AuthContext";
import { ProtectedRoute } from "./auth/ProtectedRoute";
import { routeAccess } from "./auth/routeAccess";
import LoginPage from "./pages/LoginPage";
import UnauthorizedPage from "./pages/UnauthorizedPage";
import AssessmentHistoryPage from "./pages/AssessmentHistoryPage";
import { AlertsPage, AnalyticsPage, DashboardPage, ExplainableAIPage, ModelPerformancePage, MonitoringPage, PredictionsPage, RecommendationsPage, ResourcesPage, SettingsPage, WhatIfPage } from "./pages/OperationalPages";

const navigation = [
  ["/dashboard", "Dashboard"], ["/live-monitoring", "Live Monitoring"], ["/predictions", "Predictions"],
  ["/assessment-history", "Assessment History"],
  ["/resources", "Resources"], ["/alerts", "Alerts"], ["/recommendations", "Recommendations"], ["/analytics", "Analytics"],
  ["/explainable-ai", "Explainable AI"], ["/what-if", "What-If Analysis"], ["/model-performance", "Model Performance"], ["/settings", "Settings"],
] as const;

const pages = {
  "/dashboard": <DashboardPage />, "/live-monitoring": <MonitoringPage />, "/predictions": <PredictionsPage />, "/assessment-history": <AssessmentHistoryPage />, "/resources": <ResourcesPage />,
  "/alerts": <AlertsPage />,
  "/recommendations": <RecommendationsPage />,
  "/analytics": <AnalyticsPage />,
  "/explainable-ai": <ExplainableAIPage />,
  "/what-if": <WhatIfPage />, "/model-performance": <ModelPerformancePage />, "/settings": <SettingsPage />,
} as const;

function Shell() {
  const { user, logout } = useAuth(); const navigate = useNavigate();
  const visibleNavigation = navigation.filter(([path]) => routeAccess[path]?.includes(user!.role));
  return <div className="app-shell"><aside className="sidebar"><div className="brand-lockup sidebar-brand"><span className="brand-mark">S</span><span><strong className="brand-name">SmartER</strong><small className="brand-subtitle">Emergency operations</small></span></div><nav aria-label="Primary navigation">{visibleNavigation.map(([path, label]) => <NavLink className={({ isActive }) => isActive ? "nav-link active" : "nav-link"} to={path} key={path}>{label}</NavLink>)}</nav><div className="sidebar-account"><strong>{user?.full_name}</strong><span>{user?.role.replace("_", " ")}</span><button className="logout-button" onClick={() => { logout(); navigate("/login"); }}>Log out</button></div></aside><main className="main-content"><header className="topbar"><div><p className="eyebrow">Operations console</p><p className="topbar-title">Emergency Room Intelligence</p></div><div className="topbar-actions"><NavLink to="/alerts" className="notification-button" aria-label="Open alerts">Alerts</NavLink><span className="status-pill"><span /> Secure session</span></div></header><Outlet /></main></div>;
}

export default function App() {
  return <AuthProvider><Routes><Route path="/login" element={<LoginPage />} /><Route path="/unauthorized" element={<UnauthorizedPage />} /><Route element={<ProtectedRoute />}><Route element={<Shell />}><Route path="/monitoring" element={<Navigate to="/live-monitoring" replace />} />{navigation.map(([path]) => <Route path={path} element={<ProtectedRoute allowedRoles={routeAccess[path]} />} key={`${path}-guard`}><Route index element={pages[path]} /></Route>)}</Route></Route><Route path="*" element={<Navigate to="/dashboard" replace />} /></Routes></AuthProvider>;
}
