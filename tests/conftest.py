"""Suite-wide guard: no test may add a run to the repo's real run ledgers (data/**/_runs)."""

from __future__ import annotations

import pytest

from narrativewiki import paths


def _real_runs() -> set[str]:
    root = paths.PROJECT_ROOT / "data"
    return {str(p) for pat in ("_runs/*", "*/_runs/*") for p in root.glob(pat) if p.is_dir()}


@pytest.fixture(autouse=True, scope="session")
def _no_run_leaks_into_real_data():
    before = _real_runs()
    yield
    leaked = _real_runs() - before
    assert not leaked, f"tests wrote runs into the real ledger: {sorted(leaked)}"
