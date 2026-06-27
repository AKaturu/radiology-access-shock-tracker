# Data directory

Large or licensed production data should not be committed by default. Small public-data-derived
review artifacts may be committed when they are required for reproducible tests or documentation and
their provenance metadata is included.

Expected inputs:

- `snapshots/YYYY-MM-DD/facilities.csv`: validated facility snapshot.
- `source_metadata/*.metadata.json`: source archive metadata needed by readiness audits when raw
  source files are too large or unsuitable to commit.
- `population_points.csv`: small-area population points and weights.
- `counties.csv`: county names, centroids, population, and vulnerability context.
- `candidate_sites.csv`: reviewed hypothetical mobile or fixed response locations from
  `finalize-candidate-review`.
- `travel_times/*.csv`: reviewed or testing route-time matrices plus row-level route-review CSVs
  when provider metadata is needed for reproducibility.
- `utilization.csv`: period-by-county screening services and denominator.

Use `radshock demo` to generate fully synthetic examples of every input and output schema.
Never commit patient-level information, protected health information, API secrets, or licensed data that prohibit redistribution.
