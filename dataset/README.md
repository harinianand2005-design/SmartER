# SmartER Dataset

All files in this directory are synthetic or anonymized operational data for academic demonstration. No real patient personal information is used or permitted.

- `raw/`: source files before cleaning.
- `generated/`: reproducible synthetic source data created by `ml.data.generator`.
- `processed/`: validated, feature-engineered chronological training, validation, and test exports.

Generate the default three-year hourly dataset from the repository root:

```powershell
C:/Users/harin/AppData/Local/Programs/Python/Python314/python.exe -m ml.data.generator
```

The generator uses seed `42` by default. Patterns are intentionally synthetic and must not be presented as representative hospital statistics.# SmartER Dataset

Development and testing must use synthetic or fully anonymized emergency-room operational data. Do not place names, addresses, medical record numbers, contact details, or other personal information in this directory.

Expected time-series columns include:

- `timestamp`: interval start in ISO 8601 format.
- `er_unit_id`: non-identifying emergency-room unit identifier.
- `arrivals`, `departures`: event counts during the interval.
- `active_patients`, `waiting_patients`: operational patient counts.
- `occupied_beds`, `available_beds`: capacity measures.
- `average_wait_minutes`: aggregate waiting time.
- `critical_patient_count`: aggregate high-acuity count.
- `available_doctors`, `available_nurses`: available staffing counts.
- `scheduled_doctors`, `scheduled_nurses`: planned staffing counts.
- `holiday_flag`, `weekend_flag`, `local_event_flag`: synthetic contextual features.

Raw files belong in `raw/`; validated, transformed files belong in `processed/`. Dataset generation and validation will be implemented in Phase 2.