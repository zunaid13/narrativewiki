"""[33] C17: cited one-line quotes (baseline pages) are cited assertions, never a pooled 'scene' unit."""
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "eval"))
_spec = importlib.util.spec_from_file_location("assertion_inventory", ROOT / "scripts/eval/assertion_inventory.py")
inv = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(inv)


def test_cited_quote_lines_do_not_pool_into_a_scene_unit():
    md = ("# Dora\n\n## Quotes\n\n> I'm frightened.  <sub>[v2 c21 P3](../source/v02-c21.md#nw-v02-c21-p0003)</sub>\n\n"
          "> Yes, I was a little scared.  <sub>[v2 c24 P30](../source/v02-c24.md#nw-v02-c24-p0030)</sub>\n\n"
          "## Shared scenes\n\n> Davy and Dora come to Green Gables.\n>\n> — v2 · VIII Marilla Adopts Twins\n")
    rows = inv.units(md, "character/dora.md", "character")
    assert [(r["surface"], r["value"]) for r in rows] == [("scene", "Davy and Dora come to Green Gables.")]
