import type { CSSProperties } from "react";

import { StatusBadge } from "./States";
import type { CongestionScoreResponse } from "../services/api";

export default function CongestionScore({ result }: { result: CongestionScoreResponse }) {
  const score = Math.round(result.score);
  return <article className="congestion-panel"><div className="score-ring" style={{ "--score": `${score * 3.6}deg` } as CSSProperties}><strong>{score}</strong><span>/100</span></div><div className="score-copy"><p className="eyebrow">AI-derived operational signal</p><h2>SmartER Congestion Score</h2><StatusBadge value={result.level} />{result.confidence !== null && <p>Classifier confidence {Math.round(result.confidence * 100)}%.</p>}<p>{result.explanation} This score is not a medical diagnosis.</p><div className="score-factors">{result.factors.map((factor) => <span key={factor.name}>{factor.name}: +{factor.contribution.toFixed(1)}</span>)}</div><small>Updated {new Date(result.timestamp).toLocaleString()}</small></div></article>;
}