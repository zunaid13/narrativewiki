"""Fetch the arXiv PDFs behind this project's design decisions, and verify each id resolves.

Why this exists: `docs/archive/GUIDE_TO_PUBLISHING.md` R15 ("unverified citations") is a fatal-integrity risk
and every id in that file's §8 was collected from web search, never opened. This script asks the
arXiv API for each id's real title/authors/date, downloads the PDF into
`docs/papers/pdf/`, and writes the verified table to `docs/papers/REFERENCES.md`. An id
that does not resolve is reported, not silently dropped.

PDFs are named `{Paper Title}.pdf` (arXiv's own title, `:` -> ` - `), not `{arxiv_id}.pdf` --
commit 497087f renamed all 54 files this way for GitHub readability and flipped `.gitignore` to
track them (they are checked in, not local-only). `download()` and `--check` both key off the
title filename this produces, so a re-run finds the files that are actually on disk instead of
silently re-downloading everything under the old arxiv-id name. See `docs/papers/PAPERS.md` for the
naming convention written out in full, and for the per-paper Applied/Failed/Reference status this
script does not track.

    python scripts/papers/fetch_reference_pdfs.py            # fetch everything missing
    python scripts/papers/fetch_reference_pdfs.py --check    # metadata only, no PDF downloads; also
                                                     # verifies PAPERS <-> disk <-> docs/papers/PAPERS.md
                                                     # stay in sync (see check_consistency())

Stdlib only, no API key, ~3s between requests per arXiv's robot policy.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PAPERS_DIR = ROOT / "docs" / "papers"
OUT_DIR = PAPERS_DIR / "pdf"
MANIFEST = PAPERS_DIR / "REFERENCES.md"
API = "https://export.arxiv.org/api/query?id_list={}&max_results=100"
UA = {"User-Agent": "narrativewiki-refs/1.0 (research citation verification)"}

# (arxiv_id, section, what it is load-bearing for in THIS repo, status)
# status is one of "applied" (a named module implements it), "failed" (implemented, then measured
# worse and removed), "reference" (cited for a decision/comparison/positioning, not implemented).
# See docs/papers/PAPERS.md for the per-paper detail (where it lands, why) this tuple's `why` summarizes.
PAPERS = [
    # A — load-bearing for code that exists today
    ("2512.07474", "A", "Closest prior work: 'Narrative-Present Gate' = filter-before-generate, "
                        "the CLAUDE.md §1 invariant. Read in full; the 90.8% is their number.", "reference"),
    ("2306.13063", "A", "Verbalized LLM confidence is uncalibrated/overconfident — the evidence "
                        "that retired `rule:lowest_confidence_dropped` arbitration (Stage 3).", "reference"),
    ("2404.10774", "A", "MiniCheck: the small fact-checking classifier now wired in as "
                        "`llm/providers/minicheck.py`, replacing self-reported confidence.", "applied"),
    ("2402.03216", "A", "BGE-M3: the local embedding model used for value canonicalization "
                        "clustering in `graph/canonicalize.py` (not for retrieval).", "applied"),
    ("2402.14207", "A", "STORM: the Heading Soft Recall / Heading Entity Recall metric family "
                        "`eval/gold.py::score_heading_recall` is in.", "applied"),
    ("2305.14627", "A", "ALCE: citation-quality evaluation, the model for "
                        "`eval/gold.py::score_citation_entailment`.", "applied"),
    ("2112.12870", "A", "AIS (Attributable to Identified Sources): the attribution framework "
                        "behind claim-level 'Sources: v1 p.9' provenance.", "reference"),
    # Phase 26 — the per-paragraph source view and its citation links.
    ("2406.06125", "A", "Sub-sentence fine-grained citations: the granularity comparison behind "
                        "Phase 26's choice of a per-PARAGRAPH anchor (`site/mkdocs_wiki.py::"
                        "source_route`) rather than a sub-sentence span.", "reference"),
    ("2508.15396", "A", "Survey of evidence-based text generation (attribution/citation/"
                        "quotation): positioning for the Phase 26 citation layer, alongside "
                        "AIS above.", "reference"),
    ("2502.12124", "A", "Quote extraction as retrieve-then-rank over long documents — the "
                        "comparison point for `synth/assemble.py::_quote_notability`, which "
                        "replaced confidence-ranking with a notability heuristic.", "reference"),
    # B — method choices the design record cites as rejected/adopted alternatives
    ("2505.24553", "B", "CREFT: multi-agent character relation extraction, explicitly on "
                        "coreference and implicit relations — the comparison point for Phase "
                        "26's single-call `synth/prose.py::generate_relationship_prose`.", "reference"),
    ("2211.10511", "B", "Grapher: T-F1 / G-F1 / G-BERTScore. Adopted instead of graph isomorphism "
                        "(Guide to Publishing §1.2, §11).", "reference"),
    ("2502.05239", "B", "KG-construction evaluation with explicit hallucination/omission metrics — "
                        "the metric source for the planned `eval/kgalign.py`.", "reference"),
    ("2503.16402", "B", "Contamination-mitigation audit reporting the fidelity–resistance "
                        "tradeoff — the citation that killed event shuffling (§11).", "reference"),
    ("2502.14425", "B", "Data-contamination survey: taxonomy/detection/mitigation framing.", "reference"),
    ("2406.14644", "B", "Spectrum of data contamination: detection→remediation framing.", "reference"),
    ("2305.12392", "B", "PiVe: prompting with iterative verification — the comparison point for "
                        "`graph/verify.py`'s single flat verification call.", "reference"),
    ("2411.17388", "B", "LLM-as-graph-judge: judge-design reference and the caution about "
                        "judge/generator family overlap (R10).", "reference"),
    # B (2026-09-21) — the evidence-window BUDGET, after `extract --entities` was found sizing
    # the per-volume pool over the FILTERED character list (claims.py), giving a targeted
    # re-extract 40 windows where a full run gives 105-116. Fixed; these three are positioning
    # for the allocation POLICY, which the fix does not change and which currently never binds
    # (0 of 359 windows discarded corpus-wide at two volumes).
    ("2601.18116", "B", "BEAR: budgeted evidence allocation across documents — the framing for "
                        "`windows.allocate_window_caps` as a budget-allocation problem rather "
                        "than a cap. Coarse-to-fine hierarchical access, not our sqrt-of-"
                        "mentions split; comparison point if the cap ever binds.", "reference"),
    ("2605.00336", "B", "Budget-Aware Routing for Long Clinical Text: RCD, a monotone submodular "
                        "relevance/coverage/diversity objective, vs positional and frequency "
                        "selection under a fixed budget. The comparison point for "
                        "`build_windows`' top-k-by-`mention_count` truncation. NOT adopted: it "
                        "reports positional heuristics winning on LOW-BUDGET EXTRACTIVE tasks, "
                        "which is this stage, and our cap does not currently bind.", "reference"),
    ("2411.06254", "B", "EviRerank: adaptive evidence budgeting with information-density-aware "
                        "early stopping over long documents — the per-item 'how much evidence "
                        "is enough' question `max_windows_per_entity_per_volume` answers with a "
                        "flat sqrt share.", "reference"),
    # C — baselines the programme must run
    ("2404.16130", "C", "GraphRAG (Microsoft, 'From Local to Global'): the reference graph-RAG "
                        "baseline.", "reference"),
    ("2410.05779", "C", "LightRAG: the closest architectural competitor and cheapest graph-RAG "
                        "baseline.", "reference"),
    # D — task/benchmark positioning
    ("1712.07040", "D", "NarrativeQA: the benchmark-outlives-the-model precedent.", "reference"),
    ("2403.12766", "D", "NovelQA: long-novel QA positioning.", "reference"),
    ("2510.09869", "D", "NarraBench: narrative evaluation positioning.", "reference"),
    ("2506.13641", "D", "EvolvTrip: temporal theory-of-mind graphs over literary characters.", "reference"),
    ("1907.02704", "D", "Character-network survey: the co-occurrence tradition used only for "
                        "structural (centrality-rank) comparison.", "reference"),
    ("2410.14666", "D", "DiscoGraMS: character-aware discourse graph, summarization side.", "reference"),
    ("2310.18783", "D", "Narrative understanding overview: framing.", "reference"),
    ("2009.09162", "D", "Summary KGs from long documents: pre-LLM extraction baseline.", "reference"),
    ("2510.20345", "D", "LLM-empowered KG construction survey: positioning.", "reference"),
    ("2503.00751", "D", "RAPID: retrieval-augmented long-text generation, efficiency comparison.", "reference"),
    ("2506.23393", "D", "Hierarchical memory organization for Wikipedia generation.", "reference"),
    ("2503.07170", "D", "DeFine: fine-grained annotation for long-form article generation.", "reference"),
    ("2510.13193", "D", "ReMindRAG: graph-RAG breadth citation.", "reference"),
    ("2510.02418", "D", "BrowserArena: web-agent benchmark breadth citation.", "reference"),
    ("2506.01952", "D", "WebChoreArena: web-agent benchmark breadth citation.", "reference"),
    # E — ids taken from web search on 2026-09-11 and never opened (verify or drop)
    ("2606.31946", "E", "Cited in ConvinceMe Addendum 1 as a same-pattern paper in another "
                        "modality. PDF already on disk; confirm the id/title match.", "reference"),
    ("2606.25632", "E", "'Staying In Character' — adjacent perspective-bounded memory work.", "reference"),
    ("2606.05724", "E", "'Narrative Knowledge Weaver'.", "reference"),
    ("2607.05577", "E", "'Narrative World Model'.", "reference"),
    ("2508.03358", "E", "'Taggus' — Portuguese fiction character networks.", "reference"),
    ("2602.15851", "E", "Narrative-theory-driven LLM methods survey.", "reference"),
    ("2603.04751", "E", "Mind-ParaWorld / parallel-world search-agent evaluation — the "
                        "fabricated-entity environment this work contrasts itself against.", "reference"),
    ("2603.00801", "E", "'The Synthetic Web' — closed-book contamination probe protocol borrowed "
                        "from here.", "reference"),
    ("2607.26070", "E", "'SimpleWikiSearch'.", "reference"),
    ("2604.10938", "E", "'AgentWebBench'.", "reference"),
    ("2605.29218", "E", "'GTA' — long-horizon web-agent task generation.", "reference"),
    ("2604.24964", "E", "'Odysseys'.", "reference"),
    ("2601.10504", "E", "'DR-Arena'.", "reference"),
    ("2605.22219", "E", "'SGR-Bench'.", "reference"),
    ("2604.24623", "E", "'XGRAG'.", "reference"),
    ("2605.18775", "E", "Query-aware flow diffusion for graph retrieval.", "reference"),
    ("2605.19999", "E", "Contamination-resistant benchmarks position paper.", "reference"),
    ("2602.17234", "E", "'All Leaks Count, Some Count More' — Shapley-DCLR, the closest "
                        "methodological template for Leak@t.", "reference"),
    ("2608.17223", "E", "Temporal leakage in financial-news NLP.", "reference"),
    ("2605.14636", "E", "TimeSPEC / teaching LLMs when not to know — temporal-leakage definition.", "reference"),
    # G — Phase 31 publication track: parametric leakage and decontaminated Gutenberg novels
    ("2405.18027", "G", "TimeChara: LLMs leak future knowledge in point-in-time role-play; "
                        "parametric only, no retrieval gate.", "reference"),
    ("2502.07747", "G", "WHODUNIT: character-name substitution on Gutenberg stories against "
                        "memorisation — renaming is prior method, not our contribution.", "reference"),
    ("2311.04850", "G", "Rephrased samples evade n-gram contamination checks: paraphrase is a "
                        "treatment to measure, not assume.", "reference"),
    ("2505.22945", "G", "OWL: memorised literature recalled across translation — residual "
                        "recognition survives surface change.", "reference"),
    ("2505.14925", "G", "Too Long, Didn't Model: Gutenberg long-context novel benchmark; "
                        "book-memorisation checks.", "reference"),
    ("2305.00118", "G", "Speak, Memory: the name-cloze memorisation probe "
                        "`probe/memorization.py` implements.", "applied"),
    ("2402.13718", "G", "InfiniteBench: key-entity replacement in novels to defeat memorisation.",
                        "reference"),
    ("2605.24564", "G", "Parametric look-ahead bias in backtesting — the finance analogue of "
                        "parametric spoiler leakage.", "reference"),
    ("2405.16281", "G", "ConStat: contamination as a performance gap between original and "
                        "rephrased items — the original/decontaminated comparison.", "reference"),
    # H — plan 0012 D17 / plan 0013 R7-R10: evaluation design and prior work for the paper
    ("2407.06501", "H", "STORYSUMM: faithfulness labels on story summaries; protocol union and "
                        "balanced accuracy for judge validation (plan 0013 R7).", "reference"),
    ("2501.09993", "H", "NarrativeFactScore: name-only third-person atomizer "
                        "(scripts/eval/assertion_inventory.py) and perturbation negatives (R8).",
                        "applied"),
    ("2609.05139", "H", "NS-ST-GraphRAG: spatio-temporal literary GraphRAG; related-work "
                        "positioning only (R9).", "reference"),
    ("2608.29953", "H", "SearchWiki: corpus-to-wiki construction for active information "
                        "seeking; related-work positioning (R10).", "reference"),
    ("2604.03141", "H", "Beyond Precision: importance-aware recall for long-form factuality — "
                        "gold importance weights.", "reference"),
    ("2502.10855", "H", "Claimify: factual-claim extraction and its evaluation — the atomizer "
                        "recall check's design.", "reference"),
    ("2608.29835", "H", "EVAR: evidence-validated hypothesis admission for budget-aware "
                        "narrative reasoning.", "reference"),
    ("2609.01352", "H", "CHARM: character hallucination benchmark for multicultural role play.",
                        "reference"),
    ("2409.11242", "H", "Trust-Align: grounded attributions and learning to refuse in RAG — the "
                        "abstain-over-invent rule.", "reference"),
    ("2502.14802", "H", "HippoRAG 2: non-parametric continual memory; PPR retrieval context for "
                        "graph/ppr.py.", "reference"),
    ("2404.01261", "H", "FABLES: faithfulness of book-length summaries, human-annotated claims.",
                        "reference"),
    ("2402.18264", "H", "WIKIGENBENCH: full-length Wikipedia generation benchmark.", "reference"),
    ("2609.22939", "H", "Graph-guided evidence navigation for long-novel reasoning with a local "
                        "9B model (optional, D17).", "reference"),
]

SECTIONS = {
    "A": "A. Load-bearing for code that exists today",
    "B": "B. Method choices recorded in the decision log",
    "C": "C. Baselines the programme must run",
    "D": "D. Task and benchmark positioning",
    "E": "E. Collected from web search 2026-09-11, verified here for the first time",
    "G": "G. Phase 31 — parametric leakage and decontaminated Gutenberg novels",
    "H": "H. Narrative faithfulness evaluation and the paper's prior work (plan 0012 D17)",
}
NS = {"a": "http://www.w3.org/2005/Atom"}
PAPERS_MD = PAPERS_DIR / "PAPERS.md"


def title_to_filename(title: str) -> str:
    """The naming convention (docs/papers/PAPERS.md's own 'Naming convention' section): arXiv's title,
    verbatim, with ':' replaced by ' - ', plus '.pdf'. No other character is touched -- a title
    containing '?' or an apostrophe keeps it, matching what's on disk today."""
    return title.replace(":", " -").strip() + ".pdf"


def _get_with_backoff(url, attempts=5, base_delay=20):
    """arXiv answers bursty access with `406 Not Acceptable` rather than 429, and keeps doing so
    for minutes after the burst stops -- measured 2026-09-21, the SAME single-id URL alternated
    406 and 200 over ten minutes with the User-Agent held constant, so a 406 here says nothing
    about the id. Before this, one such 406 aborted the whole verification with a traceback and
    took the other ~57 ids with it -- the opposite of this script's own rule that an id which
    does not resolve is REPORTED, not silently dropped. Delays are 20/40/60/80s (cumulative
    ~3min) because 15/30/45 was measured too short to outlast one of these episodes. Retries on
    406/429/5xx; a 404 is a real answer about the id and is never retried."""
    for attempt in range(attempts):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as resp:
                return resp.read()
        except urllib.error.HTTPError as exc:
            if exc.code not in (406, 429) and exc.code < 500:
                raise
            # 2026-09-28: the 406 became permanent for urllib from this machine while curl, same
            # URL and User-Agent, got 200 on every try -- the server filters the client, not the
            # rate. curl ships with Windows 10+ and every Linux/macOS; its answer is used as-is.
            if exc.code == 406 and shutil.which("curl"):
                got = subprocess.run(["curl", "-sfL", "-m", "120", "-A", UA["User-Agent"], url],
                                     capture_output=True)
                if got.returncode == 0 and got.stdout:
                    return got.stdout
            if attempt == attempts - 1:
                raise RuntimeError(
                    f"arXiv returned {exc.code} on {attempts} attempts. This is rate limiting, "
                    f"not a bad id -- wait a few minutes and re-run. URL: {url}"
                ) from exc
            time.sleep(base_delay * (attempt + 1))
    raise AssertionError("unreachable")


def fetch_metadata(ids):
    """One API call per batch of 20. Returns (found, unreachable).

    `found` is {id: {...}} for ids arXiv actually answered for; `unreachable` is the ids whose
    BATCH never got a response. The two are different facts and the caller must not conflate
    them: an id missing from `found` after a clean response is a citation that does not resolve
    (the thing this script exists to catch), while an unreachable id is only arXiv being
    unavailable and says nothing about the citation.

    A batch that exhausts its retries no longer aborts the run. Measured 2026-09-21: batch 1 of
    3 returned 20 verified records, batch 2 hit the 406 flap, and the exception discarded all of
    batch 1's work along with it -- so a transient outage produced no progress at all, however
    often it was re-run.
    """
    found, unreachable = {}, []
    for i in range(0, len(ids), 20):
        batch = ids[i:i + 20]
        try:
            feed = ET.fromstring(_get_with_backoff(API.format(",".join(batch))))
        except RuntimeError as exc:
            print(f"  [unreachable] {len(batch)} id(s) not checked: {exc}", file=sys.stderr)
            unreachable.extend(batch)
            continue
        for entry in feed.findall("a:entry", NS):
            raw = entry.findtext("a:id", default="", namespaces=NS)
            m = re.search(r"abs/([0-9]{4}\.[0-9]{4,5})v?(\d*)", raw)
            if not m:
                continue
            found[m.group(1)] = {
                "version": m.group(2) or "?",
                "title": " ".join(entry.findtext("a:title", "", NS).split()),
                "authors": [a.findtext("a:name", "", NS)
                            for a in entry.findall("a:author", NS)][:4],
                "published": entry.findtext("a:published", "", NS)[:10],
                "updated": entry.findtext("a:updated", "", NS)[:10],
                "primary": next(
                    (c.get("term", "?") for c in entry.findall(
                        "arxiv:primary_category", {"arxiv": "http://arxiv.org/schemas/atom"})),
                    "?"),
            }
        time.sleep(3)
    return found, unreachable


def _normalize(name: str) -> str:
    """Letters and digits only, lowercased -- collapses capitalization/punctuation edits a human
    made by hand when renaming (a trailing '?' dropped, 'a GraphRAG' hyphenated to 'a Graph RAG',
    ...) into the same key, so an existing file matches even when it isn't byte-identical to what
    `title_to_filename` would mechanically produce from the arXiv title."""
    return re.sub(r"[^a-z0-9]", "", name.lower())


def find_existing(title: str) -> Path | None:
    """The file already on disk for this title, found by normalized name rather than an exact
    match against `title_to_filename(title)` -- see that function's docstring on why the two can
    differ for a paper renamed by hand. Returns None only for a title with no file on disk at
    all, never a near-miss."""
    target = _normalize(title)
    for path in OUT_DIR.glob("*.pdf"):
        if _normalize(path.stem) == target:
            return path
    return None


def download(paper_id, title):
    existing = find_existing(title)
    if existing is not None and existing.stat().st_size > 10_000:
        return f"already on disk ({existing.name})"
    dest = existing or (OUT_DIR / title_to_filename(title))
    try:
        data = _get_with_backoff(f"https://arxiv.org/pdf/{paper_id}")
    except Exception as exc:
        return f"FAILED: {exc}"
    if not data.startswith(b"%PDF"):
        return "FAILED: response was not a PDF"
    dest.write_bytes(data)
    time.sleep(3)
    return f"downloaded ({len(data) // 1024} KB) as {dest.name}"


def write_manifest(meta, status):
    lines = [
        "# docs/papers/REFERENCES.md — every citation, verified against the arXiv API",
        "",
        "**Generated by `scripts/papers/fetch_reference_pdfs.py`. Do not hand-edit the tables.**",
        "",
        "`docs/archive/GUIDE_TO_PUBLISHING.md` §8 was assembled from web search on 2026-09-11 and never opened.",
        "This file is the verification pass for risk **R15**: every id below was resolved against",
        "the arXiv API, and the title/date printed here is arXiv's, not a search snippet. PDFs are",
        f"checked into `docs/papers/pdf/` ({len(list(OUT_DIR.glob('*.pdf')))} files,",
        "named `{Paper Title}.pdf` -- see `docs/papers/PAPERS.md` for the naming convention and the",
        "per-paper Applied/Failed/Reference status this file doesn't track.",
        "",
        "**An id in the 'Unresolved' table below has no arXiv record and must not be cited.**",
        "",
    ]
    unresolved = []
    for key, heading in SECTIONS.items():
        rows = [p for p in PAPERS if p[1] == key]
        if not rows:
            continue
        lines += [f"## {heading}", "",
                  "| arXiv | Verified title | Primary | Date | Why this repo needs it | PDF file |",
                  "|---|---|---|---|---|---|"]
        for paper_id, _, why, _status in rows:
            m = meta.get(paper_id)
            if not m:
                unresolved.append((paper_id, why))
                continue
            authors = ", ".join(m["authors"])
            if len(m["authors"]) == 4:
                authors += " et al."
            existing = find_existing(m["title"])
            pdf_cell = (
                f"[{existing.name}](<{existing.relative_to(MANIFEST.parent).as_posix()}>)"
                if existing else "not downloaded"
            )
            lines.append(
                f"| [{paper_id}](https://arxiv.org/abs/{paper_id}) | {m['title']} "
                f"<br/><sub>{authors}</sub> | {m['primary']} | {m['published']} | {why} | "
                f"{pdf_cell} |")
        lines.append("")
    if unresolved:
        lines += ["## Unresolved — no arXiv record for this id", "",
                  "These came from web search and **do not resolve**. Treat the claim attached to",
                  "each as unsourced until a real reference is found; never cite the id.", "",
                  "| arXiv id as written | What it was supposed to be |", "|---|---|"]
        lines += [f"| `{pid}` | {why} |" for pid, why in unresolved]
        lines.append("")
    lines += ["## Not on arXiv (fetch by hand)", "",
              "- Aho & Corasick (1975), *Efficient string matching: an aid to bibliographic "
              "search*, CACM 18(6) — the matcher in `entities/automaton.py`.",
              "- Haveliwala (2002), *Topic-sensitive PageRank*, WWW — personalized PageRank, "
              "`graph/ppr.py`.",
              "- WikiMAG (AAAI) — multi-agent Wikipedia-like generation; the closed-vocabulary "
              "`page_outline` is a static version of its planner.",
              ""]
    MANIFEST.write_text("\n".join(lines), encoding="utf-8")


def check_consistency(meta) -> list[str]:
    """Both directions of the drift `497087f` introduced (see module docstring): a `PAPERS` entry
    with no file on disk, and a disk PDF that no `PAPERS` entry (and so no `docs/papers/PAPERS.md` row)
    accounts for. Returns problem strings; empty means everything lines up."""
    problems = []
    known_files: set[str] = set()
    for paper_id, _, why, _status in PAPERS:
        m = meta.get(paper_id)
        if not m:
            continue  # already reported as unresolved
        existing = find_existing(m["title"])
        if existing is None:
            problems.append(f"PAPERS entry {paper_id} ({why[:50]}...) has no PDF on disk")
        else:
            known_files.add(existing.name)
    # Version-pinned review copies (non-arXiv editions) are claimed by their review's manifest.
    for manifest in (PAPERS_DIR / "reviews").glob("*-downloads.json"):
        known_files.update(Path(r["path"]).name for r in json.loads(manifest.read_text("utf-8"))
                           if "path" in r)
    for path in OUT_DIR.glob("*.pdf"):
        if path.name not in known_files:
            problems.append(f"orphan PDF, no PAPERS entry claims it: {path.name}")
    if PAPERS_MD.is_file():
        papers_md_text = PAPERS_MD.read_text(encoding="utf-8")
        for name in known_files:
            if name not in papers_md_text:
                problems.append(f"{name!r} is in PAPERS but not documented as a row in docs/papers/PAPERS.md")
    else:
        problems.append(f"{PAPERS_MD.name} does not exist -- every paper below is undocumented")
    return problems


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="verify ids and PAPERS<->disk<->PAPERS.md "
                     "consistency; download nothing")
    args = ap.parse_args()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    ids = [p[0] for p in PAPERS]
    print(f"verifying {len(ids)} arXiv ids ...")
    meta, unreachable = fetch_metadata(ids)
    status = {}
    for paper_id, _, _why, _status in PAPERS:
        if paper_id in unreachable:
            print(f"  {paper_id}  not checked — arXiv unreachable this run")
            continue
        if paper_id not in meta:
            print(f"  {paper_id}  UNRESOLVED — no arXiv record")
            continue
        status[paper_id] = "n/a (--check)" if args.check else download(paper_id, meta[paper_id]["title"])
        print(f"  {paper_id}  {meta[paper_id]['title'][:60]:<60} {status[paper_id]}")

    # REFERENCES.md is a FULL REWRITE, so building it from a partial fetch would silently drop
    # the verified row of every id arXiv happened not to answer for -- turning a transient
    # outage into permanent loss in the one file that exists to prove citations were checked.
    # A partial run therefore reports and changes nothing.
    if unreachable:
        print(f"\n{len(unreachable)} id(s) unreachable: {', '.join(unreachable)}")
        print(f"{MANIFEST.name} NOT rewritten — a partial fetch would drop their verified rows.")
        print("arXiv 406s in flapping episodes lasting minutes; re-run when it settles.")
        return 1

    write_manifest(meta, status)
    missing = [p for p in ids if p not in meta]
    print(f"\nresolved {len(meta)}/{len(ids)}; unresolved: {', '.join(missing) or 'none'}")
    print(f"manifest: {MANIFEST}")

    problems = check_consistency(meta)
    if problems:
        print(f"\n{len(problems)} consistency problem(s):")
        for p in problems:
            print(f"  - {p}")
        return 1
    print("\nPAPERS <-> disk <-> docs/papers/PAPERS.md: consistent.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
