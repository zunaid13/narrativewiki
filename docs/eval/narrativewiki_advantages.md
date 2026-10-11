# Where NarrativeWiki pulls ahead of long-context prompting, prefix retrieval and LightRAG

Date: 2026-10-11. Data: the *Anne of Green Gables* series, five books, all systems as reported in
the paper. Nothing here required a new model call; every number comes from stored labels, the
built wikis, or the paper's results file. Sources and the reproducing command are in section 7.

## 1. Short answer

On the paper's headline averages NarrativeWiki is not the best system: prefix retrieval is ahead on
average recall, precision and citation quality and discloses no later facts, at about a tenth of
the input tokens (section 3). The headline averages hide five situations in which NarrativeWiki is
ahead, and they share one cause: **its pages are assembled from facts that accumulate in a graph,
while every other system rewrites each page from scratch in one model call with a fixed length
budget.**

| # | Situation | NarrativeWiki | Best other system |
|---|---|---|---|
| 1 | Recall on the three most-covered characters, unfamiliar text | 0.929 | 0.794 (long context) |
| 2 | Facts a page loses when the reader moves to the next book, unfamiliar text | 1 | 11–24 (all others) |
| 3 | Average recall on unfamiliar text, and its spread across reading positions | 0.843, spread 0.017 | 0.845, spread 0.078 (long context) |
| 4 | Recall against LightRAG, the other graph-based system | 0.802 | 0.536 (LightRAG) |
| 5 | Size of what is published per reading position | 6,970 distinct statements, 97–440 pages | 1,821 statements, 14–43 pages (long context) |

Sections 4 and 5 give the data behind each row. Section 6 lists what these results do **not**
show; it should be read before any of this is quoted.

## 2. What a reader needs to know first

### 2.1 The task

Each system builds a character wiki for a book series. The reader says "I have read up to book
*t*" (the **cutoff**), and the wiki for that cutoff may only say what books 1 to *t* establish.
There are five cutoffs, *t* = 1 to 5.

### 2.2 The corpus

Five books of the *Anne of Green Gables* series, in reading order: *Anne of Green Gables* (book 1),
*Anne of Avonlea* (2), *Anne of the Island* (3), *Anne's House of Dreams* (4), *Rainbow Valley* (5).
Together: 428,122 words, 8,489 paragraphs, 184 chapters. All five books fit in one model context
window.

### 2.3 The systems

All systems use the same language model. The first four write one page per character from a given
list of characters, using one shared page template with sentence limits per section (appearance
2–4 sentences, personality 2–6, history 3–12, at most five quotes).

| Name used here | Code in the paper | How a page is produced |
|---|---|---|
| **Long context** | B1 | The whole text of books 1..*t* is placed in the prompt; the model writes the page in one call. |
| **Prefix retrieval** | B2 | A search index over books 1..*t* (keyword + embedding search) returns up to 20,000 tokens of passages about the character; the model writes the page from them in one call. |
| **LightRAG** | B3 | The open-source graph-retrieval system LightRAG 1.5.7 indexes books 1..*t* and returns up to 20,000 tokens of entities, relations and passages; the model writes the page from them in one call. |
| **Graph + retrieval** | B4 | NarrativeWiki's own graph supplies the facts and evidence paragraphs visible at *t*; the model writes the page from them in one call. |
| **NarrativeWiki** | B5 | Facts ("claims") are extracted once from all five books into a graph; each claim records the book that supplied its evidence. The wiki for cutoff *t* is rendered from the claims with evidence in books 1..*t*. Names, roles, titles, family and relationship lines are printed directly from graph rows without a model call; only short prose paragraphs are generated, from the already-filtered claims. It discovers its own characters and also publishes relationship pages, a timeline and shared pages for places and groups. |
| *Closed book* (diagnostic) | X1 | The model is given only the series title and the character's name, no text. Shows what the model already knows. |
| *Full text + instruction* (diagnostic) | X2 | All five books are in the prompt with the instruction "write for a reader of book *t*". |

