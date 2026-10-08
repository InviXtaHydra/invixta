"""Recognising product questions (Dutch and English) for the agent's catalogue search."""

import pytest

from app.agents.product_intent import product_search_from_message
from app.agents.support_agent import mentioned_size


@pytest.mark.parametrize(
    ("message", "clubs", "expected"),
    [
        ("Hebben jullie shirts tussen 40-50 euro?", [], {"min_price": 40, "max_price": 50}),
        ("Any shirts between €40 and €50?", [], {"min_price": 40, "max_price": 50}),
        ("Welke retro shirts hebben jullie onder de €60?", [], {"category": "retro", "max_price": 60}),
        ("Do you have kids kits under 45 euro?", [], {"category": "kids", "max_price": 45}),
        ("Wat zijn jullie aanbiedingen?", [], {"on_sale": True}),
        ("Is the Polder United away shirt in stock?", ["Polder United"], {"query": "Polder United", "category": "away"}),
        ("Hebben jullie een sjaal van Haven Rovers?", ["Haven Rovers"], {"query": "Haven Rovers", "category": "accessory"}),
        ("Welke shirts kosten meer dan 60 euro?", [], {"min_price": 60}),
        ("What do you sell?", [], None),
        ("Where is my order?", [], None),
        ("How many days do I have to return something?", [], None),
    ],
)
def test_product_questions(message: str, clubs: list[str], expected: dict[str, object] | None) -> None:
    assert product_search_from_message(message, clubs, mentioned_size(message)) == expected


def test_size_is_added_to_a_product_question() -> None:
    message = "Hebben jullie het Polder shirt in maat M?"
    assert product_search_from_message(message, ["Polder United"], mentioned_size(message)) == {"query": "Polder United", "size": "M"}
