"""The assertion inventory must find every uncited surface a reader sees, and leave cited lines
to `assertion_precision.assertions()` so the two populations never double-count."""
from scripts.eval.assertion_inventory import units

CHARACTER = """---
entity_id: marheit
---

# Marheit

[Milone Company](../codex/factions.md#milone-company)

## Overview

- **Gender:** male  <sub>[v1 ch.4 P409](../source/v01-c04.md#nw-v01-c04-p0409)</sub>
- **Status:** alive  _(assumed)_

## Personality

Marheit is pragmatic. He protects the [Milone Company](../codex/factions.md#milone-company).

_Sources: [v1 ch.5 P1](../source/v01-c05.md#nw-v01-c05-p0001)_

## Goals

_Not yet known._

## Quotes

> "The profit before us is almost unimaginable."
>
> — Marheit — [v1 ch.4 P455](../source/v01-c04.md#nw-v01-c04-p0455)

## Related

- [Holo](../character/holo.md) — 7 shared scenes

## Appearances

Volume 1
"""

CODEX = """# Factions & Organizations

## Medio Company {#medio-company}

The Medio Company hoards trenni silver.

**Members:** [Yarei](../character/yarei.md), [Zheren](../character/zheren.md)

> [Lawrence](../character/kraft-lawrence.md) learns who backs the Medio Company.
>
> — v1 · Chapter 5
"""

TIMELINE = """# Volume 1 timeline

## AFTERWORD

**[Holo](../character/holo.md), Marheit** — Holo finds the apples.
"""


def _by(rows):
    return {(r["surface"], r["label"], r["value"]): r for r in rows}


def test_character_page_surfaces():
    rows = units(CHARACTER, "character/marheit.md", "character")
    got = _by(rows)
    assert ("uncited", "Categories", "Milone Company") in got
    assert ("uncited", "Status", "alive  (assumed)") in got
    prose = got[("prose", "Personality", "Marheit is pragmatic. He protects the Milone Company.")]
    assert prose["evidence"] == ["v01:c05:p0001"] and prose["unit"] == prose["value"]
    quote = got[("quote", "Quote", 'Marheit said: "The profit before us is almost unimaginable."')]
    assert quote["evidence"] == ["v01:c04:p0455"]
    assert ("related", "Related", "Holo — 7 shared scenes") in got
    assert ("uncited", "Appearances", "Volume 1") in got
    # cited "Gender" line and the empty-section placeholder are not uncited units
    assert not any("male" == r["value"] or "known" in r["value"] for r in rows)
    assert len(rows) == 6


def test_codex_entries_belong_to_their_section():
    rows = units(CODEX, "codex/factions.md", "codex")
    assert {r["entity"] for r in rows} == {"Medio Company"}
    assert [r["value"] for r in rows if r["label"] == "Members"] == ["Yarei", "Zheren"]
    scene = next(r for r in rows if r["surface"] == "scene")
    assert scene["chapter"] == "v1 · Chapter 5" and scene["evidence"] == []
    assert sum(r["surface"] == "prose" for r in rows) == 1


def test_timeline_scene_keeps_its_own_heading():
    [row] = units(TIMELINE, "timeline/v01.md", "timeline")
    assert (row["surface"], row["entity"], row["chapter"]) == ("scene", "Holo, Marheit", "AFTERWORD")
