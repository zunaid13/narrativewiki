"""Download only the public papers used by review 0007; never sends repository data.

Files land in docs/papers/pdf/ under the `{Paper Title}.pdf` convention (docs/papers/PAPERS.md);
the manifest is docs/papers/reviews/0007-downloads.json. Existing files are preserved.
"""
import hashlib
import json
from pathlib import Path
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
PDF_DIR = ROOT / "docs" / "papers" / "pdf"
MANIFEST = ROOT / "docs" / "papers" / "reviews" / "0007-downloads.json"
PAPERS = [
    ("CHIRON", "https://aclanthology.org/2024.findings-emnlp.499.pdf",
     "CHIRON - Rich Character Representations in Long-Form Narratives.pdf"),
    ("STAGE-v9", "https://arxiv.org/pdf/2601.08510v9",
     "STAGE - A Full-Screenplay Benchmark for Reasoning over Evolving Stories.pdf"),
    ("EvolvTrip-v1", "https://arxiv.org/pdf/2506.13641v1",
     "EvolvTrip - Enhancing Literary Character Understanding with Temporal Theory-of-Mind Graphs.pdf"),
    ("E2RAG-v1", "https://arxiv.org/pdf/2506.05939v1",
     "Respecting Temporal-Causal Consistency - Entity-Event Knowledge Graphs for "
     "Retrieval-Augmented Generation.pdf"),
    ("MiniCheck", "https://aclanthology.org/2024.emnlp-main.499.pdf",
     "MiniCheck - Efficient Fact-Checking of LLMs on Grounding Documents (EMNLP 2024).pdf"),
]

if __name__ == "__main__":
    PDF_DIR.mkdir(parents=True, exist_ok=True)
    records = []
    for name, url, filename in PAPERS:
        path = PDF_DIR / filename
        try:
            if path.exists():
                data = path.read_bytes()
            else:
                with urllib.request.urlopen(url, timeout=45) as response:
                    data = response.read()
            if not data.startswith(b"%PDF"):
                raise ValueError("Response is not a PDF")
            path.write_bytes(data)
            records.append({"id": name, "url": url, "path": f"pdf/{filename}",
                            "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(),
                            "status": "downloaded"})
        except Exception as exc:
            records.append({"id": name, "url": url, "status": "failed", "error": str(exc)})
    MANIFEST.write_text(json.dumps(records, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(records, indent=2))
    raise SystemExit(any(r["status"] != "downloaded" for r in records))
