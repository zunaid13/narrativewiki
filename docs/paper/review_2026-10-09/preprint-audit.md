# Independent audit of preprints and non-Anthology references

Audit date: 2026-10-09. Source: `docs/paper/refs.bib`. This audit independently opened the authoritative source for each assigned entry; repository comments claiming prior verification were not treated as evidence. It also searched for subsequent publication where the bibliography currently cites a preprint. A failed publication search is reported as a bounded search result, never as proof that a publication does not exist.

## Findings

None of the ten assigned sources is hallucinated. The seven arXiv IDs all resolve to the stated work, including the August and September 2026 papers. All seven author lists, their order, titles apart from inconsequential capitalization, and first-submission years agree with arXiv. The existing preprint entries are valid; missing arXiv DOI/eprint fields are optional enrichment, not bibliographic errors.

The only source-version cleanup identified in this subset concerns the Amazon page. Its current visible headline and byline differ from the bibliography's older page title and corporate attribution. The tool/browser metadata still advertises the old title, so this is a title/version inconsistency rather than evidence of fabrication. The page's publication year 2025 remains defensible because it explicitly gives that original publication date. Do not silently change the year to 2026 without indicating that it is an updated version.

| Key | Independent result | Authoritative evidence and publication check |
| --- | --- | --- |
| `yang2025evolvtrip` | Correct title, all six authors/order, arXiv ID and year. Submitted June 16, 2025. | [arXiv record](https://arxiv.org/abs/2506.13641). The [OpenReview page](https://openreview.net/forum?id=8r9xMCqPkh) identifies an ACL ARR May 2025 submission, not an accepted proceedings article. [Author repository](https://github.com/Bernard-Yang/EvolvTrip) and exact-title searches yielded no authoritative published replacement. Keep the preprint citation unless the authors supply a publication record. |
| `huang2025living` | Correct title, all eight authors/order, arXiv ID and year. Submitted December 8, 2025. | [arXiv record](https://arxiv.org/abs/2512.07474). No journal reference appears in this record; an exact-title search, including ACM sources, did not establish a refereed replacement. |
| `lin2026nsst` | Correct title, sole author Zheng Kui Lin, arXiv ID and year. Submitted September 4, 2026. | [arXiv record](https://arxiv.org/abs/2609.05139). The comments say it was submitted to *Information Processing and Management*. Submission is not acceptance or publication, and no published replacement was established. |
| `edge2024graphrag` | Correct title, all ten current-version authors/order, arXiv ID and first-submission year. Version 1: April 24, 2024; version 2: February 19, 2025. | [arXiv record](https://arxiv.org/abs/2404.16130). [Microsoft Research's project publications page](https://www.microsoft.com/en-us/research/project/graphrag/publications/) still classifies the work as a preprint/unpublished. Some search snippets and older citations omit Metropolitansky and Ness; that is older-version metadata and does not invalidate this entry's complete current author list. |
| `singh2026searchwiki` | Correct title, all six authors/order, arXiv ID and year. Submitted August 30, 2026. | [arXiv record](https://arxiv.org/abs/2608.29953). No published replacement was established. The ID is unusual-looking but genuine; do not label it hallucinated based on its numeric form or recency. |
| `cheng2025contamination` | Correct title, all three authors/order, arXiv ID and year. Version 1: February 20, 2025; version 2: June 5, 2025. | [arXiv record](https://arxiv.org/abs/2502.14425). No journal reference is supplied there; the exact-title search did not establish a refereed replacement. |
| `gupta2025whodunit` | Correct title apart from harmless case normalization, sole author, arXiv ID and year. Submitted February 11, 2025. | [arXiv record](https://arxiv.org/abs/2502.07747), independently supported by the [author's repository and supplied citation](https://github.com/kjgpta/WhoDunIt-Evaluation_benchmark_for_culprit_detection_in_mystery_stories). No published replacement was established. |
| `kim2024fables` | Correct all eight authors/order, title, venue and year. It really is a COLM 2024 paper. | [arXiv journal-reference field](https://arxiv.org/abs/2404.01261), [official COLM accepted-paper list](https://github.com/COLM-org/COLM2024/blob/main/AcceptedPapers.html), and [published OpenReview PDF](https://openreview.net/pdf?id=YfHxQSoaWU). Current URL points to arXiv even though entry correctly names COLM. Prefer the proceedings URL as a consistency improvement, not a correction of a nonexistent venue: `https://openreview.net/forum?id=YfHxQSoaWU`. |
| `jones2018spoilers` | Correct authors, title, volume 19, issue 1, pages 77–93, DOI and issue year 2018. | [Springer publisher record](https://link.springer.com/article/10.1007/s00799-016-0200-8), supported by the [Los Alamos repository](https://laro.lanl.gov/esploro/outputs/journalArticle/Avoiding-spoilers-wiki-time-travel-with/9916369746403761). Springer gives online publication December 21, 2016 and issue date March 2018. The bibliography's 2018 is correct for this fully assigned journal citation. Do not replace it with 2016 simply because the DOI suffix or initial online date contains 2016. |
| `amazon2025kindle` | Genuine product page; URL, original year, and host are correct. Current visible headline and byline warrant version cleanup. | [Amazon source page](https://www.aboutamazon.com/news/books-and-authors/kindle-recaps-feature-ebook-series-refreshers). It identifies Amazon Staff as author, April 2, 2025 as original publication date, and July 2, 2026 as update date. Its present visible headline is used in the optional replacement below. The article supports Amazon's stated position-aware feature behavior; it is not independent empirical validation of spoiler safety. |

## Recommended entry for the current Amazon page version

This captures the current visible headline/byline and preserves original publication year with an explicit update note. It is a source-version cleanup, not a hallucinated-reference repair. `note` is intentional here because it documents the updated web source used for the claim; the existing repository preference to avoid notes is a formatting preference, not a requirement to conceal the version date.

```bibtex
@misc{amazon2025kindle,
  author       = {{Amazon Staff}},
  title        = {How {Kindle} Helps You Stay Immersed in Every Book You Read},
  howpublished = {About Amazon},
  year         = {2025},
  month        = apr,
  url          = {https://www.aboutamazon.com/news/books-and-authors/kindle-recaps-feature-ebook-series-refreshers},
  note         = {Published April 2, 2025; updated July 2, 2026; accessed October 9, 2026}
}
```

The other assigned entries need no substantive BibTeX replacement. No new journal, conference, DOI, or author should be invented to make a preprint look refereed. An arXiv DOI, if desired, is simply `10.48550/arXiv.<existing-ID>`; adding it does not change publication status.

One source-use nuance deserves correction in `sections/02-related.tex`: Jones et al. find nearest-capture replay from the Internet Archive unsafe, and propose access to the wiki's own exact revision history through Memento. The current description can sound as if generic archived-webpage replay reliably avoids spoilers. Describe their proposal as accessing pre-episode wiki revisions via Memento, making clear that web archives may contain a later nearest capture. This is a paraphrase-precision issue, not a metadata error. The temporal-graph and navigable-wiki descriptions of the assigned preprints align with their abstracts; full technical claim verification would require deeper reading.

## Official submission requirements relevant to venue suitability

The subject is within both conferences' general scope: generation, information retrieval/extraction, evaluation, and digital humanities. Neither conference requires selection of its special theme. COLING's theme is NLP for Linguistics; NAACL's theme is agentic communication, neither of which the present application automatically satisfies.

The [COLING 2027 official main CFP](https://2027.coling-iccl.org/calls/main_conference_papers/) gives October 12, 2026 as the latest ARR submission deadline, December 23, 2026 as commitment, and February 10, 2027 as notification. It permits eight pages for a long paper or four for a short paper, unlimited references/appendix, and requires limitations after the conclusion and before references.

The [NAACL 2027 official main CFP](https://2027.naacl.org/calls/main_conference_papers/) gives the same submission, commitment, and notification dates, and the same main-content limits. The October ARR submission remains conference-agnostic until commitment. Authors designate only one primary conference; optional consideration at the second venue after rejection is capacity-dependent, not guaranteed. NAACL deadlines are 23:59 UTC−12 (AoE), so October 12 corresponds to October 13 at 17:59 in Bangladesh. NAACL lists reviewer registration October 12 and metareviews December 18, while the live ARR schedule below lists October 14 and December 17; use the submission system's instructions for these administrative dates rather than assuming the pages agree.

The [live ARR schedule](https://aclrollingreview.org/dates) agrees with the conference CFPs on December 23 commitment. Cached search results for the source repository still showed an older December 20 commitment date; the current official rendered page supersedes that cache.

The [current ARR CFP](https://aclrollingreview.org/cfp) requires a dedicated Limitations section and anonymized main and supplementary artifacts; eight-page long submissions exceeding the content limit are desk-rejected. A refereed publication should supersede or accompany its preprint. Papers appearing within three months of submission are contemporaneous, so an additional experimental comparison with the recent SearchWiki or NS-ST-GraphRAG preprints is not mandatory. Since October 2026, guaranteed review requires a qualified service contributor and complete author OpenReview profiles; consult its linked sustainable-reviewing policy for administration.

The [NAACL 2027 demonstration CFP](https://2027.naacl.org/calls/system_demonstration/) is a separate possible route, with December 4, 2026 deadline, six-page body, maximum two-page appendix, single-blind submission, up to 2.5-minute video, and live demo or installable package. It explicitly requires empirical evaluation and substantive design/technical contribution: a functioning prototype alone does not qualify. It also forbids a substantially overlapping simultaneous ARR submission. A demo recommendation therefore requires redesigning the paper for that track and maintaining the same evidential standards; it is not an automatic acceptance fallback.

## Limits of this audit

This is a metadata/existence audit of the assigned sources, plus official venue rules. It does not verify every technical claim made inside the cited papers. Search results do not establish the absence of all possible subsequent publications. The valid metadata should therefore be kept unless a newer authoritative venue record is supplied. No manuscript or bibliography source files were changed.
