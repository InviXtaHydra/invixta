"""Recognise a product question in a customer's message, so the agent can search the catalogue before
the model answers (small local models often skip the tool and then say "we don't have that").

    "Hebben jullie shirts tussen 40-50 euro?"     → {"min_price": 40, "max_price": 50}
    "Any retro shirts under €60?"                  → {"category": "retro", "max_price": 60}
    "Is the Polder United away shirt in M?"        → {"query": "Polder United", "category": "away", "size": "M"}

Plain rules, no model: they are cheap, predictable and unit tested.
"""

import re
from typing import Any

_NUMBER = r"€?\s*(\d{1,4})(?:[.,]\d{1,2})?\s*(?:€|eur(?:o|os)?)?"
_ARTICLE = r"\s*(?:de|the|een|a)?\s*"
_RANGE = re.compile(rf"(?:tussen|between|van|from)?{_ARTICLE}{_NUMBER}\s*(?:-|\u2013|en|and|tot|to){_ARTICLE}{_NUMBER}", re.IGNORECASE)
_MAX_WORDS = r"onder|under|below|less than|minder dan|max(?:imaal|imum)?|tot|up to|cheaper than|goedkoper dan"
_MIN_WORDS = r"boven|above|over|more than|meer dan|vanaf|at least|minimaal|duurder dan"
_MAX = re.compile(rf"(?:{_MAX_WORDS}){_ARTICLE}{_NUMBER}", re.IGNORECASE)
_MIN = re.compile(rf"(?:{_MIN_WORDS}){_ARTICLE}{_NUMBER}", re.IGNORECASE)

# (category, words that point to it) — Dutch and English
_CATEGORIES = [
    ("retro", ("retro", "vintage", "classic shirt", "klassiek")),
    ("training", ("training", "trainingstop", "warm-up")),
    ("kids", ("kids", "kinder", "kind ", "kinderen", "junior", "jongen", "meisje")),
    ("away", ("away", "uitshirt", "uit shirt", "uittenue")),
    ("home", ("home shirt", "thuisshirt", "thuis shirt", "thuistenue")),
    ("accessory", ("accessoire", "accessories", "sjaal", "scarf", "bal ", "ball", "sokken", "socks", "handschoen", "gloves",
                   "scheenbeschermer", "shin guard", "tas ", "bag")),
]  # fmt: skip
_PRODUCT_WORDS = ("shirt", "tenue", "kit", "jersey", "product", "artikel", "aanbieding", "sale", "korting", "discount", "deal",
                  "voorraad", "in stock", "op voorraad", "kopen", "buy", "prijs", "price", "kost", "cost", "goedkoop", "cheap")  # fmt: skip
_SALE_WORDS = ("aanbieding", "sale", "korting", "discount", "deal", "afgeprijsd", "reduced")
# Topics the help articles cover: printing, delivery, returns, payment, size advice, care, cancelling.
_POLICY = re.compile(
    r"bedruk|print|naam|nummer|\bname\b|\bnumber\b|verzend|verzonden|lever|bezorg|ship|deliver|track|retour|terugstur|"
    r"ruil|return|exchange|refund|terugbetal|geld terug|betal|\bpay|ideal|bancontact|paypal|factuur|invoice|btw|vat\b|"
    r"welke maat|which size|what size|maattabel|size guide|pasvorm|\bfit|valt (groot|klein|ruim|krap)|wassen|\bwash|"
    r"onderhoud|\bcare\b|annuler|cancel|garantie|warranty|beschadig|damaged|kapot|verkeerd|wrong",
    re.IGNORECASE,
)


def _price_filters(text: str) -> dict[str, int]:
    if match := _RANGE.search(text):
        low, high = sorted((int(match.group(1)), int(match.group(2))))
        if high > 0 and ("€" in match.group(0) or "eur" in match.group(0).lower() or re.search(r"tussen|between", match.group(0), re.I)):
            return {"min_price": low, "max_price": high}
    filters: dict[str, int] = {}
    if match := _MAX.search(text):
        filters["max_price"] = int(match.group(1))
    if match := _MIN.search(text):
        filters["min_price"] = int(match.group(1))
    return filters


def asks_about_policy(message: str) -> bool:
    """True when the message also touches a topic of the help articles (then the agent searches them too)."""
    return bool(_POLICY.search(message))


def product_search_from_message(message: str, clubs: list[str], size: str | None) -> dict[str, Any] | None:
    """Arguments for search_products when the message asks about products, otherwise None."""
    text = f" {message.lower()} "
    search: dict[str, Any] = {}
    if clubs:
        search["query"] = clubs[0]
    for category, words in _CATEGORIES:
        if any(w in text for w in words):
            search["category"] = category
            break
    search.update(_price_filters(message))
    if any(w in text for w in _SALE_WORDS):
        search["on_sale"] = True
    if size:
        search["size"] = size
    asks_about_products = (
        clubs or "category" in search or "min_price" in search or "max_price" in search or any(w in text for w in _PRODUCT_WORDS)
    )
    if not asks_about_products or (set(search) <= {"size"} and not any(w in text for w in _PRODUCT_WORDS)):
        return None
    return search
