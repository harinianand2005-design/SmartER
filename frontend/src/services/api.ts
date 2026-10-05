
import axios from "axios";

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000",
  timeout: 15000,
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("smarter_access_token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// Existing operational prediction input
export type PredictionInput = {
  timestamp: string;
  patient_arrivals: number;
  current_patients: number;
  available_beds: number;
  doctors_available: number;
  nurses_available: number;
  doctors_scheduled: number;
  nurses_scheduled: number;
  average_waiting_time: number;
  triage_1: number;
  triage_2: number;
  triage_3: number;
  triage_4: number;
  triage_5: number;
  temperature: number;
  rainfall: number;
  holiday: number;
  local_event: number;
  flu_index: number;
  weather_category: "clear" | "rain" | "storm";
  er_unit_id: string;
};

// NEW: Wait-time prediction input
export type WaitTimePredictionInput = {
  timestamp: string;
  patient_gender: string;
  patient_age: number;
  patient_race: string;
  department_referral: string;
};

// NEW: Wait-time prediction response
export type WaitTimePredictionResponse = {
  predicted_waittime_minutes: number;
  model_name: string;
  unit: string;
};

export type ForecastResponse = {
  timestamp: string;
  forecasts: Record<string, number>;
  model_version: string;
};

export type CongestionResponse = {
  timestamp: string;
  congestion_level: string;
  probabilities: Record<string, number>;
  confidence: number;
  model_version: string;
};

export type ResourceResponse = {
  timestamp: string;
  required_beds: number;
  required_doctors: number;
  required_nurses: number;
  model_versions: Record<string, string>;
};

export type CombinedResponse = {
  timestamp: string;
  forecast: ForecastResponse;
  congestion: CongestionResponse;
  resources: ResourceResponse;
};

export type ModelStatus = {
  model_name: string;
  version: string | null;
  loaded: boolean;
  artifact_name: string;
  validation_metrics?: Record<string, number>;
  test_metrics?: Record<string, number>;
  error?: string;
};

export type CongestionScoreFactor = {
  name: string;
  value: number;
  contribution: number;
  explanation: string;
};

export type CongestionScoreResponse = {
  score: number;
  level: "LOW" | "MODERATE" | "HIGH" | "CRITICAL";
  confidence: number | null;
  timestamp: string;
  factors: CongestionScoreFactor[];
  explanation: string;
};

export type IntelligenceRecommendation = {
  id: number | null;
  priority: string;
  title: string;
  reason: string;
  supporting_metric: string;
  timestamp: string;
  status: string;
};

export type OperationalAlert = {
  id: number;
  alert_type: string;
  severity: string;
  title: string;
  description: string;
  trigger_value: number | null;
  threshold: number | null;
  timestamp: string;
  status: string;
};

export type ExplainModel =
  | "congestion_classifier"
  | "bed_prediction_model"
  | "doctor_prediction_model"
  | "nurse_prediction_model";

export type ExplanationResponse = {
  model_name: string;
  model_version: string;
  prediction: string | number;
  base_value: number | null;
  top_contributing_features: Array<{
    feature: string;
    mean_absolute_shap: number;
    feature_value?: number;
  }>;
  timestamp: string;
  interpretation: string;
};

export type AnalyticsResponse = {
  summary: {
    observed_metric_count: number;
    forecast_count: number;
    congestion_prediction_count: number;
    resource_prediction_count: number;
    first_recorded_at: string | null;
    last_recorded_at: string | null;
  };
  observed_metrics: Array<{
    timestamp: string;
    arrivals: number;
    active_patients: number;
    waiting_patients: number;
    available_beds: number;
    occupied_beds: number;
    average_wait_minutes: number;
    occupancy_percentage: number | null;
  }>;
  arrival_forecasts: Array<{
    target_timestamp: string;
    horizon: string;
    predicted_arrivals: number;
    model_version: string;
  }>;
  congestion_history: Array<{
    target_timestamp: string;
    congestion_level: string | null;
    confidence: number | null;
    model_version: string;
  }>;
  resource_history: Array<{
    target_timestamp: string;
    required_beds: number;
    required_doctors: number;
    required_nurses: number;
    model_version: string;
  }>;
};

export type ERMetricInput = {
  er_unit_id: string;
  timestamp: string;
  arrivals: number;
  departures: number;
  active_patients: number;
  waiting_patients: number;
  occupied_beds: number;
  available_beds: number;
  average_wait_minutes: number;
  critical_patient_count: number;
};

export type ERMetricRecord = ERMetricInput & {
  id: number;
};

export type AIAssessmentHistoryItem = {
  id: number;
  er_unit_id: string;
  assessment_timestamp: string;
  created_at: string;
  input_payload: Record<string, unknown>;
  prediction_payload: CombinedResponse & {
    congestion_score?: {
      score: number;
      level: string;
      confidence: number | null;
    };
  };
  congestion_score: number;
  congestion_level: string;
};

export type AIAssessmentHistoryResponse = {
  assessments: AIAssessmentHistoryItem[];
  count: number;
};

export const predictionApi = {
  // NEW: Call the trained wait-time ML model
  waittime: (payload: WaitTimePredictionInput) =>
    api
      .post<WaitTimePredictionResponse>(
        "/api/v1/predictions/waittime",
        payload
      )
      .then((response) => response.data),

  run: async (payload: PredictionInput) => {
    const { data } = await api.post<CombinedResponse>(
      "/api/v1/predictions/run",
      payload
    );
    window.dispatchEvent(new Event("smarter-assessment-saved"));
    return data;
  },

  forecast: (payload: PredictionInput) =>
    api
      .post<ForecastResponse>("/api/v1/predictions/forecast", payload)
      .then((response) => response.data),

  congestion: (payload: PredictionInput) =>
    api
      .post<CongestionResponse>("/api/v1/predictions/congestion", payload)
      .then((response) => response.data),

  resources: (payload: PredictionInput) =>
    api
      .post<ResourceResponse>("/api/v1/predictions/resources", payload)
      .then((response) => response.data),

  latest: () =>
    api.get("/api/v1/predictions/latest").then((response) => response.data),

  modelStatus: () =>
    api
      .get<{ models: ModelStatus[] }>("/api/v1/models/status")
      .then((response) => response.data),

  assessmentHistory: (limit = 20, offset = 0) =>
    api
      .get<AIAssessmentHistoryResponse>(
        "/api/v1/predictions/assessments/history",
        { params: { limit, offset } }
      )
      .then((response) => response.data),
};

export const intelligenceApi = {
  congestionScore: (payload: PredictionInput) =>
    api
      .post<CongestionScoreResponse>(
        "/api/v1/intelligence/congestion-score",
        payload
      )
      .then((response) => response.data),

  explain: (model: ExplainModel, scenario: PredictionInput) =>
    api
      .post<ExplanationResponse>("/api/v1/intelligence/explain", {
        model,
        scenario,
      })
      .then((response) => response.data),

  recommendations: (payload: PredictionInput) =>
    api
      .post<IntelligenceRecommendation[]>(
        "/api/v1/intelligence/recommendations",
        payload
      )
      .then((response) => response.data),
  
  whatIf: (payload: {
    additional_beds: number;
    additional_doctors: number;
    additional_nurses: number;
    expected_arrival_change: number;
  }) =>
    api
      .post("/api/v1/intelligence/what-if", payload)
      .then((response) => response.data),


  latestRecommendations: () =>
    api
      .get<IntelligenceRecommendation[]>(
        "/api/v1/intelligence/recommendations/latest"
      )
      .then((response) => response.data),

  alerts: () =>
    api
      .get<OperationalAlert[]>("/api/v1/alerts")
      .then((response) => response.data),

  latestAlerts: () =>
    api
      .get<OperationalAlert[]>("/api/v1/alerts/latest")
      .then((response) => response.data),

  resolveAlert: (alertId: number) =>
    api
      .post<OperationalAlert>(`/api/v1/alerts/${alertId}/resolve`, {})
      .then((response) => response.data),
};

export const analyticsApi = {
  summary: (start?: string, end?: string) => {
    const params = new URLSearchParams();

    if (start) params.set("start", `${start}T00:00:00Z`);
    if (end) params.set("end", `${end}T23:59:59Z`);

    return api
      .get<AnalyticsResponse>(
        `/api/v1/analytics/summary${params.size ? `?${params}` : ""}`
      )
      .then((response) => response.data);
  },
};

export const metricsApi = {
  ingest: (payload: ERMetricInput) =>
    api
      .post<ERMetricRecord>("/api/v1/er-metrics", payload)
      .then((response) => response.data),
};

export function apiErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail;

    if (typeof detail === "string") return detail;
    if (typeof detail?.message === "string") return detail.message;

    return "The SmartER API is unavailable.";
  }

  return "The SmartER API is unavailable.";
}
