import { useState, type FormEvent } from "react";

import { apiErrorMessage, metricsApi, type ERMetricInput, type ERMetricRecord } from "../services/api";
import { ErrorState } from "./States";

type FormValues = Omit<ERMetricInput, "timestamp" | "arrivals" | "departures" | "active_patients" | "waiting_patients" | "occupied_beds" | "available_beds" | "average_wait_minutes" | "critical_patient_count"> & {
  timestamp: string;
  arrivals: string;
  departures: string;
  active_patients: string;
  waiting_patients: string;
  occupied_beds: string;
  available_beds: string;
  average_wait_minutes: string;
  critical_patient_count: string;
};

function localDateTimeValue(date: Date) {
  return new Date(date.getTime() - date.getTimezoneOffset() * 60_000).toISOString().slice(0, 16);
}

const initialValues: FormValues = {
  er_unit_id: "",
  timestamp: localDateTimeValue(new Date()),
  arrivals: "",
  departures: "",
  active_patients: "",
  waiting_patients: "",
  occupied_beds: "",
  available_beds: "",
  average_wait_minutes: "",
  critical_patient_count: "",
};

const fields: Array<[keyof Omit<FormValues, "er_unit_id" | "timestamp">, string, number]> = [
  ["arrivals", "Arrivals during interval", 5000], ["departures", "Departures during interval", 5000],
  ["active_patients", "Active patients", 5000], ["waiting_patients", "Waiting patients", 5000],
  ["occupied_beds", "Occupied beds", 2000], ["available_beds", "Available beds", 2000],
  ["average_wait_minutes", "Average waiting time (minutes)", 1440], ["critical_patient_count", "Critical patients", 5000],
];

export default function OperationalMetricForm() {
  const [values, setValues] = useState(initialValues);
  const [error, setError] = useState("");
  const [saved, setSaved] = useState<ERMetricRecord | null>(null);
  const [busy, setBusy] = useState(false);

  function update(field: keyof FormValues, value: string) {
    setValues((current) => ({ ...current, [field]: value }));
    setSaved(null);
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    const active = Number(values.active_patients);
    if (Number(values.waiting_patients) > active || Number(values.occupied_beds) > active || Number(values.critical_patient_count) > active) {
      setError("Waiting patients, occupied beds, and critical patients cannot exceed active patients.");
      return;
    }
    const payload: ERMetricInput = {
      er_unit_id: values.er_unit_id.trim(),
      timestamp: new Date(values.timestamp).toISOString(),
      arrivals: Number(values.arrivals),
      departures: Number(values.departures),
      active_patients: active,
      waiting_patients: Number(values.waiting_patients),
      occupied_beds: Number(values.occupied_beds),
      available_beds: Number(values.available_beds),
      average_wait_minutes: Number(values.average_wait_minutes),
      critical_patient_count: Number(values.critical_patient_count),
    };
    setBusy(true);
    try { setSaved(await metricsApi.ingest(payload)); }
    catch (reason) { setError(apiErrorMessage(reason)); }
    finally { setBusy(false); }
  }

  return <section className="surface metric-ingestion"><div className="section-heading"><div><p className="eyebrow">Authenticated observation entry</p><h2>Record operational metrics</h2></div><span className="data-note">No patient identifiers are collected</span></div><p className="muted">Enter an observed interval. Saving stores this observation and makes it available to authorized Analytics users.</p>{error && <ErrorState message={error} />}<form onSubmit={submit}><div className="metric-entry-grid"><label>ER unit ID<input required maxLength={80} value={values.er_unit_id} onChange={(event) => update("er_unit_id", event.target.value)} /></label><label>Observation timestamp<input required type="datetime-local" value={values.timestamp} onChange={(event) => update("timestamp", event.target.value)} /></label>{fields.map(([field, label, max]) => <label key={field}>{label}<input required type="number" min="0" max={max} step={field === "average_wait_minutes" ? "0.1" : "1"} value={values[field]} onChange={(event) => update(field, event.target.value)} /></label>)}</div><button className="primary-button" type="submit" disabled={busy}>{busy ? "Saving observation..." : "Save observed metrics"}</button></form>{saved && <p className="saved-note" role="status">Observation {saved.id} saved for {new Date(saved.timestamp).toLocaleString()}.</p>}</section>;
}