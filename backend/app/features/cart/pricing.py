"""Pure pricing engine — no DB, no framework. Integer minor units (paise) only.

Kept pure so it is unit-testable in isolation and has a single, auditable source of
truth for money math. The service layer hydrates these dataclasses from the DB.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class CouponType(str, Enum):
    percentage = "percentage"
    fixed = "fixed"
    free_delivery = "free_delivery"


@dataclass
class LineItem:
    unit_price: int          # variant price, minor units
    quantity: int
    addons_total: int = 0    # per-unit addon total, minor units
    tax_bps: int = 0         # tax rate in basis points (500 = 5%)

    @property
    def line_subtotal(self) -> int:
        return (self.unit_price + self.addons_total) * self.quantity

    @property
    def line_tax(self) -> int:
        return self.line_subtotal * self.tax_bps // 10_000


@dataclass
class CouponSpec:
    type: CouponType
    value: int               # percentage→bps, fixed→minor units
    min_order: int = 0
    max_discount: int | None = None


@dataclass
class PricingInput:
    items: list[LineItem]
    coupon: CouponSpec | None = None
    membership_discount_bps: int = 0
    membership_free_delivery: bool = False
    base_shipping: int = 0
    free_above: int | None = None      # free shipping threshold
    tip: int = 0
    wallet_balance: int = 0
    use_wallet: bool = False


@dataclass
class PricingBreakdown:
    subtotal: int = 0
    discount_total: int = 0
    membership_discount: int = 0
    tax_total: int = 0
    shipping_total: int = 0
    tip_amount: int = 0
    wallet_applied: int = 0
    grand_total: int = 0
    coupon_applied: bool = False
    coupon_error: str | None = None
    notes: list[str] = field(default_factory=list)


def compute(inp: PricingInput) -> PricingBreakdown:
    b = PricingBreakdown(tip_amount=max(inp.tip, 0))
    b.subtotal = sum(i.line_subtotal for i in inp.items)

    # ---- coupon ----
    free_delivery = inp.membership_free_delivery
    if inp.coupon is not None:
        c = inp.coupon
        if b.subtotal < c.min_order:
            b.coupon_error = "min_order_not_met"
        elif c.type is CouponType.percentage:
            disc = b.subtotal * c.value // 10_000
            if c.max_discount is not None:
                disc = min(disc, c.max_discount)
            b.discount_total = disc
            b.coupon_applied = True
        elif c.type is CouponType.fixed:
            b.discount_total = min(c.value, b.subtotal)
            b.coupon_applied = True
        elif c.type is CouponType.free_delivery:
            free_delivery = True
            b.coupon_applied = True

    # ---- membership discount (on subtotal) ----
    if inp.membership_discount_bps:
        b.membership_discount = (b.subtotal - b.discount_total) * inp.membership_discount_bps // 10_000

    # ---- tax (per-line, on line subtotals) ----
    b.tax_total = sum(i.line_tax for i in inp.items)

    # ---- shipping ----
    if free_delivery:
        b.shipping_total = 0
    elif inp.free_above is not None and b.subtotal >= inp.free_above:
        b.shipping_total = 0
        b.notes.append("free_shipping_threshold_met")
    else:
        b.shipping_total = max(inp.base_shipping, 0)

    # ---- total before wallet ----
    total = (
        b.subtotal
        - b.discount_total
        - b.membership_discount
        + b.tax_total
        + b.shipping_total
        + b.tip_amount
    )
    total = max(total, 0)

    # ---- wallet ----
    if inp.use_wallet and inp.wallet_balance > 0:
        b.wallet_applied = min(inp.wallet_balance, total)

    b.grand_total = total - b.wallet_applied
    return b
