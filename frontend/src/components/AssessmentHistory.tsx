import { useEffect, useState } from "react";

import { apiErrorMessage, predictionApi, type AIAssessmentHistoryItem } from "../services/api";
import { EmptyState, ErrorState, LoadingSpinner, StatusBadge } from "./States";

export default function AssessmentHistory() {
  const [assessments, setAssessments] = useState<AIAssessmentHistoryItem[] | null>(null);
  const [totalCount, setTotalCount] = useState(0);
  const [error, setError] = useState("");
  const [refreshKey, setRefreshKey] = useState(0);

  useEffect(() => {
    let active = true;
    const load = () => {
      predictionApi.assessmentHistory().then((result) => {
        if (active) { setAssessments(result.assessments); setTotalCount(result.count); setError(""); }
      }).catch((reason: unknown) => {
        if (active) setError(apiErrorMessage(reason));
      });
    };
    const handleSaved = () => load();
    load();
    window.addEventListener("smarter-assessment-saved", handleSaved);
    return () => { active = false; window.removeEventListener("smarter-assessment-saved", handleSaved); };
  }, [refreshKey]);

  return <section className="surface assessment-history"><div className="section-heading"><div><p className="eyebrow">Saved AI assessments</p><h2>Assessment history</h2></div><span className="data-note">Newest first · {assessments?.length ?? 0} of {totalCount}</span></div>
    {error && <ErrorState message={error} retry={() => setRefreshKey((value) => value + 1)} />}
    {!assessments && !error && <LoadingSpinner label="Loading saved assessments..." />}
    {assessments && assessments.length === 0 && <EmptyState title="No saved assessments yet" message="Run an AI assessment to save its submitted operational inputs, model outputs, congestion score, and resource estimates here." />}
    {assessments && assessments.length > 0 && <div className="assessment-list">{assessments.map((item) => {
      const prediction = item.prediction_payload;
      const score = prediction.congestion_score;
      return <article className="assessment-row" key={item.id}><div className="assessment-main"><div className="assessment-title"><strong>Assessment #{item.id}</strong><StatusBadge value={item.congestion_level} /><span>{item.er_unit_id}</span></div><time>{new Date(item.assessment_timestamp).toLocaleString()}</time><p>Input arrivals: {String(item.input_payload.patient_arrivals ?? "Not recorded")} · Current patients: {String(item.input_payload.current_patients ?? "Not recorded")}</p></div><div className="assessment-results"><span>SmartER score: {score ? `${score.score.toFixed(0)} / 100` : `${item.congestion_score.toFixed(0)} / 100`}</span><span>Next hour: {prediction.forecast.forecasts["1h"].toFixed(1)}</span><span>Beds / doctors / nurses: {prediction.resources.required_beds.toFixed(1)} / {prediction.resources.required_doctors.toFixed(1)} / {prediction.resources.required_nurses.toFixed(1)}</span></div></article>;
    })}</div>}
  </section>;
}