#!/usr/bin/env bash
set -euo pipefail

OSRM_IMAGE="${OSRM_IMAGE:-ghcr.io/project-osrm/osrm-backend:v6.0.0}"
OSM_EXTRACT_URL="${OSM_EXTRACT_URL:-https://download.geofabrik.de/north-america/us/north-carolina-latest.osm.pbf}"
OSM_EXTRACT_MD5_URL="${OSM_EXTRACT_MD5_URL:-${OSM_EXTRACT_URL}.md5}"
OSM_EXTRACT_NAME="${OSM_EXTRACT_NAME:-Geofabrik North Carolina}"
OSM_DATA_TIMESTAMP="${OSM_DATA_TIMESTAMP:?Set OSM_DATA_TIMESTAMP from the Geofabrik page before running.}"
OSRM_PROFILE="${OSRM_PROFILE:-driving}"
OSRM_PROFILE_LUA="${OSRM_PROFILE_LUA:-/opt/car.lua}"
OSRM_PORT="${OSRM_PORT:-5000}"
TRAFFIC_ASSUMPTION="${TRAFFIC_ASSUMPTION:-free-flow travel time; no live traffic}"

WORK_DIR="${WORK_DIR:-work/self-hosted-osrm}"
OSRM_DATA_DIR="${WORK_DIR}/osrm"
OSM_FILE="${OSRM_DATA_DIR}/north-carolina-latest.osm.pbf"
OSM_BASE="/data/north-carolina-latest.osrm"
ROUTE_REVIEW_INPUT="${ROUTE_REVIEW_INPUT:-data/travel_times/2026-06-20_tract_nearest20_osrm_review.csv}"
ROUTE_REVIEW_OUTPUT="${ROUTE_REVIEW_OUTPUT:-${WORK_DIR}/2026-06-20_tract_nearest20_self_hosted_osrm_review.csv}"
MATRIX_OUTPUT="${MATRIX_OUTPUT:-${WORK_DIR}/2026-06-20_tract_nearest20_self_hosted_osrm_matrix.csv}"
MATRIX_METADATA="${MATRIX_METADATA:-${WORK_DIR}/2026-06-20_tract_nearest20_self_hosted_osrm_matrix.metadata.json}"
ANALYSIS_DIR="${ANALYSIS_DIR:-${WORK_DIR}/analysis-tract-self-hosted-osrm}"
ROUTE_SOURCE_URL="http://127.0.0.1:${OSRM_PORT}/table/v1/${OSRM_PROFILE}"
CONTAINER_NAME="radshock-osrm-${OSRM_PORT}"

mkdir -p "${OSRM_DATA_DIR}" "${WORK_DIR}"

HOST_IS_WINDOWS_BASH=false
case "$(uname -s)" in
  MINGW* | MSYS* | CYGWIN*) HOST_IS_WINDOWS_BASH=true ;;
esac

if [[ "${HOST_IS_WINDOWS_BASH}" == "true" ]]; then
  OSRM_DATA_MOUNT="$(cygpath -am "${OSRM_DATA_DIR}")"
else
  OSRM_DATA_MOUNT="${PWD}/${OSRM_DATA_DIR}"
fi

docker_cli() {
  if [[ "${HOST_IS_WINDOWS_BASH}" == "true" ]]; then
    MSYS_NO_PATHCONV=1 docker "$@"
  else
    docker "$@"
  fi
}

echo "Downloading ${OSM_EXTRACT_URL}"
curl -fL "${OSM_EXTRACT_URL}" -o "${OSM_FILE}"
curl -fL "${OSM_EXTRACT_MD5_URL}" -o "${OSM_FILE}.md5"
(cd "${OSRM_DATA_DIR}" && md5sum -c "$(basename "${OSM_FILE}.md5")")
OSM_SHA256="$(sha256sum "${OSM_FILE}" | awk '{print $1}')"
echo "OSM_SHA256=${OSM_SHA256}"

