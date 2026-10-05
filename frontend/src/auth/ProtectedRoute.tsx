import { Navigate, Outlet, useLocation } from "react-router-dom";

import { useAuth, type UserRole } from "./AuthContext";

export function ProtectedRoute({ allowedRoles }: { allowedRoles?: UserRole[] }) {
  const { user, isLoading } = useAuth();
  const location = useLocation();
  if (isLoading) return <div className="loading-screen">Checking your secure session...</div>;
  if (!user) return <Navigate to="/login" replace state={{ from: location }} />;
  if (allowedRoles && !allowedRoles.includes(user.role)) return <Navigate to="/unauthorized" replace />;
  return <Outlet />;
}