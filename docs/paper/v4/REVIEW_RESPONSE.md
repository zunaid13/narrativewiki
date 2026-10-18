# Response to the two-version review (2026-10-19)

Review: `narrativewiki_review.md` (V1 = submitted PDF, V2 = this v4). Every item below was checked
against the data or the code before it was changed; observations are in `docs/MEASUREMENTS.md`
(2026-10-19 rows). Build: main text ends on p8, abstract 192–200 words, 74 pages.

## Fixed

| Review item | What changed in v4 |
|---|---|
| Causal wording ("stability comes from", "much of the gap arises", "one cause", "both effects sit at publication") | V1's hedges restored in §6.3, §6.4, Fig. 5 caption, §7, App. H, App. I intro |
| "Exploratory" dropped from the central-character split | Restored in §6.3, Fig. 5(a), Table 2 |
| Build revision missing from results | §6.4: reported build is the second; first had citation sufficiency 0.112 |
| 3.8× without comparator/condition | "3.8 times long context's distinct assertions, original text" (abstract, §6.3, teaser) |
| Abstract mixes text conditions | Each figure labelled (treated / original); central-three original values added |
| Teaser mixes conditions, crowded | Every number tagged orig./treated; one figure per line; B1-citation and B4 lines dropped (in text) |
| X2 "most at t = 1" | "all but one at t ≤ 3" (§6.1); App. N states the treated-vs-original excess |
| "Presumed keeps a belief apart" vs renderer | Checked the delivered pages: relation block marks it, infobox family field and related list do not. §6.2 and App. D say so |
| "Nothing generated from the full graph" vs later aliases in v1 prompts | §4 Build scope: filter applies to published claims, not build inputs (D3) |
| "Prompts omit the title" | App. D: prompts do not state it, but mined names carry it |
| Human-check disagreements; B4 citation labels unchecked | Limitations; §6.4 notes B4's citation labels have no human check |
| Circular "recall audit in Section 5" | App. B describes the audit in place |
| Paired-difference definition | App. B and Table 15: plain per-cutoff differences of whole-artifact rates (recomputed) |
| Proposition 2 | Dropped (premise does not hold; bound never binds); Props renumbered 1–3; R5 cites Prop. 1 |
| "Table 25 reports both builds under one rule" | Only relationship lines were re-read under one rule |
| Colour scheme declared but not kept | Table 1 declares one scheme for table cells; Table 18 aligned; figures keep their own legends |
| Defects ordered D1, D2, D3, D5, D4 | D1–D5 in order |
| §6.1 "paraphrase hides the book" | "paraphrase reduces recognition"; author identification after paraphrase added |
| Kindle "without a published evaluation" | "although we are unaware of a published evaluation" |
| "Moved here to keep eight pages" note; RQ table in appendix | Note removed; Table 2 (glance) back in the main text, with condition labels |
| Duplicates | Removed: Fig. 9 TikZ redraw of Fig. 8, Fig. 7 (= Fig. 3b), Fig. 15 (= Fig. 4b), Fig. 14 (redraw of Fig. 2), the concordance table (= Tables 4–6), the arbitration and paraphrase exchanges printed twice. One copy of each remains |
| Bibliography | Middle initials from the papers' title pages (Theodore A. Kanell, Monica S. Lam, Lydia B. Chilton); Amazon year 2026 (the July 2026 version cited) |

## Alignment fixes found while checking

- The prompt-stage table (`table*` in one-column mode) floated to p76; now `table[!ht]` at the start of App. Q.
- "Appendix~\ref{app:prompts-full}" printed "P" (unnumbered subsection); now Q.2.
- Float-only pages centred their floats vertically, leaving white bands; now top-aligned.

## Not changed, with reason

- Bamman title and "Jianlyu Chen": V2 (this bib) is already correct; V1's PDF came from an older `.bbl`.
- BooookScore / NovelQA page numbers: not verifiable from the stored PDFs; omitted rather than guessed.
- Amazon access day (11 vs 12 October): the repo records 11 October; kept.
- Running the proposed ablations, a second corpus/generator, length-matched baseline, repeated builds: experiments, not text fixes; they cost API money and need a decision.
- Five now-unused source files (`figures/f0-overview.tex`, `f3-systems.tex`, `f5-decon-recall.tex`, `f9-cutoffs.tex`, `tables/t-human-concordance.tex`) remain on disk; deletion was blocked by the permission classifier.
