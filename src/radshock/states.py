from __future__ import annotations

from dataclasses import dataclass

US_STATE_ABBR_TO_FIPS = {
    "AL": "01",
    "AK": "02",
    "AZ": "04",
    "AR": "05",
    "CA": "06",
    "CO": "08",
    "CT": "09",
    "DE": "10",
    "DC": "11",
    "FL": "12",
    "GA": "13",
    "HI": "15",
    "ID": "16",
    "IL": "17",
    "IN": "18",
    "IA": "19",
    "KS": "20",
    "KY": "21",
    "LA": "22",
    "ME": "23",
    "MD": "24",
    "MA": "25",
    "MI": "26",
    "MN": "27",
    "MS": "28",
    "MO": "29",
    "MT": "30",
    "NE": "31",
    "NV": "32",
    "NH": "33",
    "NJ": "34",
    "NM": "35",
    "NY": "36",
    "NC": "37",
    "ND": "38",
    "OH": "39",
    "OK": "40",
    "OR": "41",
    "PA": "42",
    "RI": "44",
    "SC": "45",
    "SD": "46",
    "TN": "47",
    "TX": "48",
    "UT": "49",
    "VT": "50",
    "VA": "51",
    "WA": "53",
    "WV": "54",
    "WI": "55",
    "WY": "56",
}
US_STATE_FIPS_TO_ABBR = {fips: abbr for abbr, fips in US_STATE_ABBR_TO_FIPS.items()}
US_STATE_ABBRS = tuple(US_STATE_ABBR_TO_FIPS)
US_STATE_FIPS = tuple(US_STATE_ABBR_TO_FIPS.values())

ALL_50_STATE_ALIASES = {
    "ALL", "ALL50", "ALL_50", "ALL_50_STATES", "ALL_STATES",
    "ALL_51", "ALL51", "US", "USA", "50",
}


@dataclass(frozen=True)
class StateScope:
    requested: str
    states: tuple[str, ...]
    state_fips: tuple[str, ...]
    is_all_50_states: bool = False

    @property
    def label(self) -> str:
        if self.is_all_50_states:
            return "ALL_STATES"
        return self.states[0]

    @property
    def fips_label(self) -> str:
        if self.is_all_50_states:
            return "ALL_STATES"
        return self.state_fips[0]


def resolve_state_scope(value: str | None) -> StateScope:
    """Resolve a CLI/API state argument into a supported all-state scope."""
    requested = (value or "NC").strip().upper().replace("-", "_")
    if not requested:
        requested = "NC"
    compact = requested.replace("_", "")
    if requested in ALL_50_STATE_ALIASES or compact in ALL_50_STATE_ALIASES:
        return StateScope(
            requested=requested,
            states=US_STATE_ABBRS,
            state_fips=US_STATE_FIPS,
            is_all_50_states=True,
        )
    if requested.isdigit():
        state_fips = requested.zfill(2)
        if state_fips in US_STATE_FIPS_TO_ABBR:
            return StateScope(
                requested=requested,
                states=(US_STATE_FIPS_TO_ABBR[state_fips],),
                state_fips=(state_fips,),
            )
    if requested in US_STATE_ABBR_TO_FIPS:
        return StateScope(
            requested=requested,
            states=(requested,),
            state_fips=(US_STATE_ABBR_TO_FIPS[requested],),
        )
    raise ValueError(
        "state must be a two-letter USPS abbreviation, a state FIPS code, or ALL"
    )


def state_abbr_from_fips(state_fips: str) -> str:
    fips = str(state_fips).zfill(2)
    try:
        return US_STATE_FIPS_TO_ABBR[fips]
    except KeyError as exc:
        raise ValueError(f"unsupported state FIPS code: {state_fips}") from exc