docker_cli run --rm -t -v "${OSRM_DATA_MOUNT}:/data" "${OSRM_IMAGE}" \
  osrm-extract -p "${OSRM_PROFILE_LUA}" /data/$(basename "${OSM_FILE}")
docker_cli run --rm -t -v "${OSRM_DATA_MOUNT}:/data" "${OSRM_IMAGE}" \
  osrm-partition "${OSM_BASE}"
docker_cli run --rm -t -v "${OSRM_DATA_MOUNT}:/data" "${OSRM_IMAGE}" \
  osrm-customize "${OSM_BASE}"

docker_cli rm -f "${CONTAINER_NAME}" >/dev/null 2>&1 || true
docker_cli run -d --name "${CONTAINER_NAME}" -p "${OSRM_PORT}:5000" \
  -v "${OSRM_DATA_MOUNT}:/data" "${OSRM_IMAGE}" \
  osrm-routed --algorithm mld "${OSM_BASE}" >/dev/null
trap 'docker_cli rm -f "${CONTAINER_NAME}" >/dev/null 2>&1 || true' EXIT

echo "Waiting for OSRM at ${ROUTE_SOURCE_URL}"
for _ in $(seq 1 60); do
  if curl -fsS "http://127.0.0.1:${OSRM_PORT}/route/v1/${OSRM_PROFILE}/-78.6382,35.7796;-78.6390,35.7800?overview=false" >/dev/null; then
    break
  fi
  sleep 2
done
curl -fsS "http://127.0.0.1:${OSRM_PORT}/route/v1/${OSRM_PROFILE}/-78.6382,35.7796;-78.6390,35.7800?overview=false" >/dev/null

radshock fill-travel-time-review "${ROUTE_REVIEW_INPUT}" \
  --output-csv "${ROUTE_REVIEW_OUTPUT}" \
  --provider osrm \
  --osrm-base-url "http://127.0.0.1:${OSRM_PORT}" \
  --osrm-profile "${OSRM_PROFILE}" \
  --review-status reviewed \
  --timeout 120 \
  --force

radshock finalize-travel-time-review "${ROUTE_REVIEW_OUTPUT}" \
  --output-csv "${MATRIX_OUTPUT}" \
  --metadata-json "${MATRIX_METADATA}" \
  --force

python scripts/finalize_travel_time_package.py \
  --before-csv data/snapshots/2026-06-19/facilities.csv \
  --after-csv data/snapshots/2026-06-20/facilities.csv \
  --population-csv data/population_points_tracts.csv \
  --counties-csv data/counties.csv \
  --candidates-csv data/candidate_sites.csv \
  --before-travel-times-csv "${MATRIX_OUTPUT}" \
  --after-travel-times-csv "${MATRIX_OUTPUT}" \
  --output-dir "${ANALYSIS_DIR}" \
  --before-snapshot-dir data/snapshots/2026-06-19 \
  --after-snapshot-dir data/snapshots/2026-06-20 \
  --raw-source-metadata data/source_metadata/fda-mqsa-public-2026-06-20.metadata.json \
  --matrix-metadata-json "${MATRIX_METADATA}" \
  --route-review-csv "${ROUTE_REVIEW_OUTPUT}" \
  --candidate-review-metadata-json data/candidate_sites_review.metadata.json \
  --before-period 2026-06-19 \
  --after-period 2026-06-20 \
  --route-provider "osrm:${OSRM_PROFILE}" \
  --route-profile "${OSRM_PROFILE}" \
  --route-source-url "${ROUTE_SOURCE_URL}" \
  --engine-version "${OSRM_IMAGE}" \
  --engine-deployment "self-hosted Docker OSRM container" \
  --map-extract-name "${OSM_EXTRACT_NAME}" \
  --map-extract-url "${OSM_EXTRACT_URL}" \
  --map-extract-osm-data-timestamp "${OSM_DATA_TIMESTAMP}" \
  --map-extract-sha256 "${OSM_SHA256}" \
  --traffic-assumption "${TRAFFIC_ASSUMPTION}" \
  --routing-note "Self-hosted OSRM MLD run generated from the documented Geofabrik OSM extract."
