"""Independent labeling validation, budget persistence and packet isolation."""
import importlib.util
import json
import sys
import csv
import shutil
import uuid
from pathlib import Path

import pytest

DIR = Path(__file__).resolve().parents[1] / "docs/eval/agreement"
sys.path.insert(0, str(DIR))
spec = importlib.util.spec_from_file_location("run_model_labels", DIR / "run_model_labels.py")
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


def test_blind_prompt_contains_evidence_and_explicit_label_choices():
    questions = runner.load_questions()
    assert len(questions) == 554
    assert sum(q["pair_required"] for q in questions) == 14
    for q in questions:
        prompt = runner.make_prompt(q)
        assert q["question"] in prompt
        assert q["item"] in prompt
        assert "Accepted label:" not in prompt
        assert "Earlier AI label:" not in prompt
        assert "Return exactly one JSON object" in prompt


def test_invalid_labels_ids_and_pair_placement_cannot_be_scored():
    question = next(q for q in runner.load_questions() if q["pair_required"])
    answer = {"item": question["item"], "label": "partly", "pair": "no", "reason": "Only one participates", "evidence": []}
    assert runner.validate_answer(json.dumps(answer), question)["pair"] == "no"
    for wrong in ({"item": "Q9999"}, {"label": "supported"}, {"pair": "n-a"}, {"reason": ""}, {"evidence": "invented"}):
        with pytest.raises(ValueError):
            runner.validate_answer(json.dumps(answer | wrong), question)
    nonpair = next(q for q in runner.load_questions() if not q["pair_required"])
    with pytest.raises(ValueError):
        runner.validate_answer(json.dumps(answer | {"item": nonpair["item"]}), nonpair)


def test_checkpoint_rejects_changed_model_or_prompt_without_new_calls(monkeypatch):
    class Metadata:
        def exists(self):
            return True
        def read_text(self, **kwargs):
            return json.dumps({"signature": "old-model-and-prompt"})
    class Directory:
        def __truediv__(self, other):
            assert other == "metadata.json"
            return Metadata()
    with pytest.raises(ValueError, match="Checkpoint model/options/prompt/packet changed"):
        runner.read_checkpoint(Directory(), "new-model-and-prompt", [])


def test_comparison_preserves_pair_disagreement_and_correct_denominators(monkeypatch):
    import compare_model_labels as comparator
    root = DIR.parents[2] / ".tmp" / f"model-agreement-{uuid.uuid4().hex}"
    root.mkdir(parents=True)
    try:
        questions = runner.load_questions()
        pair_id = next(q["item"] for q in questions if q["pair_required"])
        gold_id = next(q["item"] for q in questions if q["task"] == "G")
        for name in ("a", "b"):
            directory = root / name
            directory.mkdir()
            metadata = {"model": name, "packet_sha256": "same", "runs": [name]}
            (directory / "metadata.json").write_text(json.dumps(metadata))
            (directory / "budget.json").write_text(json.dumps({"total_cost_usd": 0, "stages": {}}))
            answers = {}
            for q in questions:
                answers[q["item"]] = {"item": q["item"], "task": q["task"], "label": "yes",
                    "pair": "yes" if q["pair_required"] else "n-a", "reason": "fixture", "evidence": []}
            if name == "b":
                answers[pair_id]["pair"] = "no"
                answers[gold_id]["label"] = "no"
            runner.save_answers(directory, answers, questions)
            (directory / "responses.jsonl").write_text("\n".join(map(json.dumps, answers.values())))
        monkeypatch.setattr(comparator.paths, "set_active_series", lambda sid: None)
        monkeypatch.setattr(comparator.paths, "run_dir", lambda rid: root / rid)
        report = comparator.compare(root / "a", root / "b", root / "comparison")
        assert report["items_all_agree"] == 552
        assert report["items_any_disagreement"] == 2
        assert report["tasks"]["G"]["n"] == 111
        assert report["tasks"]["G"]["kappa"] == pytest.approx(0)
        assert report["tasks"]["P"]["pair_scene"]["n"] == 14
        assert report["tasks"]["P"]["pair_scene"]["disagreements"] == [pair_id]
        with (root / "comparison/disagreements.csv").open(encoding="utf-8-sig", newline="") as f:
            assert {r["item"] for r in csv.DictReader(f)} == {pair_id, gold_id}
    finally:
        assert root.resolve().is_relative_to((DIR.parents[2] / ".tmp").resolve())
        shutil.rmtree(root)
