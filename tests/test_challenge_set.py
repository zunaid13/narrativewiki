"""[33] S08: scoring a side file (the hard set) writes verdicts there, never into the main set."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

_spec = importlib.util.spec_from_file_location("challenge_set", Path(__file__).parents[1] / "scripts/eval/challenge_set.py")
cs = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cs)


def test_score_writes_to_the_file_it_read(tmp_path, monkeypatch):
    side = tmp_path / "hard.jsonl"
    items = [{"id": "a", "label": "supported", "type": "hard_twin", "confirmed": True, "judges": {}},
             {"id": "b", "label": "unsupported", "type": "embedded_story", "confirmed": True, "judges": {}}]
    side.write_text("".join(json.dumps(i) + "\n" for i in items), encoding="utf-8")
    main = tmp_path / "main.jsonl"
    main.write_text("untouched\n", encoding="utf-8")
    monkeypatch.setattr(cs, "OUT", main)
    monkeypatch.setattr(cs, "LLMClient", lambda *a, **k: None)
    monkeypatch.setattr(cs, "load_settings", lambda *a, **k: None)
    monkeypatch.setattr(cs, "judge", lambda client, name, it: it["label"] == "supported")
    cs.score("stub", side)
    assert main.read_text(encoding="utf-8") == "untouched\n"
    assert [json.loads(l)["judges"] for l in side.read_text(encoding="utf-8").splitlines()] == [{"stub": True}, {"stub": False}]
