from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol, cast

import pandas as pd
import requests

from radshock.schemas import require_columns

CENSUS_GEOCODER_URL = "https://geocoding.geo.census.gov/geocoder/locations/address"

MQSA_GEOCODE_COLUMNS = {
    "source_record_hash",
    "source_address_1",
    "source_city",
    "source_state",
    "source_zip_code",
}

GEOCODE_OUTPUT_COLUMNS = [
    "geocode_status",
    "geocode_provider",
    "geocode_matched_address",
    "geocode_benchmark",
    "geocode_source_url",
    "geocode_cached",
    "geocode_retrieved_at_utc",
    "geocode_error",
]


@dataclass(frozen=True)
class GeocodeQuery:
    """Structured address query for a facility source row."""

    record_id: str
    street: str
    city: str
    state: str
    zip_code: str

    def cache_key(self, provider_name: str) -> str:
        normalized = "|".join(
            [
                provider_name.lower(),
                self.street.strip().upper(),
                self.city.strip().upper(),
                self.state.strip().upper(),
                self.zip_code.strip().upper(),
            ]
        )
        return normalized

    def one_line(self) -> str:
        parts = [self.street, self.city, self.state, self.zip_code]
        return ", ".join(part for part in parts if part.strip())


@dataclass(frozen=True)
class GeocodeResult:
    """Result plus provenance from a geocoding provider."""

    status: str
    provider: str
    latitude: float | None
    longitude: float | None
    matched_address: str | None
    benchmark: str | None
    source_url: str | None
    retrieved_at_utc: str
    error: str | None = None


class GeocodeProvider(Protocol):
    """Protocol implemented by live and static geocoding providers."""

    name: str

    def geocode(self, query: GeocodeQuery) -> GeocodeResult:
        """Return a geocode result for a structured address."""


