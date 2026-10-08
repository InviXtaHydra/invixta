"""The fictional catalogue of Invixta: clubs, leagues and products. Every club, league and crest is
made up; any resemblance to real clubs is accidental. Used by seed_database.py."""

from decimal import Decimal

from app.models import ProductCategory

LEAGUES = ["Lage Landen League", "Noordzee Divisie"]

# (slug, name, short name, league index, city, founded, primary colour, secondary colour, pattern)
TEAMS = [
    ("fc-dijkstad", "FC Dijkstad", "FCD", 0, "Dijkstad", 1899, "#C8102E", "#FFFFFF", "stripes"),
    ("polder-united", "Polder United", "PLU", 0, "Polderveen", 1921, "#F36C21", "#111111", "hoops"),
    ("sv-molenberg", "SV Molenberg", "SVM", 0, "Molenberg", 1908, "#1D4E9E", "#FFFFFF", "halves"),
    ("haven-rovers", "Haven Rovers", "HAR", 0, "Havenmond", 1934, "#13294B", "#E8B92F", "plain"),
    ("duinwijk-athletic", "Duinwijk Athletic", "DWA", 0, "Duinwijk", 1912, "#0B7A3E", "#FFFFFF", "hoops"),
    ("ardenne-fc", "Ardenne FC", "ARD", 0, "Bosheide", 1926, "#1F4D2B", "#F2C230", "sash"),
    ("sporting-scheldepoort", "Sporting Scheldepoort", "SSP", 1, "Scheldepoort", 1903, "#5B2C83", "#FFFFFF", "plain"),
    ("real-tulpendam", "Real Tulpendam", "RTD", 1, "Tulpendam", 1919, "#FFFFFF", "#D2232A", "plain"),
    ("kanaal-city", "Kanaal City", "KNC", 1, "Kanaalstad", 1947, "#6CABDD", "#1C2C5B", "plain"),
    ("vlasdorp-1908", "Vlasdorp 1908", "VLD", 1, "Vlasdorp", 1908, "#111111", "#FFFFFF", "stripes"),
    ("atletico-heidebeek", "Atlético Heidebeek", "ATH", 1, "Heidebeek", 1931, "#C8102E", "#1B3F94", "stripes"),
    ("maasoever-sc", "Maasoever SC", "MSC", 1, "Maasoever", 1915, "#FFD100", "#111111", "stripes"),
]

ADULT_SIZES = ["S", "M", "L", "XL", "XXL"]
KIDS_SIZES = ["116", "128", "140", "152", "164"]
ONE_SIZE = ["One size"]

# Prices
SHIRT = Decimal("69.95")
SHIRT_SALE = Decimal("49.95")
RETRO = Decimal("59.95")
TRAINING = Decimal("39.95")
KIDS = Decimal("44.95")


def team_products(team_slug: str, name: str, city: str, founded: int, sale: bool) -> list[dict[str, object]]:
    """Home and away shirt of the 26/27 season, a training top and a kids' home kit for one club."""
    home_price, home_compare = (SHIRT_SALE, SHIRT) if sale else (SHIRT, None)
    return [
        {
            "slug": f"{team_slug}-home-26-27",
            "name": f"{name} Home Shirt 26/27",
            "category": ProductCategory.HOME,
            "season": "26/27",
            "price": home_price,
            "compare_at_price": home_compare,
            "personalizable": True,
            "sizes": ADULT_SIZES,
            "description": (
                f"The shirt {name} wears at home in the 26/27 season, in the club colours fans in {city} have worn since "
                f"{founded}. Lightweight recycled polyester with a breathable mesh back and an embroidered crest. "
                "Regular fit: take your usual size, or one size up for a looser fit."
            ),
        },
        {
            "slug": f"{team_slug}-away-26-27",
            "name": f"{name} Away Shirt 26/27",
            "category": ProductCategory.AWAY,
            "season": "26/27",
            "price": SHIRT,
            "compare_at_price": None,
            "personalizable": True,
            "sizes": ADULT_SIZES,
            "description": (
                f"{name}'s away shirt for the 26/27 season, with the colours reversed. Same fabric and fit as the home "
                "shirt: recycled polyester, mesh back, embroidered crest. Regular fit."
            ),
        },
        {
            "slug": f"{team_slug}-training-top",
            "name": f"{name} Training Top",
            "category": ProductCategory.TRAINING,
            "season": "26/27",
            "price": TRAINING,
            "compare_at_price": None,
            "personalizable": False,
            "sizes": ADULT_SIZES,
            "description": f"Quarter-zip training top as worn by the {name} squad during warm-ups. Soft brushed inside, slim fit.",
        },
        {
            "slug": f"{team_slug}-kids-home-kit",
            "name": f"{name} Kids Home Kit 26/27",
            "category": ProductCategory.KIDS,
            "season": "26/27",
            "price": KIDS,
            "compare_at_price": None,
            "personalizable": True,
            "sizes": KIDS_SIZES,
            "description": f"Shirt and shorts of the {name} home kit for young fans. Sizes by height in cm (116 = about 6 years).",
        },
    ]


# (team slug, year, story) — remakes of famous (fictional) shirts
RETRO_SHIRTS = [
    ("fc-dijkstad", "1988", "the season FC Dijkstad won the double with the famous stripes"),
    ("polder-united", "1995", "Polder United's first European campaign, with the wide orange hoops"),
    ("vlasdorp-1908", "1974", "Vlasdorp's centenary-era classic with a lace-up collar"),
    ("kanaal-city", "2002", "the sky-blue shirt of Kanaal City's cup final"),
]

# (slug, name, price, compare_at_price, sizes, description)
ACCESSORIES = [
    ("invixta-match-ball", "Invixta Pro Match Ball", Decimal("29.95"), None, ONE_SIZE,
     "Size 5 match ball with thermally bonded panels. Inflated on delivery."),
    ("invixta-training-ball", "Invixta Training Ball", Decimal("14.95"), Decimal("19.95"), ONE_SIZE,
     "Durable size 5 ball for training and the park."),
    ("invixta-grip-socks", "Invixta Grip Socks", Decimal("12.95"), None, ["S", "M", "L"],
     "Anti-slip grip socks (S = EU 36-39, M = 40-43, L = 44-47)."),
    ("invixta-shin-guards", "Invixta Shin Guards", Decimal("17.95"), None, ["S", "M", "L"],
     "Lightweight shin guards with a soft foam back."),
    ("invixta-goalkeeper-gloves", "Invixta Goalkeeper Gloves", Decimal("34.95"), None, ["7", "8", "9", "10"],
     "Latex palm with finger protection. Size = hand circumference in inches."),
    ("invixta-kit-bag", "Invixta Kit Bag", Decimal("24.95"), None, ONE_SIZE, "35 L sports bag with a separate shoe compartment."),
]  # fmt: skip
SCARF_PRICE = Decimal("19.95")