### 2.4 The measurements

| Term | Meaning |
|---|---|
| **Gold fact** | One of 111 fixed facts about 43 characters, each tagged with the book that establishes it (for example "Anne wins the Avery scholarship", book 1). |
| **Fact check** | One gold fact tested at one cutoff. A fact is tested at every cutoff from its own book onward, giving 23 + 46 + 66 + 89 + 111 = **335 fact checks** over the five cutoffs. |
| **Recall** | The share of fact checks where the system's wiki at that cutoff conveys the fact, on any page and in any wording. The same rule and the same search over the whole wiki were applied to every system. |
| **Precision** | The share of 40 sampled statements per cutoff that the eligible text supports, judged where the statement appears on its page. |
| **Citation sufficiency** | The share of sampled statements whose cited paragraphs are enough, on their own, to establish the statement. |
| **Later facts disclosed** | Out of 220 checks (88 + 65 + 45 + 22 for cutoffs 1–4) of facts established *after* the cutoff, how many the wiki states or implies. Lower is better; this is the spoiler measure. |
| **Distinct statements** | The number of different atomic statements a system's wiki makes at one cutoff, duplicates removed. |

### 2.5 Original text and unfamiliar ("treated") text

The series is famous, so the model knows much of it from training. Given no text at all, the
closed-book diagnostic still reaches recall 0.683. To separate *reading the supplied text* from
*remembering the book*, every system was run a second time on a **treated** copy: names are
replaced and every paragraph is paraphrased, paragraph by paragraph, so the content is the same
but the model no longer recognises the book. On the treated copy closed-book
recall falls to 0.003. This document calls the treated copy **unfamiliar text**. Results on it are
the cleaner test of what a system gets from the text it was given.

### 2.6 Who made the labels

Recall, precision and citation labels were produced by an AI annotator (Claude) under written
rules and then reviewed and accepted by the authors. They are not independent human annotation.

## 3. The overall picture (so the advantages are read in context)

Means over the five cutoffs. Bold marks the best of the five compared systems in each column.

| System | Recall, original | Recall, unfamiliar | Precision, original | Citation sufficiency, original | Later facts disclosed, original / unfamiliar | Distinct statements per cutoff | Input / output tokens, millions |
|---|---|---|---|---|---|---|---|
| Long context | **0.848** | **0.845** | 0.929 | 0.658 | 0 / 0 of 220 | 1,821 | 69.23 / 0.37 |
| Prefix retrieval | 0.834 | 0.784 | 0.960 | 0.774 | 0 / 0 of 220 | 1,718 | **3.42** / 0.37 |
| LightRAG | 0.536 | 0.470 | 0.950 | 0.765 | 0 / 0 of 220 | 1,404 | 5.08 / 1.01 |
| Graph + retrieval | 0.761 | 0.704 | **0.965** | **0.915** | 0 / 2 of 220 | 1,701 | not reported |
| NarrativeWiki | 0.802 | 0.843 | 0.789 | 0.512 | 1 / 4 of 220 | **6,970** | 33.13 / 1.86 |
| *Closed book* | 0.683 | 0.003 | 0.814 | none (cites nothing) | 4 / 0 of 220 | 1,526 | 0.06 / 0.15 |
| *Full text + instruction* | 0.814 | 0.744 | 0.910 | 0.625 | 8 / 23 of 220 | 1,829 | 98.67 / 0.37 |

Read plainly: NarrativeWiki is third on average recall on the original text, last of the five on
precision and citation sufficiency, and the only compared system besides Graph + retrieval with
any later-fact disclosure. The rest of this document is about where it is nevertheless ahead.

## 4. The five situations where NarrativeWiki is ahead

### 4.1 Characters with a lot of material

