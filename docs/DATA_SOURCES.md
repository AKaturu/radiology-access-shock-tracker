# Data sources and ingestion notes

## FDA MQSA facility information

The FDA maintains a searchable listing of certified mammography facilities and describes the database as periodically updated. The MVP does not assume that the public search interface is a stable bulk API. Production snapshots should archive a dated export or reproducible, reviewed extraction and retain provenance metadata.

Official entry point: <https://www.fda.gov/findmammography>

Official public ZIP: <https://www.accessdata.fda.gov/premarket/ftparea/public.zip>

Official national statistics page:
<https://www.fda.gov/radiation-emitting-products/mammography-information-patients/mqsa-national-statistics>

The production workflow now supports `radshock fetch-fda-mqsa` for downloading and archiving the
weekly ZIP, `radshock archive-source` for manually downloaded files, and
`radshock prepare-mqsa-review` for creating a human-review CSV. The FDA page documents a fixed-width
layout, while the live ZIP retrieved on 2026-06-19 contained pipe-delimited rows with the same
logical fields. The parser supports both formats and records the observed `source_schema_version`.
The layout includes facility name, address lines, city, state, ZIP, phone, and fax. It does not
provide stable tracker IDs, coordinates, facility-level annual capacity, or verified active status,
so the review CSV leaves those fields blank before snapshot ingestion.

`radshock finalize-mqsa-review` is the required gate between the FDA review CSV and a
snapshot-ready facility file. It fails if any row remains `needs_review` or if `facility_id`,
`latitude`, `longitude`, or `active` is blank. Approved review statuses are `reviewed`, `verified`,
and `approved`. `annual_capacity` is optional and should remain blank unless a reviewed source or
explicitly labeled proxy supports it.

The FDA MQSA national statistics page reports total annual mammography procedures as an aggregate
national number from facility reports to accreditation bodies, not as a facility-level public
capacity field. NC DHSR's Registration and Inventory of Medical Equipment database may support
equipment or procedure proxy research, but its documentation describes it as in-process working data
and it should not be treated as authoritative facility annual capacity without review.

For the first 2026-06-19 NC reviewed snapshot, `facility_id` values were generated as deterministic
`MQSA-NC-<source_record_hash prefix>` identifiers because the FDA public ZIP did not expose a stable
facility ID. `active=true` was inferred from inclusion in the current FDA MQSA certified-facility
extract. These are reviewed snapshot fields, not raw FDA fields.

Official NC DHSR equipment database:
<https://info.ncdhhs.gov/dhsr/mfp/data/equipment.html>

## CDC PLACES

The CDC PLACES county dataset provides model-based small-area estimates. The adapter uses the official Socrata resource endpoint for the current county dataset and filters for North Carolina mammography records. Measurement year and data-value type must remain visible in downstream products.

Official dataset: <https://data.cdc.gov/resource/swc5-untb.json>

## American Community Survey

The ACS 5-year API supplies county socioeconomic context. `radshock fetch-census-county-context`
retrieves North Carolina county indicators and joins them to the Census county Gazetteer file for
county names, land area, and internal-point coordinates. The 2024 county context files are:

- `data/counties.csv`: access-engine county schema.
- `data/census_county_context_2024.csv`: source-rich Census/Gazetteer context.
- `data/population_points.csv`: county-centroid population points weighted by eligible population
  for smoke testing.
- `data/census_county_context_2024.metadata.json`: source URLs, derivation notes, and checksums.

`radshock fetch-census-population-points` retrieves North Carolina tract indicators and joins them
to the Census tract Gazetteer file for finer population-point inputs:

- `data/population_points_tracts.csv`: tract-centroid population points weighted by eligible
  population.
- `data/census_tract_context_2024.csv`: source-rich tract ACS/Gazetteer context.
- `data/census_tract_context_2024.metadata.json`: source URLs, derivation notes, and checksums.

The eligible-population field is ACS female population age 50-74, summed from `B01001_040E`
through `B01001_046E`, to align with the CDC PLACES mammography measure age band. The current
`rurality_index` is an inverse min-max scaling of Census population density within NC counties.
The current `high_risk_index` is a min-max scaling of ACS households with no vehicle available
within NC counties, used as a provisional access-vulnerability proxy. These derived indexes are
transparent analysis inputs, not clinically validated risk scores.

County-centroid population points are acceptable for local smoke testing. Tract-centroid points are
the preferred built-in public-data option for production review because they are finer than county
centroids, but they remain centroid approximations and require regenerated route matrices before
publication. Variable definitions and release-year changes must be reviewed whenever the configured
ACS year changes. The Census developer documentation currently states that ACS API queries require
an API key, so production workflows should read the key from local configuration or environment
variables rather than committing it.

Official API documentation: <https://www.census.gov/data/developers/data-sets/acs-5year.html>

Official Census Gazetteer files:
<https://www.census.gov/geographies/reference-files/time-series/geo/gazetteer-files.html>

## CMS provider/service data

CMS publishes Medicare Physician and Other Practitioners data by provider and service. The included adapter accepts a downloaded extract and explicit source-column mappings because release schemas and analytic choices can change. Medicare fee-for-service utilization does not represent the entire population.

Official dataset family: <https://data.cms.gov/provider-summary-by-type-of-service/medicare-physician-other-practitioners>

## Road travel-time matrices

