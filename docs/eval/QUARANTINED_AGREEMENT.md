# Review and agreement artifact quarantine — 2026-10-12

Status: relocation completed; completion and integrity checks are recorded in
`quarantine_agreement_20261012.json`.

The maintainer requested moving every human-review and LLM-annotation artifact
used for kappa/alpha measurements into the repository's sibling directory
`G:/UIU classes/Falsified`. They explicitly selected artifacts and agreement
reports, retaining manuscript sources and historical documents that cite them.

The inventory covers the data and supporting records from `agreement/`,
`human_check/`, `human/` and `agent_annotation/`; the standalone annotation
provenance record; Claude's pair-placement labels used for the earlier AI-pair
kappa; agreement-stage model-call records and cached responses; annotation and
release ZIPs containing copies; and rendered review/agreement previews. The
previous external Gemini/Nemotron archive is consolidated into the same directory.
Every file keeps its bytes and original relative path; its size and SHA256 are
recorded before moving. Scripts remain in their existing repository locations.

Only agreement-stage cache entries are relocated. No unrelated pipeline cache,
corpus, gold inventory, manuscript or historical measurement record is removed.
The requested directory name is not an independent finding about authorship.

The retained historical coefficients and manuscript references point to
quarantined evidence. They must not be presented as newly validated human
reliability. Reviewers' authorship and blinding were already unverified or
conflicted in the original provenance records, which are preserved externally.
No new agreement measurement or label correction is made by this relocation.

The packet builders, annotation runners, agreement scorers, reviewer reproduction
script, data-dependent agreement tests, and pair-based scoring/release workflows
require the external artifacts after this move. Their previous default input
paths are deliberately empty. Do not regenerate missing annotations or start
provider calls to restore them. No manuscript rebuild or release is performed.

Verify the move without modifying the archive:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File ./scripts/eval/quarantine_agreement_artifacts.ps1 -VerifyOnly
```

The same script without `-VerifyOnly` executes or resumes the exact inventoried
move, refusing changed sources, path escapes and destination overwrites. It
requires filesystem permission to write the explicitly requested sibling directory.

`python scripts/eval/verify_agreement_quarantine.py` additionally checks for
exact artifact duplicates and ZIPs containing annotation copies throughout the
first-party working tree. The final scan used elevated read access to inspect
otherwise inaccessible test directories. It reported no remaining duplicates,
annotation packages, integrity failures or unreadable paths. Git history,
dependencies, EPUB corpora and Python/pytest caches are excluded explicitly.
