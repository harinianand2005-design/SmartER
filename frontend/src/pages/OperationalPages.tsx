import { useEffect, useState } from "react";



import { useAuth } from "../auth/AuthContext";



import CongestionScore from "../components/CongestionScore";



import {

  ForecastChart,

  ObservedArrivalsChart,

  ObservedWaitingOccupancyChart,

  ResourceChart,

  ResourceHistoryChart,

} from "../components/Charts";



import PredictionInputForm from "../components/PredictionInputForm";



import {

  EmptyState,

  ErrorState,

  LoadingSpinner,

  MetricCard,

  StatusBadge,

} from "../components/States";



import {

  analyticsApi,

  apiErrorMessage,

  intelligenceApi,

  predictionApi,

  type AnalyticsResponse,

  type CombinedResponse,

  type CongestionScoreResponse,

  type ExplainModel,

  type ExplanationResponse,

  type IntelligenceRecommendation,

  type OperationalAlert,

  type PredictionInput,

  type ModelStatus,

} from "../services/api";



function PageHeader({

  eyebrow,

  title,

  description,

}: {

  eyebrow: string;

  title: string;

  description: string;

}) {

  return (

    <div className="page-header">

      <div>

        <p className="eyebrow">{eyebrow}</p>

        <h1>{title}</h1>

        <p className="muted">{description}</p>

      </div>

    </div>

  );

}



function useCombinedPrediction() {

  const [result, setResult] = useState<CombinedResponse | null>(null);

  const [score, setScore] = useState<CongestionScoreResponse | null>(null);

  const [topRecommendation, setTopRecommendation] =

    useState<IntelligenceRecommendation | null>(null);

  const [alerts, setAlerts] = useState<OperationalAlert[]>([]);

  const [scenario, setScenario] = useState<PredictionInput | null>(null);

  const [error, setError] = useState("");

  const [busy, setBusy] = useState(false);



  async function run(input: PredictionInput) {

    setBusy(true);

    setError("");



    try {

      setScenario(input);



      const [combined, congestionScore] = await Promise.all([

        predictionApi.run(input),

        intelligenceApi.congestionScore(input),

      ]);



      setResult(combined);

      setScore(congestionScore);



      const recommendationResult = await intelligenceApi

        .recommendations(input)

        .catch(() => null);



      if (recommendationResult) {

        setTopRecommendation(recommendationResult[0] ?? null);

      }



      const alertResult = await intelligenceApi

        .latestAlerts()

        .catch(() => null);



      if (alertResult) {

        setAlerts(

          alertResult.filter((alert) => alert.status === "OPEN")

        );

      }

    } catch (reason) {

      setError(apiErrorMessage(reason));

    } finally {

      setBusy(false);

    }

  }



  return {

    result,

    score,

    topRecommendation,

    alerts,

    scenario,

    error,

    busy,

    run,

  };

}



function ResultsGrid({ result }: { result: CombinedResponse }) {

  return (

    <div className="metric-grid">

      <MetricCard

        label="Next 1 hour"

        value={result.forecast.forecasts["1h"].toFixed(1)}

        detail="predicted arrivals"

        tone="teal"

      />



      <MetricCard

        label="Next 3 hours"

        value={result.forecast.forecasts["3h"].toFixed(1)}

        detail="predicted arrivals"

        tone="blue"

      />



      <MetricCard

        label="Required beds"

        value={result.resources.required_beds.toFixed(1)}

        detail="model requirement"

        tone="orange"

      />



      <MetricCard

        label="Required doctors"

        value={result.resources.required_doctors.toFixed(1)}

        detail="model requirement"

        tone="neutral"

      />



      <MetricCard

        label="Required nurses"

        value={result.resources.required_nurses.toFixed(1)}

        detail="model requirement"

        tone="neutral"

      />

    </div>

  );

}



