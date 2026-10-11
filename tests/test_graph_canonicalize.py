

def test_a_value_without_a_vector_stays_its_own_cluster():
    """[30] LLMClient.embed returns None for a text the model could not encode."""
    from narrativewiki.graph.canonicalize import cluster_values
    entries = [{"claim_id": str(i), "value": v, "confidence": 1.0, "first_vol": 1}
               for i, v in enumerate(["to be a merchant", "or a bard", "to become a merchant"])]
    vectors = {"to be a merchant": [1.0, 0.0], "or a bard": None, "to become a merchant": [1.0, 0.0]}
    clusters = cluster_values(entries, lambda texts: [vectors[t] for t in texts], 0.86)
    assert sorted(len(c.members) for c in clusters) == [1, 2]
