# Data sources and ingestion notes

## FDA MQSA facility information

The FDA maintains a searchable listing of certified mammography facilities and describes the database as periodically updated. The MVP does not assume that the public search interface is a stable bulk API. Production snapshots should archive a dated export or reproducible, reviewed extraction and retain provenance metadata.

Official entry point: <https://www.fda.gov/findmammography>

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

No production geocoder is bundled. Facility coordinates should be generated using a documented geocoder, cached, quality-checked, and manually reviewed for events that drive alerts.

## Fixture-based testing

CI tests should not depend on live FDA, CDC, Census, CMS, geocoding, or routing endpoints. Adapter
tests should use fixture files or mocked responses and reserve live endpoint checks for manually
triggered workflows with explicit credentials and source review.