export function DashboardPage() {
  const {
    result,
    score,
    topRecommendation,
    alerts,
    scenario,
    error,
    busy,
    run,
  } = useCombinedPrediction();

  const [timestamp, setTimestamp] = useState("");
  const [gender, setGender] = useState("");
  const [age, setAge] = useState("35");
  const [race, setRace] = useState("");
  const [department, setDepartment] = useState("");

  const [waitTimeResult, setWaitTimeResult] = useState<{
    predicted_waittime_minutes: number;
    model_name: string;
    unit: string;
  } | null>(null);

  const [waitTimeError, setWaitTimeError] = useState("");
  const [waitTimeBusy, setWaitTimeBusy] = useState(false);

  const [analyticsData, setAnalyticsData] =
    useState<AnalyticsResponse | null>(null);
  const [analyticsBusy, setAnalyticsBusy] = useState(true);
  const [analyticsError, setAnalyticsError] = useState("");

  async function predictWaitTime() {
    setWaitTimeBusy(true);
    setWaitTimeError("");
    setWaitTimeResult(null);

    try {
      const prediction = await predictionApi.waittime({
        timestamp,
        patient_gender: gender.trim(),
        patient_age: Number(age),
        patient_race: race.trim(),
        department_referral: department.trim(),
      });

      setWaitTimeResult(prediction);
    } catch (reason) {
      setWaitTimeError(apiErrorMessage(reason));
    } finally {
      setWaitTimeBusy(false);
    }
  }

  useEffect(() => {
    let active = true;

    analyticsApi
      .summary()
      .then((response) => {
        if (active) {
          setAnalyticsData(response);
        }
      })
      .catch((reason) => {
        if (active) {
          setAnalyticsError(apiErrorMessage(reason));
        }
      })
      .finally(() => {
        if (active) {
          setAnalyticsBusy(false);
        }
      });

    return () => {
      active = false;
    };
  }, []);

  return (
    <div className="page-content">
      <PageHeader
        eyebrow="Decision support"
        title="ER command center"
        description="A focused operational view of demand, congestion, and resource pressure from the persisted SmartER models."
      />

      {error && <ErrorState message={error} />}

      <PredictionInputForm onSubmit={run} busy={busy} />

      {busy && <LoadingSpinner />}

      {result && (
        <>
          <ResultsGrid result={result} />

          {score ? (
            <CongestionScore result={score} />
          ) : (
            <EmptyState
              title="Score unavailable"
              message="The congestion score service did not return a score for this scenario."
            />
          )}

          <section className="surface intelligence-summary">
            <div className="section-heading">
              <div>
                <p className="eyebrow">Decision support</p>
                <h2>AI Operational Insights</h2>
              </div>
              <span className="data-note">
                Based on this submitted snapshot
              </span>
            </div>

            <div className="insight-grid">
              <article>
                <span>Current congestion</span>
                <strong>{score?.level ?? "Unavailable"}</strong>
                <small>
                  {score
                    ? `${score.score.toFixed(0)} / 100`
                    : "Score API unavailable"}
                </small>
              </article>

              <article>
                <span>Next-hour forecast</span>
                <strong>
                  {result.forecast.forecasts["1h"].toFixed(1)}
                </strong>
                <small>predicted arrivals</small>
              </article>

              <article>
                <span>Resource pressure</span>
                <strong>
                  {Math.max(
                    0,
                    result.resources.required_beds -
                      (scenario?.available_beds ?? 0)
                  ).toFixed(1)}{" "}
                  bed ·{" "}
                  {Math.max(
                    0,
                    result.resources.required_doctors -
                      (scenario?.doctors_available ?? 0)
                  ).toFixed(1)}{" "}
                  doctor ·{" "}
                  {Math.max(
                    0,
                    result.resources.required_nurses -
                      (scenario?.nurses_available ?? 0)
                  ).toFixed(1)}{" "}
                  nurse gaps
                </strong>
                <small>
                  Model requirements compared with submitted availability
                </small>
              </article>

              <article>
                <span>Highest-priority recommendation</span>
                <strong>
                  {topRecommendation?.title ?? "None returned"}
                </strong>
                <small>
                  {topRecommendation?.supporting_metric ??
                    "No recommendation available"}
                </small>
              </article>

              <article>
                <span>Active critical/high alerts</span>
                <strong>
                  {
                    alerts.filter((alert) =>
                      ["CRITICAL", "HIGH"].includes(alert.severity)
                    ).length
                  }
                </strong>
                <small>Persisted open alerts</small>
              </article>
            </div>
          </section>

          <section className="dashboard-grid">
            <div className="surface">
              <div className="section-heading">
                <div>
                  <p className="eyebrow">Demand outlook</p>
                  <h2>Arrival forecast</h2>
                </div>
                <span className="data-note">
                  Model {result.forecast.model_version}
                </span>
              </div>
              <ForecastChart forecasts={result.forecast.forecasts} />
            </div>

            <div className="surface">
              <div className="section-heading">
                <div>
                  <p className="eyebrow">Capacity plan</p>
                  <h2>Resource requirement</h2>
                </div>
              </div>
              <ResourceChart resources={result.resources} />
            </div>
          </section>
        </>
      )}

      <section className="surface">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Machine Learning</p>
            <h2>ER Wait Time Prediction</h2>
          </div>
          <span className="data-note">Random Forest Model</span>
        </div>

        <p className="muted">
          Enter patient details to estimate the expected emergency room waiting time.
        </p>

        <form
          className="input-grid"
          onSubmit={(event) => {
            event.preventDefault();
            void predictWaitTime();
          }}
        >
          <label>
            Admission Date and Time
            <input
              type="datetime-local"
              value={timestamp}
              onChange={(event) => setTimestamp(event.target.value)}
              required
            />
          </label>

          <label>
            Patient Gender
            <input
              type="text"
              value={gender}
              onChange={(event) => setGender(event.target.value)}
              placeholder="Enter dataset value"
              required
            />
          </label>

          <label>
            Patient Age
            <input
              type="number"
              min="0"
              max="120"
              value={age}
              onChange={(event) => setAge(event.target.value)}
              required
            />
          </label>

          <label>
            Patient Race
            <input
              type="text"
              value={race}
              onChange={(event) => setRace(event.target.value)}
              placeholder="Enter dataset value"
              required
            />
          </label>

          <label>
            Department Referral
            <input
              type="text"
              value={department}
              onChange={(event) => setDepartment(event.target.value)}
              placeholder="Enter dataset value"
              required
            />
          </label>

          <div>
            <button
              className="primary-button"
              type="submit"
              disabled={waitTimeBusy}
            >
              {waitTimeBusy ? "Predicting..." : "Predict Wait Time"}
            </button>
          </div>
        </form>

        {waitTimeBusy && <LoadingSpinner />}
        {waitTimeError && <ErrorState message={waitTimeError} />}

        {waitTimeResult && (
          <div className="simulation-result">
            <p className="eyebrow">Prediction Result</p>
            <h2>
              {waitTimeResult.predicted_waittime_minutes.toFixed(2)}{" "}
              {waitTimeResult.unit || "minutes"}
            </h2>
            <p>Model: {waitTimeResult.model_name}</p>
            <p className="muted">
              This is a model estimate, not a guaranteed waiting time.
            </p>
          </div>
        )}
      </section>

      <section className="surface">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Historical Analytics</p>
            <h2>ER Data Overview</h2>
          </div>
          <span className="data-note">Persisted backend data</span>
        </div>

        {analyticsBusy && <LoadingSpinner />}
        {analyticsError && <ErrorState message={analyticsError} />}

        {analyticsData && (
          <>
            <div className="metric-grid">
              <MetricCard
                label="Observed Metric Rows"
                value={analyticsData.summary.observed_metric_count}
                detail="persisted ER measurements"
              />
              <MetricCard
                label="Forecast Records"
                value={analyticsData.summary.forecast_count}
                detail="persisted arrival predictions"
                tone="teal"
              />
              <MetricCard
                label="Congestion Predictions"
                value={analyticsData.summary.congestion_prediction_count}
                detail="persisted classifications"
                tone="orange"
              />
              <MetricCard
                label="Resource Predictions"
                value={analyticsData.summary.resource_prediction_count}
                detail="persisted resource records"
              />
            </div>

            <div className="dashboard-grid">
              <div className="surface">
                <div className="section-heading">
                  <div>
                    <p className="eyebrow">Observed measurements</p>
                    <h2>Patient Arrivals</h2>
                  </div>
                </div>
                {analyticsData.observed_metrics.length ? (
                  <ObservedArrivalsChart data={analyticsData.observed_metrics} />
                ) : (
                  <EmptyState
                    title="No arrival history"
                    message="No persisted arrival measurements are available yet."
                  />
                )}
              </div>

              <div className="surface">
                <div className="section-heading">
                  <div>
                    <p className="eyebrow">Observed measurements</p>
                    <h2>Waiting & Occupancy</h2>
                  </div>
                </div>
                {analyticsData.observed_metrics.length ? (
                  <ObservedWaitingOccupancyChart
                    data={analyticsData.observed_metrics}
                  />
                ) : (
                  <EmptyState
                    title="No waiting history"
                    message="No persisted waiting or occupancy measurements are available yet."
                  />
                )}
              </div>
            </div>

            <div className="dashboard-grid">
              <div className="surface">
                <div className="section-heading">
                  <div>
                    <p className="eyebrow">Model outputs</p>
                    <h2>Predicted Resource Requirements</h2>
                  </div>
                </div>
                {analyticsData.resource_history.length ? (
                  <ResourceHistoryChart data={analyticsData.resource_history} />
                ) : (
                  <EmptyState
                    title="No resource prediction history"
                    message="Resource predictions will appear here after authenticated prediction runs are stored."
                  />
                )}
              </div>

              <div className="surface">
                <div className="section-heading">
                  <div>
                    <p className="eyebrow">Model outputs</p>
                    <h2>Congestion Trend</h2>
                  </div>
                </div>

                {analyticsData.congestion_history.length ? (
                  <div className="recommendation-list">
                    {analyticsData.congestion_history.map((point, index) => (
                      <article
                        className="history-row"
                        key={`${point.target_timestamp}-${index}`}
                      >
                        <time>
                          {new Date(point.target_timestamp).toLocaleString()}
                        </time>
                        <StatusBadge
                          value={point.congestion_level ?? "Not classified"}
                        />
                        <span>
                          {point.confidence === null
                            ? "Confidence unavailable"
                            : `${Math.round(point.confidence * 100)}% confidence`}
                        </span>
                      </article>
                    ))}
                  </div>
                ) : (
                  <EmptyState
                    title="No congestion history"
                    message="No congestion predictions are persisted yet."
                  />
                )}
              </div>
            </div>

            <section className="surface">
              <div className="section-heading">
                <div>
                  <p className="eyebrow">Data availability</p>
                  <h2>Historical Data Limitations</h2>
                </div>
              </div>
              <EmptyState
                title="Some operational history is unavailable"
                message="The current persisted ERMetric data does not contain historical triage distribution or staff availability. SmartER will not infer or fabricate those values."
              />
            </section>
          </>
        )}
      </section>
    </div>
  );
}

