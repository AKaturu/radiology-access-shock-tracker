# Production Completion Audit

**Overall status:** BLOCKED
**Blockers:** 2
**Warnings:** 0

| Domain | Check | Status | Value | Details |
|---|---|---|---|---|
| `review_owner` | `mqsa_snapshot` | PASS | 1 | Owner configured. |
| `review_owner` | `geocoding` | PASS | 1 | Owner configured. |
| `review_owner` | `routing` | PASS | 1 | Owner configured. |
| `review_owner` | `candidate_sites` | PASS | 1 | Owner configured. |
| `review_owner` | `publication` | PASS | 1 | Owner configured. |
| `credential` | `CENSUS_API_KEY` | PASS | set | Environment variable is present. |
| `routing` | `provider` | PASS | self-hosted-osrm | Routing provenance field configured. |
| `routing` | `profile` | PASS | driving | Routing provenance field configured. |
| `routing` | `traffic_assumption` | PASS | free-flow travel time; no live traffic | Routing provenance field configured. |
| `routing` | `matrix_metadata_json` | PASS | data/travel_times/2026-06-20_tract_nearest20_osrm_matrix.metadata.json | Routing provenance field configured. |
| `all_states_package` | `state_scope` | PASS | ALL_STATES | Package is scoped to all states. |
| `all_states_package` | `state_count` | PASS | 51 | Manifest reports 51 states. |
| `all_states_package` | `public_source_coverage` | PASS | 51 | No public no-secret source state gaps detected. |
| `all_states_package` | `acs_context_coverage` | BLOCKER | county=50; tract=50 | Set CENSUS_API_KEY and rebuild the package to add all-state ACS context. |
| `all_states_package` | `publication_status` | BLOCKER | not_ready_for_publication | Package manifest is not marked ready for publication. |
| `all_states_package` | `readiness_gates` | PASS | 0 | No unresolved all-state package readiness gates. |
| `analysis_readiness` | `overall_status` | PASS | READY | Analysis readiness report has 0 blocker(s) and 0 warning(s). |
