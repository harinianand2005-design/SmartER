import { useState } from "react";

import type { PredictionInput } from "../services/api";
import { initialPredictionInput } from "./predictionDefaults";

const fields: Array<[keyof PredictionInput, string]> = [
  ["patient_arrivals", "Arrivals / hour"], ["current_patients", "Current patients"], ["available_beds", "Available beds"],
  ["doctors_available", "Doctors available"], ["nurses_available", "Nurses available"], ["average_waiting_time", "Average wait (min)"],
  ["triage_1", "Triage 1"], ["triage_2", "Triage 2"], ["triage_3", "Triage 3"], ["triage_4", "Triage 4"], ["triage_5", "Triage 5"],
];

export default function PredictionInputForm({ onSubmit, busy }: { onSubmit: (input: PredictionInput) => void; busy?: boolean }) {
  const [input, setInput] = useState(initialPredictionInput);
  function update(field: keyof PredictionInput, value: string) {
    setInput((current) => ({ ...current, [field]: field === "er_unit_id" || field === "weather_category" || field === "timestamp" ? value : Number(value) } as PredictionInput));
  }
  return <form className="input-form" onSubmit={(event) => { event.preventDefault(); onSubmit({ ...input, timestamp: new Date().toISOString() }); }}>
    <div className="form-heading"><div><p className="eyebrow">Operational snapshot</p><h2>Run a current scenario</h2></div><span className="form-note">Synthetic development input</span></div>
    <div className="input-grid">{fields.map(([field, label]) => <label key={field}>{label}<input type="number" min="0" value={input[field] as number} onChange={(event) => update(field, event.target.value)} /></label>)}
      <label>Weather<select value={input.weather_category} onChange={(event) => update("weather_category", event.target.value)}><option value="clear">Clear</option><option value="rain">Rain</option><option value="storm">Storm</option></select></label>
      <label>Holiday<select value={input.holiday} onChange={(event) => update("holiday", event.target.value)}><option value="0">No</option><option value="1">Yes</option></select></label>
      <label>Local event<select value={input.local_event} onChange={(event) => update("local_event", event.target.value)}><option value="0">No</option><option value="1">Yes</option></select></label>
      <label>Flu index<input type="number" min="0" max="100" value={input.flu_index} onChange={(event) => update("flu_index", event.target.value)} /></label>
    </div><button className="primary-button" type="submit" disabled={busy}>{busy ? "Running models..." : "Run AI assessment"}</button>
  </form>;
}