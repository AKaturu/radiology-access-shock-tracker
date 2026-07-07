from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

import pytest

RESOLVE_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "resolve_all_gates.py"


def _load_resolve_script() -> ModuleType:
    spec = importlib.util.spec_from_file_location("resolve_all_gates", RESOLVE_SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


RESOLVE_MODULE = _load_resolve_script()


def test_gate_evidence_records_opencode_review_attestation_for_dc() -> None:
    evidence = RESOLVE_MODULE.build_gate_evidence("mqsa_review", "DC", "2026-07-07")

    assert "User-attested manual opencode review on 2026-07-07" in evidence
    assert "DC MQSA facility review" in evidence
    assert "geocoding/coordinate disposition" in evidence


def test_gate_evidence_rejects_unknown_gate() -> None:
    with pytest.raises(ValueError, match="Unknown gate"):
        RESOLVE_MODULE.build_gate_evidence("unknown", "DC", "2026-07-07")
