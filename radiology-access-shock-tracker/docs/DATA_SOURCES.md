# Data sources and ingestion notes

## FDA MQSA facility information

The FDA maintains a searchable listing of certified mammography facilities and describes the database as periodically updated. The MVP does not assume that the public search interface is a stable bulk API. Production snapshots should archive a dated export or reproducible, reviewed extraction and retain provenance metadata.

Official entry point: <https://www.fda.gov/findmammography>

Official public ZIP: <https://www.accessdata.fda.gov/premarket/ftparea/public.zip>

The production workflow now supports `radshock fetch-fda-mqsa` for downloading and archiving the
weekly ZIP, `radshock archive-source` for manually downloaded files, and
`radshock prepare-mqsa-review` for creating a human-review CSV. The FDA page documents a fixed-width
layout, while the live ZIP retrieved on 2026-06-19 contained pipe-delimited rows with the same
logical fields. The parser supports both formats and records the observed `source_schema_version`.
The layout includes facility name, address lines, city, state, ZIP, phone, and fax. It does not
provide stable tracker IDs, coordinates, capacity, or verified active status, so the review CSV
leaves those fields blank before snapshot ingestion.

`radshock finalize-mqsa-review` is the required gate between the FDA review CSV and a
snapshot-ready facility file. It fails if any row remains `needs_review` or if `facility_id`,
`latitude`, `longitude`, `annual_capacity`, or `active` is blank. Approved review statuses are
`reviewed`, `verified`, and `approved`.

## CDC PLACES

The CDC PLACES county dataset provides model-based small-area estimates. The adapter uses the official Socrata resource endpoint for the current county dataset and filters for North Carolina mammography records. Measurement year and data-value type must remain visible in downstream products.

Official dataset: <https://data.cdc.gov/resource/swc5-untb.json>

## American Community Survey

The ACS 5-year API supplies county socioeconomic context. The included adapter retrieves poverty and vehicle-access components for North Carolina counties. Variable definitions and release-year changes must be reviewed whenever the configured ACS year changes. The Census developer documentation currently states that ACS API queries require an API key, so production workflows should read the key from local configuration or environment variables rather than committing it.

Official API documentation: <https://www.census.gov/data/developers/data-sets/acs-5year.html>

## CMS provider/service data

CMS publishes Medicare Physician and Other Practitioners data by provider and service. The included adapter accepts a downloaded extract and explicit source-column mappings because release schemas and analytic choices can change. Medicare fee-for-service utilization does not represent the entire population.

Official dataset family: <https://data.cms.gov/provider-summary-by-type-of-service/medicare-physician-other-practitioners>

## Geocoding

`radshock geocode-mqsa-review` can fill candidate coordinates in an MQSA review CSV before human
review. The default live provider uses the US Census Geocoder single-address endpoint with
structured street, city, state, ZIP, benchmark, and JSON response parameters. The Census geocoder
documentation states that the service supports US, Puerto Rico, and US Island Areas addresses.

Official API documentation:
<https://geocoding.geo.census.gov/geocoder/Geocoding_Services_API.html>

Live geocoder results are cached under `data/cache/geocoding/` by normalized address and provider.
The output keeps `geocode_status`, provider, matched address, benchmark, source URL, cache flag,
retrieval timestamp, and error columns. Candidate coordinates remain unapproved: review rows must
still be checked and marked `reviewed`, `verified`, or `approved` before
`radshock finalize-mqsa-review` will produce a snapshot-ready file.

## Fixture-based testing

CI tests should not depend on live FDA, CDC, Census, CMS, geocoding, or routing endpoints. Adapter
tests should use fixture files or mocked responses and reserve live endpoint checks for manually
triggered workflows with explicit credentials and source review.
