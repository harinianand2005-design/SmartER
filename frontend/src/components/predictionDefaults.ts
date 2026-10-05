import type { PredictionInput } from "../services/api";

export const initialPredictionInput: PredictionInput = {
  timestamp: new Date().toISOString(), patient_arrivals: 12, current_patients: 30, available_beds: 18,
  doctors_available: 6, nurses_available: 14, doctors_scheduled: 8, nurses_scheduled: 18,
  average_waiting_time: 55, triage_1: 1, triage_2: 2, triage_3: 4, triage_4: 3, triage_5: 2,
  temperature: 12, rainfall: 1.5, holiday: 0, local_event: 0, flu_index: 40, weather_category: "clear", er_unit_id: "synthetic-er",
};