**Finding.** On the three characters that have the most gold facts, NarrativeWiki has the highest
recall of every system, and on the unfamiliar text its lead grows as more books are read. On the
other 40 characters it is behind.

The three characters are Anne Shirley (81 of the 335 fact checks), Gilbert Blythe (39) and Diana
Barry (21): 141 fact checks together. They were chosen by that count alone, before looking at any
system's results. "Other" means the remaining 40 characters, 194 fact checks.

Recall pooled over the five cutoffs (facts conveyed / fact checks):

| System | Central three, original | Central three, unfamiliar | Other 40, original | Other 40, unfamiliar |
|---|---|---|---|---|
| NarrativeWiki | **126/141 = 0.894** | **131/141 = 0.929** | 143/194 = 0.737 | 150/194 = 0.773 |
| Long context | 118/141 = 0.837 | 112/141 = 0.794 | 164/194 = 0.845 | 161/194 = 0.830 |
| Prefix retrieval | 110/141 = 0.780 | 94/141 = 0.667 | **169/194 = 0.871** | **164/194 = 0.845** |
| LightRAG | 67/141 = 0.475 | 56/141 = 0.397 | 125/194 = 0.644 | 110/194 = 0.567 |
| Graph + retrieval | 106/141 = 0.752 | 86/141 = 0.610 | 147/194 = 0.758 | 155/194 = 0.799 |
| Full text + instruction | 115/141 = 0.816 | 95/141 = 0.674 | 156/194 = 0.804 | 153/194 = 0.789 |

Recall on the central three at each cutoff, unfamiliar text. NarrativeWiki rises as the reader
advances; long context and prefix retrieval fall:

| System | Cutoff 1 | Cutoff 2 | Cutoff 3 | Cutoff 4 | Cutoff 5 |
|---|---|---|---|---|---|
| NarrativeWiki | 12/14 (86%) | 19/21 (90%) | 29/31 (94%) | 35/37 (95%) | 36/38 (95%) |
| Long context | 14/14 (100%) | 19/21 (90%) | 23/31 (74%) | 27/37 (73%) | 29/38 (76%) |
| Prefix retrieval | 12/14 (86%) | 14/21 (67%) | 19/31 (61%) | 23/37 (62%) | 26/38 (68%) |
| LightRAG | 5/14 (36%) | 9/21 (43%) | 12/31 (39%) | 16/37 (43%) | 14/38 (37%) |

The same on the original text:

| System | Cutoff 1 | Cutoff 2 | Cutoff 3 | Cutoff 4 | Cutoff 5 |
|---|---|---|---|---|---|
| NarrativeWiki | 12/14 (86%) | 18/21 (86%) | 27/31 (87%) | 34/37 (92%) | 35/38 (92%) |
| Long context | 11/14 (79%) | 19/21 (90%) | 25/31 (81%) | 30/37 (81%) | 33/38 (87%) |
| Prefix retrieval | 12/14 (86%) | 15/21 (71%) | 22/31 (71%) | 29/37 (78%) | 32/38 (84%) |
| LightRAG | 3/14 (21%) | 13/21 (62%) | 12/31 (39%) | 19/37 (51%) | 20/38 (53%) |

