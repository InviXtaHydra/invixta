"""Generate the Invixta knowledge-base PDFs in sample_documents/.

    docker compose run --rm -v ./sample_documents:/app/sample_documents backend python scripts/generate_sample_documents.py

The policies match what the shop really does (backend/app/core/config.py, app/services/pricing.py,
the fulfillment simulator and the checkout), so the AI agent's answers line up with the orders in the
database. The text lives here, readable in Git; the PDFs are generated from it.
"""

from pathlib import Path

from fpdf import FPDF

OUT = Path(__file__).resolve().parent.parent / "sample_documents"

DOCUMENTS: dict[str, list[tuple[str, list[str]]]] = {
    "Returns and Exchanges.pdf": [
        (
            "Returns and Exchanges",
            [
                "This policy explains how to return or exchange something you bought at Invixta and how refunds work. It applies "
                "to all orders delivered in the Netherlands, Belgium and the rest of the European Union.",
            ],
        ),
        (
            "Return window",
            [
                "You can return unprinted items within 30 days after delivery, without giving a reason. The 30 days start on the "
                "day the parcel is delivered, as shown in the carrier's tracking.",
                "Items must be unworn and unwashed, with the tags still attached. Shirts that have been worn or washed can be "
                "refused or refunded partially.",
            ],
        ),
        (
            "Printed shirts",
            [
                "Shirts with a name or number printed on them are made for you, so they can't be returned or exchanged, unless "
                "they arrive damaged or the print is wrong. Check the name, number and size carefully before you order.",
            ],
        ),
        (
            "Exchanging a size",
            [
                "Is an unprinted shirt too small or too big? Open a support ticket within 30 days with your order number and the "
                "size you need. We send the new size as soon as we receive the old one, and the exchange is free in the "
                "Netherlands and Belgium. Exchanges depend on stock: if your size is sold out, we refund you instead.",
            ],
        ),
        (
            "How to return an item",
            [
                "1. Open a support ticket or ask the assistant, and mention your order number.",
                "2. You receive a free return label by email within one working day. Returns within the Netherlands go with PostNL, "
                "returns within Belgium and Luxembourg with bpost. Customers in other EU countries pay the return shipping themselves.",
                "3. Pack the item and hand the parcel in at a drop-off point within 14 days of receiving the label.",
            ],
        ),
        (
            "Refunds",
            [
                "We refund the item price, including the original shipping cost if you return the entire order. The refund goes to "
                "the original payment method within 5 working days after we receive the return.",
                "If you cancel an order before it has shipped, you get a full refund straight away and don't have to return anything.",
            ],
        ),
        (
            "Damaged, wrong or misprinted items",
            [
                "If an item arrives damaged, you received the wrong club or size, or the name or number is printed wrongly, report "
                "it within 14 days of delivery. Include your order number and a photo. We send a free replacement or reprint, or "
                "give a full refund, whichever you prefer. You don't need to send the item back unless we ask for it.",
            ],
        ),
    ],
    "Shipping and Delivery.pdf": [
        (
            "Shipping and Delivery",
            [
                "This page explains when orders are shipped, which carriers we use, what shipping costs and what to do if a parcel "
                "is late or lost.",
            ],
        ),
        (
            "Where we deliver",
            [
                "We deliver to the Netherlands, Belgium, Luxembourg, Germany, France, Austria, Denmark, Spain, Ireland, Italy and "
                "Portugal. We don't ship outside the European Union.",
            ],
        ),
        (
            "Shipping costs",
            [
                "Standard shipping is free for orders of EUR 50 or more. For smaller orders it costs EUR 4.95 in the Netherlands, "
                "Belgium and Luxembourg and EUR 9.95 elsewhere in the EU.",
                "Express delivery costs EUR 7.50 extra, also on orders above EUR 50, and is only available in the Netherlands and Belgium.",
            ],
        ),
        (
            "Delivery times",
            [
                "Paid orders are packed and shipped within one working day, printed shirts included. Standard delivery takes 1 to 3 "
                "working days in the Netherlands, Belgium and Luxembourg and 3 to 7 working days elsewhere in the EU. Express "
                "delivery arrives the next working day.",
            ],
        ),
        (
            "Carriers and tracking",
            [
                "Parcels to the Netherlands go with PostNL, to Belgium and Luxembourg with bpost, to Germany with DHL, and to other "
                "countries with DPD or UPS. As soon as your order ships, its status changes to shipped and you get the carrier and "
                "a tracking number. You can also ask the assistant for the status of your order at any time.",
            ],
        ),
        (
            "Changing or cancelling an order",
            [
                "While an order is pending or processing, it hasn't shipped yet and you can still cancel it on the order page or by "
                "asking the assistant. Once it has shipped it can't be cancelled; you can return unprinted items after delivery.",
            ],
        ),
        (
            "Late or lost parcels",
            [
                "Tracking can sometimes go a day or two without an update. If the tracking hasn't changed for 5 working days, open a "
                "support ticket with your order number and we start an investigation with the carrier. If the parcel is confirmed "
                "lost, we send a replacement at no cost or refund the order in full.",
            ],
        ),
    ],
    "Size Guide.pdf": [
        (
            "Size Guide",
            [
                "How our shirts fit and which size to choose. Measure your chest at the widest point, under the arms.",
            ],
        ),
        (
            "Adult shirts",
            [
                "S fits a chest of 88 to 94 cm, M 94 to 100 cm, L 100 to 106 cm, XL 106 to 112 cm and XXL 112 to 120 cm.",
                "Home and away shirts have a regular fit: take your usual size, or one size up if you like a looser fit or want to "
                "wear something underneath. Between two sizes? Choose the larger one.",
            ],
        ),
        (
            "Retro shirts",
            [
                "Retro shirts are remakes of classic shirts and have a wider, boxier fit, like shirts from that era. Most people take "
                "their usual size or one size down.",
            ],
        ),
        (
            "Training tops",
            [
                "Training tops have a slim, athletic fit. Take one size up if you prefer a relaxed fit.",
            ],
        ),
        (
            "Kids kits",
            [
                "Kids kits are sized by height in cm: 116 (about 6 years), 128 (about 8 years), 140 (about 10 years), 152 (about "
                "12 years) and 164 (about 14 years). If your child is between two sizes, take the larger one.",
            ],
        ),
        (
            "Accessories",
            [
                "Grip socks: S fits shoe size EU 36 to 39, M 40 to 43 and L 44 to 47. Goalkeeper gloves come in sizes 7 to 10, which "
                "is the hand circumference in inches. Shin guards: S up to 140 cm body height, M 140 to 170 cm, L above 170 cm.",
            ],
        ),
    ],
    "Shirt Printing.pdf": [
        (
            "Shirt Printing",
            [
                "You can have a name and a number printed on the back of home, away, retro and kids shirts.",
            ],
        ),
        (
            "What can be printed",
            [
                "A name of up to 12 characters (letters, spaces, dots, hyphens and apostrophes) and a number from 0 to 99. You can "
                "choose a name, a number or both. Names are printed in capitals in the club's official lettering colours.",
                "Training tops, scarves and accessories can't be printed.",
            ],
        ),
        (
            "Price and delivery",
            [
                "Printing costs EUR 15.00 per shirt, whether you choose a name, a number or both. Printed shirts are made in our "
                "own workshop and ship within the same time as other orders.",
            ],
        ),
        (
            "Mistakes in the print",
            [
                "We print exactly what you typed, so check it before you order. If we made a mistake, or the print peels or cracks "
                "within 6 months, we reprint the shirt for free. Report it with your order number and a photo.",
                "A printed shirt can't be returned for a refund unless the print is wrong or the shirt is damaged.",
            ],
        ),
        (
            "Washing printed shirts",
            [
                "Wash printed shirts inside out at 30 degrees, don't use a tumble dryer and never iron the print.",
            ],
        ),
    ],
    "Payment FAQ.pdf": [
        (
            "Payment FAQ",
            [
                "Answers to common questions about paying for your order, invoices and refunds.",
            ],
        ),
        (
            "Which payment methods do you accept?",
            [
                "You can pay with iDEAL, Bancontact, credit card or PayPal. All prices are in euros (EUR) and include VAT.",
            ],
        ),
        (
            "When do I pay?",
            [
                "You pay right after placing your order. Until the payment is approved the order stays pending and the items are "
                "reserved for you. If you don't complete the payment, the order is cancelled automatically and the items go back "
                "into stock.",
            ],
        ),
        (
            "My payment was declined. What now?",
            [
                "Open the order on your order page and choose Pay now to try again, with the same or another payment method. Your "
                "items stay reserved while the order is pending.",
            ],
        ),
        (
            "Can I get an invoice with my company's VAT number?",
            [
                "Yes. Open a support ticket with your order number and your company name and VAT number, and we send a corrected "
                "invoice within 2 working days. Clubs and teams ordering several shirts can ask for one invoice for the whole order.",
            ],
        ),
        (
            "When will I get my refund?",
            [
                "Refunds go back to the payment method you used. A cancelled order that was paid is refunded straight away. A "
                "return is refunded within 5 working days after we receive it. Depending on your bank it can take another 2 to 3 "
                "days before the money shows up on your account.",
            ],
        ),
    ],
    "Product Care.pdf": [
        (
            "Product Care",
            [
                "What our products are made of and how to keep them looking good.",
            ],
        ),
        (
            "Shirts",
            [
                "Home, away and kids shirts are made of lightweight recycled polyester with a breathable mesh back and an embroidered "
                "crest. Retro shirts are made of a heavier cotton blend.",
                "Wash inside out at 30 degrees with similar colours. Don't use bleach or fabric softener, don't tumble dry and don't "
                "iron the crest or the print.",
            ],
        ),
        (
            "Training tops",
            [
                "Quarter-zip training tops have a soft brushed inside. Close the zip before washing and wash at 30 degrees.",
            ],
        ),
        (
            "Scarves",
            [
                "Knitted scarves measure 140 x 18 cm. Wash them by hand in cold water and let them dry flat.",
            ],
        ),
        (
            "Balls and gloves",
            [
                "Match and training balls are size 5 and are delivered inflated. Keep them at a pressure of 0.8 bar. Rinse goalkeeper "
                "gloves in lukewarm water after use and let them dry away from a heater.",
            ],
        ),
    ],
}


def build(filename: str, sections: list[tuple[str, list[str]]]) -> None:
    pdf = FPDF(format="A4")
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.set_title(filename.removesuffix(".pdf"))
    pdf.set_author("Invixta")
    pdf.add_page()
    title, intro = sections[0]
    pdf.set_font("Helvetica", "B", 20)
    pdf.cell(0, 12, title, new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 11)
    for paragraph in intro:
        pdf.multi_cell(0, 6, paragraph, new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2)
    for heading, paragraphs in sections[1:]:
        pdf.ln(4)
        pdf.set_font("Helvetica", "B", 13)
        pdf.cell(0, 8, heading, new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 11)
        for paragraph in paragraphs:
            pdf.multi_cell(0, 6, paragraph, new_x="LMARGIN", new_y="NEXT")
            pdf.ln(2)
    OUT.mkdir(exist_ok=True)
    pdf.output(str(OUT / filename))


if __name__ == "__main__":
    for old in OUT.glob("*.pdf"):
        if old.name not in DOCUMENTS:
            old.unlink()  # documents of an older version of the shop
    for name, content in DOCUMENTS.items():
        build(name, content)
        print(f"wrote {OUT / name}")