class GeocodeCache:
    """Small JSON cache keyed by provider and normalized address."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self._items: dict[str, dict[str, Any]] = {}
        if path.exists():
            self._items = cast(dict[str, dict[str, Any]], json.loads(path.read_text()))

    def get(self, query: GeocodeQuery, provider_name: str) -> GeocodeResult | None:
        item = self._items.get(query.cache_key(provider_name))
        if item is None:
            return None
        return GeocodeResult(**item)

    def set(self, query: GeocodeQuery, result: GeocodeResult) -> None:
        self._items[query.cache_key(result.provider)] = asdict(result)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self._items, indent=2, sort_keys=True) + "\n")


class CensusGeocoder:
    """US Census Geocoder single-address provider."""

    name = "census"

    def __init__(
        self,
        benchmark: str = "Public_AR_Current",
        timeout: int = 30,
        endpoint: str = CENSUS_GEOCODER_URL,
    ) -> None:
        self.benchmark = benchmark
        self.timeout = timeout
        self.endpoint = endpoint

    def geocode(self, query: GeocodeQuery) -> GeocodeResult:
        retrieved_at = datetime.now(UTC).isoformat()
        params: dict[str, str] = {
            "street": query.street,
            "city": query.city,
            "state": query.state,
            "zip": query.zip_code,
            "benchmark": self.benchmark,
            "format": "json",
        }
        try:
            response = requests.get(self.endpoint, params=params, timeout=self.timeout)
            response.raise_for_status()
            payload = cast(dict[str, Any], response.json())
            matches = cast(
                list[dict[str, Any]],
                cast(dict[str, Any], payload.get("result", {})).get("addressMatches", []),
            )
            if not matches:
                return GeocodeResult(
                    status="no_match",
                    provider=self.name,
                    latitude=None,
                    longitude=None,
                    matched_address=None,
                    benchmark=self.benchmark,
                    source_url=self.endpoint,
                    retrieved_at_utc=retrieved_at,
                )
            match = matches[0]
            coordinates = cast(dict[str, Any], match.get("coordinates", {}))
            longitude = float(coordinates["x"])
            latitude = float(coordinates["y"])
            return GeocodeResult(
                status="matched",
                provider=self.name,
                latitude=latitude,
                longitude=longitude,
                matched_address=str(match.get("matchedAddress", "")),
                benchmark=self.benchmark,
                source_url=self.endpoint,
                retrieved_at_utc=retrieved_at,
            )
        except Exception as exc:
            return GeocodeResult(
                status="error",
                provider=self.name,
                latitude=None,
                longitude=None,
                matched_address=None,
                benchmark=self.benchmark,
                source_url=self.endpoint,
                retrieved_at_utc=retrieved_at,
                error=str(exc),
            )


class StaticGeocoder:
    """Deterministic provider backed by a reviewed coordinate CSV."""

    name = "static"

    def __init__(self, frame: pd.DataFrame) -> None:
        require_columns(frame, {"source_record_hash", "latitude", "longitude"}, "static geocoder")
        self.records = frame.fillna("").set_index("source_record_hash").to_dict(orient="index")

    @classmethod
    def from_csv(cls, path: Path) -> StaticGeocoder:
        return cls(pd.read_csv(path, dtype=str, keep_default_na=False))

    def geocode(self, query: GeocodeQuery) -> GeocodeResult:
        retrieved_at = datetime.now(UTC).isoformat()
        row = self.records.get(query.record_id)
        if row is None:
            return GeocodeResult(
                status="no_match",
                provider=self.name,
                latitude=None,
                longitude=None,
                matched_address=None,
                benchmark=None,
                source_url=None,
                retrieved_at_utc=retrieved_at,
            )
        return GeocodeResult(
            status="matched",
            provider=self.name,
            latitude=float(row["latitude"]),
            longitude=float(row["longitude"]),
            matched_address=str(row.get("matched_address", "")) or query.one_line(),
            benchmark=str(row.get("benchmark", "")) or None,
            source_url=str(row.get("source_url", "")) or None,
            retrieved_at_utc=retrieved_at,
        )


def geocode_mqsa_review(
    frame: pd.DataFrame,
    provider: GeocodeProvider,
    cache: GeocodeCache | None = None,
    overwrite_coordinates: bool = False,
    limit: int | None = None,
) -> pd.DataFrame:
    """Fill blank MQSA review coordinates with geocoder candidates and provenance."""
    require_columns(frame, MQSA_GEOCODE_COLUMNS, "MQSA review")
    result = frame.copy().fillna("")
    for column in GEOCODE_OUTPUT_COLUMNS:
        if column not in result.columns:
            result[column] = ""

    attempted = 0
    for index, row in result.iterrows():
        has_coordinates = (
            str(row.get("latitude", "")).strip() and str(row.get("longitude", "")).strip()
        )
        if has_coordinates and not overwrite_coordinates:
            continue
        if limit is not None and attempted >= limit:
            break
        query = GeocodeQuery(
            record_id=str(row["source_record_hash"]).strip(),
            street=str(row["source_address_1"]).strip(),
            city=str(row["source_city"]).strip(),
            state=str(row["source_state"]).strip(),
            zip_code=str(row["source_zip_code"]).strip(),
        )
        if not query.street:
            _write_geocode_result(
                result,
                index,
                GeocodeResult(
                    status="skipped_missing_street",
                    provider=provider.name,
                    latitude=None,
                    longitude=None,
                    matched_address=None,
                    benchmark=None,
                    source_url=None,
                    retrieved_at_utc=datetime.now(UTC).isoformat(),
                    error="source_address_1 is blank",
                ),
                cached=False,
            )
            continue
        cached = cache.get(query, provider.name) if cache is not None else None
        if cached is not None:
            geocode_result = cached
            is_cached = True
        else:
            geocode_result = provider.geocode(query)
            is_cached = False
            if cache is not None:
                cache.set(query, geocode_result)
        _write_geocode_result(result, index, geocode_result, cached=is_cached)
        attempted += 1
    return result


def _write_geocode_result(
    frame: pd.DataFrame,
    index: object,
    result: GeocodeResult,
    cached: bool,
) -> None:
    frame.at[index, "geocode_status"] = result.status
    frame.at[index, "geocode_provider"] = result.provider
    frame.at[index, "geocode_matched_address"] = result.matched_address or ""
    frame.at[index, "geocode_benchmark"] = result.benchmark or ""
    frame.at[index, "geocode_source_url"] = result.source_url or ""
    frame.at[index, "geocode_cached"] = str(cached).lower()
    frame.at[index, "geocode_retrieved_at_utc"] = result.retrieved_at_utc
    frame.at[index, "geocode_error"] = result.error or ""
    if result.status == "matched" and result.latitude is not None and result.longitude is not None:
        frame.at[index, "latitude"] = _format_coordinate(result.latitude)
        frame.at[index, "longitude"] = _format_coordinate(result.longitude)


def _format_coordinate(value: float) -> str:
    return f"{value:.8f}".rstrip("0").rstrip(".")
