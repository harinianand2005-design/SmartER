export function LoadingSpinner({ label = "Loading operational data..." }: { label?: string }) {
  return <div className="state-panel" role="status"><span className="spinner" />{label}</div>;
}

export function ErrorState({ message = "This data could not be loaded.", retry }: { message?: string; retry?: () => void }) {
  return <div className="state-panel state-error" role="alert"><strong>Connection unavailable</strong><span>{message}</span>{retry && <button className="text-button" onClick={retry}>Retry</button>}</div>;
}

export function EmptyState({ title, message }: { title: string; message: string }) {
  return <div className="state-panel"><strong>{title}</strong><span>{message}</span></div>;
}

export function StatusBadge({ value }: { value: string }) {
  const tone = value.toLowerCase().replaceAll(" ", "-");
  return <span className={`status-badge tone-${tone}`}>{value}</span>;
}

export function MetricCard({ label, value, detail, tone = "neutral" }: { label: string; value: string | number; detail?: string; tone?: string }) {
  return <article className={`metric-card metric-${tone}`}><p>{label}</p><strong>{value}</strong>{detail && <span>{detail}</span>}</article>;
}