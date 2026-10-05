import AssessmentHistory from "../components/AssessmentHistory";

export default function AssessmentHistoryPage() {
  return <main className="page-content"><div className="page-header"><div><p className="eyebrow">Saved operational assessments</p><h1>Assessment history</h1><p className="muted">Review the submitted aggregate scenario and actual persisted model outputs for each completed AI assessment.</p></div></div><AssessmentHistory /></main>;
}