Per character, pooled over cutoffs (facts conveyed out of that character's fact checks):

| Character (fact checks) | Text | NarrativeWiki | Long context | Prefix retrieval | LightRAG |
|---|---|---|---|---|---|
| Anne Shirley (81) | original | **78** | 64 | 60 | 41 |
| Anne Shirley (81) | unfamiliar | **72** | 61 | 53 | 41 |
| Gilbert Blythe (39) | original | 31 | 33 | **34** | 12 |
| Gilbert Blythe (39) | unfamiliar | **38** | 31 | 30 | 8 |
| Diana Barry (21) | original | 17 | **21** | 16 | 14 |
| Diana Barry (21) | unfamiliar | **21** | 20 | 11 | 7 |

Note the precise shape of this result: on the original text the lead comes from the protagonist
alone (Anne Shirley, 78 against 64 and 60); on the unfamiliar text NarrativeWiki leads on all
three.

**Why this happens.** A page written in one model call under a fixed template does not get longer
as the story gets longer. NarrativeWiki's page is rendered from every eligible claim, so it grows.
Length of Anne Shirley's page in words a reader actually reads (citations removed):

| System | Cutoff 1 | Cutoff 2 | Cutoff 3 | Cutoff 4 | Cutoff 5 |
|---|---|---|---|---|---|
| NarrativeWiki | 1,813 | 2,363 | 2,688 | 3,719 | 3,439 |
| Long context | 864 | 852 | 913 | 984 | 1,157 |
| Prefix retrieval | 699 | 553 | 708 | 711 | 688 |
| LightRAG | 620 | 731 | 653 | 554 | 410 |

The text available about Anne grows from one book to five, while the single-call pages stay
between 400 and 1,200 words, so they must leave more out at every cutoff. In addition, prefix
retrieval and LightRAG can pass at most 20,000 tokens of passages to the model, far less than the
series says about its protagonist.

### 4.2 Pages do not lose facts as the reader advances

**Finding.** When a reader moves from book *t* to book *t*+1, a NarrativeWiki page almost never
drops a fact it conveyed before. The other systems do, because they rewrite each page for each
cutoff.

Number of gold facts conveyed at cutoff *t* and no longer conveyed at cutoff *t*+1, summed over
*t* = 1 to 4:

| System | Original text | Unfamiliar text |
|---|---|---|
| NarrativeWiki | **1** | **1** |
| Long context | 10 | 14 |
| Prefix retrieval | 4 | 24 |
| LightRAG | 19 | 13 |
| Graph + retrieval | 12 | 14 |
| Full text + instruction | 7 | 11 |

Graph + retrieval reads the same graph as NarrativeWiki but writes each page in one model call,
and it loses 12 and 14 facts. This points to the rendering step, where the page is printed from
stored claims, as the source of the stability, and not to the graph alone.

### 4.3 Text the model has not seen before

**Finding.** On the unfamiliar text NarrativeWiki's average recall equals long context's, exceeds
prefix retrieval's, is the steadiest across cutoffs, and is the only one that did not fall.

| System | Recall, original | Recall, unfamiliar | Change | Spread across cutoffs, unfamiliar (standard deviation) |
|---|---|---|---|---|
| NarrativeWiki | 0.802 | 0.843 | **+0.041** | **0.017** |
| Long context | 0.848 | 0.845 | −0.003 | 0.078 |
| Prefix retrieval | 0.834 | 0.784 | −0.050 | 0.052 |
| LightRAG | 0.536 | 0.470 | −0.067 | 0.074 |
| Graph + retrieval | 0.761 | 0.704 | −0.057 | 0.057 |
| Closed book | 0.683 | 0.003 | −0.680 | — |
| Full text + instruction | 0.814 | 0.744 | −0.070 | — |

Head to head on the same 335 fact checks, unfamiliar text:

| NarrativeWiki against | Both convey | Only NarrativeWiki | Only the other | Neither |
|---|---|---|---|---|
| Long context | 247 | 34 | 26 | 28 |
| Prefix retrieval | 234 | 47 | 24 | 30 |
| LightRAG | 154 | 127 | 12 | 42 |

A system whose recall drops when the book becomes unrecognisable was partly leaning on what the
model remembered. NarrativeWiki's result is consistent with its design, which extracts claims
passage by passage; the rise of 0.041 itself is from single builds and may be noise.

### 4.4 Against LightRAG, the other graph-based system

**Finding.** NarrativeWiki conveys far more of the gold facts than LightRAG on both texts.

| | Recall, original | Recall, unfamiliar |
|---|---|---|
| NarrativeWiki | 0.802 | 0.843 |
| LightRAG | 0.536 | 0.470 |

Head to head on the 335 fact checks: on the original text NarrativeWiki alone conveys 94 and
LightRAG alone 17 (both 175, neither 49); on the unfamiliar text NarrativeWiki alone conveys 127
and LightRAG alone 12. LightRAG's recall is also the least stable across cutoffs on the original
text (standard deviation 0.133 against NarrativeWiki's 0.026). LightRAG remains ahead on precision
(0.950 against 0.789), citation sufficiency (0.765 against 0.512) and input tokens (5.08 million
against 33.13 million).

### 4.5 How much is published, and in what form

**Finding.** NarrativeWiki publishes about four times as many distinct statements as any other
system and seven to ten times as many pages, including page types the others do not produce.

Size of the wiki at each cutoff (pages / words with citations removed):

| System | Cutoff 1 | Cutoff 2 | Cutoff 3 | Cutoff 4 | Cutoff 5 |
|---|---|---|---|---|---|
| NarrativeWiki | 97 / 38,910 | 193 / 80,165 | 275 / 113,891 | 345 / 148,154 | 440 / 194,562 |
| Long context | 14 / 6,058 | 21 / 10,585 | 25 / 14,018 | 33 / 18,170 | 43 / 24,625 |
| Prefix retrieval | 14 / 6,627 | 21 / 10,762 | 25 / 13,217 | 33 / 17,352 | 43 / 22,989 |
| LightRAG | 14 / 4,736 | 21 / 8,384 | 25 / 10,386 | 33 / 14,273 | 43 / 18,951 |

NarrativeWiki repeats relationship lines on both characters' pages and on the pair's page, so its
word count overstates its distinct content. The deduplicated measure is distinct statements per
cutoff: 6,970 for NarrativeWiki against 1,821 (long context), 1,718 (prefix retrieval) and 1,404
(LightRAG).

What the 345 pages at cutoff 4 are: 191 character pages, 147 relationship pages (one per pair of
characters), 4 timeline pages and 3 shared pages for groups, places and objects. The other systems
publish only the character pages of the given cast (33 at cutoff 4).

**A worked example: the relationship between Anne and Gilbert, as shown on Anne's page at cutoff 4**
(book 4 is where they marry).

Long context prints one line:

> Spouse of — Husband, former schoolmate and college rival

NarrativeWiki prints a short generated paragraph, whose source list names 82 paragraphs of the
books, followed by seven dated lines, each with its own paragraph citations:

> - Rival of — academic rivals competing for top marks in school
> - Romantically involved with — harbors romantic feelings for her
> - Saved by
> - Enemy of — persistent grudge and refusal to speak after insult *(ended v1)*
> - Comrade of — literary collaborators writing newspaper notes together (since v2)
> - Friend of — close friend (since v2)
> - Spouse of — husband and wife (since v4)

The same block at cutoff 2 has no "Spouse of" line, because that line's evidence is in book 4.
This is the property the design exists for: the history of a relationship is kept as intervals
with start and end books, and a cutoff simply hides the intervals that have not started yet.

Anne's page lists this many related characters, each as its own block linked to that character's
page and to the pair's page:

| System | Cutoff 1 | Cutoff 2 | Cutoff 3 | Cutoff 4 | Cutoff 5 |
|---|---|---|---|---|---|
| NarrativeWiki | 18 | 26 | 31 | 39 | 42 |
| Long context | 10 | 10 | 13 | 12 | 15 |
| Prefix retrieval | 8 | 5 | 9 | 10 | 10 |
| LightRAG | 8 | 8 | 8 | 5 | 5 |

Structured fields keep their history in the same way. Gilbert Blythe's overview at cutoff 2 lists
him as a teacher; at cutoff 4 it reads "country doctor (since v4)" with "previously: teacher
(v1–v2)" kept beneath it, and a family line naming Anne as his spouse appears only from cutoff 4.

## 5. Three further points in its favour

### 5.1 The stored facts are sound; the loss is in how they are printed

Graph + retrieval reads NarrativeWiki's graph and lets the model write the page. It has the
highest precision (0.965) and the highest citation sufficiency (0.915) of any system on the
original text. So the facts and evidence NarrativeWiki stores are good enough to support the
most precise, best-cited pages in the comparison.

NarrativeWiki's own lower precision is concentrated in one place. Relationship pages hold 46% of
its statements. Of 102 sampled statements on those pages, 99 (0.971) are true as statements, but
only 72 (0.706) are supported where they are printed, because lines from a scene that names both
characters are placed on the pair's page even when the two do not share that episode. On the
character pages of the evaluated cast its precision is 0.886 (31 of 35 sampled statements),
against 0.930 for long context. This is a placement problem with a known cause, not unreliable
extraction.

### 5.2 Cost for the amount published

One NarrativeWiki build serves all five cutoffs. Long context must resend the whole prefix for
every page at every cutoff, so its input grows with each book (2.2, 7.0, 10.8, 19.6 and 29.7
million tokens at cutoffs 1 to 5).

| System | Input tokens, all five cutoffs (millions) | Pages delivered, all five cutoffs | Input tokens per page | Input tokens per distinct statement |
|---|---|---|---|---|
| NarrativeWiki | 33.13 | 1,350 | 24,541 | 951 |
| Long context | 69.23 | 136 | 509,044 | 7,604 |
| Prefix retrieval | 3.42 | 136 | 25,147 | 398 |
| LightRAG | 5.08 | 136 | 37,353 | 724 |

The last two columns are arithmetic on reported totals, not a separate run. Per distinct statement
NarrativeWiki costs one eighth of long context. Prefix retrieval is still the cheapest: its
9.7-fold advantage in total tokens becomes 2.4-fold per statement and about equal per page.

### 5.3 Facts only NarrativeWiki conveys

Gold facts that NarrativeWiki conveys while long context and prefix retrieval **both** miss them
(the cutoffs at which this holds are in brackets).

Original text, 7 facts (15 fact checks):

- Anne has two braids of very thick red hair and eyes that look green in some lights. [4]
- Anne is given old letters that belonged to her mother. [3, 4, 5]
- Anne longs for a dress with puffed sleeves. [1, 3, 4]
- Anne writes a story whose heroine is named Averil Lester. [3, 4, 5]
- Gilbert rows up to Anne in a boat when her flat sinks. [2, 4, 5]
- Rachel Lynde says Anne's hair is as red as carrots. [3]
- Walter hates Dan Reese. [5]

Unfamiliar text, 13 facts (20 fact checks): the five facts above about the braids, the letters, the
puffed sleeves, the story heroine and the boat, the fact about Walter, and also: Anne dyes her
hair [3]; Anne realises she loves Gilbert when he falls ill with typhoid [3]; Carl gets a sore
throat after getting wet in the marsh [5]; Anne accidentally gets Diana drunk on currant wine [5];
Gilbert gives up the Avonlea school so that Anne can teach there [4]; Gilbert is said to be going
about with Christine Stuart [4]; Gilbert proposes to Anne and she refuses him [5].

Most are early-book details about the main characters that a later, budget-limited page no longer
has room for. The reverse list (facts both other systems convey and NarrativeWiki misses) has 13
facts on the original text and 10 on the unfamiliar text; see section 6.

## 6. What these results do not show

1. **The comparison pages had a length budget.** Long context, prefix retrieval, LightRAG and
   Graph + retrieval write each page in one call under sentence limits, and the retrieval systems
   under a 20,000-token input limit. Sections 4.1 and 4.2 show NarrativeWiki beating
   *budget-limited single-call pages*. A comparison system allowed a longer page, or several calls
   per character, was not tested and might close the gap.
2. **The split in 4.1 was made after the results existed.** It uses three characters from one
   build per system. No significance test was run. On the original text the lead rests on Anne
   Shirley alone.
3. **NarrativeWiki is behind on the other 40 characters.** Much of that deficit sits in a few
   characters about whom it conveys no gold fact at any cutoff on the original text: Phillips (0 of
   10 fact checks), Charlotta (0 of 4), Reverend Jo (0 of 3) and Roy Gardner (0 of 3). The cause was
   not investigated. Facts it misses that both long context and prefix retrieval convey include
   "Gilbert is going to teach at the White Sands school" and "Paul Irving comes from the States to
   live with his grandmother".
4. **It is the weakest of the five on precision and citation sufficiency** (0.789 and 0.512 on the
   original text), for the reason given in 5.1.
5. **It discloses later facts and the text-bounded systems do not.** One of 220 checks on the
   original text (a relationship summary that inverted who was whose bridesmaid) and four of 220 on
   the unfamiliar text (a neighbour's prediction of a marriage stored and printed as a marriage).
   Long context, prefix retrieval and LightRAG have none, by construction: they never see later
   books.
6. **Its entities are shaped by later books.** It builds its character list from all five books,
   so which names are grouped into one character at cutoff 1 can depend on text the reader has not
   reached (this affects 23 of 59 character pages at cutoff 1 and 17 of 191 at cutoff 4).
7. **The worked example has visible defects.** In the same block quoted in 4.5 the generated
   paragraph prints internal reference keys such as "[R7, R10]"; the line "Romantically involved
   with" is open from book 1 on weak evidence; and Anne's overview at cutoff 4 still shows the age
   "20 (since v3)" and the role "teacher (since v4)", where long context writes "Housewife, former
   schoolteacher, and writer".
8. **The value of structure to a reader is not measured.** Dated intervals, links and relationship
   pages are described here, not scored. No reader study was run.
9. **The labels are AI labels accepted by the authors** (section 2.6). The count in 4.2 compares
   labels across cutoffs, so a labelling inconsistency between two cutoffs would also be counted as
   a lost fact.
10. **One series, one build per system.** A series too long for a context window, where the
    accumulation advantage should matter most and long context cannot run at all, was not tested.

## 7. Sources and how to reproduce

| What | Where |
|---|---|
| Sections 4.1, 4.2, 4.5 (page counts, word counts, relationship blocks), 5.3 | `.venv/Scripts/python.exe -X utf8 scripts/eval/recall_by_centrality.py`, which reads `docs/eval/recall_hand/*.json` and `dist/anne@{v2,b1,b2,b3}/wiki/` and writes `docs/eval/recall_by_centrality.json`. No model call. |
| Section 3 and the averages in 4.3, 4.4, 5.1, 5.2 | `docs/paper/results.tex` (keys `M1-`, `M3-`, `M8-`, `M4-`, `ND-`, `TOK-`, `STAT-M1-`, `M3K-`, `ID-` for `anne` and `annedecon`). |
| Head-to-head counts in 4.3 and 4.4 | `docs/MEASUREMENTS.md`, rows dated 2026-10-09, "Common-assessment recall pairing". |
| Every number first reported in this document | `docs/MEASUREMENTS.md`, section dated 2026-10-11. |
| The worked example in 4.5 | `dist/anne@v2/wiki/v04/character/anne-shirley.md` (NarrativeWiki) and `dist/anne@b1/wiki/v04/character/anne-shirley.md` (long context); Gilbert's overview in `docs/paper/appendix/m-qualitative.tex`. |
| Comparison-system settings and the shared template | `docs/paper/appendix/d-baselines.tex`. |

Folder names: `anne@v2` is the reported NarrativeWiki build, `anne@b1` long context, `anne@b2`
prefix retrieval, `anne@b3` LightRAG, `anne@b4-v2` Graph + retrieval, `anne@x1` closed book,
`anne@x2` full text + instruction; the `anne-decon@…` folders are the same systems on the
unfamiliar text.
