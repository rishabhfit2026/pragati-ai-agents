from app.agents.capability_matching import match_requirement, tokenize, overlap_score


def test_tokenize_strips_stopwords_and_short_tokens():
    tokens = tokenize("The helmet shall provide ballistic protection at NIJ Level IIIA standalone.")
    assert "shall" not in tokens
    assert "at" not in tokens
    assert "helmet" in tokens
    assert "nij" in tokens


def test_overlap_score_is_containment_of_requirement_vocabulary():
    req = {"helmet", "nij", "level", "iiia"}
    candidate = {"helmet", "nij", "level", "iiia", "shield", "vest", "plate", "armour"}
    score, hits = overlap_score(req, candidate)
    assert hits == 4
    assert score == 1.0  # full containment of the (smaller) requirement vocabulary


def test_helmet_requirement_matches_helmet_product():
    result = match_requirement(
        "The helmet shall provide ballistic protection at NIJ Level IIIA standalone.", "ballistic"
    )
    assert result.status in ("MATCH", "PARTIAL_MATCH")
    assert result.kb_reference_id is not None


def test_drone_requirement_is_a_gap():
    result = match_requirement(
        "The system shall detect and neutralize hostile drones using an integrated jamming array.", "technical"
    )
    assert result.status == "GAP"
    assert result.kb_reference_id is None


def test_unknown_requirement_never_silently_becomes_match():
    # A vague requirement with no strong evidence must never resolve to MATCH.
    result = match_requirement("The widget shall be blue and shiny.", "technical")
    assert result.status in ("UNKNOWN", "GAP", "PARTIAL_MATCH")
    assert result.status != "MATCH"
