from app.llm.mock_provider import MockLLMProvider, _categorize, _is_mandatory
from app.services.pdf_extract import PageExtract


def test_certification_language_wins_over_incidental_standard_mention():
    # Mentions "NIJ" (a ballistic standard) but is fundamentally a
    # certification/compliance ask, not a ballistic spec.
    category, _ = _categorize("Bidder shall submit valid NIJ 0101.06 certification for the offered helmet model.")
    assert category == "certification"


def test_pure_ballistic_spec_is_categorized_as_ballistic():
    category, _ = _categorize("The helmet shall provide ballistic protection at NIJ Level IIIA standalone.")
    assert category == "ballistic"


def test_uncategorized_clause_falls_back_to_technical_not_dropped():
    category, confidence = _categorize("The system shall integrate with an existing radar and sensor suite.")
    assert category == "technical"
    assert confidence > 0


def test_mandatory_language_detection():
    assert _is_mandatory("The helmet shall provide ballistic protection.") is True
    assert _is_mandatory("The helmet should ideally be lightweight.") is False
    assert _is_mandatory("Bidder must submit a valid certificate.") is True


def test_extract_requirements_only_picks_up_bulleted_clauses():
    provider = MockLLMProvider()
    pages = [
        PageExtract(
            page_number=1,
            text=(
                "TENDER FOR SUPPLY OF COMBAT HELMETS\n"
                "This is narrative cover text that is not a requirement at all, just filler.\n"
                "- The helmet shall provide ballistic protection at NIJ Level IIIA standalone.\n"
                "- Bidder shall submit valid NIJ 0101.06 certification for the offered helmet model.\n"
            ),
            method="native",
            confidence=0.97,
            section="General",
        )
    ]
    requirements = provider.extract_requirements(pages)
    descriptions = [r["description"] for r in requirements]
    assert len(requirements) == 2
    assert any("ballistic protection" in d for d in descriptions)
    assert not any("narrative cover text" in d for d in descriptions)
    categories = {r["category"] for r in requirements}
    assert "certification" in categories
    assert "ballistic" in categories


def test_extract_tender_metadata_reads_cover_sheet_fields():
    provider = MockLLMProvider()
    pages = [
        PageExtract(
            page_number=1,
            text=(
                "Tender Number: IA/ORD/2026/HEL-014\n"
                "Issuing Organization: Indian Army - Directorate of Ordnance\n"
                "Submission Deadline: 10 Oct 2026\n"
            ),
            method="native",
            confidence=0.97,
            section="General",
        )
    ]
    meta = provider.extract_tender_metadata(pages)
    assert meta["tender_number"] == "IA/ORD/2026/HEL-014"
    assert "Indian Army" in meta["issuing_organization"]
    assert meta["submission_deadline"] == "10 Oct 2026"
