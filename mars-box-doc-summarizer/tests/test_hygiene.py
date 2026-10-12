from box_doc_summarizer.hygiene import hygiene_text


def test_numeric_ranges_kept():
    assert hygiene_text("costs $60–$120 and 75–85°F") == "costs $60-$120 and 75-85°F"
    assert hygiene_text("75–85 degrees") == "75-85 degrees"


def test_prose_dash_replaced():
    assert hygiene_text("Maui — great") == "Maui, great"