export function MonitoringPage() {

  const { result, score, error, busy, run } =

    useCombinedPrediction();



  return (

    <div className="page-content">

      <PageHeader

        eyebrow="Operational watch"

        title="Live ER monitoring"

        description="Run a refreshed snapshot against SmartER models. This is an API refresh workflow, not a live hospital feed."

      />



      <div className="refresh-note">

        Last updated:{" "}

        {result? new Date(result.timestamp).toLocaleString()

          : "No snapshot requested"}

      </div>



      {error && <ErrorState message={error} />}



      <PredictionInputForm onSubmit={run} busy={busy} />



      {busy && <LoadingSpinner />}



      {result && (

        <>

          <div className="metric-grid">

            <MetricCard

              label="Current patients"

              value="From submitted snapshot"

              detail="No patient feed endpoint available"

            />



            <MetricCard

              label="Congestion"

              value={result.congestion.congestion_level}

              detail={`${Math.round(

                result.congestion.confidence * 100

              )}% confidence`}

              tone="orange"

            />



            <MetricCard

              label="Forecasted 6h arrivals"

              value={result.forecast.forecasts["6h"].toFixed(1)}

              detail="model output"

              tone="teal"

            />

          </div>



          {score ? (

            <CongestionScore result={score} />

          ) : (

            <EmptyState

              title="Score unavailable"

              message="The congestion score service did not return a score for this scenario."

            />

          )}



          <section className="surface">

            <div className="section-heading">

              <div>

                <p className="eyebrow">Triage snapshot</p>

                <h2>Current operational inputs</h2>

              </div>

            </div>



            <p className="muted">

              Triage counts are accepted by the prediction API and are not

              persisted as patient-level information.

            </p>

          </section>

        </>

      )}

    </div>

  );

}



