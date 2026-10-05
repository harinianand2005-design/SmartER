# SmartER Intelligence Layer

## Scope and safety

This layer combines persisted ML predictions with transparent operational rules. It supports review by authorized operational staff; it is not a medical diagnosis, clinical instruction, or autonomous decision system. Its thresholds and weights are academic prototype assumptions, not validated clinical standards.

## SmartER Congestion Score

The score is bounded to 0-100 and returned with each component value, weighted contribution, and explanation:

| Component | Weight | Normalization |
|---|---:|---|
| ER occupancy | 30% | Current patients / (current patients + available beds) x 100 |
| Next-hour arrivals | 20% | Model forecast / 20 x 100, bounded to 0-100 |
| Bed pressure | 20% | Positive predicted required-bed gap / available beds x 100, bounded |
| Waiting time | 20% | Average waiting minutes / 120 x 100, bounded |
| Staffing pressure | 10% | 100 minus mean doctor and nurse scheduled availability percentages |

The weighted component sum is bounded to 0-100. A small classifier-level adjustment is included: +5 for HIGH and +10 for CRITICAL; the result is bounded again. Level boundaries are LOW 0-30, MODERATE 31-60, HIGH 61-80, and CRITICAL 81-100. Classifier confidence is shown separately and is not the score.

## Recommendation rules

Recommendations are produced from actual model results and submitted operational values:

- HIGH or CRITICAL score: increase monitoring frequency.
- Required beds greater than available beds: review bed allocation and expected discharge capacity.
- Required doctors greater than available doctors: review upcoming staffing coverage.
- Required nurses greater than available nurses: review nursing coverage.
- Forecast arrivals above the available-bed comparison: prepare additional operational capacity.
- No configured rule triggered: continue routine monitoring.

Each persisted item includes priority, reason, supporting metric, timestamp, and status. Suggestions do not direct clinical care or perform actions.

## Alert rules

Alerts are generated only from measurable values: score at least 61/81 for HIGH/CRITICAL, predicted resource requirements above availability, next-hour arrivals above `max(current arrivals + 5, current arrivals x 1.5)`, or waiting time at least 120 minutes. Duplicate OPEN alerts of the same type and ER unit are suppressed. ADMIN and TRIAGE_NURSE can resolve alerts; listing is authenticated.

## SHAP interpretation

Explainability uses the saved Phase 4 SHAP summaries and an actual prediction from the selected persisted model. Existing summaries contain global mean absolute SHAP importance. They do not contain signed per-scenario SHAP values or base values, so the API reports `base_value: null` and does not claim positive/negative local contribution. Feature values are included when present in the inference vector.

Use the phrase “Features contributing to the model prediction.” SHAP contribution is not medical causation.

## Limitations

- Inputs are submitted snapshots, not a live hospital feed.
- Models and SHAP summaries are based on synthetic academic data.
- The score's formulas, weights, and thresholds are not clinically validated.
- No historical analytics service or true real-time stream is provided by this phase.# SmartER Intelligence Layer

## Purpose and safety boundary

The Phase 7 intelligence layer combines existing Phase 4 model outputs with explicit operational rules. It is an academic operational decision-support prototype. It does not make diagnoses, provide clinical instructions, or make autonomous decisions. Scores and recommendations must be reviewed by authorized staff.

## SmartER Congestion Score

The score is transparent and bounded to 0-100. The current implementation calculates five normalized pressure components and weights them as follows:

| Component | Weight | Normalization |
|---|---:|---|
| Current ER occupancy | 30% | Current patients / (current patients + available beds) x 100 |
| Predicted next-hour arrivals | 20% | Forecast arrivals / 20 x 100, bounded to 0-100 |
| Bed pressure | 20% | Positive predicted bed gap / available beds x 100, bounded |
| Average waiting time | 20% | Waiting minutes / 120 x 100, bounded |
| Staff pressure | 10% | 100 minus mean doctor/nurse scheduled availability percentage |

For high/critical classifier outputs, a small transparent offset is added before clamping to 0-100: +5 for HIGH and +10 for CRITICAL. The score endpoint returns every factor's value and weighted contribution, plus classifier confidence when available.

Score bands are exactly: 0-30 LOW, 31-60 MODERATE, 61-80 HIGH, and 81-100 CRITICAL.

## Recommendation rules

Rules consume actual forecast, congestion, and resource model outputs for the submitted scenario:

- HIGH/CRITICAL score: increase monitoring frequency.
- Required beds exceed available beds: review bed allocation and expected discharge capacity.
- Required doctors exceed available doctors: review upcoming staffing coverage.
- Required nurses exceed available nurses: review nursing coverage.
- Next-hour forecast exceeds the configured available-bed comparison: prepare operational capacity.
- No threshold met: continue routine monitoring.

Each generated item contains priority, reason, supporting metric, timestamp, and OPEN status. Recommendations are persisted. They are suggestions for operational review, not autonomous actions.

## Alert rules

Alerts are generated only from measurable scenario values. Current rules cover HIGH/CRITICAL score, bed/doctor/nurse shortage, next-hour arrival spike relative to the submitted arrival baseline, and waiting time of at least 120 minutes. An open alert of the same type for the same ER unit is not duplicated. Alert resolution is available to ADMIN and TRIAGE_NURSE; listing requires an authenticated supported role.

## Explainability

The explain endpoint supports the congestion classifier and the bed, doctor, and nurse regressors. It combines the actual selected model prediction with saved Phase 4 SHAP summaries. Current Phase 4 summaries contain global mean absolute SHAP importance, not signed local scenario contributions; therefore the response includes feature values and global importance but reports `base_value` as unavailable. Wording is limited to “Features contributing to the model prediction.” SHAP values are not medical causation.

## Limitations

- Inputs are scenario submissions, not a live hospital feed.
- Phase 4 model and SHAP results are based on synthetic academic data.
- Historical analytics endpoints and a dedicated What-If service are not included in this phase.
- Rule thresholds and score weights are configurable methodology assumptions, not validated clinical standards.
- The score is a summary signal and should not replace review of its displayed factors.