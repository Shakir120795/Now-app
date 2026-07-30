"""Pricing engine unit tests (pure, no DB). Run: pytest -q."""
from app.features.cart.pricing import (
    CouponSpec,
    CouponType,
    LineItem,
    PricingInput,
    compute,
)


def test_base_subtotal_tax_shipping():
    b = compute(PricingInput(items=[
        LineItem(unit_price=29900, quantity=2, addons_total=5000, tax_bps=500),
        LineItem(unit_price=19900, quantity=1, tax_bps=500),
    ], base_shipping=4000))
    assert b.subtotal == 89700
    assert b.tax_total == 4485
    assert b.shipping_total == 4000
    assert b.grand_total == 89700 + 4485 + 4000


def test_percentage_coupon_capped():
    b = compute(PricingInput(
        items=[LineItem(unit_price=100000, quantity=1, tax_bps=500)],
        coupon=CouponSpec(CouponType.percentage, value=1000, min_order=50000, max_discount=10000),
        base_shipping=4000,
    ))
    assert b.discount_total == 10000 and b.coupon_applied


def test_coupon_min_order_guard():
    b = compute(PricingInput(
        items=[LineItem(unit_price=10000, quantity=1)],
        coupon=CouponSpec(CouponType.fixed, value=5000, min_order=50000),
    ))
    assert not b.coupon_applied and b.coupon_error == "min_order_not_met"


def test_free_delivery_coupon():
    b = compute(PricingInput(
        items=[LineItem(unit_price=20000, quantity=1)],
        coupon=CouponSpec(CouponType.free_delivery, value=0), base_shipping=4000,
    ))
    assert b.shipping_total == 0 and b.coupon_applied


def test_free_above_threshold():
    b = compute(PricingInput(
        items=[LineItem(unit_price=60000, quantity=1)], base_shipping=4000, free_above=49900,
    ))
    assert b.shipping_total == 0


def test_membership_wallet_tip():
    b = compute(PricingInput(
        items=[LineItem(unit_price=100000, quantity=1)],
        membership_discount_bps=1000, membership_free_delivery=True,
        base_shipping=4000, wallet_balance=5000, use_wallet=True, tip=2000,
    ))
    assert b.membership_discount == 10000
    assert b.shipping_total == 0
    assert b.wallet_applied == 5000
    assert b.grand_total == 87000


def test_wallet_capped_at_total():
    b = compute(PricingInput(
        items=[LineItem(unit_price=1000, quantity=1)], wallet_balance=999999, use_wallet=True,
    ))
    assert b.wallet_applied == 1000 and b.grand_total == 0
