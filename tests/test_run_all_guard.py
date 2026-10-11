"""Phase 11: `run-all` is demoted -- it refuses an unattended multi-volume scope unless
`--i-accept-unaudited` is given, making `wiki step` the default path (rule 3).

The six delegated stage commands are monkeypatched to no-ops so this only tests the guard
itself, not a real pipeline run.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest
import typer

from narrativewiki import cli


class _FakeSettings:
    def __init__(self, vols: list[int]) -> None:
        self.series_id = "test-series"
        self.series: dict = {}
        self._vols = vols

    def discover_volumes(self):
        return [SimpleNamespace(vol=v) for v in self._vols]


@pytest.fixture()
def stub_stages(monkeypatch):
    calls: list[str] = []
    for name in ("ingest", "gazetteer", "scenes", "extract", "graph_build", "verify", "events_build", "synthesize", "site_build"):
        monkeypatch.setattr(cli, name, lambda *a, __n=name, **k: calls.append(__n))
    return calls


@pytest.fixture()
def fake_settings(monkeypatch):
    def _install(vols: list[int]):
        monkeypatch.setattr(cli, "_settings", lambda series, model=None, set_=None: _FakeSettings(vols))

    return _install


def test_multi_volume_scope_refused_without_the_flag(stub_stages, fake_settings):
    fake_settings([1, 2])
    with pytest.raises(typer.Exit):
        cli.run_all(series=None, volumes="1-2", upto=1, i_accept_unaudited=False)
    assert stub_stages == []  # nothing ran


def test_multi_volume_scope_proceeds_with_the_flag(stub_stages, fake_settings):
    fake_settings([1, 2])
    cli.run_all(series=None, volumes="1-2", upto=1, i_accept_unaudited=True)
    # Phase 23 B5: graph_build now calls verify internally (never as an optional, skippable
    # later stage) -- run_all's own explicit verify(...) call was removed as redundant. The
    # stubbed graph_build here is a bare no-op, so "verify" correctly does not appear; a real
    # graph_build's own internal verify call is covered separately.
    assert stub_stages == [
        "ingest", "gazetteer", "scenes", "gazetteer", "extract", "graph_build",
        "events_build", "synthesize", "site_build",
    ]


def test_single_volume_scope_needs_no_flag(stub_stages, fake_settings):
    fake_settings([1, 2])
    cli.run_all(series=None, volumes="1", upto=1, i_accept_unaudited=False)
    assert stub_stages == [
        "ingest", "gazetteer", "scenes", "gazetteer", "extract", "graph_build",
        "events_build", "synthesize", "site_build",
    ]
