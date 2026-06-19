# Data directory

Production data are intentionally not committed by default.

Expected inputs:

- `snapshots/YYYY-MM-DD/facilities.csv`: validated facility snapshot.
- `population_points.csv`: small-area population points and weights.
- `counties.csv`: county names, centroids, population, and vulnerability context.
- `candidate_sites.csv`: hypothetical mobile or fixed response locations.
- `utilization.csv`: period-by-county screening services and denominator.

Use `radshock demo` to generate fully synthetic examples of every input and output schema.
Never commit patient-level information, protected health information, API secrets, or licensed data that prohibit redistribution.
