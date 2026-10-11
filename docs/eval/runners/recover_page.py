"""recover_page.py <series> <B1|X2> <t> "<Character>": write a baseline page from its RECORDED response. $0, no model call.

Why (2026-10-07, ledger row "full text t=1: one page lost to a mismatched bracket"): on `anne-decon` X2 t=1 the
page of the main character came back three times (the call and its two repair retries) with a list closed by
`}` where `]` belongs. `llm/client.py` rejects it, the three responses are cached, so every rerun of
`run_baseline.py` replays the same failure for $0 and the cell is left without its most important page. The
content of the response is complete; only that closing bracket is wrong.

What it does: takes the FIRST recorded response for the character (the answer to the unmodified prompt, which
the runner would have used had the bracket been right; the repair retries exist only because of the fault) in the
newest run of the cell
(`data/<series>@<sys>/_runs/*-baseline-<sys>-v<t>/calls.jsonl`), replaces a closing bracket that does not match
the bracket it closes (outside strings, nothing else is touched), and passes the result through the same
`common.Page` validation, `common.enforce` (citations outside the prompt's paragraphs dropped) and
`common.render` as `run_baseline.py`. `_baseline.json` moves the character from `failures` to `written` and
gains a `recovered` entry. It refuses to write if no bracket was wrong or if the result still does not validate.

A rerun of `run_baseline.py` for the cell deletes the page again (it rewrites the directory from the cache), so
run this after the last billed attempt and log the cell as ok.

Lives here, not under scripts/: the tree under scripts/ is frozen (v2j) while the matrix is built.
Run from the repository root:
  .venv/Scripts/python.exe docs/eval/runners/recover_page.py anne-decon X2 1 "Nell Harcourt"
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts" / "baselines"))
import common as C  # noqa: E402
from narrativewiki import paths  # noqa: E402
from narrativewiki.entities.gazetteer import slugify  # noqa: E402

PAIR = {"{": "}", "[": "]"}


def fix_brackets(s: str) -> tuple[str, int]:
    """Replace each closing bracket that does not match the one it closes. Strings are left alone."""
    out, stack, fixed, in_str, esc = [], [], 0, False, False
    for ch in s:
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
        elif ch == '"':
            in_str = True
        elif ch in PAIR:
            stack.append(ch)
        elif ch in "}]" and stack:
            want = PAIR[stack.pop()]
            if ch != want:
                ch, fixed = want, fixed + 1
        out.append(ch)
    return "".join(out), fixed


def main(series: str, system: str, t: int, character: str) -> None:
    variant = f"{series}@{system.lower()}"
    paths.set_active_series(variant)
    runs = sorted((ROOT / "data" / variant / "_runs").glob(f"*-baseline-{system.lower()}-v{t}"))
    assert runs, "no run for this cell"
    needle = f'Write the page for the character "{character}" as known after volume {t}.'
    calls = [json.loads(l) for l in (runs[-1] / "calls.jsonl").open(encoding="utf-8")]
    mine = [c for c in calls if needle in c["prompt"]]
    assert mine, f"no recorded call for {character} in {runs[-1].name}"
    raw = mine[0]["response"]
    raw = raw[raw.index("{"): raw.rindex("}") + 1]
    try:
        json.loads(raw)
        raise SystemExit("the recorded response parses as it is: nothing to recover here")
    except json.JSONDecodeError:
        pass
    text, fixed = fix_brackets(raw)
    assert fixed, "no mismatched bracket found: not this fault"
    page = C.Page.model_validate(json.loads(text))
    vmax = 5 if system == "X2" else t
    paras = C.load_paras(paths.PARSED_DIR, vmax)
    allowed = {p["para_id"] for p in paras if system == "X2" or p["vol"] <= t}
    page, stats = C.enforce(page, allowed)
    out_dir = paths.wiki_cutoff_dir(t) / "character"
    slug = slugify(character)
    (out_dir / f"{slug}.md").write_text(C.render(page, character, slug, t, system), encoding="utf-8")
    mf = paths.wiki_cutoff_dir(t) / "_baseline.json"
    m = json.loads(mf.read_text(encoding="utf-8"))
    m["failures"] = [f for f in m["failures"] if f["character"] != character]
    if character not in m["written"]:
        m["written"].append(character)
    m["recovered"] = [r for r in m.get("recovered", []) if r["character"] != character] + [{
        "character": character, "run_id": runs[-1].name, "recorded_calls": len(mine), "brackets_fixed": fixed,
        "stats": stats, "by": "docs/eval/runners/recover_page.py"}]
    mf.write_text(json.dumps(m, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"{variant} t={t}: {character} recovered from {runs[-1].name} ({len(mine)} recorded calls, "
          f"{fixed} brackets fixed, stats {stats}); {len(m['written'])} pages, {len(m['failures'])} failures")


def demo() -> None:
    bad = '{"a": [{"t": "x } ] \\" y", "e": ["p1", "p2" }}], "b": {"c": [1, 2]}}'
    good, n = fix_brackets(bad)
    assert n == 1 and json.loads(good) == {"a": [{"t": 'x } ] " y', "e": ["p1", "p2"]}], "b": {"c": [1, 2]}}, good
    same, n = fix_brackets('{"a": ["\\\\"], "b": "]"}')
    assert n == 0 and json.loads(same) == {"a": ["\\"], "b": "]"}


if __name__ == "__main__":
    demo()
    main(sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4])