export function PredictionsPage() {

  const [forecast, setForecast] =

    useState<CombinedResponse["forecast"] | null>(null);



  const [error, setError] = useState("");

  const [busy, setBusy] = useState(false);



  async function run(input: PredictionInput) {

    setBusy(true);

    setError("");



    try {

      setForecast(await predictionApi.forecast(input));

    } catch (reason) {

      setError(apiErrorMessage(reason));

    } finally {

      setBusy(false);

    }

  }



  return (

    <div className="page-content">

      <PageHeader

        eyebrow="Forecasting"

        title="Arrival predictions"

        description="Forecast horizons generated by the existing Phase 4 arrival models."

      />



      {error && <ErrorState message={error} />}



      <PredictionInputForm onSubmit={run} busy={busy} />



      {busy && <LoadingSpinner />}



      {forecast && (

        <section className="surface">

          <div className="section-heading">

            <div>

              <p className="eyebrow">Forecast horizons</p>

              <h2>Expected arrivals</h2>

            </div>



            <span className="data-note">

              Updated{" "}

              {new Date(forecast.timestamp).toLocaleString()}

            </span>

          </div>



          <ForecastChart forecasts={forecast.forecasts} />

        </section>

      )}

    </div>

  );

}



export function ResourcesPage() {

  const [result, setResult] =

    useState<CombinedResponse["resources"] | null>(null);



  const [error, setError] = useState("");

  const [busy, setBusy] = useState(false);



  async function run(input: PredictionInput) {

    setBusy(true);

    setError("");



    try {

      setResult(await predictionApi.resources(input));

    } catch (reason) {

      setError(apiErrorMessage(reason));

    } finally {

      setBusy(false);

    }

  }



  return (

    <div className="page-content">

      <PageHeader

        eyebrow="Capacity planning"

        title="Resource requirements"

        description="Compare AI-estimated requirements against the availability submitted in the current scenario."

      />



      {error && <ErrorState message={error} />}



      <PredictionInputForm onSubmit={run} busy={busy} />



      {busy && <LoadingSpinner />}



      {result && (

        <>

          <div className="metric-grid">

            <MetricCard

              label="Required beds"

              value={result.required_beds.toFixed(1)}

              detail="model output"

              tone="orange"

            />



            <MetricCard

              label="Required doctors"

              value={result.required_doctors.toFixed(1)}

              detail="model output"

            />



            <MetricCard

              label="Required nurses"

              value={result.required_nurses.toFixed(1)}

              detail="model output"

            />

          </div>



          <section className="surface">

            <ResourceChart resources={result} />

          </section>

        </>

      )}

    </div>

  );

}



export function ModelPerformancePage() {

  const [models, setModels] =

    useState<ModelStatus[] | null>(null);



  const [error, setError] = useState("");



  useEffect(() => {

    predictionApi

      .modelStatus()

      .then((response) => setModels(response.models))

      .catch((reason) => setError(apiErrorMessage(reason)));

  }, []);



  return (

    <div className="page-content">

      <PageHeader

        eyebrow="Model governance"

        title="Model performance"

        description="Recorded evaluation metrics from the Phase 4 artifacts exposed by the model-status API."

      />



      {error && (

        <ErrorState

          message={error}

          retry={() => setError("")}

        />

      )}



      {!models && !error && <LoadingSpinner />}



      {models && (

        <section className="surface">

          <div className="table-wrap">

            <table>

              <thead>

                <tr>

                  <th>Model</th>

                  <th>Status</th>

                  <th>Version</th>

                  <th>Validation</th>

                  <th>Final test</th>

                </tr>

              </thead>



              <tbody>

                {models.map((model) => (

                  <tr key={model.model_name}>

                    <td>

                      <strong>{model.model_name}</strong>

                    </td>



                    <td>

                      <StatusBadge

                        value={

                          model.loaded

                            ? "Loaded"

                            : "Unavailable"

                        }

                      />

                    </td>



                    <td>

                      {model.version ?? "Not recorded"}

                    </td>



                    <td>

                      {model.validation_metrics

                        ? Object.entries(

                            model.validation_metrics

                          )

                            .slice(0, 3)

                            .map(([key, value]) => (

                              <span

                                className="table-metric"

                                key={key}

                              >

                                {key}:{" "}

                                {typeof value === "number"

                                  ? value.toFixed(3)

                                  : String(value)}

                              </span>

                            ))

                        : "Not recorded"}

                    </td>



                    <td>

                      {model.test_metrics

                        ? Object.entries(

                            model.test_metrics

                          )

                            .slice(0, 3)

                            .map(([key, value]) => (

                              <span

                                className="table-metric"

                                key={key}

                              >

                                {key}:{" "}

                                {typeof value === "number"

                                  ? value.toFixed(3)

                                  : String(value)}

                              </span>

                            ))

                        : "Not recorded"}

                    </td>

                  </tr>

                ))}

              </tbody>

            </table>

          </div>

        </section>

      )}

    </div>

  );

}



