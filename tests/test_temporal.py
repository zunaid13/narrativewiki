

def test_same_relation_with_a_new_qualifier_does_not_end():
    """[32] Effa SPOUSE_OF Gunther: "husband" (v1) then "married" (v2) is one marriage."""
    from narrativewiki.graph import temporal as T
    rows = T.assign_relation_supersession("effa", "gunther", [
        {"predicate": "SPOUSE_OF", "qualifier": "husband", "first_vol": 1, "claim_ids": ["a"]},
        {"predicate": "SPOUSE_OF", "qualifier": "married", "first_vol": 2, "claim_ids": ["b"]},
        {"predicate": "SIBLING_OF", "qualifier": None, "first_vol": 4, "claim_ids": ["c"]},
    ])
    assert [(r["predicate"], r["vol_start"], r["vol_end"]) for r in rows] == [("SPOUSE_OF", 1, 3), ("SIBLING_OF", 4, None)]
    assert rows[0]["claim_ids"] == ["a", "b"] and rows[0]["qualifier"] == "husband"
