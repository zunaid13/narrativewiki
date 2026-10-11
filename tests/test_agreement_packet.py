"""Focused checks for blind packet coverage and agreement denominator handling."""
import csv
import importlib.util
import shutil
import sys
import uuid
import zipfile
from pathlib import Path

import pytest

DIR = Path(__file__).resolve().parents[1] / "docs/eval/agreement"


def module(name):
    spec = importlib.util.spec_from_file_location(name, DIR / f"{name}.py")
    m = importlib.util.module_from_spec(spec)
    sys.modules[name] = m
    spec.loader.exec_module(m)
    return m


packet = module("build_packet")
agreement = module("score_agreement")


@pytest.fixture
def packet_tmp():
    # Normal directory permissions avoid Windows' restrictive pytest tmpdir mode.
    path = DIR.parents[2] / ".tmp" / f"agreement-check-{uuid.uuid4().hex}"
    path.mkdir(parents=True)
    yield path
    assert path.resolve().is_relative_to((DIR.parents[2] / ".tmp").resolve())
    shutil.rmtree(path)


def test_known_multiclass_kappa_and_undefined_cases():
    # Official sklearn documentation's example: 4/6 agreements, pe=5/12, kappa=3/7.
    r = agreement.kappa([2, 0, 2, 2, 0, 1], [0, 0, 2, 2, 0, 2])
    assert r["kappa"] == pytest.approx(3 / 7)
    assert r["agreement"] == pytest.approx(4 / 6)
    assert agreement.kappa(["yes", "no"], ["yes", "no"])["kappa"] == 1
    assert agreement.kappa(["yes"], ["yes"])["kappa"] is None
    assert agreement.kappa([], [])["kappa"] is None
    with pytest.raises(ValueError):
        agreement.kappa([1], [])


def test_packet_retains_every_item_and_evidence_without_answer_leak(packet_tmp):
    tmp_path = packet_tmp
    manifest = packet.build(tmp_path)
    source = {r["source_item"]: r for r in packet.load_items()}
    questions = (tmp_path / "questions_only.html").read_text(encoding="utf-8")
    answers = (tmp_path / "questions_and_answers.html").read_text(encoding="utf-8")
    assert len(manifest["items"]) == len(source) == 554
    assert manifest["counts"] == {"C": 60, "G": 111, "P": 148, "R": 235}
    assert len(set(r["item"] for r in manifest["items"])) == len(source)
    for r in manifest["items"]:
        old = source[r["source_item"]]
        assert old["body"] in questions and old["body"] in answers
        assert r["label"] == old["label"] and r["pair"] == old["pair"]
        assert r["source_item"] not in questions
    assert "Previously accepted answer:" not in questions
    assert questions.count("<div class='item'") == answers.count("<div class='item'") == 554
    assert answers.count("Previously accepted answer:") == 554
    with zipfile.ZipFile(tmp_path / "reader_packet.zip") as z:
        assert set(z.namelist()) == {"questions_only.html", "reader_answers_blank.csv"}
    original_bytes = {p.name: p.read_bytes() for p in tmp_path.iterdir()}
    packet.build(tmp_path)
    assert original_bytes == {p.name: p.read_bytes() for p in tmp_path.iterdir()}


def write_sheet(path, rows):
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=packet.FIELDS)
        w.writeheader()
        w.writerows(rows)


def test_scorer_rejects_missing_and_invalid_labels_and_separates_tasks(packet_tmp):
    tmp_path = packet_tmp
    template = tmp_path / "template.csv"
    base = [{"item": "Q0001", "task": "P", "label": "", "pair": ""},
            {"item": "Q0002", "task": "P", "label": "", "pair": "n-a"},
            {"item": "Q0003", "task": "R", "label": "", "pair": "n-a"}]
    write_sheet(template, base)
    a, b = tmp_path / "a.csv", tmp_path / "b.csv"
    write_sheet(a, base)
    write_sheet(b, base)
    with pytest.raises(ValueError, match="Incomplete"):
        agreement.score(a, b, template)
    partial = agreement.score(a, b, template, allow_partial=True)
    assert partial["status"] == "partial"
    assert partial["tasks"]["P"]["n"] == 0
    ra = [dict(base[0], label="yes", pair="yes"), dict(base[1], label="not shown"),
          dict(base[2], label="yes")]
    rb = [dict(base[0], label="yes", pair="no"), dict(base[1], label="partly"),
          dict(base[2], label="no")]
    write_sheet(a, ra)
    write_sheet(b, rb)
    r = agreement.score(a, b, template)
    assert r["tasks"]["P"]["n"] == 2 and r["tasks"]["R"]["n"] == 1
    assert r["tasks"]["P"]["binary_yes_vs_rest"]["n"] == 1
    assert r["tasks"]["P"]["binary_excluded_not_shown"] == ["Q0002"]
    assert r["tasks"]["P"]["pair_scene"]["agreement"] == 0
    assert r["tasks"]["P"]["supported_on_page"]["agreement"] == 0
    assert r["tasks"]["P"]["pair_scene"]["disagreements"] == ["Q0001"]
    write_sheet(b, rb + [rb[0]])
    with pytest.raises(ValueError, match="duplicate"):
        agreement.score(a, b, template)
    write_sheet(b, [dict(rb[0], label="supported")] + rb[1:])
    with pytest.raises(ValueError, match="Invalid label"):
        agreement.score(a, b, template)
    write_sheet(b, rb[:2])
    with pytest.raises(ValueError, match="Incomplete"):
        agreement.score(a, b, template)