export function SettingsPage() {
  const { user, logout } = useAuth();

  const [congestionAlerts, setCongestionAlerts] = useState(
    localStorage.getItem("smarter_congestion_alerts") !== "false"
  );

  const [bedShortageAlerts, setBedShortageAlerts] = useState(
    localStorage.getItem("smarter_bed_shortage_alerts") !== "false"
  );

  const [criticalAlerts, setCriticalAlerts] = useState(
    localStorage.getItem("smarter_critical_alerts") !== "false"
  );

  const [alertSound, setAlertSound] = useState(
    localStorage.getItem("smarter_alert_sound") !== "false"
  );

  const updatePreference = (
    key: string,
    value: boolean,
    setter: (value: boolean) => void
  ) => {
    setter(value);
    localStorage.setItem(key, String(value));
  };

  return (
    <div className="page-content">
      <PageHeader
        eyebrow="Account"
        title="Settings"
        description="Review your SmartER account and local notification preferences."
      />

      <section className="surface settings-card">
        <p className="eyebrow">Signed-in profile</p>

        <h2>{user?.full_name}</h2>

        <p>{user?.email}</p>

        <StatusBadge
          value={user?.role.replace("_", " ") ?? "Unknown"}
        />

        <div className="setting-row">
          <span>Congestion alerts</span>

          <input
            type="checkbox"
            checked={congestionAlerts}
            onChange={(event) =>
              updatePreference(
                "smarter_congestion_alerts",
                event.target.checked,
                setCongestionAlerts
              )
            }
          />
        </div>

        <div className="setting-row">
          <span>Bed shortage alerts</span>

          <input
            type="checkbox"
            checked={bedShortageAlerts}
            onChange={(event) =>
              updatePreference(
                "smarter_bed_shortage_alerts",
                event.target.checked,
                setBedShortageAlerts
              )
            }
          />
        </div>

        <div className="setting-row">
          <span>Critical alerts</span>

          <input
            type="checkbox"
            checked={criticalAlerts}
            onChange={(event) =>
              updatePreference(
                "smarter_critical_alerts",
                event.target.checked,
                setCriticalAlerts
              )
            }
          />
        </div>

        <div className="setting-row">
          <span>Alert sound</span>

          <input
            type="checkbox"
            checked={alertSound}
            onChange={(event) =>
              updatePreference(
                "smarter_alert_sound",
                event.target.checked,
                setAlertSound
              )
            }
          />
        </div>

        <p className="muted">
          These preferences are saved locally in this browser.
        </p>

        <button
          className="primary-button"
          onClick={logout}
        >
          Sign out securely
        </button>
      </section>
    </div>
  );
}



export function BackendPendingPage({

  title,

  description,

}: {

  title: string;

  description: string;

}) {

  return (

    <div className="page-content">

      <PageHeader

        eyebrow="Integration pending"

        title={title}

        description={description}

      />



      <EmptyState

        title="No backend endpoint available"

        message="SmartER will show this view when its corresponding authenticated API is implemented. No operational values are being fabricated in the meantime."

      />

    </div>

  );

}



