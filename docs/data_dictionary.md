# SmartER Synthetic Dataset Dictionary

This dictionary describes the synthetic hourly ER operations dataset. It contains no names, identifiers, diagnoses, or other personal information. Ranges describe generator expectations and validation bounds, not real hospital statistics.

| Column | Type | Description | Example | Input feature | Future target | Expected range |
|---|---|---|---|---|---|---|
| `timestamp` | datetime UTC | Hour beginning timestamp | `2022-01-01T00:00:00Z` | Yes | No | Valid UTC datetime |
| `patient_arrivals` | integer | Patients arriving in the hour | `9` | Yes | Yes | >= 0 |
| `current_patients` | integer | Patients currently in the ER | `31` | Yes | No | >= 0 |
| `available_beds` | integer | Beds available in the synthetic unit | `17` | Yes | No | >= 0 |
| `doctors_available` | integer | Doctors available during the hour | `5` | Yes | No | >= 0 and <= scheduled |
| `nurses_available` | integer | Nurses available during the hour | `16` | Yes | No | >= 0 and <= scheduled |
| `average_waiting_time` | float | Aggregate waiting time in minutes | `48.2` | Yes | No | 0 to 1440 |
| `triage_1` to `triage_5` | integer | Counts by triage acuity level | `2` | Yes | No | >= 0; sum equals arrivals |
| `temperature` | float | Synthetic outdoor temperature | `9.4` | Yes | No | Approx. -10 to 40 C |
| `rainfall` | float | Synthetic rainfall in millimetres | `2.7` | Yes | No | >= 0 |
| `holiday` | integer | Synthetic fixed-date holiday flag | `0` | Yes | No | 0 or 1 |
| `local_event` | integer | Synthetic local-event flag | `1` | Yes | No | 0 or 1 |
| `flu_index` | float | Synthetic seasonal flu pressure index | `61.5` | Yes | No | 0 to 100 |
| `weather_category` | category | Derived weather label | `rain` | Yes | No | clear, rain, storm |
| `doctors_scheduled` | integer | Scheduled doctors before availability variation | `8` | Yes | No | > 0 |
| `nurses_scheduled` | integer | Scheduled nurses before availability variation | `18` | Yes | No | > 0 |

## Engineered features

`hour`, `day_of_week`, `day_of_month`, `month`, `is_weekend`, and `is_holiday` are calendar features. `previous_1hr_arrivals`, `previous_3hr_arrivals`, `previous_6hr_arrivals`, and `previous_24hr_arrivals` use only completed prior intervals. The rolling averages use the same past-only windows.

`occupancy_percentage` and `bed_availability_percentage` use current patients plus available beds as the observed capacity denominator. Doctor and nurse availability percentages use scheduled staffing as their denominator. `event_indicator` combines holiday and local-event flags. `rainy_flag` marks rainfall of at least 2 mm, and `flu_index_change_24hr` compares the index with the prior day.

## Future targets

`next_hour_arrivals`, `next_3hr_arrivals`, `next_6hr_arrivals`, and `next_24hr_arrivals` are forward-looking labels and must never be used as input features. `congestion_level` is a transparent academic label for the next interval based on next-interval occupancy/wait thresholds. `required_beds`, `required_doctors`, and `required_nurses` are prepared operational targets for later phases; they are not model predictions.