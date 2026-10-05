import type { UserRole } from "./AuthContext";

export const routeAccess: Record<string, UserRole[]> = {
  "/dashboard": ["ADMIN", "TRIAGE_NURSE", "HEALTH_AUTHORITY"], "/monitoring": ["ADMIN", "TRIAGE_NURSE"],
  "/live-monitoring": ["ADMIN", "TRIAGE_NURSE"],
  "/assessment-history": ["ADMIN", "TRIAGE_NURSE", "HEALTH_AUTHORITY"],
  "/predictions": ["ADMIN", "TRIAGE_NURSE"], "/resources": ["ADMIN"], "/alerts": ["ADMIN", "TRIAGE_NURSE"],
  "/recommendations": ["ADMIN", "TRIAGE_NURSE"], "/analytics": ["ADMIN", "HEALTH_AUTHORITY"], "/explainable-ai": ["ADMIN"],
  "/what-if": ["ADMIN"], "/model-performance": ["ADMIN"], "/settings": ["ADMIN"],
};