export function WhatIfPage() {
  const [beds, setBeds] = useState(0);
  const [doctors, setDoctors] = useState(0);
  const [nurses, setNurses] = useState(0);
  const [arrivalChange, setArrivalChange] = useState(0);

  const [pressure, setPressure] = useState("No demand adjustment");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function runScenario() {
    setBusy(true);
    setError("");

    try {
      const result = await intelligenceApi.whatIf({
        additional_beds: beds,
        additional_doctors: doctors,
        additional_nurses: nurses,
        expected_arrival_change: arrivalChange,
      });

      setPressure(result.demand_pressure);
    } catch (reason) {
      setError(apiErrorMessage(reason));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="page-content">
      <PageHeader
        eyebrow="Scenario planning"
        title="What-if analysis"
        description="A transparent rule-based scenario worksheet. It does not claim to be an ML optimization or clinical recommendation."
      />

      <section className="surface">
        <div className="input-grid simulation-grid">
          <label>
            Additional beds
            <input
              type="number"
              min="0"
              value={beds}
              onChange={(event) =>
                setBeds(Number(event.target.value))
              }
            />
          </label>

          <label>
            Additional doctors
            <input
              type="number"
              min="0"
              value={doctors}
              onChange={(event) =>
                setDoctors(Number(event.target.value))
              }
            />
          </label>

          <label>
            Additional nurses
            <input
              type="number"
              min="0"
              value={nurses}
              onChange={(event) =>
                setNurses(Number(event.target.value))
              }
            />
          </label>

          <label>
            Expected arrival change
            <input
              type="number"
              value={arrivalChange}
              onChange={(event) =>
                setArrivalChange(Number(event.target.value))
              }
            />
          </label>
        </div>

        <button
          className="primary-button"
          onClick={runScenario}
          disabled={busy}
        >
          {busy ? "Running scenario..." : "Run scenario"}
        </button>

        {error && <ErrorState message={error} />}

        <div className="simulation-result">
          <p className="eyebrow">Rule-based scenario output</p>

          <h2>{pressure}</h2>

          <p className="muted">
            Capacity adjustments: +{beds} beds, +{doctors} doctors,
            +{nurses} nurses.
          </p>
        </div>
      </section>
    </div>
  );
}



export function AnalyticsPage() {

  const [data, setData] =

    useState<AnalyticsResponse | null>(null);



  const [error, setError] = useState("");

  const [busy, setBusy] = useState(true);

  const [start, setStart] = useState("");

  const [end, setEnd] = useState("");



  async function load() {

    setBusy(true);

    setError("");



    try {

      setData(

        await analyticsApi.summary(

          start || undefined,

          end || undefined

        )

      );

    } catch (reason) {

      setError(apiErrorMessage(reason));

    } finally {

      setBusy(false);

    }

  }



  useEffect(() => {

    let active = true;



    analyticsApi

      .summary()

      .then((response) => {

        if (active) {

          setData(response);

        }

      })

      .catch((reason) => {

        if (active) {

          setError(apiErrorMessage(reason));

        }

      })

      .finally(() => {

        if (active) {

          setBusy(false);

        }

      });



    return () => {active = false;

    };

  }, []);



  return (

    <div className="page-content">

      <PageHeader

        eyebrow="Historical performance"

        title="Analytics"

        description="Historical measurements and saved model outputs from the operational database. These charts only show records that actually exist."

      />



      <section className="surface analytics-controls">

        <label>

          From

          <input

            aria-label="Analytics start date"

            type="date"

            value={start}

            onChange={(event) =>

              setStart(event.target.value)

            }

          />

        </label>



        <label>

          Through

          <input

            aria-label="Analytics end date"

            type="date"

            value={end}

            onChange={(event) =>

              setEnd(event.target.value)

            }

          />

        </label>



        <button

          className="primary-button"

          onClick={() => void load()}

          disabled={busy}

        >

          {busy ? "Loading..." : "Apply range"}

        </button>



        {data?.summary.first_recorded_at && (

          <span className="data-note">

            Stored range:{" "}

            {new Date(

              data.summary.first_recorded_at

            ).toLocaleDateString()}{" "}

            –{" "}

            {new Date(

              data.summary.last_recorded_at ??

                data.summary.first_recorded_at

            ).toLocaleDateString()}

          </span>

        )}

      </section>



      {error && (

        <ErrorState

          message={error}

          retry={() => void load()}

        />

      )}



      {busy && !data && <LoadingSpinner />}



      {data && (

        <>

          <div className="metric-grid">

            <MetricCard

              label="Observed metric rows"

              value={data.summary.observed_metric_count}

              detail="persisted ERMetric rows"

            />



            <MetricCard

              label="Arrival forecast rows"

              value={data.summary.forecast_count}

              detail="persisted predictions"

              tone="teal"

            />



            <MetricCard

              label="Congestion predictions"

              value={data.summary.congestion_prediction_count}

              detail="persisted classifications"

              tone="orange"

            />



            <MetricCard

              label="Resource predictions"

              value={data.summary.resource_prediction_count}

              detail="persisted resource rows"

            />

          </div>



          <section className="dashboard-grid">

            <div className="surface">

              <div className="section-heading">

                <div>

                  <p className="eyebrow">

                    Observed measurements

                  </p>

                  <h2>Patient arrivals</h2>

                </div>

              </div>



              {data.observed_metrics.length ? (

                <ObservedArrivalsChart

                  data={data.observed_metrics}

                />

              ) : (

                <EmptyState

                  title="No observed arrival history"

                  message="No ERMetric arrival rows are stored for this range."

                />

              )}

            </div>



            <div className="surface">

              <div className="section-heading">

                <div>

                  <p className="eyebrow">

                    Observed measurements

                  </p>

                  <h2>Waiting and occupancy</h2>

                </div>

              </div>



              {data.observed_metrics.length ? (

                <ObservedWaitingOccupancyChart

                  data={data.observed_metrics}

                />

              ) : (

                <EmptyState

                  title="No waiting or occupancy history"

                  message="No persisted ER metric rows are available for this range."

                />

              )}

            </div>

          </section>



          <section className="dashboard-grid">

            <div className="surface">

              <div className="section-heading">

                <div>

                  <p className="eyebrow">Model outputs</p>

                  <h2>Predicted resource requirements</h2>

                </div>

              </div>



              {data.resource_history.length ? (

                <ResourceHistoryChart

                  data={data.resource_history}

                />

              ) : (

                <EmptyState

                  title="No resource prediction history"

                  message="Resource predictions appear here after authenticated prediction runs are stored."

                />

              )}

            </div>



            <div className="surface">

              <div className="section-heading">

                <div>

                  <p className="eyebrow">Model outputs</p>

                  <h2>Congestion trend</h2>

                </div>

              </div>



              {data.congestion_history.length ? (

                <div className="recommendation-list">

                  {data.congestion_history.map(

                    (point, index) => (

                      <article

                        className="history-row"

                        key={`${point.target_timestamp}-${index}`}

                      >

                        <time>

                          {new Date(

                            point.target_timestamp

                          ).toLocaleString()}

                        </time>



                        <StatusBadge

                          value={

                            point.congestion_level ??

                            "Not classified"

                          }

                        />



                        <span>

                          {point.confidence === null

                            ? "Confidence unavailable"

                            : `${Math.round(

                                point.confidence * 100

                              )}% confidence`}

                        </span>

                      </article>

                    )

                  )}

                </div>

              ) : (

                <EmptyState

                  title="No congestion history"

                  message="No congestion predictions are persisted for this range."

                />

              )}

            </div>

          </section>



          <section className="surface">

            <div className="section-heading">

              <div>

                <p className="eyebrow">Data availability</p>

                <h2>Other historical signals</h2>

              </div>

            </div>



            <EmptyState

              title="Triage and staff history unavailable"

              message="The current ERMetric schema does not persist triage distribution or historical doctor/nurse availability. This view will not infer or fabricate those values."

            />

          </section>

        </>

      )}

    </div>

  );

}



export function RecommendationsPage() {

  const [items, setItems] =

    useState<IntelligenceRecommendation[] | null>(null);



  const [error, setError] = useState("");

  const [filter, setFilter] = useState("ALL");



  useEffect(() => {

    intelligenceApi

      .latestRecommendations()

      .then(setItems)

      .catch((reason) => setError(apiErrorMessage(reason)));

  }, []);



  const filtered = (items ?? []).filter(

    (item) =>

      filter === "ALL" || item.priority === filter

  );



  return (

    <div className="page-content">

      <PageHeader

        eyebrow="Operational guidance"

        title="Recommendations"

        description="Transparent, rule-based operational suggestions created from model outputs and measurable scenario thresholds. They are not autonomous medical decisions."

      />



      {error && <ErrorState message={error} />}



      {!items && !error && <LoadingSpinner />}



      <div

        className="filter-row"

        aria-label="Filter recommendations"

      >

        {["ALL", "CRITICAL", "HIGH", "MODERATE", "LOW"].map(

          (priority) => (

            <button

              key={priority}

              className={

                filter === priority

                  ? "filter-button selected"

                  : "filter-button"

              }

              onClick={() => setFilter(priority)}

            >

              {priority}

            </button>

          )

        )}

      </div>



      {items && !filtered.length && (

        <EmptyState

          title="No recommendations"

          message="No persisted recommendations match this filter."

        />

      )}



      <div className="recommendation-list">

        {filtered.map((item) => (

          <article

            className="surface recommendation-card"

            key={

              item.id ??

              `${item.timestamp}-${item.title}`

            }

          >

            <div className="recommendation-top">

              <StatusBadge value={item.priority} />



              <time>

                {new Date(

                  item.timestamp

                ).toLocaleString()}

              </time>

            </div>



            <h2>{item.title}</h2>



            <p>{item.reason}</p>



            <strong>Supporting metric</strong>



            <span>{item.supporting_metric}</span>

          </article>

        ))}

      </div>

    </div>

  );

}



export function AlertsPage() {

  const { user } = useAuth();



  const [items, setItems] =

    useState<OperationalAlert[] | null>(null);



  const [error, setError] = useState("");

  const [filter, setFilter] = useState("ALL");



  async function refresh() {

    try {

      setItems(await intelligenceApi.alerts());

      setError("");

    } catch (reason) {

      setError(apiErrorMessage(reason));

    }

  }



  useEffect(() => {

    let active = true;



    intelligenceApi

      .alerts()

      .then((data) => {

        if (active) {

          setItems(data);

        }

      })

      .catch((reason) => {

        if (active) {

          setError(apiErrorMessage(reason));

        }

      });



    return () => {

      active = false;

    };

  }, []);



  async function resolve(alertId: number) {

    try {

      await intelligenceApi.resolveAlert(alertId);

      await refresh();

    } catch (reason) {

      setError(apiErrorMessage(reason));

    }

  }



  const filtered = (items ?? []).filter(

    (alert) =>

      filter === "ALL" ||

      (filter === "RESOLVED"

        ? alert.status === "RESOLVED"

        : filter === "OPEN"

        ? alert.status === "OPEN"

        : alert.severity === filter)

  );



  const canResolve =

    user?.role === "ADMIN" ||

    user?.role === "TRIAGE_NURSE";



  return (

    <div className="page-content">

      <PageHeader

        eyebrow="Measured conditions"

        title="Operational alerts"

        description="Alerts are generated from score, forecast, resource, and waiting-time thresholds. No randomized alerts are used."

      />



      {error && (

        <ErrorState

          message={error}

          retry={() => void refresh()}

        />

      )}



      <div className="filter-row">

        {[

          "ALL",

          "CRITICAL",

          "HIGH",

          "MODERATE",

          "LOW",

          "OPEN",

          "RESOLVED",

        ].map((severity) => (

          <button

            key={severity}

            className={

              filter === severity

                ? "filter-button selected"

                : "filter-button"

            }

            onClick={() => setFilter(severity)}

          >

            {severity}

          </button>

        ))}

      </div>



      {!items && !error && <LoadingSpinner />}



      {items && !filtered.length && (

        <EmptyState

          title="No matching alerts"

          message="There are no persisted alerts matching this filter."

        />

      )}



      <div className="recommendation-list">

        {filtered.map((alert) => (

          <article

            className="surface alert-card"

            key={alert.id}

          >

            <div className="recommendation-top">

              <StatusBadge value={alert.severity} />



              <span>{alert.status}</span>



              <time>

                {new Date(

                  alert.timestamp

                ).toLocaleString()}

              </time>

            </div>



            <h2>{alert.title}</h2>



            <p>{alert.description}</p>



            <div className="alert-measure">

              Trigger:{" "}

              {alert.trigger_value ?? "Not recorded"}



              <span>

                Threshold:{" "}

                {alert.threshold ?? "Not recorded"}

              </span>

            </div>



            {canResolve &&

              alert.status !== "RESOLVED" && (

                <button

                  className="text-button"

                  onClick={() =>

                    void resolve(alert.id)

                  }

                >

                  Resolve alert

                </button>

              )}

          </article>

        ))}

      </div>

    </div>

  );

}



export function ExplainableAIPage() {

  const [model, setModel] =

    useState<ExplainModel>("congestion_classifier");



  const [result, setResult] =

    useState<ExplanationResponse | null>(null);



  const [error, setError] = useState("");

  const [busy, setBusy] = useState(false);



  async function explain(input: PredictionInput) {

    setBusy(true);

    setError("");try {

      setResult(

        await intelligenceApi.explain(model, input)

      );

    } catch (reason) {

      setError(apiErrorMessage(reason));

    } finally {

      setBusy(false);

    }

  }



  const maxImportance = Math.max(

    1,

    ...(result?.top_contributing_features.map(

      (feature) => feature.mean_absolute_shap

    ) ?? [])

  );



  return (

    <div className="page-content">

      <PageHeader

        eyebrow="Model transparency"

        title="Explainable AI"

        description="Explore saved Phase 4 SHAP feature-importance summaries alongside a real prediction from the selected model."

      />



      <section className="surface explain-panel">

        <label className="model-select">

          Model to explain



          <select

            value={model}

            onChange={(event) =>

              setModel(

                event.target.value as ExplainModel

              )

            }

          >

            <option value="congestion_classifier">

              Congestion classifier

            </option>



            <option value="bed_prediction_model">

              Bed requirement

            </option>



            <option value="doctor_prediction_model">

              Doctor requirement

            </option>



            <option value="nurse_prediction_model">

              Nurse requirement

            </option>

          </select>

        </label>



        <PredictionInputForm

          onSubmit={explain}

          busy={busy}

        />



        {error && <ErrorState message={error} />}



        {busy && (

          <LoadingSpinner label="Preparing explanation..." />

        )}



        {result && (

          <>

            <div className="section-heading">

              <div>

                <p className="eyebrow">

                  {result.model_name} · v

                  {result.model_version}

                </p>



                <h2>

                  Prediction: {String(result.prediction)}

                </h2>

              </div>



              <time>

                {new Date(

                  result.timestamp

                ).toLocaleString()}

              </time>

            </div>



            <p className="muted">

              {result.interpretation}

            </p>



            {result.top_contributing_features.length ? (

              <div className="feature-list">

                {result.top_contributing_features.map(

                  (feature) => (

                    <div

                      className="feature-row"

                      key={feature.feature}

                    >

                      <div className="feature-heading">

                        <strong>

                          {feature.feature.replaceAll(

                            "\_",

                            " "

                          )}

                        </strong>



                        <span>

                          Input:{" "}

                          {feature.feature_value ??

                            "Not available"}{" "}

                          · Mean |SHAP|:{" "}

                          {feature.mean_absolute_shap.toFixed(

                            4

                          )}

                        </span>

                      </div>



                      <div className="feature-track">

                        <span

                          style={{

                            width: `${Math.max(

                              2,

                              (feature.mean_absolute_shap /

                                maxImportance) *

                                100

                            )}%`,

                          }}

                        />

                      </div>

                    </div>

                  )

                )}

              </div>

            ) : (

              <EmptyState

                title="No SHAP summary available"

                message="The selected model has no saved feature-contribution summary."

              />

            )}



            <section className="interpretation-note">

              <strong>How to interpret this</strong>



              <p>

                {result.interpretation} Contributions are

                global mean absolute importance in the saved

                summary; signed scenario-level contributions

                are not available.

              </p>

            </section>

          </>

        )}

      </section>

    </div>

  );

}