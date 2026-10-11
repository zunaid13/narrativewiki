# 0017 — Independent Codex paper rewrite and stored-evidence sensitivity analyses

Status: COMPLETE (2026-10-09). User-authorised separate manuscript at repository-root `paper_codex/`; original `docs/paper/` remains the reviewed source. Completion concerns the honest manuscript and reproducible sensitivity analyses; the scientific requirements below remain unperformed.

## Problem and evidence

`docs/paper/REVIEW_2026-10-09.md` and `review_2026-10-09/method-review.md` identify unresolved human-accepted quality-label disagreements, weak cross-page disclosure search, confounded annotators, insufficient gold evidence packets, single-series tuning, faulty pairing and zero-bound descriptions, treatment overclaims, and unequal published surfaces. Original arithmetic reproduces the stored labels, but that is not independent validation.

## Scope and approach

Write the strongest defensible complete diagnostic/negative-results manuscript with current evidence. Do not manufacture independent humans, held-out runs, significance or better performance. Repair inaccurate reporting; prominently distinguish observations from validated population/safety claims. Recompute useful descriptive sensitivity analyses from stored labels only: accepted-review discrepancies by system/build, common-cast surface breakdown, common gold-fact/cutoff paired differences, and recall on the fully established gold-evidence subset. Keep post-hoc selection and missing labels explicit. No original label/schema or pipeline change, no paid call, no additional corpus run.

## Deliverables and files

- `paper_codex/main.tex`, sections, figures, tables, appendix, verified `refs.bib`, anonymous ACL style and result registry.
- Reading and review-numbered PDFs, an Overleaf-compatible source archive, README and submission checklist.
- `paper_codex/REVIEW_RESPONSE.md`: every criticism resolved by correction/reanalysis versus empirical work still outstanding.
- `scripts/papers/codex_paper_analysis.py`: deterministic stored-evidence analysis; JSON/TeX outputs in `paper_codex/analysis` and `tables`.
- `scripts/papers/build_codex_paper.py`: portable Windows-compatible build and focused checks.
- Append observations/new values to `docs/MEASUREMENTS.md`; record reinterpretation/new sensitivity analyses in `docs/eval/CHANGES.md` without replacing prior history.

## Sources and reading depth

Original manuscript, source tables, annotation review sheets and recorded outputs are primary local evidence. Prior complete publisher/arXiv metadata audit is in `docs/paper/review_2026-10-09/`. ARR [CFP](https://aclrollingreview.org/cfp) and ACL [formatting rules](https://acl-org.github.io/ACLPUB/formatting.html) checked as official submission requirements. CHIRON/Jones/StorySumm source interpretations were checked during prior review; reuse those bounded interpretations. No claim that preprint publication searches establish universal absence.

## Ordered work and validation

1. Establish isolated source folder, inputs and conservative task/contribution framing.
2. Produce deterministic reanalysis with exact input provenance and explicit population labels. Stop if sheet fields cannot be mapped reliably; omit the analysis rather than infer missing judgements.
3. Write main manuscript and condensed factual supplement; put annotation/detector caveats beside the claims, not only in Limitations. Define gold nuggets and extracted evidence stamps separately from gold reveal volumes.
4. Build both anonymous PDFs and source package without installing packages. Check abstract at most 200 words, content at most eight pages, Limitations and Ethics placement, references, measured keys, unresolved citations, overfull boxes and render legibility. Read generated pages, not only source.
5. Independent reviewer audits scientific claims, every critique response and generated counts. Correct until focused checks pass; preserve any remaining empirical limitation explicitly.
6. Commit only work-owned files after verification.

Commands: `python scripts/papers/codex_paper_analysis.py`; `python scripts/papers/build_codex_paper.py`; `.venv/Scripts/python.exe docs/eval/labelling_tools/derived_values.py --results paper_codex/results.tex` (unchanged shared keys only); targeted PDF/source checks in builder.

## Stop criteria and unresolved decisions

Completed: separate main manuscript and concise supplement; audited bibliography; stored-evidence reanalysis with input hashes and byte-identical rerun; current-versus-frozen review counts; evidence-packet, surface, paired and same-graph sensitivities; independent Codex source/PDF critique; anonymous reading/review PDFs and self-contained Overleaf source archive. Focused source, numerical and compilation checks passed. Final mechanical counts and commands are recorded in `docs/MEASUREMENTS.md`; each criticism's disposition is in `paper_codex/REVIEW_RESPONSE.md`.

Do not claim all empirical weaknesses fixed by writing. The user confirmed internal author reviewers, general familiarity with Anne, one day, no compensation, and full-set versus sample correction policy on 2026-10-09. Describe the internal review accurately; keep time/pay metadata in the submission checklist unless required in the manuscript. Independent blinded human disclosure validation, held-out generalisation and treatment proof-reading remain unperformed unless real evidence arrives. A modified treatment or new label rule would invalidate affected earlier cells and requires a separate complete measured run; no such run is needed to finish this honest rewrite. Existing anonymous release may require author update before submission; local artefact generation does not publish externally.