`radshock prepare-travel-time-review` creates the reproducible point-to-facility routing worklist
from reviewed population points and facility snapshots. It includes point coordinates, facility
coordinates, active status, straight-line miles, blank `travel_time_minutes`, route provenance
columns, and review status. The optional straight-line distance filter can reduce the route set
before sending it to a routing engine. The optional nearest-facility cap keeps only the nearest N
facilities per population point after distance filtering; if used, record that pruning assumption
with the route metadata before publication review.

Route reviewers should fill `travel_time_minutes`, set `route_status` to `routed`, `unreachable`,
or `excluded`, record the provider/source metadata, and set `review_status` to `reviewed`,
`verified`, or `approved`. `radshock finalize-travel-time-review` blocks unapproved rows, invalid
route statuses, duplicate point/facility pairs, and routed rows without minutes. It emits only the
minimal matrix columns accepted by `radshock compare-travel-time-access`: `point_id`,
`facility_id`, and `travel_time_minutes`.

Store the routing engine, network vintage, travel mode, departure-time or traffic assumption, and
any excluded routes with the source archive. The toolkit validates matrix shape and review status,
but it does not validate the upstream road network or routing assumptions.

`radshock fill-travel-time-review` can populate a route-review CSV from an OSRM-compatible Table
service or the OpenRouteService Matrix API. The output remains a draft by default: route rows keep
`review_status=needs_review` until the routing source and row-level outputs are approved. The
public OSRM demo server and hosted OpenRouteService free plan are useful for drafting and smoke
tests, but production route matrices should use an approved routing provider or self-hosted routing
instance with documented OpenStreetMap/network vintage, profile, traffic assumption, quota/terms,
and license attribution.

The production NC route workflow is `.github/workflows/self-hosted-osrm-travel-time.yml`. It builds
a self-hosted OSRM MLD graph from the Geofabrik North Carolina OSM PBF extract and records the OSM
data timestamp, routing profile, container image, map extract URL, extract checksum, and
free-flow/no-traffic assumption in the analysis manifest.

Geofabrik North Carolina extract page:
<https://download.geofabrik.de/north-america/us/north-carolina.html>

Direct Geofabrik North Carolina OSM PBF:
<https://download.geofabrik.de/north-america/us/north-carolina-latest.osm.pbf>

Official OSRM Table API documentation:
<https://project-osrm.org/docs/v5.23.0/api/#table-service>

OSRM public demo server policy:
<https://github.com/Project-OSRM/osrm-backend/wiki/Api-usage-policy>

Official OpenRouteService Matrix documentation:
<https://giscience.github.io/openrouteservice/api-reference/endpoints/matrix/>

OpenRouteService API restrictions:
<https://openrouteservice.org/restrictions/>

Google Routes API Compute Route Matrix is an alternative production provider. It returns distance
and duration route elements and requires a Google Maps Platform API key with billing enabled.

Official Google Routes Compute Route Matrix documentation:
<https://developers.google.com/maps/documentation/routes/compute-route-matrix-over>

## Candidate response sites

`radshock prepare-candidate-review` can create a starter review CSV from county centroids in
`data/counties.csv`. Those rows are placeholders for planning review, not recommended mobile stops
or fixed sites.

For a documented real-source alternative, `radshock prepare-hrsa-candidate-review` converts the
HRSA Health Center Program Service Delivery and Look-Alike Sites CSV into candidate review rows.
The default filter keeps active state-matched rows whose `Health Center Type Description` includes
service delivery, excluding administrative-only rows. HRSA `Permanent` rows become
`fixed_site_assumption`, `Seasonal` rows become `seasonal_fixed_site_assumption`, and `Mobile Van`
rows become `mobile_stop_assumption`.

Official HRSA download page:
<https://data.hrsa.gov/data/download>

Direct HRSA CSV:
<https://data.hrsa.gov/DataDownload/DD_Files/Health_Center_Service_Delivery_and_LookAlike_Sites.csv>

These HRSA candidates are real health-center service delivery locations, but they remain planning
assumptions. They are not claims that a location currently provides mammography or has available
mobile-unit capacity. Reviewers should keep the source, candidate type, and notes, then set
`review_status` to `reviewed`, `verified`, or `approved`. `radshock finalize-candidate-review`
blocks unapproved rows and emits the minimal `data/candidate_sites.csv` columns consumed by
`radshock analyze`.

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

If reviewers supplement Census matches with manual or fallback geocoding, the fallback provider,
matched address, score or benchmark, source URL, retrieval timestamp, and any approximate-match note
must stay in the geocode provenance columns. The 2026-06-19 NC review artifact used Census one-line
matching and ArcGIS World Geocoding fallback rows for addresses that the structured Census pass did
not resolve; those rows remain candidate coordinates until reviewed.

## Fixture-based testing

CI tests should not depend on live FDA, CDC, Census, CMS, geocoding, or routing endpoints. Adapter
tests should use fixture files or mocked responses and reserve live endpoint checks for manually
triggered workflows with explicit credentials and source review.

The `quarterly MQSA source refresh` workflow is a review-artifact workflow, not a publication
workflow. Manual dispatch or the quarterly schedule fetches the FDA MQSA ZIP and uploads a
state-filtered review CSV plus source metadata. Reviewers must still fill required fields, approve
rows, finalize snapshots, generate route matrices, and pass the readiness audit before sharing
findings.
