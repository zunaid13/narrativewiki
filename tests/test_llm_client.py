def test_no_prompt_assumes_a_genre_or_names_a_series_character():
    """[32] req. 8: one pipeline for every series. Prompts said "translated Japanese light novel"
    and a per-series `prompt_vocabulary` reworded them; few-shot examples named Spice and Wolf's
    cast. Every prompt is now series-neutral, so no series needs a patch."""
    import pathlib
    import re

    src = pathlib.Path(__file__).resolve().parents[1] / "src" / "narrativewiki"
    code = "\n".join(
        line for f in src.rglob("*.py") for line in f.read_text(encoding="utf-8").splitlines()
        if not line.lstrip().startswith("#")
    )
    # Join backslash continuations and wrapped lines: verify.py's "a light \<newline>novel" hid.
    assert not re.search(r"light\s*\\?\s*novel|Japanese", code)
