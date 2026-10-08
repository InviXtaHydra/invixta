"""web shop: teams, product variants, carts, payments and checkout fields on orders

Revision ID: c4d5e6f7a8b9
Revises: b3c1d2e4f5a6
Create Date: 2026-10-08 13:00:00

Existing data is kept: old products get a slug and an "accessory" category, their stock moves into a
"One size" variant, and existing orders get their subtotal, item names and payment status filled in.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "c4d5e6f7a8b9"
down_revision: str | None = "b3c1d2e4f5a6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

product_category = postgresql.ENUM("home", "away", "retro", "training", "kids", "accessory", name="product_category", create_type=False)
shipping_method = postgresql.ENUM("standard", "express", name="shipping_method", create_type=False)
payment_method = postgresql.ENUM("ideal", "bancontact", "card", "paypal", name="payment_method", create_type=False)
payment_status = postgresql.ENUM("pending", "paid", "failed", "refunded", name="payment_status", create_type=False)
ENUMS = [product_category, shipping_method, payment_method, payment_status]


def upgrade() -> None:
    bind = op.get_bind()
    for enum in ENUMS:
        enum.create(bind, checkfirst=True)

    op.create_table(
        "teams",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("slug", sa.String(length=80), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("short_name", sa.String(length=12), nullable=False),
        sa.Column("league", sa.String(length=80), nullable=False),
        sa.Column("city", sa.String(length=80), nullable=False),
        sa.Column("founded", sa.Integer(), nullable=False),
        sa.Column("primary_color", sa.String(length=7), nullable=False),
        sa.Column("secondary_color", sa.String(length=7), nullable=False),
        sa.Column("pattern", sa.String(length=20), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug", name="uq_teams_slug"),
    )
    op.create_index("ix_teams_league", "teams", ["league"])

    # --- products: catalogue fields; stock moves to the variants ---------------------------------
    op.add_column("products", sa.Column("slug", sa.String(length=120), nullable=True))
    op.add_column("products", sa.Column("category", product_category, nullable=True))
    op.add_column("products", sa.Column("team_id", sa.Integer(), nullable=True))
    op.add_column("products", sa.Column("season", sa.String(length=10), nullable=True))
    op.add_column("products", sa.Column("compare_at_price", sa.Numeric(precision=10, scale=2), nullable=True))
    op.add_column("products", sa.Column("personalizable", sa.Boolean(), server_default=sa.false(), nullable=False))
    op.add_column("products", sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False))
    op.add_column("products", sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False))
    op.execute("UPDATE products SET slug = 'product-' || id, category = 'accessory'")
    op.alter_column("products", "slug", nullable=False)
    op.alter_column("products", "category", nullable=False)
    op.create_unique_constraint("uq_products_slug", "products", ["slug"])
    op.create_index("ix_products_category", "products", ["category"])
    op.create_index("ix_products_team_id", "products", ["team_id"])
    op.create_foreign_key("fk_products_team_id_teams", "products", "teams", ["team_id"], ["id"], ondelete="SET NULL")
    op.create_check_constraint("ck_products_compare_at_above_price", "products", "compare_at_price IS NULL OR compare_at_price > price")

    op.create_table(
        "product_variants",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("size", sa.String(length=12), nullable=False),
        sa.Column("sku", sa.String(length=40), nullable=False),
        sa.Column("stock", sa.Integer(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.CheckConstraint("stock >= 0", name="ck_product_variants_stock_non_negative"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("product_id", "size", name="uq_product_variants_product_size"),
        sa.UniqueConstraint("sku", name="uq_product_variants_sku"),
    )
    op.create_index("ix_product_variants_product_id", "product_variants", ["product_id"])
    op.execute(
        "INSERT INTO product_variants (product_id, size, sku, stock, position) SELECT id, 'One size', 'SKU-' || id, stock, 0 FROM products"
    )
    op.drop_constraint("ck_products_stock_non_negative", "products", type_="check")
    op.drop_column("products", "stock")

    # --- carts --------------------------------------------------------------------------------
    op.create_table(
        "carts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("token", sa.String(length=64), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token", name="uq_carts_token"),
        sa.UniqueConstraint("user_id", name="uq_carts_user_id"),
    )
    op.create_table(
        "cart_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("cart_id", sa.Integer(), nullable=False),
        sa.Column("variant_id", sa.Integer(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("personalization_name", sa.String(length=12), nullable=True),
        sa.Column("personalization_number", sa.Integer(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("personalization_number IS NULL OR personalization_number BETWEEN 0 AND 99", name="ck_cart_items_number_range"),
        sa.CheckConstraint("quantity BETWEEN 1 AND 10", name="ck_cart_items_quantity_range"),
        sa.ForeignKeyConstraint(["cart_id"], ["carts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["variant_id"], ["product_variants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_cart_items_cart_id", "cart_items", ["cart_id"])

    # --- orders: prices, address, shipping, payment, timeline -----------------------------------
    op.add_column("orders", sa.Column("subtotal", sa.Numeric(precision=10, scale=2), server_default="0", nullable=False))
    op.add_column("orders", sa.Column("shipping_cost", sa.Numeric(precision=10, scale=2), server_default="0", nullable=False))
    for column, length in [
        ("shipping_name", 120),
        ("shipping_street", 200),
        ("shipping_postcode", 16),
        ("shipping_city", 80),
        ("shipping_country", 2),
    ]:
        op.add_column("orders", sa.Column(column, sa.String(length=length), nullable=True))
    op.add_column("orders", sa.Column("shipping_method", shipping_method, server_default="standard", nullable=False))
    op.add_column("orders", sa.Column("payment_method", payment_method, nullable=True))
    op.add_column("orders", sa.Column("payment_status", payment_status, server_default="pending", nullable=False))
    for column in ["paid_at", "shipped_at", "delivered_at", "cancelled_at"]:
        op.add_column("orders", sa.Column(column, sa.DateTime(timezone=True), nullable=True))
    op.execute("UPDATE orders SET subtotal = total_amount")
    op.execute("UPDATE orders SET payment_status = 'paid', paid_at = created_at WHERE status IN ('processing', 'shipped', 'delivered')")

    op.add_column("order_items", sa.Column("variant_id", sa.Integer(), nullable=True))
    op.add_column("order_items", sa.Column("product_name", sa.String(length=200), server_default="", nullable=False))
    op.add_column("order_items", sa.Column("size", sa.String(length=12), nullable=True))
    op.add_column("order_items", sa.Column("personalization_name", sa.String(length=12), nullable=True))
    op.add_column("order_items", sa.Column("personalization_number", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_order_items_variant_id_product_variants", "order_items", "product_variants", ["variant_id"], ["id"], ondelete="SET NULL"
    )
    op.execute("UPDATE order_items SET product_name = products.name FROM products WHERE products.id = order_items.product_id")

    op.create_table(
        "payments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("order_id", sa.Integer(), nullable=False),
        sa.Column("amount", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("method", payment_method, nullable=False),
        sa.Column("status", payment_status, nullable=False),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_payments_order_id", "payments", ["order_id"])


def downgrade() -> None:
    op.drop_table("payments")
    op.drop_constraint("fk_order_items_variant_id_product_variants", "order_items", type_="foreignkey")
    for column in ["personalization_number", "personalization_name", "size", "product_name", "variant_id"]:
        op.drop_column("order_items", column)
    for column in [
        "cancelled_at", "delivered_at", "shipped_at", "paid_at", "payment_status", "payment_method", "shipping_method",
        "shipping_country", "shipping_city", "shipping_postcode", "shipping_street", "shipping_name", "shipping_cost", "subtotal",
    ]:  # fmt: skip
        op.drop_column("orders", column)
    op.drop_table("cart_items")
    op.drop_table("carts")

    op.add_column("products", sa.Column("stock", sa.Integer(), server_default="0", nullable=False))
    op.execute("UPDATE products SET stock = COALESCE((SELECT SUM(stock) FROM product_variants v WHERE v.product_id = products.id), 0)")
    op.create_check_constraint("ck_products_stock_non_negative", "products", "stock >= 0")
    op.drop_table("product_variants")
    op.drop_constraint("ck_products_compare_at_above_price", "products", type_="check")
    op.drop_constraint("fk_products_team_id_teams", "products", type_="foreignkey")
    op.drop_constraint("uq_products_slug", "products", type_="unique")
    op.drop_index("ix_products_team_id", table_name="products")
    op.drop_index("ix_products_category", table_name="products")
    for column in ["created_at", "is_active", "personalizable", "compare_at_price", "season", "team_id", "category", "slug"]:
        op.drop_column("products", column)
    op.drop_table("teams")
    bind = op.get_bind()
    for enum in ENUMS:
        enum.drop(bind, checkfirst=True)
