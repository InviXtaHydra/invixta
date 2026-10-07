"""Unit tests for cleaning and chunking (pure functions, no database)."""

from itertools import pairwise

from app.rag.text_processing import Section, chunk_page, chunk_sections, clean_lines, is_heading, split_sections


def test_clean_lines_fixes_hyphenation_whitespace_and_page_numbers() -> None:
    raw = "Delivery takes 1 to 3 work-\ndays.\r\n\n  Page 2 of 5  \n3\nShipping   is\u00a0free."
    assert clean_lines(raw) == ["Delivery takes 1 to 3 workdays.", "", "Shipping is free."]


def test_is_heading() -> None:
    assert is_heading("Return window", previous=None)
    assert is_heading("When will I receive my refund?", previous="Some text that ends here.")
    assert not is_heading("returns are free", previous=None)  # starts lowercase
    assert not is_heading("This line ends a sentence.", previous=None)
    assert not is_heading("1. Open a support ticket", previous=None)  # list item
    assert not is_heading("continues the previous line", previous="A sentence that wraps onto")


def test_split_sections_groups_paragraphs_under_headings() -> None:
    lines = clean_lines("Return window\nYou can return products within 30 days.\nThey must be unused.\n\nRefunds\nWe refund in 5 days.")
    sections = split_sections(lines)
    assert [s.heading for s in sections] == ["Return window", "Refunds"]
    assert sections[0].paragraphs == ["You can return products within 30 days. They must be unused."]


def test_each_chunk_carries_its_section_heading() -> None:
    chunks = chunk_page("Return window\nYou can return products within 30 days.\n\nRefunds\nWe refund in 5 working days.")
    assert chunks == ["Return window: You can return products within 30 days.", "Refunds: We refund in 5 working days."]


def test_question_headings_are_not_followed_by_a_colon() -> None:
    chunks = chunk_page("When will I receive my refund?\nWithin 5 working days.")
    assert chunks == ["When will I receive my refund? Within 5 working days."]


def test_a_title_without_text_is_carried_to_the_next_section() -> None:
    chunks = chunk_sections([Section("Warranty", []), Section("Coverage", ["Two years from delivery."])])
    assert chunks == ["Warranty — Coverage: Two years from delivery."]


def test_long_sections_are_split_with_one_sentence_overlap() -> None:
    sentences = [f"Sentence number {i} explains one detail of the policy." for i in range(30)]
    chunks = chunk_sections([Section("Policy", [" ".join(sentences)])], max_chars=300)
    assert len(chunks) > 1
    assert all(len(c) <= 300 for c in chunks)
    assert all(c.startswith("Policy: ") for c in chunks)
    for previous, current in pairwise(chunks):
        last_sentence = previous.removeprefix("Policy: ").split(". ")[-1]
        assert current.removeprefix("Policy: ").startswith(last_sentence.rstrip("."))
    joined = " ".join(chunks)
    assert all(s in joined for s in sentences)  # nothing is lost


def test_a_single_very_long_sentence_is_split_on_words() -> None:
    chunks = chunk_sections([Section(None, ["word " * 400])], max_chars=200)
    assert len(chunks) > 1
    assert all(len(c) <= 200 for c in chunks)


def test_empty_page_gives_no_chunks() -> None:
    assert chunk_page("   \n\n 4 \n") == []
