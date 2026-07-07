# All-States Data Package

Generated: `2026-07-07T04:27:33.208878+00:00`

Package directory: `work\all-states\2026-07-06-rebuild`

## What Was Gathered

- FDA MQSA national source rows: `8918`
- FDA MQSA review-template rows: `8918`
- HRSA source rows: `18938`
- HRSA candidate review-template rows: `17444`
- CDC PLACES mammography rows: `6288`
- CDC/ATSDR SVI county rows: `3144`
- Census county Gazetteer rows: `3144`
- Census tract Gazetteer rows: `84415`
- ACS county context rows: `0`
- ACS tract context rows: `0`

## Coverage

- States in scope: `51`
- States with MQSA rows: `51`
- States with HRSA candidate rows: `51`
- States with CDC PLACES mammography rows: `51`
- States with CDC/ATSDR SVI county rows: `51`
- States with Census counties: `51`
- States with Census tracts: `51`
- States with all public no-secret sources present: `51`
- States with ACS county context: `0`
- States with ACS tract context: `0`

## Coverage Gaps

- Public no-secret source coverage: no state gaps detected.
- missing_acs_county_context: AK, AL, AR, AZ, CA, CO, CT, DC, DE, FL, GA, HI, and 39 more
- missing_acs_tract_context: AK, AL, AR, AZ, CA, CO, CT, DC, DE, FL, GA, HI, and 39 more

## Highest MQSA Row Counts

| State | MQSA rows | HRSA candidates | PLACES counties |
|---|---:|---:|---:|
| CA | 772 | 2721 | 58 |
| FL | 651 | 735 | 67 |
| TX | 627 | 761 | 254 |
| NY | 550 | 828 | 62 |
| IL | 358 | 519 | 102 |
| PA | 341 | 456 | 67 |
| OH | 330 | 592 | 88 |
| GA | 307 | 442 | 159 |

## Readiness Gates

- ACS county/tract context is incomplete; missing county context for AK, AL, AR, AZ, CA, CO, CT, DC, DE, FL, GA, HI, and 39 more; missing tract context for AK, AL, AR, AZ, CA, CO, CT, DC, DE, FL, GA, HI, and 39 more.

## Key Files

- `review/fda_mqsa_all_50_review.csv`
- `review/hrsa_candidate_sites_all_50_review.csv`
- `context/cdc_places_mammography_all_50.csv`
- `context/cdc_atsdr_svi_counties_all_50.csv`
- `context/census_counties_gazetteer_all_50.csv`
- `context/census_tracts_gazetteer_all_50.csv`
- `summary/state_source_summary.csv`
- `summary/state_readiness_gates.csv`
- `summary/data_package_manifest.json`
