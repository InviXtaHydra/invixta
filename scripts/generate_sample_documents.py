"""Generate the demo knowledge-base PDFs in sample_documents/.

    docker compose run --rm -v ./sample_documents:/app/sample_documents backend python scripts/generate_sample_documents.py

The policies match the seed data (carriers, products), so the AI agent's answers line up with the
orders in the database. The text lives here, readable in Git; the PDFs are generated from it.
"""

from pathlib import Path

from fpdf import FPDF

OUT = Path(__file__).resolve().parent.parent / "sample_documents"

DOCUMENTS: dict[str, list[tuple[str, list[str]]]] = {
    "Return Policy.pdf": [
        (
            "Return Policy",
            [
                "This policy explains how to return a product bought from SupportAI Store and how refunds work. It applies to all "
                "orders delivered in the Netherlands, Belgium and the rest of the European Union.",
            ],
        ),
        (
            "Return window",
            [
                "You can return most products within 30 days after delivery, without giving a reason. The 30 days start on the "
                "day the parcel is delivered, as shown in the carrier's tracking.",
                "Products must be unused, complete and in their original packaging. Items that show signs of use can be refused "
                "or refunded partially.",
            ],
        ),
        (
            "Items that can't be returned",
            [
                "For hygiene reasons, bed linen (such as the Terra Linen Bed Sheet Set) and yoga mats can only be returned if the "
                "original seal is unbroken. Gift cards can't be returned.",
            ],
        ),
        (
            "How to return a product",
            [
                "1. Open a support ticket or ask the assistant to start a return, and mention your order number.",
                "2. You receive a free return label by email within one working day. Returns within the Netherlands go with "
                "PostNL, returns within Belgium with bpost. Customers in other EU countries pay the return shipping themselves.",
                "3. Pack the product securely and hand the parcel in at a drop-off point within 14 days of receiving the label.",
            ],
        ),
        (
            "Refunds",
            [
                "We refund the full product price, including the original shipping cost if you return the entire order. The "
                "refund is made to the original payment method within 5 working days after we receive the return.",
                "If you cancel an order before it has shipped, you get a full refund within 3 to 5 working days and don't have to "
                "return anything.",
            ],
        ),
        (
            "Damaged or wrong items",
            [
                "If a product arrives damaged or you received the wrong item, report it within 48 hours of delivery. Include your "
                "order number and photos of the product and the packaging. We then send a free replacement or give a full "
                "refund, whichever you prefer. You don't need to send damaged items back unless we ask for it.",
            ],
        ),
    ],
    "Shipping Policy.pdf": [
        (
            "Shipping Policy",
            [
                "This page explains how and when orders are shipped, which carriers we use and what to do if a parcel is late or lost.",
            ],
        ),
        (
            "Processing time",
            [
                "Orders placed on a working day before 15:00 are processed the same day. Other orders are processed within 1 to 2 "
                "working days. While an order is pending or processing you can still change the delivery address or cancel it.",
            ],
        ),
        (
            "Carriers and delivery times",
            [
                "We ship with PostNL, DHL, bpost, UPS and DPD. The carrier is chosen automatically based on the destination and "
                "the size of the parcel.",
                "Delivery in the Netherlands and Belgium takes 1 to 3 working days after shipping. Delivery elsewhere in the EU "
                "takes 3 to 7 working days. We currently don't ship outside the European Union.",
            ],
        ),
        (
            "Shipping costs",
            [
                "Shipping is free for orders of EUR 50 or more. For smaller orders the shipping cost is EUR 4.95 in the "
                "Netherlands and Belgium and EUR 9.95 elsewhere in the EU.",
            ],
        ),
        (
            "Tracking your order",
            [
                "As soon as your order ships, its status changes to shipped and you receive an email with the carrier and a "
                "tracking number. You can also ask the assistant for the status of your order at any time.",
            ],
        ),
        (
            "Late or lost parcels",
            [
                "Tracking can sometimes go a day or two without an update. If the tracking hasn't changed for 5 working days, "
                "open a support ticket with your order number and we will start an investigation with the carrier. If the "
                "parcel is confirmed lost, we send a replacement at no cost or refund the order in full.",
            ],
        ),
    ],
    "Warranty.pdf": [
        (
            "Warranty",
            [
                "All products sold by SupportAI Store come with a 2-year warranty from the date of delivery, in line with EU "
                "consumer law. The warranty covers manufacturing defects and products that stop working under normal use.",
            ],
        ),
        (
            "Extended warranty",
            [
                "The Lumen Smart Desk Lamp has a 3-year warranty on its LED module. The Aurora Wireless Headphones and the Pixel "
                "Mechanical Keyboard have a 2-year warranty; their rechargeable batteries are covered for 1 year, because battery "
                "capacity naturally decreases with use.",
            ],
        ),
        (
            "What isn't covered",
            [
                "The warranty doesn't cover damage caused by accidents, drops, water or other liquids, incorrect use, normal "
                "wear and tear, or repairs carried out by anyone other than us or the manufacturer.",
            ],
        ),
        (
            "How to make a warranty claim",
            [
                "Open a support ticket with your order number, a description of the problem and, if possible, a photo or video. "
                "Our support team replies within 2 working days. Depending on the problem we repair the product, replace it, or "
                "refund it if repair or replacement isn't possible. Shipping for warranty claims is free.",
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
                "You can pay with iDEAL, Bancontact, Visa, Mastercard, PayPal and Klarna. With Klarna you can choose to pay "
                "within 30 days after delivery. All prices are in euros (EUR) and include VAT.",
            ],
        ),
        (
            "When is my payment charged?",
            [
                "Payment is charged when you place the order. If a payment fails, the order stays pending for 48 hours so you "
                "can try again; after that it is cancelled automatically.",
            ],
        ),
        (
            "Can I get an invoice with my company's VAT number?",
            [
                "Yes. Every order comes with an invoice by email. If you need an invoice that shows your company name and VAT "
                "number, open a support ticket with your order number and the company details, and we will send a corrected "
                "invoice within 2 working days.",
            ],
        ),
        (
            "When will I receive my refund?",
            [
                "Refunds go back to the payment method you used. They are processed within 5 working days after we receive a "
                "return, or within 3 to 5 working days after you cancel an order that hasn't shipped. Depending on your bank "
                "it can take another 2 to 3 days before the money shows up on your account.",
            ],
        ),
        (
            "Is my payment information safe?",
            [
                "We never see or store your full card details. Payments are handled by a certified payment provider that "
                "complies with the PCI DSS security standard.",
            ],
        ),
    ],
    "Product Information.pdf": [
        (
            "Product Information",
            [
                "Details, specifications and care instructions for the products in our range.",
            ],
        ),
        (
            "Aurora Wireless Headphones",
            [
                "Over-ear Bluetooth 5.3 headphones with active noise cancelling. The battery lasts up to 30 hours with noise "
                "cancelling on, and a 10-minute charge over USB-C gives about 5 hours of playback.",
                "Pairing: hold the power button for 5 seconds until the light flashes blue, then select Aurora in your device's "
                "Bluetooth settings. To reset, hold the power and volume-down buttons for 10 seconds.",
            ],
        ),
        (
            "Nordic Ceramic Mug Set",
            [
                "Four hand-glazed stoneware mugs of 350 ml each. Dishwasher and microwave safe. Because every mug is glazed by "
                "hand, small differences in colour are normal and not a defect.",
            ],
        ),
        (
            "TrailPro Hiking Backpack 28L",
            [
                "Water-resistant 28-litre daypack with a padded hip belt, a sleeve for laptops up to 15 inches and a rain cover "
                "stored in the bottom pocket. Clean with a damp cloth; don't put it in the washing machine.",
            ],
        ),
        (
            "Lumen Smart Desk Lamp",
            [
                "Dimmable LED desk lamp with five brightness levels, adjustable colour temperature from 2700 K to 6500 K and a "
                "USB-C port to charge your phone. The LED module has a 3-year warranty.",
            ],
        ),
        (
            "Barista Pour-Over Kettle",
            [
                "1-litre stainless-steel gooseneck kettle with a built-in thermometer. Suitable for gas, electric and induction "
                "hobs. Not suitable for the dishwasher.",
            ],
        ),
        (
            "FlexFit Yoga Mat",
            [
                "6 mm natural rubber mat, 183 x 61 cm, with a non-slip surface and a carrying strap. Wipe clean with water and "
                "mild soap. Natural rubber can smell slightly when new; this fades within a few days.",
            ],
        ),
        (
            "Pixel Mechanical Keyboard",
            [
                "Compact 75% layout with hot-swappable switches, connecting over Bluetooth, 2.4 GHz or USB-C. Available in "
                "black and white. Works with Windows, macOS, Linux, iOS and Android. The battery lasts about 4 weeks with the "
                "backlight off.",
            ],
        ),
        (
            "Terra Linen Bed Sheet Set",
            [
                "Stonewashed 100% linen set for a double bed: one fitted sheet (160 x 200 cm), one flat sheet and two "
                "pillowcases. Wash at 40 degrees and tumble dry on low; linen gets softer with every wash.",
            ],
        ),
        (
            "Volt 20,000 mAh Power Bank",
            [
                "20,000 mAh power bank with 65 W USB-C Power Delivery, enough to charge most laptops. It can charge two devices "
                "at the same time. Allowed in hand luggage on flights.",
            ],
        ),
        (
            "Cedar Wood Cutting Board",
            [
                "End-grain cedar board of 40 x 28 cm with a juice groove. Wash by hand and oil it once a month with food-safe "
                "mineral oil. Never put it in the dishwasher.",
            ],
        ),
    ],
}


def build(filename: str, sections: list[tuple[str, list[str]]]) -> None:
    pdf = FPDF(format="A4")
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.set_title(filename.removesuffix(".pdf"))
    pdf.set_author("SupportAI Store")
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
    for name, content in DOCUMENTS.items():
        build(name, content)
        print(f"wrote {OUT / name}")
