import { useState, type FormEvent } from "react";
import { useLocation, useNavigate } from "react-router-dom";

import { useAuth } from "../auth/AuthContext";

export default function LoginPage() {
  const { login } = useAuth(); const navigate = useNavigate(); const location = useLocation();
  const [email, setEmail] = useState(""); const [password, setPassword] = useState(""); const [error, setError] = useState(""); const [isSubmitting, setIsSubmitting] = useState(false);
  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setError(""); setIsSubmitting(true);
    try { const user = await login(email, password); const from = (location.state as { from?: { pathname: string } } | null)?.from?.pathname; navigate(from ?? (user.role === "HEALTH_AUTHORITY" ? "/analytics" : "/dashboard"), { replace: true }); }
    catch { setError("We could not sign you in. Check your email and password."); }
    finally { setIsSubmitting(false); }
  }
  return <main className="login-page"><section className="login-panel"><div className="brand-lockup"><span className="brand-mark">S</span><span><strong>SmartER</strong><small>Emergency operations</small></span></div><p className="eyebrow">Secure workspace</p><h1>Welcome back</h1><p className="muted">Sign in to access your role-specific emergency room intelligence workspace.</p><form onSubmit={handleSubmit} className="login-form"><label htmlFor="email">Email address</label><input id="email" type="email" value={email} onChange={(event) => setEmail(event.target.value)} autoComplete="email" required /><label htmlFor="password">Password</label><input id="password" type="password" value={password} onChange={(event) => setPassword(event.target.value)} autoComplete="current-password" minLength={8} required />{error && <p className="form-error" role="alert">{error}</p>}<button type="submit" className="primary-button" disabled={isSubmitting}>{isSubmitting ? "Signing in..." : "Sign in"}</button></form></section><aside className="login-aside"><p className="eyebrow">SmartER command center</p><h2>Clearer signals for safer emergency operations.</h2><p>Secure, role-aware access for the people coordinating emergency care.</p></aside></main>;
}